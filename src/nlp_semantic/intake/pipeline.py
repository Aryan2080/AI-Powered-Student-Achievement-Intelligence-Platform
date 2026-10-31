"""Reviewer-gated evidence intake pipeline (fail-closed, additive).

The pipeline accepts a reviewer-supplied evidence file, hashes its
bytes, allocates a stable intake id, stores the file under an
evidence root, and writes a per-intake YAML manifest with provenance
metadata. It also provides structural validation of intake entries
against the existing :mod:`nlp_semantic.schema` constraints.

**Fail-closed contract.** Intake is strictly additive and does NOT
imply approval:

* An ``IntakeEntry`` is NOT an ``Evidence`` row. It records what a
  reviewer supplied; it does not confer source approval, annotation
  verification, taxonomy promotion, or training-readiness.
* ``IntakeStatus.VALIDATED`` means the entry passed structural
  checks only, not that any reviewer authenticated the file or
  endorsed the claim it supports.
* No field of ``hybrid_dataset/metadata/sources.yaml``,
  ``hybrid_dataset/labels/primary_taxonomy.yaml``,
  ``hybrid_dataset/labels/domain_tags.yaml``, or
  ``hybrid_dataset/dataset/records/*.yaml`` is modified by this
  module. Any such change belongs to a separate reviewer-driven
  workflow.
* No external URL is fetched. No website is scraped. No source
  document is fabricated.

The pipeline is deliberately narrow — it provides file handling and
manifest I/O that a reviewer can audit, not an automated collector.
"""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from nlp_semantic.schema import (
    DocumentFileType,
    validate_label_id,
    validate_prefixed_id,
)
from nlp_semantic.schema.path_safety import reject_unsafe_relative_path


# ---- constants -------------------------------------------------------------

#: Repository-relative prefix under which intake raw files live. Mirrors
#: ``APPROVED_EVIDENCE_PREFIX`` for approved Evidence; the two prefixes are
#: distinct so an intake file is never mistaken for an Evidence row's
#: ``relative_path``.
INTAKE_ROOT_PREFIX = "hybrid_dataset/raw/evidence_intake/"

#: Default raw-file root (relative to a configured ``dataset_root``).
DEFAULT_EVIDENCE_ROOT = "hybrid_dataset/raw/evidence_intake"

#: Default manifest directory (relative to a configured ``dataset_root``).
DEFAULT_MANIFEST_DIR = "hybrid_dataset/intake/manifests"


# File-type auto-detection. Deliberately narrow; unknown extensions are
# REJECTED rather than coerced to ``DocumentFileType.OTHER``, which is
# reserved for cases the reviewer explicitly identifies.
SUPPORTED_EXTENSIONS: dict[str, DocumentFileType] = {
    ".pdf": DocumentFileType.PDF,
    ".jpg": DocumentFileType.IMAGE_JPG,
    ".jpeg": DocumentFileType.IMAGE_JPG,
    ".png": DocumentFileType.IMAGE_PNG,
    ".tif": DocumentFileType.IMAGE_TIFF,
    ".tiff": DocumentFileType.IMAGE_TIFF,
    ".txt": DocumentFileType.TEXT,
    ".md": DocumentFileType.TEXT,
    ".html": DocumentFileType.TEXT,
    ".htm": DocumentFileType.TEXT,
    ".json": DocumentFileType.TEXT,
    ".yaml": DocumentFileType.TEXT,
    ".yml": DocumentFileType.TEXT,
}


# Intake-local ID regexes. Distinct from the record-ID prefixes in
# :mod:`nlp_semantic.schema.identifiers` because intake is NOT a schema
# record — the visibly different ``intk_`` / ``cand_`` prefixes keep
# intake metadata from being confused with record ids downstream.
_INTAKE_ID_RE = re.compile(r"^intk_[0-9a-f]{32}$")
_CANDIDATE_ID_RE = re.compile(r"^cand_[0-9a-f]{32}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PSEUDONYM_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$")
_EMAIL_LIKE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---- error / finding codes -------------------------------------------------


