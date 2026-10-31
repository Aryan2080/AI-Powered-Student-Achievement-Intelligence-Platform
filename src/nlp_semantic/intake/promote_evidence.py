"""Reviewer-gated evidence promotion: IntakeEntry → Evidence row.

Implements the Chunk 7.44 §2.3 design. A reviewer takes an existing
:class:`IntakeEntry` (produced by Chunk 7.39 intake) and promotes
its raw file to a persistent :class:`Evidence` row:

* The intake file is **copied** (not moved) from
  ``hybrid_dataset/raw/evidence_intake/<intk_id>/<name>`` to
  ``hybrid_dataset/raw/evidence_documents/<intk_id>__<name>``.
* A new :class:`Evidence` row is written as its own YAML under
  ``hybrid_dataset/dataset/evidence/<evd_id>.yaml`` (one file per
  Evidence, same append-only pattern as Chunk 7.45 CandidateReview).
* The intake original is preserved untouched.

**Fail-closed contract.**

* The function does **not** approve the source cited by the intake.
  ``sources.yaml`` is byte-identical after a successful promotion.
* The new Evidence row starts at
  :attr:`ReviewStatus.UNREVIEWED` and
  :attr:`ExtractionMethod.NONE_YET`. Promotion is **not**
  verification.
* The function does **not** create any :class:`Achievement`,
  :class:`AchievementCandidate`, or :class:`Annotation` row.
* The function does **not** run OCR or extract text.
* The function does **not** change ``training_ready_subset``
  behaviour.
* All preconditions run **before** any file is written. If any
  fails, :class:`PromoteEvidenceError` is raised and the file
  system is unchanged.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from nlp_semantic.schema import (
    Evidence,
    ExtractionMethod,
    ReviewStatus,
    make_id,
)
from nlp_semantic.schema.path_safety import (
    APPROVED_EVIDENCE_PREFIX,
    reject_unsafe_relative_path,
)

from .pipeline import (
    INTAKE_ROOT_PREFIX,
    IntakeEntry,
    sha256_of_file,
)


# ---- constants -------------------------------------------------------------

#: Default on-disk destination root for promoted evidence files.
DEFAULT_EVIDENCE_DOCUMENTS_ROOT = "hybrid_dataset/raw/evidence_documents"

#: Default directory for per-Evidence YAML records.
DEFAULT_EVIDENCE_RECORD_DIR = "hybrid_dataset/dataset/evidence"


_PSEUDONYM_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$")
_EMAIL_LIKE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PromoteEvidenceErrorCode:
    """Stable string codes for promotion precondition failures."""

    MISSING_ORIGINAL_FILE = "MISSING_ORIGINAL_FILE"
    HASH_MISMATCH_ON_DISK = "HASH_MISMATCH_ON_DISK"
    EVIDENCE_FILE_ALREADY_EXISTS = "EVIDENCE_FILE_ALREADY_EXISTS"
    EVIDENCE_RECORD_ALREADY_EXISTS = "EVIDENCE_RECORD_ALREADY_EXISTS"
    DUPLICATE_EVIDENCE_HASH = "DUPLICATE_EVIDENCE_HASH"
    REVIEWER_IS_PROPOSER = "REVIEWER_IS_PROPOSER"
    INVALID_DESTINATION_PATH = "INVALID_DESTINATION_PATH"
    INVALID_REVIEWER = "INVALID_REVIEWER"
    EVIDENCE_RECORD_INVALID = "EVIDENCE_RECORD_INVALID"
    EVIDENCE_ROOT_NOT_FOUND = "EVIDENCE_ROOT_NOT_FOUND"


# ---- exceptions ------------------------------------------------------------


@dataclass
class PromoteEvidenceFinding:
    """One precondition finding."""

    code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "field": self.field}


class PromoteEvidenceError(ValueError):
    """Raised when any precondition fails. Carries ``findings``."""

    def __init__(self, message: str, findings: list[PromoteEvidenceFinding]):
        super().__init__(message)
        self.findings = findings


# ---- result model ---------------------------------------------------------


@dataclass(frozen=True)
class PromoteEvidenceResult:
    """Return value of :func:`promote_evidence`."""

    evidence: Evidence
    source_intake_id: str
    source_file_path: Path
    destination_file_path: Path
    evidence_record_path: Path
    duplicate_of_evidence_ids: list[str] = field(default_factory=list)


# ---- loader helpers -------------------------------------------------------


def _evidence_to_yaml_dict(e: Evidence) -> dict[str, Any]:
    """Produce a YAML-friendly dict for one :class:`Evidence` row."""
    return {
        "evidence_id": e.evidence_id,
        "linked_achievement_id": e.linked_achievement_id,
        "relative_path": e.relative_path,
        "original_filename": e.original_filename,
        "file_type": e.file_type.value,
        "document_type": e.document_type,
        "extraction_method": e.extraction_method.value,
        "extracted_text_ref": e.extracted_text_ref,
        "extracted_text_inline": e.extracted_text_inline,
        "ocr_confidence": e.ocr_confidence,
        "review_status": e.review_status.value,
        "is_synthetic": e.is_synthetic,
    }


def load_evidence_record(path: str | Path) -> Evidence:
    """Load one :class:`Evidence` row from its YAML file."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(
            f"{p}: top-level YAML must be a mapping; got "
            f"{type(data).__name__}"
        )
    return Evidence(**data)


