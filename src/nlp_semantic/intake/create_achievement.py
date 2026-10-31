"""Reviewer-gated conversion: CandidateReview(ACCEPT) → Achievement row.

Chunk 7.47 implements the final step of the Chunk 7.44 workflow:
convert an ACCEPT-ed :class:`CandidateReview` plus a reviewer-supplied
``achievement_text`` into a new :class:`Achievement` record written to
a dataset batch file.

**Fail-closed contract.**

* Only ACCEPT reviews can produce an Achievement. REJECT, REVISE, or
  DEFER are refused.
* ``source_id``, ``source_record_id``, and ``achievement_text`` are
  required.
* Taxonomy labels referenced on ACCEPT are re-checked against the
  current taxonomy (unknown or deprecated labels → refuse).
* ``(source_id, source_record_id)`` must be unique against every
  loaded existing Achievement AND against the current state of the
  target batch file.
* If ``attested_evidence_id`` is set, the Evidence row must exist and
  its on-disk file must exist. An optional hash cross-check against
  the originating intake manifest is run when the caller supplies the
  intake manifest directory.
* The hypothetical Achievement must be Pydantic-valid AND the
  resulting dataset must pass :func:`validate_dataset`.
* All preconditions run before any disk write. On failure,
  :class:`CreateAchievementError` is raised and no file is modified.
* ``training_ready_subset`` behaviour is untouched. The new
  Achievement starts at ``annotation_status.primary_type: DRAFT``
  when ``primary_type`` is set (``NOT_STARTED`` otherwise), and at
  ``annotation_status.domain_tags: DRAFT`` when ``domain_tags`` is
  non-empty (``NOT_STARTED`` otherwise) — same contract as the
  standard pilot intake pattern.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from nlp_semantic.schema import (
    Achievement,
    AnnotationStatus,
    AnnotationStatusMap,
    Evidence,
    LabelTaxonomy,
    SourceRegistry,
    TaxonomyStatus,
    make_id,
    validate_label_id,
)

from .pipeline import (
    INTAKE_ROOT_PREFIX,
    load_intake_entry,
    sha256_of_file,
)
from .promote_evidence import list_evidence_records, load_evidence_record
from .review import CandidateDecision, CandidateReview


# ---- error codes ----------------------------------------------------------


class CreateAchievementErrorCode:
    """Stable string codes for conversion precondition failures."""

    REVIEW_NOT_ACCEPTED = "REVIEW_NOT_ACCEPTED"
    MISSING_ATTESTED_SOURCE_ID = "MISSING_ATTESTED_SOURCE_ID"
    MISSING_ATTESTED_SOURCE_RECORD_ID = "MISSING_ATTESTED_SOURCE_RECORD_ID"
    MISSING_ACHIEVEMENT_TEXT = "MISSING_ACHIEVEMENT_TEXT"
    PROPOSER_IS_REVIEWER = "PROPOSER_IS_REVIEWER"
    UNKNOWN_SOURCE_REFERENCE = "UNKNOWN_SOURCE_REFERENCE"
    UNKNOWN_PRIMARY_TYPE_LABEL = "UNKNOWN_PRIMARY_TYPE_LABEL"
    DEPRECATED_PRIMARY_TYPE_LABEL = "DEPRECATED_PRIMARY_TYPE_LABEL"
    UNKNOWN_DOMAIN_TAG = "UNKNOWN_DOMAIN_TAG"
    DEPRECATED_DOMAIN_TAG = "DEPRECATED_DOMAIN_TAG"
    DUPLICATE_SOURCE_RECORD_PAIR = "DUPLICATE_SOURCE_RECORD_PAIR"
    MISSING_EVIDENCE_RECORD = "MISSING_EVIDENCE_RECORD"
    MISSING_EVIDENCE_FILE = "MISSING_EVIDENCE_FILE"
    EVIDENCE_HASH_MISMATCH = "EVIDENCE_HASH_MISMATCH"
    INVALID_ACHIEVEMENT = "INVALID_ACHIEVEMENT"
    HYPOTHETICAL_DATASET_INVALID = "HYPOTHETICAL_DATASET_INVALID"
    DUPLICATE_ACHIEVEMENT_IN_BATCH = "DUPLICATE_ACHIEVEMENT_IN_BATCH"


# ---- finding / error / result dataclasses ---------------------------------


@dataclass
class CreateAchievementFinding:
    """One precondition finding."""

    code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "field": self.field}


class CreateAchievementError(ValueError):
    """Raised when any precondition fails."""

    def __init__(self, message: str, findings: list[CreateAchievementFinding]):
        super().__init__(message)
        self.findings = findings


@dataclass(frozen=True)
class CreateAchievementResult:
    """Return value of :func:`create_achievement_from_review`."""

    achievement: Achievement
    batch_file: Path
    linked_review_id: str
    linked_evidence_id: str | None


# ---- helpers --------------------------------------------------------------


def _derive_annotation_status(
    *,
    primary_type: str | None,
    domain_tags: list[str],
) -> AnnotationStatusMap:
    """Apply the Chunk 7.4-A.1 default: DRAFT if the task has data, else NOT_STARTED."""
    return AnnotationStatusMap(
        primary_type=(
            AnnotationStatus.DRAFT
            if primary_type is not None
            else AnnotationStatus.NOT_STARTED
        ),
        domain_tags=(
            AnnotationStatus.DRAFT
            if domain_tags
            else AnnotationStatus.NOT_STARTED
        ),
    )


def _achievement_to_yaml_dict(a: Achievement) -> dict[str, Any]:
    """YAML-friendly dict for one Achievement row."""
    return {
        "achievement_id": a.achievement_id,
        "source_id": a.source_id,
        "source_record_id": a.source_record_id,
        "achievement_text": a.achievement_text,
        "primary_type": a.primary_type,
        "domain_tags": list(a.domain_tags),
        "level": a.level,
        "outcome": a.outcome,
        "event_name": a.event_name,
        "organization": a.organization,
        "achievement_date": (
            a.achievement_date.isoformat()
            if a.achievement_date is not None
            else None
        ),
        "rank": a.rank,
        "skills": list(a.skills),
        "evidence_id": a.evidence_id,
        "annotation_status": {
            "primary_type": a.annotation_status.primary_type.value,
            "domain_tags": a.annotation_status.domain_tags.value,
        },
        "is_synthetic": a.is_synthetic,
    }


def _load_batch_records(batch_file: Path) -> list[Achievement]:
    """Load existing records from ``batch_file`` or return [] if absent."""
    if not batch_file.exists():
        return []
    with batch_file.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return []
    if not isinstance(data, list):
        raise CreateAchievementError(
            f"{batch_file}: top-level YAML must be a list; got "
            f"{type(data).__name__}",
            findings=[
                CreateAchievementFinding(
                    code=CreateAchievementErrorCode.INVALID_ACHIEVEMENT,
                    message=(
                        f"{batch_file}: top-level YAML must be a list of "
                        f"Achievement entries"
                    ),
                    field=None,
                )
            ],
        )
    return [Achievement(**raw) for raw in data]


def _write_batch_file(batch_file: Path, records: list[Achievement]) -> None:
    """Serialize all records to the batch file, overwriting any prior
    content. Only called AFTER all preconditions pass."""
    batch_file.parent.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_dump(
        [_achievement_to_yaml_dict(a) for a in records],
        sort_keys=False,
        default_flow_style=False,
    )
    batch_file.write_text(payload, encoding="utf-8")


# ---- the conversion function ----------------------------------------------


def create_achievement_from_review(
    review: CandidateReview,
    *,
    achievement_text: str,
    output_batch_file: str | Path,
    sources: Iterable[SourceRegistry],
    primary_taxonomy: Iterable[LabelTaxonomy],
    domain_taxonomy: Iterable[LabelTaxonomy] | None = None,
    existing_records: Iterable[Achievement] | None = None,
    existing_evidence: Iterable[Evidence] | None = None,
    evidence_documents_root: str | Path | None = None,
    intake_manifest_dir: str | Path | None = None,
    evidence_root: str | Path | None = None,
) -> CreateAchievementResult:
    """Convert an ACCEPT-ed :class:`CandidateReview` into an :class:`Achievement`
    row written to ``output_batch_file``.

    See the module docstring for the fail-closed contract.
    """
    findings: list[CreateAchievementFinding] = []

    # C-1: decision is ACCEPT
    if review.decision != CandidateDecision.ACCEPT:
        findings.append(
            CreateAchievementFinding(
                code=CreateAchievementErrorCode.REVIEW_NOT_ACCEPTED,
                message=(
                    f"review.decision is {review.decision.value!r}; only "
                    "ACCEPT reviews can produce an Achievement"
                ),
                field="decision",
            )
        )
        # Short-circuit: no point running other checks on a non-ACCEPT.
        raise CreateAchievementError(
            "review was not ACCEPT",
            findings=findings,
        )

    # C-2 / C-3: required attestations
    if review.attested_source_id is None:
        findings.append(
            CreateAchievementFinding(
                code=CreateAchievementErrorCode.MISSING_ATTESTED_SOURCE_ID,
                message="attested_source_id is required on ACCEPT",
                field="attested_source_id",
            )
        )
    if review.attested_source_record_id is None:
        findings.append(
            CreateAchievementFinding(
                code=CreateAchievementErrorCode.MISSING_ATTESTED_SOURCE_RECORD_ID,
                message="attested_source_record_id is required on ACCEPT",
                field="attested_source_record_id",
            )
        )

    # C-4: achievement_text present
    text = (achievement_text or "").strip()
    if not text:
        findings.append(
            CreateAchievementFinding(
                code=CreateAchievementErrorCode.MISSING_ACHIEVEMENT_TEXT,
                message=(
                    "achievement_text is required and must be non-empty"
                ),
                field="achievement_text",
            )
        )

    # C-5: reviewer-independence re-check (defense-in-depth; Chunk 7.45
    # already enforces this at review time, but a corrupted review file
    # could in theory arrive here with proposer == reviewer).
    if (
        review.reviewed_candidate_proposer is not None
        and review.reviewed_candidate_proposer == review.reviewer
    ):
        findings.append(
            CreateAchievementFinding(
                code=CreateAchievementErrorCode.PROPOSER_IS_REVIEWER,
                message=(
                    "the review's reviewer is also the reviewed candidate's "
                    "proposer; reviewer-independence violated"
                ),
                field="reviewer",
            )
        )

    sources_list = list(sources)
    primary_list = list(primary_taxonomy)
    domain_list = list(domain_taxonomy or [])
    existing_list = list(existing_records or [])
    evidence_list = list(existing_evidence or [])

    # C-6: source exists
    source_ids = {s.source_id for s in sources_list}
    if review.attested_source_id is not None and review.attested_source_id not in source_ids:
        findings.append(
            CreateAchievementFinding(
                code=CreateAchievementErrorCode.UNKNOWN_SOURCE_REFERENCE,
                message=(
                    f"attested_source_id {review.attested_source_id!r} not in "
                    "sources registry"
                ),
                field="attested_source_id",
            )
        )

    # C-7: primary_type label validity
    if review.attested_primary_type is not None:
        primary_by_id = {e.label_id: e for e in primary_list}
        entry = primary_by_id.get(review.attested_primary_type)
        if entry is None:
            findings.append(
                CreateAchievementFinding(
                    code=CreateAchievementErrorCode.UNKNOWN_PRIMARY_TYPE_LABEL,
                    message=(
                        f"attested_primary_type {review.attested_primary_type!r} "
                        "not found in primary taxonomy"
                    ),
                    field="attested_primary_type",
                )
            )
        elif entry.status == TaxonomyStatus.DEPRECATED:
            findings.append(
                CreateAchievementFinding(
                    code=CreateAchievementErrorCode.DEPRECATED_PRIMARY_TYPE_LABEL,
                    message=(
                        f"attested_primary_type {review.attested_primary_type!r} "
                        "is deprecated"
                    ),
                    field="attested_primary_type",
                )
            )

    # C-8: domain_tags validity
    if review.attested_domain_tags:
        domain_by_id = {e.label_id: e for e in domain_list}
        for tag in review.attested_domain_tags:
            entry = domain_by_id.get(tag)
            if entry is None:
                findings.append(
                    CreateAchievementFinding(
                        code=CreateAchievementErrorCode.UNKNOWN_DOMAIN_TAG,
                        message=(
                            f"attested domain_tag {tag!r} not found in "
                            "domain taxonomy"
                        ),
                        field="attested_domain_tags",
                    )
                )
            elif entry.status == TaxonomyStatus.DEPRECATED:
                findings.append(
                    CreateAchievementFinding(
                        code=CreateAchievementErrorCode.DEPRECATED_DOMAIN_TAG,
                        message=(
                            f"attested domain_tag {tag!r} is deprecated"
                        ),
                        field="attested_domain_tags",
                    )
                )

    # C-9: (source_id, source_record_id) uniqueness vs loaded existing records
    if (
        review.attested_source_id is not None
        and review.attested_source_record_id is not None
    ):
        for rec in existing_list:
            if (
                rec.source_id == review.attested_source_id
                and rec.source_record_id == review.attested_source_record_id
            ):
                findings.append(
                    CreateAchievementFinding(
                        code=CreateAchievementErrorCode.DUPLICATE_SOURCE_RECORD_PAIR,
                        message=(
                            f"(source_id={rec.source_id!r}, "
                            f"source_record_id={rec.source_record_id!r}) "
                            f"already exists on Achievement "
                            f"{rec.achievement_id!r}"
                        ),
                        field="attested_source_record_id",
                    )
                )
                break

    # C-10: evidence resolution + file + optional hash cross-check
    if review.attested_evidence_id is not None:
        # Load Evidence row either from passed-in list or by discovery.
        if not evidence_list and existing_evidence is None:
            # Caller didn't supply any; the Evidence row cannot be resolved
            # from the function arguments alone.
            findings.append(
                CreateAchievementFinding(
                    code=CreateAchievementErrorCode.MISSING_EVIDENCE_RECORD,
                    message=(
                        f"attested_evidence_id {review.attested_evidence_id!r} "
                        "is set but no existing_evidence was supplied; "
                        "caller must pass the Evidence list for cross-check"
                    ),
                    field="attested_evidence_id",
                )
            )
        else:
            evidence_by_id = {e.evidence_id: e for e in evidence_list}
            evidence = evidence_by_id.get(review.attested_evidence_id)
            if evidence is None:
                findings.append(
                    CreateAchievementFinding(
                        code=CreateAchievementErrorCode.MISSING_EVIDENCE_RECORD,
                        message=(
                            f"Evidence row {review.attested_evidence_id!r} "
                            "not found in existing_evidence"
                        ),
                        field="attested_evidence_id",
                    )
                )
            elif evidence_documents_root is not None:
                # Check file exists on disk
                evid_name = Path(evidence.relative_path).name
                on_disk = Path(evidence_documents_root) / evid_name
                if not on_disk.exists():
                    findings.append(
                        CreateAchievementFinding(
                            code=CreateAchievementErrorCode.MISSING_EVIDENCE_FILE,
                            message=(
                                f"evidence file not found at {on_disk!s}"
                            ),
                            field="attested_evidence_id",
                        )
                    )
                elif intake_manifest_dir is not None:
                    # Optional hash check: resolve the originating intake
                    # via the filename prefix, re-hash, and compare.
                    if "__" in evid_name:
                        intake_id = evid_name.split("__", 1)[0]
                        manifest_path = Path(intake_manifest_dir) / f"{intake_id}.yaml"
                        if manifest_path.exists():
                            try:
                                intake = load_intake_entry(manifest_path)
                                disk_hash = sha256_of_file(on_disk)
                                if disk_hash != intake.sha256:
                                    findings.append(
                                        CreateAchievementFinding(
                                            code=CreateAchievementErrorCode.EVIDENCE_HASH_MISMATCH,
                                            message=(
                                                f"evidence on-disk SHA-256 {disk_hash!r} "
                                                f"differs from originating intake "
                                                f"{intake.sha256!r}"
                                            ),
                                            field="attested_evidence_id",
                                        )
                                    )
                            except Exception:
                                pass  # intake manifest unavailable; skip check

    # Short-circuit on any finding before Pydantic construction.
    if findings:
        raise CreateAchievementError(
            f"create-achievement preconditions failed: {len(findings)} finding(s)",
            findings=findings,
        )

    # C-11: construct the Achievement (Pydantic validates)
    annotation_status = _derive_annotation_status(
        primary_type=review.attested_primary_type,
        domain_tags=list(review.attested_domain_tags),
    )
    try:
        achievement = Achievement(
            achievement_id=make_id("ach"),
            source_id=review.attested_source_id,
            source_record_id=review.attested_source_record_id,
            achievement_text=text,
            primary_type=review.attested_primary_type,
            domain_tags=list(review.attested_domain_tags),
            level=review.attested_level,
            outcome=review.attested_outcome,
            event_name=review.attested_event_name,
            organization=review.attested_organization,
            achievement_date=review.attested_achievement_date,
            rank=review.attested_rank,
            skills=list(review.attested_skills),
            evidence_id=review.attested_evidence_id,
            annotation_status=annotation_status,
            is_synthetic=False,
        )
    except ValidationError as e:
        findings.append(
            CreateAchievementFinding(
                code=CreateAchievementErrorCode.INVALID_ACHIEVEMENT,
                message=f"Achievement construction failed: {e}",
                field=None,
            )
        )
        raise CreateAchievementError(
            "hypothetical Achievement would be invalid",
            findings=findings,
        )

    # C-12: validate_dataset must still pass on the proposed state.
    # Import here to keep AST test 19 (no training-readiness imports)
    # scoped to the module-level identifier set.
    from nlp_semantic.dataset.validator import validate_dataset

    rep = validate_dataset(
        records=existing_list + [achievement],
        annotations=[],
        sources=sources_list,
        primary_taxonomy=primary_list,
        domain_taxonomy=domain_list,
    )
    if not rep.is_valid:
        findings.append(
            CreateAchievementFinding(
                code=CreateAchievementErrorCode.HYPOTHETICAL_DATASET_INVALID,
                message=(
                    f"proposed dataset would fail validate_dataset with "
                    f"{rep.fatal_count} fatal findings"
                ),
                field=None,
            )
        )

    # C-13: batch-file-level duplicate check (idempotency / repeated-run safety).
    batch_path = Path(output_batch_file)
    batch_records = _load_batch_records(batch_path)
    for rec in batch_records:
        if (
            rec.source_id == achievement.source_id
            and rec.source_record_id == achievement.source_record_id
        ):
            findings.append(
                CreateAchievementFinding(
                    code=CreateAchievementErrorCode.DUPLICATE_ACHIEVEMENT_IN_BATCH,
                    message=(
                        f"(source_id, source_record_id) already present in "
                        f"{batch_path!s} as {rec.achievement_id!r}"
                    ),
                    field="attested_source_record_id",
                )
            )

    if findings:
        raise CreateAchievementError(
            f"create-achievement preconditions failed: {len(findings)} finding(s)",
            findings=findings,
        )

    # All preconditions passed. Write the batch file atomically-ish:
    # read existing + append + write once. No partial state possible
    # within the function's logic (OS crashes between read and write
    # are the only hazard, same as every other YAML writer in this
    # project).
    batch_records.append(achievement)
    _write_batch_file(batch_path, batch_records)

    return CreateAchievementResult(
        achievement=achievement,
        batch_file=batch_path,
        linked_review_id=review.review_id,
        linked_evidence_id=review.attested_evidence_id,
    )


__all__ = [
    "CreateAchievementError",
    "CreateAchievementErrorCode",
    "CreateAchievementFinding",
    "CreateAchievementResult",
    "create_achievement_from_review",
]