class IntakeValidationCode:
    """Stable string codes for intake findings."""

    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    EMPTY_FILE = "EMPTY_FILE"
    UNSAFE_FILENAME = "UNSAFE_FILENAME"
    UNSAFE_RELATIVE_PATH = "UNSAFE_RELATIVE_PATH"
    DUPLICATE_HASH = "DUPLICATE_HASH"
    FILENAME_COLLISION_DIFFERENT_HASH = "FILENAME_COLLISION_DIFFERENT_HASH"
    HASH_MISMATCH_ON_DISK = "HASH_MISMATCH_ON_DISK"
    UNKNOWN_SOURCE_REFERENCE = "UNKNOWN_SOURCE_REFERENCE"
    UNKNOWN_ACHIEVEMENT_REFERENCE = "UNKNOWN_ACHIEVEMENT_REFERENCE"
    INVALID_INTAKE_ID = "INVALID_INTAKE_ID"
    INVALID_CANDIDATE_ID = "INVALID_CANDIDATE_ID"
    INVALID_SOURCE_ID = "INVALID_SOURCE_ID"
    MISSING_SOURCE_ASSOCIATION = "MISSING_SOURCE_ASSOCIATION"
    MISSING_ACHIEVEMENT_ASSOCIATION = "MISSING_ACHIEVEMENT_ASSOCIATION"
    AUTHENTICATION_NOT_ESTABLISHED = "AUTHENTICATION_NOT_ESTABLISHED"


# ---- ID helpers ------------------------------------------------------------


def make_intake_id() -> str:
    """Allocate a fresh ``intk_<32-hex>`` id."""
    return f"intk_{uuid.uuid4().hex}"


def make_candidate_id() -> str:
    """Allocate a fresh ``cand_<32-hex>`` id."""
    return f"cand_{uuid.uuid4().hex}"


def validate_intake_id(value: str) -> str:
    """Validate an intake id. Returns ``value`` unchanged on success."""
    if not isinstance(value, str) or not _INTAKE_ID_RE.fullmatch(value):
        raise ValueError(
            "intake_id must match 'intk_' followed by 32 lowercase hex "
            f"chars; got {value!r}"
        )
    return value