def list_evidence_records(evidence_record_dir: str | Path) -> list[Evidence]:
    """Return every :class:`Evidence` row under ``evidence_record_dir``.

    Reads every ``evd_*.yaml`` file in filename order. Returns an
    empty list if the directory does not exist.
    """
    d = Path(evidence_record_dir)
    if not d.is_dir():
        return []
    out: list[Evidence] = []
    for p in sorted(d.glob("evd_*.yaml")):
        out.append(load_evidence_record(p))
    return out


# ---- helpers --------------------------------------------------------------


def _validate_pseudonym(v: str) -> str:
    if _EMAIL_LIKE_RE.match(v):
        raise ValueError("pseudonym must not be an email")
    if not _PSEUDONYM_RE.fullmatch(v):
        raise ValueError(
            f"pseudonym {v!r} does not match the required pattern"
        )
    return v


def _destination_filename(intake: IntakeEntry) -> str:
    """Prefix the original filename with the intake id to avoid collisions."""
    return f"{intake.intake_id}__{intake.original_filename}"


def _resolve_intake_file(intake: IntakeEntry, evidence_root: Path) -> Path:
    """Resolve the on-disk path of the intake's original file."""
    if not intake.relative_path.startswith(INTAKE_ROOT_PREFIX):
        raise ValueError(
            f"intake.relative_path {intake.relative_path!r} does not start "
            f"with INTAKE_ROOT_PREFIX {INTAKE_ROOT_PREFIX!r}"
        )
    rel_tail = intake.relative_path[len(INTAKE_ROOT_PREFIX):]
    return evidence_root / rel_tail


# ---- promotion ------------------------------------------------------------


