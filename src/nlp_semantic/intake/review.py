"""Candidate review workflow — ACCEPT and REJECT decisions only.

Implements the Chunk 7.44 design for the ACCEPT and REJECT reviewer
decisions. REVISE and DEFER are deliberately deferred to a future
chunk.

**Fail-closed contract.**

* ``review_candidate`` runs every applicable precondition BEFORE
  writing any file. If any precondition fails, no file is written
  and :class:`CandidateReviewError` is raised with the specific
  failing codes.
* ACCEPT means "the reviewer attests the candidate is a genuine
  achievement with sufficient evidence to produce an Achievement
  in a later chunk." It does NOT mean: source approved, taxonomy
  approved, Evidence row created, Annotation verified, Achievement
  created, or training-eligible. All four conditions in
  :func:`nlp_semantic.dataset.validator.training_ready_subset`
  remain unchanged.
* Each decision is persisted as its own file at
  ``<output_dir>/<review_id>.yaml``. Append-only: a later
  decision does not overwrite an earlier one — it is a separate
  file with a different ``review_id``.
"""
from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from nlp_semantic.schema import (
    Achievement,
    AnnotationStatus,
    AnnotationStatusMap,
    LabelTaxonomy,
    SourceRegistry,
    TaxonomyStatus,
    validate_label_id,
    validate_prefixed_id,
)
from nlp_semantic.dataset.validator import validate_dataset

from .pipeline import (
    AchievementCandidate,
    IntakeEntry,
    load_intake_entry,
    sha256_of_file,
    validate_candidate_id,
    validate_intake_id,
)


# ---- enums & constants -----------------------------------------------------


class CandidateDecision(str, Enum):
    """ACCEPT and REJECT only. REVISE and DEFER are deferred."""

    ACCEPT = "accept"
    REJECT = "reject"


class ReviewErrorCode:
    """Stable string codes for precondition failures (P-1 … P-8)."""

    # P-2
    INTAKE_NOT_FOUND = "INTAKE_NOT_FOUND"
    HASH_MISMATCH_ON_DISK = "HASH_MISMATCH_ON_DISK"
    EVIDENCE_FILE_NOT_FOUND = "EVIDENCE_FILE_NOT_FOUND"

    # P-3
    MISSING_SOURCE_RECORD_ID = "MISSING_SOURCE_RECORD_ID"
    MISSING_SOURCE_ID = "MISSING_SOURCE_ID"

    # P-4
    DUPLICATE_SOURCE_RECORD_PAIR = "DUPLICATE_SOURCE_RECORD_PAIR"

    # P-5
    UNKNOWN_PRIMARY_TYPE_LABEL = "UNKNOWN_PRIMARY_TYPE_LABEL"
    DEPRECATED_PRIMARY_TYPE_LABEL = "DEPRECATED_PRIMARY_TYPE_LABEL"

    # P-6
    UNKNOWN_DOMAIN_TAG = "UNKNOWN_DOMAIN_TAG"
    DEPRECATED_DOMAIN_TAG = "DEPRECATED_DOMAIN_TAG"

    # P-7
    PROPOSER_IS_REVIEWER = "PROPOSER_IS_REVIEWER"

    # P-8
    HYPOTHETICAL_DATASET_INVALID = "HYPOTHETICAL_DATASET_INVALID"

    # Decision-level
    UNSUPPORTED_DECISION = "UNSUPPORTED_DECISION"
    REVIEW_ID_COLLISION = "REVIEW_ID_COLLISION"


_REVIEW_ID_RE = re.compile(r"^crev_[0-9a-f]{32}$")
_PSEUDONYM_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$")
_EMAIL_LIKE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---- ID helpers ------------------------------------------------------------


def make_review_id() -> str:
    """Allocate a fresh ``crev_<32-hex>`` id."""
    return f"crev_{uuid.uuid4().hex}"


def validate_review_id(value: str) -> str:
    """Validate a review id. Returns ``value`` unchanged on success."""
    if not isinstance(value, str) or not _REVIEW_ID_RE.fullmatch(value):
        raise ValueError(
            "review_id must match 'crev_' followed by 32 lowercase hex "
            f"chars; got {value!r}"
        )
    return value


def _validate_pseudonym(v: str) -> str:
    if _EMAIL_LIKE_RE.match(v):
        raise ValueError("pseudonym must not be an email")
    if not _PSEUDONYM_RE.fullmatch(v):
        raise ValueError(
            f"pseudonym {v!r} does not match the required pattern"
        )
    return v