def validate_candidate_id(value: str) -> str:
    """Validate a candidate id. Returns ``value`` unchanged on success."""
    if not isinstance(value, str) or not _CANDIDATE_ID_RE.fullmatch(value):
        raise ValueError(
            "candidate_id must match 'cand_' followed by 32 lowercase hex "
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


def _validate_original_filename(v: str) -> str:
    """Shape-match the Evidence model's filename rule."""
    if not v:
        raise ValueError("original_filename must be non-empty")
    if "/" in v or "\\" in v:
        raise ValueError("original_filename must not contain path separators")
    if v in {".", ".."}:
        raise ValueError("original_filename must not be '.' or '..'")
    if "\0" in v:
        raise ValueError("original_filename must not contain NUL characters")
    return v


# ---- file-type classification ---------------------------------------------


def classify_file_type(filename: str) -> DocumentFileType:
    """Classify a filename by extension. Raises on unsupported extensions.

    Does **not** read the file content or do magic-byte detection;
    extension-based classification is deliberately conservative so a
    reviewer always knows what the intake pipeline decided from the name
    alone.
    """
    ext = Path(filename).suffix.lower()
    if not ext:
        raise ValueError(
            f"filename {filename!r} has no extension; cannot classify"
        )
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"unsupported file extension {ext!r} on {filename!r}; "
            f"supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return SUPPORTED_EXTENSIONS[ext]


# ---- Pydantic models -------------------------------------------------------


class IntakeStatus(str, Enum):
    """Intake pipeline status.

    Deliberately disjoint from ``AnnotationStatus``, ``ReviewStatus``,
    and ``TaxonomyStatus``: an intake entry at ``VALIDATED`` is **not**
    an approved source, a verified annotation, or an approved taxonomy
    label.
    """

    RECEIVED = "received"
    VALIDATED = "validated"
    REJECTED = "rejected"


class IntakeFinding(BaseModel):
    """One intake validation finding."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    code: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    field: str | None = Field(default=None, max_length=120)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "field": self.field}


class IntakeEntry(BaseModel):
    """One evidence file + provenance metadata."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    intake_id: str = Field(min_length=1, max_length=64)
    original_filename: str = Field(min_length=1, max_length=255)
    file_type: DocumentFileType
    relative_path: str = Field(min_length=1, max_length=1024)
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    intake_timestamp: datetime
    source_id: str | None = None
    achievement_candidate_ids: list[str] = Field(default_factory=list)
    proposer: str | None = Field(default=None, max_length=64)
    status: IntakeStatus = IntakeStatus.RECEIVED
    validation_findings: list[IntakeFinding] = Field(default_factory=list)

    @field_validator("intake_id")
    @classmethod
    def _validate_intake_id(cls, v: str) -> str:
        return validate_intake_id(v)

    @field_validator("original_filename")
    @classmethod
    def _validate_filename(cls, v: str) -> str:
        return _validate_original_filename(v)

    @field_validator("relative_path")
    @classmethod
    def _validate_relative_path(cls, v: str) -> str:
        return reject_unsafe_relative_path(v, must_start_with=INTAKE_ROOT_PREFIX)

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, v: str) -> str:
        if not _SHA256_RE.fullmatch(v):
            raise ValueError(
                "sha256 must be exactly 64 lowercase hex chars; "
                f"got {v!r}"
            )
        return v

    @field_validator("intake_timestamp")
    @classmethod
    def _validate_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError(
                "intake_timestamp must be timezone-aware"
            )
        return v

    @field_validator("source_id")
    @classmethod
    def _validate_source_id(cls, v: str | None) -> str | None:
        return v if v is None else validate_prefixed_id(v, "src")

    @field_validator("achievement_candidate_ids")
    @classmethod
    def _validate_candidate_ids(cls, v: list[str]) -> list[str]:
        for cid in v:
            validate_candidate_id(cid)
        if len(set(v)) != len(v):
            raise ValueError("achievement_candidate_ids must be unique")
        return v

    @field_validator("proposer")
    @classmethod
    def _validate_proposer(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_pseudonym(v)


class AchievementCandidate(BaseModel):
    """Lightweight candidate record.

    Explicitly NOT an :class:`nlp_semantic.schema.Achievement`. The
    candidate carries at most proposed values; it never enters the
    dataset's records directory until a reviewer promotes it to a real
    Achievement row through the existing workflow.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    candidate_id: str = Field(min_length=1, max_length=64)
    evidence_intake_ids: list[str] = Field(default_factory=list)
    source_id: str | None = None
    extracted_text_inline: str | None = Field(default=None, max_length=2000)
    proposed_achievement_text: str | None = Field(default=None, max_length=4000)
    proposed_primary_type: str | None = None
    proposer: str | None = Field(default=None, max_length=64)
    status: IntakeStatus = IntakeStatus.RECEIVED
    validation_findings: list[IntakeFinding] = Field(default_factory=list)

    @field_validator("candidate_id")
    @classmethod
    def _validate_candidate_id(cls, v: str) -> str:
        return validate_candidate_id(v)

    @field_validator("evidence_intake_ids")
    @classmethod
    def _validate_evidence_intake_ids(cls, v: list[str]) -> list[str]:
        for iid in v:
            validate_intake_id(iid)
        if len(set(v)) != len(v):
            raise ValueError("evidence_intake_ids must be unique")
        return v

    @field_validator("source_id")
    @classmethod
    def _validate_source_id(cls, v: str | None) -> str | None:
        return v if v is None else validate_prefixed_id(v, "src")

    @field_validator("proposed_primary_type")
    @classmethod
    def _validate_proposed_primary_type(cls, v: str | None) -> str | None:
        return v if v is None else validate_label_id(v)

    @field_validator("proposer")
    @classmethod
    def _validate_proposer(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_pseudonym(v)


# ---- exceptions ------------------------------------------------------------


class IntakeError(ValueError):
    """File-level or ingestion-level issue (missing file, unsupported
    type, filename collision with different content, etc).

    Per-entry format problems surface as :class:`pydantic.ValidationError`
    - same split as the Chunk 3 taxonomy loader, Chunk 4 ingestion loaders,
    and the Chunk 7.38B evidence-bundle loader.
    """


# ---- hashing & file ops ----------------------------------------------------


def sha256_of_file(path: Path, chunk_size: int = 65536) -> str:
    """Return the lowercase-hex SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- manifest I/O ----------------------------------------------------------


def _manifest_path(manifest_dir: Path, intake_id: str) -> Path:
    return manifest_dir / f"{intake_id}.yaml"


def _write_manifest(manifest_dir: Path, entry: IntakeEntry) -> Path:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = _manifest_path(manifest_dir, entry.intake_id)
    if path.exists():
        raise IntakeError(
            f"manifest already exists at {path}; refusing to overwrite "
            "(intake pipeline is strictly additive)"
        )
    payload = yaml.safe_dump(
        _entry_as_yaml_dict(entry),
        sort_keys=False,
        default_flow_style=False,
    )
    path.write_text(payload, encoding="utf-8")
    return path


def _entry_as_yaml_dict(entry: IntakeEntry) -> dict[str, Any]:
    """YAML-friendly representation (ISO 8601 timestamp, enum .value)."""
    return {
        "intake_id": entry.intake_id,
        "original_filename": entry.original_filename,
        "file_type": entry.file_type.value,
        "relative_path": entry.relative_path,
        "sha256": entry.sha256,
        "size_bytes": entry.size_bytes,
        "intake_timestamp": entry.intake_timestamp.isoformat(),
        "source_id": entry.source_id,
        "achievement_candidate_ids": list(entry.achievement_candidate_ids),
        "proposer": entry.proposer,
        "status": entry.status.value,
        "validation_findings": [f.to_dict() for f in entry.validation_findings],
    }


def load_intake_entry(path: str | Path) -> IntakeEntry:
    """Load one intake entry from a YAML manifest file."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise IntakeError(
            f"{p}: top-level YAML must be a mapping; got "
            f"{type(data).__name__}"
        )
    return IntakeEntry(**data)


def list_intake_entries(manifest_dir: str | Path) -> list[IntakeEntry]:
    """Return every intake entry under ``manifest_dir`` in filename order."""
    d = Path(manifest_dir)
    if not d.is_dir():
        return []
    out: list[IntakeEntry] = []
    for p in sorted(d.glob("intk_*.yaml")):
        out.append(load_intake_entry(p))
    return out


# ---- duplicate detection ---------------------------------------------------


def find_duplicate_hashes(
    manifest_dir: str | Path,
) -> dict[str, list[str]]:
    """Return ``{sha256: [intake_id, ...]}`` for hashes with >1 entries."""
    entries = list_intake_entries(manifest_dir)
    buckets: dict[str, list[str]] = {}
    for e in entries:
        buckets.setdefault(e.sha256, []).append(e.intake_id)
    return {h: ids for h, ids in buckets.items() if len(ids) > 1}


# ---- ingest ----------------------------------------------------------------


@dataclass(frozen=True)
class IntakeIngestResult:
    """Return value of :func:`ingest_evidence`."""

    entry: IntakeEntry
    manifest_path: Path
    stored_file_path: Path
    duplicate_of_intake_ids: list[str] = field(default_factory=list)


def ingest_evidence(
    source_file: str | Path,
    *,
    evidence_root: str | Path,
    manifest_dir: str | Path,
    source_id: str | None = None,
    achievement_candidate_ids: Iterable[str] | None = None,
    proposer: str | None = None,
    file_type: DocumentFileType | None = None,
) -> IntakeIngestResult:
    """Intake one reviewer-supplied evidence file.

    Steps:

    1. Verify ``source_file`` exists and the filename is safe.
    2. Classify the file type by extension (unless ``file_type`` is
       passed explicitly).
    3. Compute SHA-256 and size.
    4. Allocate a fresh ``intake_id``.
    5. Scan ``manifest_dir`` for existing entries with the same hash
       (duplicate-content detection). Allocation proceeds regardless;
       duplicates are recorded as advisory findings.
    6. Copy the source file to
       ``<evidence_root>/<intake_id>/<original_filename>``, failing if
       the destination already exists.
    7. Write a per-intake YAML manifest to
       ``<manifest_dir>/<intake_id>.yaml``, failing if the manifest
       already exists.
    8. Return an :class:`IntakeIngestResult` with the entry and the
       paths used.

    The function **never** overwrites existing files or manifests. If
    an operation would overwrite, :class:`IntakeError` is raised and
    nothing is left half-written.
    """
    src = Path(source_file)
    if not src.exists():
        raise IntakeError(f"source file not found: {src}")
    if not src.is_file():
        raise IntakeError(f"source is not a regular file: {src}")

    _validate_original_filename(src.name)

    if file_type is None:
        file_type_resolved = classify_file_type(src.name)
    else:
        file_type_resolved = file_type

    size_bytes = src.stat().st_size
    sha256 = sha256_of_file(src)

    intake_id = make_intake_id()
    now = datetime.now(timezone.utc)

    # Duplicate-content detection (scan existing manifests before allocating).
    manifest_dir_p = Path(manifest_dir)
    duplicate_of: list[str] = []
    if manifest_dir_p.exists():
        for p in sorted(manifest_dir_p.glob("intk_*.yaml")):
            try:
                prior = load_intake_entry(p)
            except (IntakeError, Exception):
                continue
            if prior.sha256 == sha256:
                duplicate_of.append(prior.intake_id)

    # Build and persist the entry.
    evidence_root_p = Path(evidence_root)
    stored_dir = evidence_root_p / intake_id
    stored_file = stored_dir / src.name

    # Relative-path strings must use forward slashes and start with the
    # intake-root prefix. The relative_path is computed from the
    # INTAKE_ROOT_PREFIX convention, not from the on-disk absolute path.
    rel_path = f"{INTAKE_ROOT_PREFIX}{intake_id}/{src.name}"
    # Validate the relative path shape against the shared path-safety
    # helper so the Pydantic field validator cannot reject it later.
    reject_unsafe_relative_path(rel_path, must_start_with=INTAKE_ROOT_PREFIX)

    # Advisory findings
    findings: list[IntakeFinding] = []
    for prior_id in duplicate_of:
        findings.append(
            IntakeFinding(
                code=IntakeValidationCode.DUPLICATE_HASH,
                message=(
                    f"this content was previously intaken as {prior_id!r} "
                    f"(same sha256)"
                ),
                field="sha256",
            )
        )
    if source_id is None:
        findings.append(
            IntakeFinding(
                code=IntakeValidationCode.MISSING_SOURCE_ASSOCIATION,
                message=(
                    "no source_id supplied; a reviewer must link this "
                    "intake entry to a SourceRegistry entry before any "
                    "downstream workflow consumes it"
                ),
                field="source_id",
            )
        )
    cand_ids = list(achievement_candidate_ids or [])
    if not cand_ids:
        findings.append(
            IntakeFinding(
                code=IntakeValidationCode.MISSING_ACHIEVEMENT_ASSOCIATION,
                message=(
                    "no achievement_candidate_ids supplied; the intake "
                    "entry stands alone and will not seed a candidate "
                    "unless a reviewer links one"
                ),
                field="achievement_candidate_ids",
            )
        )
    if size_bytes == 0:
        findings.append(
            IntakeFinding(
                code=IntakeValidationCode.EMPTY_FILE,
                message=(
                    "evidence file is empty (0 bytes); reviewers should "
                    "confirm this is intentional"
                ),
                field="size_bytes",
            )
        )
    # Authentication caveat (same spirit as Chunk 7.38B validator).
    findings.append(
        IntakeFinding(
            code=IntakeValidationCode.AUTHENTICATION_NOT_ESTABLISHED,
            message=(
                "Intake records what a reviewer supplied; it does NOT "
                "authenticate the reviewer identity, verify the source, "
                "or approve the content. Downstream workflows must "
                "complete their own review."
            ),
            field=None,
        )
    )

    entry = IntakeEntry(
        intake_id=intake_id,
        original_filename=src.name,
        file_type=file_type_resolved,
        relative_path=rel_path,
        sha256=sha256,
        size_bytes=size_bytes,
        intake_timestamp=now,
        source_id=source_id,
        achievement_candidate_ids=cand_ids,
        proposer=proposer,
        status=IntakeStatus.RECEIVED,
        validation_findings=findings,
    )

    # File copy (fail-safe, never overwrite).
    if stored_dir.exists():
        raise IntakeError(
            f"intake directory already exists at {stored_dir}; refusing "
            "to proceed (intake_id collision is a bug)"
        )
    stored_dir.mkdir(parents=True, exist_ok=False)
    data = src.read_bytes()
    stored_file.write_bytes(data)

    manifest_path = _write_manifest(manifest_dir_p, entry)
    return IntakeIngestResult(
        entry=entry,
        manifest_path=manifest_path,
        stored_file_path=stored_file,
        duplicate_of_intake_ids=duplicate_of,
    )


# ---- validation ------------------------------------------------------------


def validate_intake_entry(
    entry: IntakeEntry,
    *,
    evidence_root: str | Path,
    sources_yaml: str | Path | None = None,
    known_candidate_ids: Iterable[str] | None = None,
) -> list[IntakeFinding]:
    """Return a list of :class:`IntakeFinding` for cross-reference checks.

    Does **not** mutate ``entry``. Does **not** touch any file. If
    ``sources_yaml`` is provided, cross-checks ``entry.source_id``
    against the registered sources (unknown ids become fatal findings).
    If ``known_candidate_ids`` is provided, cross-checks any
    ``achievement_candidate_ids``.
    """
    findings: list[IntakeFinding] = []
    evidence_root_p = Path(evidence_root)

    # On-disk file existence & hash integrity (optional, best-effort)
    rel_tail = entry.relative_path[len(INTAKE_ROOT_PREFIX):]
    on_disk = evidence_root_p / rel_tail
    if not on_disk.exists():
        findings.append(
            IntakeFinding(
                code=IntakeValidationCode.FILE_NOT_FOUND,
                message=(
                    f"evidence file not found at expected location "
                    f"{on_disk!s}"
                ),
                field="relative_path",
            )
        )
    else:
        disk_hash = sha256_of_file(on_disk)
        if disk_hash != entry.sha256:
            findings.append(
                IntakeFinding(
                    code=IntakeValidationCode.HASH_MISMATCH_ON_DISK,
                    message=(
                        f"on-disk sha256 {disk_hash!r} differs from "
                        f"manifest {entry.sha256!r}; manifest may be "
                        "stale or file may have been tampered with"
                    ),
                    field="sha256",
                )
            )

    # Source cross-reference
    if sources_yaml is not None and entry.source_id is not None:
        known = _load_known_source_ids(Path(sources_yaml))
        if entry.source_id not in known:
            findings.append(
                IntakeFinding(
                    code=IntakeValidationCode.UNKNOWN_SOURCE_REFERENCE,
                    message=(
                        f"source_id {entry.source_id!r} is not registered "
                        f"in {sources_yaml!s}"
                    ),
                    field="source_id",
                )
            )

    # Candidate cross-reference
    if known_candidate_ids is not None:
        known = set(known_candidate_ids)
        for cid in entry.achievement_candidate_ids:
            if cid not in known:
                findings.append(
                    IntakeFinding(
                        code=IntakeValidationCode.UNKNOWN_ACHIEVEMENT_REFERENCE,
                        message=(
                            f"achievement_candidate_id {cid!r} not in the "
                            "supplied set of known candidate ids"
                        ),
                        field="achievement_candidate_ids",
                    )
                )

    return findings


def _load_known_source_ids(sources_yaml: Path) -> set[str]:
    """Minimal sources.yaml reader for existence checks.

    Reuses the shape expected by :mod:`nlp_semantic.ingestion.registry`
    without pulling its validator into intake. Returns the set of
    ``source_id`` values. Returns an empty set if the file is missing
    or empty.
    """
    if not sources_yaml.exists():
        return set()
    with sources_yaml.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or []
    if not isinstance(data, list):
        return set()
    ids: set[str] = set()
    for row in data:
        if isinstance(row, dict) and "source_id" in row:
            value = row["source_id"]
            if isinstance(value, str):
                ids.add(value)
    return ids