def promote_evidence(
    intake: IntakeEntry,
    *,
    reviewer: str,
    evidence_root: str | Path,
    evidence_documents_root: str | Path,
    evidence_record_dir: str | Path,
    document_type: str | None = None,
    existing_evidence: Iterable[Evidence] | None = None,
) -> PromoteEvidenceResult:
    """Promote one intake entry to an :class:`Evidence` row.

    Preconditions (all run before any file is written):

    1. ``reviewer`` is a valid pseudonym (non-email,
       ``^[A-Za-z0-9_][A-Za-z0-9_\\-]{1,63}$``).
    2. ``reviewer`` is **not** the ``intake.proposer`` (reviewer
       independence, same spirit as Chunk 7.45 P-7 and the
       Chunk 7.38B ``PROPOSER_IS_REVIEWER`` rule).
    3. The intake's original file exists under
       ``evidence_root`` at the path encoded by
       ``intake.relative_path``.
    4. The on-disk file's SHA-256 matches ``intake.sha256``.
    5. The destination filename
       (``<intake_id>__<original_filename>``) produces a repository-
       relative path that starts with
       :data:`APPROVED_EVIDENCE_PREFIX` and passes the shared
       :func:`reject_unsafe_relative_path` safety check.
    6. The destination file at ``evidence_documents_root/<name>``
       does not already exist (no silent overwrite).
    7. No existing :class:`Evidence` row (from ``existing_evidence``
       if supplied, else loaded from ``evidence_record_dir``) shares
       the same SHA-256 as the intake. If one does, the promotion
       is refused with ``DUPLICATE_EVIDENCE_HASH``.
    8. The hypothetical :class:`Evidence` row is Pydantic-valid.
       Constructed in memory before any disk write.

    On success the function:

    - Copies the intake file byte-for-byte to the destination.
    - Writes the Evidence row as a single YAML file at
      ``<evidence_record_dir>/<evidence_id>.yaml``.
    - Returns a :class:`PromoteEvidenceResult`.

    On any precondition failure the function raises
    :class:`PromoteEvidenceError` and the filesystem is unchanged.
    """
    evidence_root_p = Path(evidence_root)
    documents_root_p = Path(evidence_documents_root)
    record_dir_p = Path(evidence_record_dir)

    findings: list[PromoteEvidenceFinding] = []

    # (1) reviewer pseudonym
    try:
        reviewer = _validate_pseudonym(reviewer)
    except ValueError as e:
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.INVALID_REVIEWER,
                message=str(e),
                field="reviewer",
            )
        )
        raise PromoteEvidenceError(
            "reviewer pseudonym is invalid",
            findings=findings,
        )

    # (2) reviewer independence
    if intake.proposer is not None and intake.proposer == reviewer:
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.REVIEWER_IS_PROPOSER,
                message=(
                    f"reviewer {reviewer!r} is also the intake's proposer; "
                    "the reviewer-independence rule from TAXONOMY_APPROVAL_"
                    "CHECKLIST §104-106 forbids self-promotion"
                ),
                field="reviewer",
            )
        )

    # (3) intake file exists
    try:
        source_file = _resolve_intake_file(intake, evidence_root_p)
    except ValueError as e:
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.INVALID_DESTINATION_PATH,
                message=str(e),
                field="intake.relative_path",
            )
        )
        raise PromoteEvidenceError(
            "intake.relative_path is malformed",
            findings=findings,
        )
    if not source_file.exists():
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.MISSING_ORIGINAL_FILE,
                message=(
                    f"intake original file not found at {source_file!s}"
                ),
                field="intake.relative_path",
            )
        )
        raise PromoteEvidenceError(
            "intake original file missing",
            findings=findings,
        )

    # (4) hash integrity
    disk_hash = sha256_of_file(source_file)
    if disk_hash != intake.sha256:
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.HASH_MISMATCH_ON_DISK,
                message=(
                    f"on-disk SHA-256 {disk_hash!r} does not match intake "
                    f"manifest {intake.sha256!r}"
                ),
                field="sha256",
            )
        )

    # (5) destination filename path safety
    destination_filename = _destination_filename(intake)
    relative_path = f"{APPROVED_EVIDENCE_PREFIX}{destination_filename}"
    try:
        reject_unsafe_relative_path(
            relative_path, must_start_with=APPROVED_EVIDENCE_PREFIX
        )
    except ValueError as e:
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.INVALID_DESTINATION_PATH,
                message=str(e),
                field="destination_filename",
            )
        )

    destination_file = documents_root_p / destination_filename

    # (6) destination file does not already exist (no silent overwrite)
    if destination_file.exists():
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.EVIDENCE_FILE_ALREADY_EXISTS,
                message=(
                    f"destination file already exists at {destination_file!s}; "
                    "refusing to overwrite (promote-evidence is additive)"
                ),
                field="destination",
            )
        )

    # (7) duplicate-hash check
    existing = (
        list(existing_evidence)
        if existing_evidence is not None
        else list_evidence_records(record_dir_p)
    )
    duplicates = _duplicate_hashes_in(
        existing,
        target_sha256=intake.sha256,
        documents_root=documents_root_p,
    )
    if duplicates:
        # Hard fail per brief "Prevent duplicate evidence promotion".
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.DUPLICATE_EVIDENCE_HASH,
                message=(
                    f"an existing Evidence row shares the intake's SHA-256; "
                    f"existing evidence ids: {duplicates!r}"
                ),
                field="sha256",
            )
        )

    # (8) hypothetical Evidence row is Pydantic-valid
    evidence_id = make_id("evd")
    try:
        evidence = Evidence(
            evidence_id=evidence_id,
            linked_achievement_id=None,
            relative_path=relative_path,
            original_filename=intake.original_filename,
            file_type=intake.file_type,
            document_type=document_type,
            extraction_method=ExtractionMethod.NONE_YET,
            extracted_text_ref=None,
            extracted_text_inline=None,
            ocr_confidence=None,
            review_status=ReviewStatus.UNREVIEWED,
            is_synthetic=False,
        )
    except ValidationError as e:
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.EVIDENCE_RECORD_INVALID,
                message=f"hypothetical Evidence construction failed: {e}",
                field=None,
            )
        )
        raise PromoteEvidenceError(
            "hypothetical Evidence row would be invalid",
            findings=findings,
        )

    # Record-file collision guard (should be essentially impossible with
    # UUID4, but tested).
    record_path = record_dir_p / f"{evidence_id}.yaml"
    if record_path.exists():
        findings.append(
            PromoteEvidenceFinding(
                code=PromoteEvidenceErrorCode.EVIDENCE_RECORD_ALREADY_EXISTS,
                message=(
                    f"Evidence record file already exists at {record_path!s}; "
                    "refusing to overwrite"
                ),
                field="evidence_id",
            )
        )

    if findings:
        raise PromoteEvidenceError(
            f"promote-evidence preconditions failed: {len(findings)} finding(s)",
            findings=findings,
        )

    # All preconditions passed. Perform the two writes.
    # Order: write Evidence record FIRST so a mid-crash leaves the record
    # pointing at a path whose file didn't land — easy to detect and
    # recover from (orphan record is better than orphan file). Then copy
    # the bytes.
    record_dir_p.mkdir(parents=True, exist_ok=True)
    documents_root_p.mkdir(parents=True, exist_ok=True)

    record_payload = yaml.safe_dump(
        _evidence_to_yaml_dict(evidence),
        sort_keys=False,
        default_flow_style=False,
    )
    record_path.write_text(record_payload, encoding="utf-8")

    data = source_file.read_bytes()
    destination_file.write_bytes(data)

    return PromoteEvidenceResult(
        evidence=evidence,
        source_intake_id=intake.intake_id,
        source_file_path=source_file,
        destination_file_path=destination_file,
        evidence_record_path=record_path,
        duplicate_of_evidence_ids=[],
    )