# ---- Pydantic models -------------------------------------------------------


class ReviewFinding(BaseModel):
    """One precondition finding (always fatal for the review it's attached to)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    field: str | None = Field(default=None, max_length=120)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "field": self.field}


class CandidateReview(BaseModel):
    """One reviewer decision on one :class:`AchievementCandidate`.

    Stored one-file-per-review under
    ``hybrid_dataset/dataset/candidate_reviews/<review_id>.yaml``.
    Append-only: a later decision writes a new file; it does NOT
    overwrite an existing review.

    On ACCEPT, the reviewer-attested fields carry the data a future
    Candidate-to-Achievement chunk will use to construct the actual
    :class:`nlp_semantic.schema.Achievement`. On REJECT, those fields
    are empty.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    review_id: str = Field(min_length=1, max_length=64)
    candidate_id: str = Field(min_length=1, max_length=64)
    decision: CandidateDecision
    reviewer: str = Field(min_length=1, max_length=64)
    rationale: str = Field(min_length=1, max_length=4000)
    created_at: datetime

    # Snapshot of candidate state at review time, for audit.
    reviewed_candidate_proposer: str | None = Field(default=None, max_length=64)
    reviewed_candidate_source_id: str | None = None
    reviewed_candidate_evidence_intake_ids: list[str] = Field(
        default_factory=list
    )

    # Reviewer attestations (set only on ACCEPT; empty on REJECT).
    attested_source_id: str | None = None
    attested_source_record_id: str | None = Field(default=None, max_length=200)
    attested_primary_type: str | None = None
    attested_domain_tags: list[str] = Field(default_factory=list)
    attested_level: str | None = Field(default=None, max_length=120)
    attested_outcome: str | None = Field(default=None, max_length=120)
    attested_event_name: str | None = Field(default=None, max_length=250)
    attested_organization: str | None = Field(default=None, max_length=250)
    attested_achievement_date: date | None = None
    attested_rank: int | None = None
    attested_skills: list[str] = Field(default_factory=list)
    attested_evidence_id: str | None = None

    @field_validator("review_id")
    @classmethod
    def _validate_review_id(cls, v: str) -> str:
        return validate_review_id(v)

    @field_validator("candidate_id")
    @classmethod
    def _validate_candidate_id(cls, v: str) -> str:
        return validate_candidate_id(v)

    @field_validator("reviewer")
    @classmethod
    def _validate_reviewer(cls, v: str) -> str:
        return _validate_pseudonym(v)

    @field_validator("reviewed_candidate_proposer")
    @classmethod
    def _validate_reviewed_proposer(cls, v: str | None) -> str | None:
        return v if v is None else _validate_pseudonym(v)

    @field_validator("created_at")
    @classmethod
    def _validate_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return v

    @field_validator("attested_source_id", "reviewed_candidate_source_id")
    @classmethod
    def _validate_optional_source_id(cls, v: str | None) -> str | None:
        return v if v is None else validate_prefixed_id(v, "src")

    @field_validator("attested_primary_type")
    @classmethod
    def _validate_attested_primary_type(cls, v: str | None) -> str | None:
        return v if v is None else validate_label_id(v)

    @field_validator("attested_domain_tags")
    @classmethod
    def _validate_attested_domain_tags(cls, v: list[str]) -> list[str]:
        for lid in v:
            validate_label_id(lid)
        if len(set(v)) != len(v):
            raise ValueError("attested_domain_tags must be unique")
        return v

    @field_validator("reviewed_candidate_evidence_intake_ids")
    @classmethod
    def _validate_reviewed_intake_ids(cls, v: list[str]) -> list[str]:
        for iid in v:
            validate_intake_id(iid)
        if len(set(v)) != len(v):
            raise ValueError("reviewed_candidate_evidence_intake_ids must be unique")
        return v

    @field_validator("attested_evidence_id")
    @classmethod
    def _validate_attested_evidence_id(cls, v: str | None) -> str | None:
        return v if v is None else validate_prefixed_id(v, "evd")

    @field_validator("attested_rank")
    @classmethod
    def _validate_attested_rank(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v < 1:
            raise ValueError("attested_rank must be >= 1 when set")
        return v

    @field_validator("attested_skills")
    @classmethod
    def _validate_attested_skills(cls, v: list[str]) -> list[str]:
        for s in v:
            if not isinstance(s, str) or not s.strip():
                raise ValueError("attested_skills entries must be non-empty strings")
            if len(s) > 120:
                raise ValueError("attested_skills strings must be at most 120 chars")
        if len(set(v)) != len(v):
            raise ValueError("attested_skills must not contain duplicates")
        return v


# ---- exceptions ------------------------------------------------------------


class CandidateReviewError(ValueError):
    """Raised when a review's preconditions fail.

    Carries ``findings`` — a list of :class:`ReviewFinding` naming
    the specific precondition failures. No file is written when this
    is raised (fail-closed: validate before persisting).
    """

    def __init__(self, message: str, findings: list[ReviewFinding]):
        super().__init__(message)
        self.findings = findings


# ---- loader / writer ------------------------------------------------------


def _review_to_yaml_dict(r: CandidateReview) -> dict[str, Any]:
    """YAML-friendly dict (ISO dates, enum .value)."""
    return {
        "review_id": r.review_id,
        "candidate_id": r.candidate_id,
        "decision": r.decision.value,
        "reviewer": r.reviewer,
        "rationale": r.rationale,
        "created_at": r.created_at.isoformat(),
        "reviewed_candidate_proposer": r.reviewed_candidate_proposer,
        "reviewed_candidate_source_id": r.reviewed_candidate_source_id,
        "reviewed_candidate_evidence_intake_ids": list(
            r.reviewed_candidate_evidence_intake_ids
        ),
        "attested_source_id": r.attested_source_id,
        "attested_source_record_id": r.attested_source_record_id,
        "attested_primary_type": r.attested_primary_type,
        "attested_domain_tags": list(r.attested_domain_tags),
        "attested_level": r.attested_level,
        "attested_outcome": r.attested_outcome,
        "attested_event_name": r.attested_event_name,
        "attested_organization": r.attested_organization,
        "attested_achievement_date": (
            r.attested_achievement_date.isoformat()
            if r.attested_achievement_date is not None
            else None
        ),
        "attested_rank": r.attested_rank,
        "attested_skills": list(r.attested_skills),
        "attested_evidence_id": r.attested_evidence_id,
    }


def load_candidate_review(path: str | Path) -> CandidateReview:
    """Load one :class:`CandidateReview` from its YAML file."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(
            f"{p}: top-level YAML must be a mapping; got "
            f"{type(data).__name__}"
        )
    return CandidateReview(**data)


def list_candidate_reviews(
    output_dir: str | Path,
    *,
    candidate_id: str | None = None,
) -> list[CandidateReview]:
    """List reviews under ``output_dir`` in filename order.

    Filters by ``candidate_id`` when supplied.
    """
    d = Path(output_dir)
    if not d.is_dir():
        return []
    out: list[CandidateReview] = []
    for p in sorted(d.glob("crev_*.yaml")):
        r = load_candidate_review(p)
        if candidate_id is None or r.candidate_id == candidate_id:
            out.append(r)
    return out


def _write_review(review: CandidateReview, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{review.review_id}.yaml"
    if path.exists():
        raise CandidateReviewError(
            f"review file already exists at {path}; refusing to overwrite",
            findings=[
                ReviewFinding(
                    code=ReviewErrorCode.REVIEW_ID_COLLISION,
                    message=(
                        f"review_id {review.review_id!r} already has a review "
                        f"file at {path}; append-only semantics violated"
                    ),
                    field="review_id",
                )
            ],
        )
    payload = yaml.safe_dump(
        _review_to_yaml_dict(review),
        sort_keys=False,
        default_flow_style=False,
    )
    path.write_text(payload, encoding="utf-8")
    return path


# ---- precondition checks --------------------------------------------------


def _check_proposer_not_reviewer(
    candidate: AchievementCandidate,
    reviewer: str,
    findings: list[ReviewFinding],
) -> None:
    """P-7."""
    if candidate.proposer is not None and candidate.proposer == reviewer:
        findings.append(
            ReviewFinding(
                code=ReviewErrorCode.PROPOSER_IS_REVIEWER,
                message=(
                    f"reviewer {reviewer!r} is also the candidate's proposer; "
                    "the reviewer-independence rule from Chunk 7.44 §4.1 P-7 "
                    "and TAXONOMY_APPROVAL_CHECKLIST §104-106 forbids "
                    "self-acceptance"
                ),
                field="reviewer",
            )
        )


def _check_intake_integrity(
    candidate: AchievementCandidate,
    *,
    intake_manifest_dir: Path | None,
    evidence_root: Path | None,
    findings: list[ReviewFinding],
) -> None:
    """P-2: every referenced intake exists and its on-disk hash matches."""
    if intake_manifest_dir is None:
        # Caller opted out of P-2; applicable in some test fixtures and in
        # reject-paths where the file need not be present. The caller is
        # responsible for respecting the brief's rule that ACCEPT must run P-2.
        return

    for iid in candidate.evidence_intake_ids:
        manifest_path = intake_manifest_dir / f"{iid}.yaml"
        if not manifest_path.exists():
            findings.append(
                ReviewFinding(
                    code=ReviewErrorCode.INTAKE_NOT_FOUND,
                    message=(
                        f"intake manifest not found at {manifest_path}"
                    ),
                    field=f"candidate.evidence_intake_ids:{iid}",
                )
            )
            continue
        try:
            entry = load_intake_entry(manifest_path)
        except Exception as e:
            findings.append(
                ReviewFinding(
                    code=ReviewErrorCode.INTAKE_NOT_FOUND,
                    message=(
                        f"intake manifest at {manifest_path} failed to load: {e}"
                    ),
                    field=f"candidate.evidence_intake_ids:{iid}",
                )
            )
            continue
        if evidence_root is None:
            # Can't verify the file hash without the evidence_root
            continue
        # Resolve the on-disk file via the IntakeEntry.relative_path.
        from .pipeline import INTAKE_ROOT_PREFIX

        rel_tail = entry.relative_path[len(INTAKE_ROOT_PREFIX):]
        on_disk = evidence_root / rel_tail
        if not on_disk.exists():
            findings.append(
                ReviewFinding(
                    code=ReviewErrorCode.EVIDENCE_FILE_NOT_FOUND,
                    message=(
                        f"intake evidence file not found at {on_disk}"
                    ),
                    field=f"candidate.evidence_intake_ids:{iid}",
                )
            )
            continue
        disk_hash = sha256_of_file(on_disk)
        if disk_hash != entry.sha256:
            findings.append(
                ReviewFinding(
                    code=ReviewErrorCode.HASH_MISMATCH_ON_DISK,
                    message=(
                        f"on-disk sha256 {disk_hash!r} differs from intake "
                        f"manifest {entry.sha256!r}"
                    ),
                    field=f"candidate.evidence_intake_ids:{iid}",
                )
            )


def _check_source_record_id(
    *,
    source_record_id: str | None,
    findings: list[ReviewFinding],
) -> None:
    """P-3."""
    if source_record_id is None or not source_record_id.strip():
        findings.append(
            ReviewFinding(
                code=ReviewErrorCode.MISSING_SOURCE_RECORD_ID,
                message=(
                    "source_record_id must be supplied for ACCEPT per "
                    "Chunk 7.44 §4.1 P-3; it will be the reviewer's "
                    "attested identifier for the eventual Achievement row"
                ),
                field="source_record_id",
            )
        )


def _check_source_id_present(
    effective_source_id: str | None,
    findings: list[ReviewFinding],
) -> None:
    """ACCEPT needs a resolvable source_id (candidate's or reviewer's override)."""
    if effective_source_id is None:
        findings.append(
            ReviewFinding(
                code=ReviewErrorCode.MISSING_SOURCE_ID,
                message=(
                    "ACCEPT requires a source_id either on the candidate "
                    "or supplied as a reviewer override"
                ),
                field="source_id",
            )
        )


def _check_duplicate_source_record_pair(
    *,
    source_id: str | None,
    source_record_id: str | None,
    existing_records: Iterable[Achievement] | None,
    findings: list[ReviewFinding],
) -> None:
    """P-4."""
    if source_id is None or source_record_id is None or existing_records is None:
        return
    for rec in existing_records:
        if rec.source_id == source_id and rec.source_record_id == source_record_id:
            findings.append(
                ReviewFinding(
                    code=ReviewErrorCode.DUPLICATE_SOURCE_RECORD_PAIR,
                    message=(
                        f"(source_id={source_id!r}, source_record_id="
                        f"{source_record_id!r}) already exists on "
                        f"Achievement {rec.achievement_id!r}; Chunk 7.44 §4.1 "
                        "P-4 forbids duplicates"
                    ),
                    field="source_record_id",
                )
            )
            return


def _check_primary_type(
    primary_type: str | None,
    *,
    primary_taxonomy: Iterable[LabelTaxonomy] | None,
    findings: list[ReviewFinding],
) -> None:
    """P-5."""
    if primary_type is None or primary_taxonomy is None:
        return
    by_id = {e.label_id: e for e in primary_taxonomy}
    entry = by_id.get(primary_type)
    if entry is None:
        findings.append(
            ReviewFinding(
                code=ReviewErrorCode.UNKNOWN_PRIMARY_TYPE_LABEL,
                message=(
                    f"primary_type {primary_type!r} not found in "
                    "primary_taxonomy"
                ),
                field="primary_type",
            )
        )
        return
    if entry.status == TaxonomyStatus.DEPRECATED:
        findings.append(
            ReviewFinding(
                code=ReviewErrorCode.DEPRECATED_PRIMARY_TYPE_LABEL,
                message=(
                    f"primary_type {primary_type!r} is deprecated in "
                    "primary_taxonomy"
                ),
                field="primary_type",
            )
        )


def _check_domain_tags(
    domain_tags: Iterable[str] | None,
    *,
    domain_taxonomy: Iterable[LabelTaxonomy] | None,
    findings: list[ReviewFinding],
) -> None:
    """P-6."""
    if not domain_tags:
        return
    if domain_taxonomy is None:
        return
    by_id = {e.label_id: e for e in domain_taxonomy}
    for tag in domain_tags:
        entry = by_id.get(tag)
        if entry is None:
            findings.append(
                ReviewFinding(
                    code=ReviewErrorCode.UNKNOWN_DOMAIN_TAG,
                    message=(
                        f"domain_tag {tag!r} not found in domain_tags taxonomy"
                    ),
                    field="domain_tags",
                )
            )
            continue
        if entry.status == TaxonomyStatus.DEPRECATED:
            findings.append(
                ReviewFinding(
                    code=ReviewErrorCode.DEPRECATED_DOMAIN_TAG,
                    message=(
                        f"domain_tag {tag!r} is deprecated"
                    ),
                    field="domain_tags",
                )
            )


def _check_hypothetical_dataset(
    *,
    hypothetical: Achievement | None,
    existing_records: Iterable[Achievement] | None,
    sources: Iterable[SourceRegistry] | None,
    primary_taxonomy: Iterable[LabelTaxonomy] | None,
    domain_taxonomy: Iterable[LabelTaxonomy] | None,
    findings: list[ReviewFinding],
) -> None:
    """P-8: adding the hypothetical Achievement must keep validate_dataset.is_valid."""
    if hypothetical is None or sources is None:
        return
    all_records = list(existing_records or [])
    all_records.append(hypothetical)
    rep = validate_dataset(
        records=all_records,
        annotations=[],
        sources=sources,
        primary_taxonomy=primary_taxonomy or [],
        domain_taxonomy=domain_taxonomy or [],
    )
    if not rep.is_valid:
        findings.append(
            ReviewFinding(
                code=ReviewErrorCode.HYPOTHETICAL_DATASET_INVALID,
                message=(
                    "the hypothetical dataset including this ACCEPT's "
                    "Achievement would fail validate_dataset with "
                    f"{rep.fatal_count} fatal findings"
                ),
                field=None,
            )
        )


def _build_hypothetical_achievement(
    *,
    source_id: str,
    source_record_id: str,
    achievement_text: str,
    primary_type: str | None,
    domain_tags: list[str],
    level: str | None,
    outcome: str | None,
    event_name: str | None,
    organization: str | None,
    achievement_date: date | None,
    rank: int | None,
    skills: list[str],
    evidence_id: str | None,
) -> Achievement:
    """Build the hypothetical Achievement in memory for P-8.

    Follows the Chunk 7.4-A.1 pattern: annotation_status.primary_type
    defaults to DRAFT when primary_type is set, NOT_STARTED otherwise;
    annotation_status.domain_tags starts NOT_STARTED only when
    domain_tags is empty (consistency rule in achievement.py).
    """
    pt_status = (
        AnnotationStatus.DRAFT
        if primary_type is not None
        else AnnotationStatus.NOT_STARTED
    )
    dt_status = (
        AnnotationStatus.DRAFT
        if domain_tags
        else AnnotationStatus.NOT_STARTED
    )
    from nlp_semantic.schema.identifiers import make_id

    return Achievement(
        achievement_id=make_id("ach"),
        source_id=source_id,
        source_record_id=source_record_id,
        achievement_text=achievement_text,
        primary_type=primary_type,
        domain_tags=domain_tags,
        level=level,
        outcome=outcome,
        event_name=event_name,
        organization=organization,
        achievement_date=achievement_date,
        rank=rank,
        skills=skills,
        evidence_id=evidence_id,
        annotation_status=AnnotationStatusMap(
            primary_type=pt_status,
            domain_tags=dt_status,
        ),
        is_synthetic=False,
    )


# ---- public API ------------------------------------------------------------


def review_candidate(
    candidate: AchievementCandidate,
    *,
    decision: CandidateDecision,
    reviewer: str,
    rationale: str,
    output_dir: str | Path,
    created_at: datetime | None = None,
    # ACCEPT-time attestations (all optional at the signature level;
    # some are required for ACCEPT and will fail P-* if absent).
    source_id: str | None = None,
    source_record_id: str | None = None,
    primary_type: str | None = None,
    domain_tags: Iterable[str] | None = None,
    level: str | None = None,
    outcome: str | None = None,
    event_name: str | None = None,
    organization: str | None = None,
    achievement_date: date | None = None,
    rank: int | None = None,
    skills: Iterable[str] | None = None,
    evidence_id: str | None = None,
    # Validation inputs (needed for ACCEPT preconditions; may be None on REJECT)
    intake_manifest_dir: str | Path | None = None,
    evidence_root: str | Path | None = None,
    sources: Iterable[SourceRegistry] | None = None,
    primary_taxonomy: Iterable[LabelTaxonomy] | None = None,
    domain_taxonomy: Iterable[LabelTaxonomy] | None = None,
    existing_records: Iterable[Achievement] | None = None,
) -> CandidateReview:
    """Execute a Phase-3 reviewer decision on ``candidate``.

    Returns the persisted :class:`CandidateReview`. Fail-closed on
    precondition failure: raises :class:`CandidateReviewError` and
    writes no file.

    REJECT runs only P-7 (reviewer-independence) and persists.
    ACCEPT runs P-2 through P-8 and persists only if every check
    passes.
    """
    if not isinstance(decision, CandidateDecision):
        raise CandidateReviewError(
            f"unsupported decision {decision!r}",
            findings=[
                ReviewFinding(
                    code=ReviewErrorCode.UNSUPPORTED_DECISION,
                    message=(
                        f"decision must be CandidateDecision.ACCEPT or REJECT; "
                        f"got {decision!r}"
                    ),
                    field="decision",
                )
            ],
        )

    reviewer = _validate_pseudonym(reviewer)

    findings: list[ReviewFinding] = []
    _check_proposer_not_reviewer(candidate, reviewer, findings)

    # Attestations default to the Candidate's own proposed fields where
    # the reviewer did not override.
    effective_source_id = source_id if source_id is not None else candidate.source_id
    effective_primary_type = (
        primary_type if primary_type is not None else candidate.proposed_primary_type
    )
    effective_domain_tags = list(domain_tags) if domain_tags is not None else []
    effective_skills = list(skills) if skills is not None else []

    achievement_text_for_hypothetical = (
        candidate.proposed_achievement_text or ""
    ).strip()

    if decision == CandidateDecision.ACCEPT:
        # P-2
        _check_intake_integrity(
            candidate,
            intake_manifest_dir=(
                Path(intake_manifest_dir)
                if intake_manifest_dir is not None
                else None
            ),
            evidence_root=(
                Path(evidence_root) if evidence_root is not None else None
            ),
            findings=findings,
        )
        # P-3
        _check_source_record_id(
            source_record_id=source_record_id, findings=findings
        )
        # Need an effective source_id for both P-4 and the hypothetical
        _check_source_id_present(effective_source_id, findings)
        # P-5
        _check_primary_type(
            effective_primary_type,
            primary_taxonomy=primary_taxonomy,
            findings=findings,
        )
        # P-6
        _check_domain_tags(
            effective_domain_tags,
            domain_taxonomy=domain_taxonomy,
            findings=findings,
        )
        # P-4
        _check_duplicate_source_record_pair(
            source_id=effective_source_id,
            source_record_id=source_record_id,
            existing_records=existing_records,
            findings=findings,
        )
        # P-8: only if the earlier checks produced no fatals that would
        # make Achievement construction itself fail.
        if (
            not findings
            and effective_source_id is not None
            and source_record_id is not None
            and achievement_text_for_hypothetical
        ):
            try:
                hypothetical = _build_hypothetical_achievement(
                    source_id=effective_source_id,
                    source_record_id=source_record_id,
                    achievement_text=achievement_text_for_hypothetical,
                    primary_type=effective_primary_type,
                    domain_tags=effective_domain_tags,
                    level=level,
                    outcome=outcome,
                    event_name=event_name,
                    organization=organization,
                    achievement_date=achievement_date,
                    rank=rank,
                    skills=effective_skills,
                    evidence_id=evidence_id,
                )
            except Exception as e:
                findings.append(
                    ReviewFinding(
                        code=ReviewErrorCode.HYPOTHETICAL_DATASET_INVALID,
                        message=(
                            f"hypothetical Achievement construction failed: {e}"
                        ),
                        field=None,
                    )
                )
            else:
                _check_hypothetical_dataset(
                    hypothetical=hypothetical,
                    existing_records=existing_records,
                    sources=sources,
                    primary_taxonomy=primary_taxonomy,
                    domain_taxonomy=domain_taxonomy,
                    findings=findings,
                )
        elif not achievement_text_for_hypothetical:
            findings.append(
                ReviewFinding(
                    code="MISSING_PROPOSED_ACHIEVEMENT_TEXT",
                    message=(
                        "candidate has no proposed_achievement_text; ACCEPT "
                        "requires one so the hypothetical Achievement can "
                        "carry a non-empty achievement_text"
                    ),
                    field="candidate.proposed_achievement_text",
                )
            )

    # REJECT runs only P-7 above.

    if findings:
        raise CandidateReviewError(
            f"review preconditions failed: {len(findings)} finding(s)",
            findings=findings,
        )

    # All preconditions passed. Build the CandidateReview and persist.
    now = created_at if created_at is not None else _utcnow()
    review = CandidateReview(
        review_id=make_review_id(),
        candidate_id=candidate.candidate_id,
        decision=decision,
        reviewer=reviewer,
        rationale=rationale,
        created_at=now,
        reviewed_candidate_proposer=candidate.proposer,
        reviewed_candidate_source_id=candidate.source_id,
        reviewed_candidate_evidence_intake_ids=list(
            candidate.evidence_intake_ids
        ),
        attested_source_id=(
            effective_source_id if decision == CandidateDecision.ACCEPT else None
        ),
        attested_source_record_id=(
            source_record_id if decision == CandidateDecision.ACCEPT else None
        ),
        attested_primary_type=(
            effective_primary_type
            if decision == CandidateDecision.ACCEPT
            else None
        ),
        attested_domain_tags=(
            effective_domain_tags if decision == CandidateDecision.ACCEPT else []
        ),
        attested_level=(
            level if decision == CandidateDecision.ACCEPT else None
        ),
        attested_outcome=(
            outcome if decision == CandidateDecision.ACCEPT else None
        ),
        attested_event_name=(
            event_name if decision == CandidateDecision.ACCEPT else None
        ),
        attested_organization=(
            organization if decision == CandidateDecision.ACCEPT else None
        ),
        attested_achievement_date=(
            achievement_date if decision == CandidateDecision.ACCEPT else None
        ),
        attested_rank=(
            rank if decision == CandidateDecision.ACCEPT else None
        ),
        attested_skills=(
            effective_skills if decision == CandidateDecision.ACCEPT else []
        ),
        attested_evidence_id=(
            evidence_id if decision == CandidateDecision.ACCEPT else None
        ),
    )
    _write_review(review, Path(output_dir))
    return review


def _utcnow() -> datetime:
    """Timezone-aware UTC now (indirection makes mocking easier in tests)."""
    from datetime import timezone

    return datetime.now(timezone.utc)


__all__ = [
    "CandidateDecision",
    "CandidateReview",
    "CandidateReviewError",
    "ReviewErrorCode",
    "ReviewFinding",
    "load_candidate_review",
    "list_candidate_reviews",
    "make_review_id",
    "review_candidate",
    "validate_review_id",
]