def _duplicate_hashes_in(
    existing_evidence: list[Evidence],
    *,
    target_sha256: str,
    documents_root: Path,
) -> list[str]:
    """Return the evidence_ids of any Evidence rows whose on-disk file
    shares ``target_sha256`` with the intake being promoted.

    Resolves each existing Evidence's ``relative_path`` to an on-disk
    path under ``documents_root`` and recomputes SHA-256. This is
    O(N × file-size); the project's evidence corpus is expected to
    stay small (dozens of files, not millions), so the cost is
    acceptable. Evidence rows whose file is missing on disk are
    silently skipped (they cannot be duplicates of the target).
    """
    duplicates: list[str] = []
    for e in existing_evidence:
        file_name = Path(e.relative_path).name
        on_disk = documents_root / file_name
        if not on_disk.exists():
            continue
        if sha256_of_file(on_disk) == target_sha256:
            duplicates.append(e.evidence_id)
    return duplicates


__all__ = [
    "DEFAULT_EVIDENCE_DOCUMENTS_ROOT",
    "DEFAULT_EVIDENCE_RECORD_DIR",
    "PromoteEvidenceError",
    "PromoteEvidenceErrorCode",
    "PromoteEvidenceFinding",
    "PromoteEvidenceResult",
    "list_evidence_records",
    "load_evidence_record",
    "promote_evidence",
]
