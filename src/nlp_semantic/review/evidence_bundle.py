"""Evidence-bundle validator (read-only, fail-closed).

Validates taxonomy-promotion and annotation-review evidence bundles
against the structural requirements documented in
``hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md`` and
``hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md``.

**Fail-closed contract.** Structural validity is NOT approval:

* A bundle that passes :func:`validate_bundle` has only been checked for
  shape, arity, pseudonym format, and reviewer-independence against the
  bundle's own data. It has **not** been authenticated.
* Every report carries :attr:`ErrorCode.IDENTITY_AUTHENTICATION_NOT_ESTABLISHED`
  as a limitation unconditionally.
  Structural validity does **not** imply taxonomy approved, annotation
  verified, source verified, or record training-ready.
* The validator reads only the bundle object passed in; it never writes
  to the taxonomy YAML, the source registry, any record batch, or any
  annotation row. The eligibility conditions enforced by
  :func:`nlp_semantic.dataset.validator.training_ready_subset` are
  untouched by this module.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date as _date
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from nlp_semantic.schema import (
    AnnotationTask,
    TaxonomyStatus,
    validate_label_id,
    validate_prefixed_id,
)


# ---- enums & constants -----------------------------------------------------


class BundleType(str, Enum):
    """Shape dispatch for the validator."""

    TAXONOMY_PROMOTION = "taxonomy_promotion"
    ANNOTATION_REVIEW = "annotation_review"


class Decision(str, Enum):
    """Reviewer decision values permitted by TAXONOMY_APPROVAL_CHECKLIST.md."""

    APPROVE = "approve"
    REVISE = "revise"


class ErrorCode:
    """Stable identifiers for machine-readable findings."""

    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_DECISION = "INVALID_DECISION"
    DUPLICATE_REVIEWER = "DUPLICATE_REVIEWER"
    REVIEWER_INDEPENDENCE_NOT_ESTABLISHED = (
        "REVIEWER_INDEPENDENCE_NOT_ESTABLISHED"
    )
    MISSING_EVIDENCE_REFERENCE = "MISSING_EVIDENCE_REFERENCE"
    TARGET_ID_MISMATCH = "TARGET_ID_MISMATCH"
    UNSUPPORTED_BUNDLE_TYPE = "UNSUPPORTED_BUNDLE_TYPE"
    IDENTITY_AUTHENTICATION_NOT_ESTABLISHED = (
        "IDENTITY_AUTHENTICATION_NOT_ESTABLISHED"
    )
    PROPOSER_IS_REVIEWER = "PROPOSER_IS_REVIEWER"
    WRONG_REVIEWER_COUNT = "WRONG_REVIEWER_COUNT"
    INVALID_LABEL_ARITY = "INVALID_LABEL_ARITY"
    MIXED_BUNDLE_FIELDS = "MIXED_BUNDLE_FIELDS"


# Match the annotator pseudonym contract from Annotation schema
# (PROJECT_HANDOFF.md §4 Chunk 2): starts with word char, 2-64 total,
# word chars and hyphens only. Emails are rejected explicitly.
_PSEUDONYM_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$")
_EMAIL_LIKE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---- Pydantic shapes -------------------------------------------------------


class ReviewerSignOff(BaseModel):
    """One reviewer's sign-off, matching the TAXONOMY_APPROVAL_CHECKLIST
    §110-131 template verbatim.

    * ``reviewer`` is a pseudonym per the Annotation-schema contract;
      email-shaped strings are rejected.
    * ``rationale`` must be non-empty after whitespace strip
      (``str_strip_whitespace=True`` + ``min_length=1``). An empty
      rationale is a structural failure, not an advisory.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    reviewer: str = Field(min_length=1, max_length=64)
    date: _date
    decision: Decision
    rationale: str = Field(min_length=1, max_length=4000)
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("reviewer")
    @classmethod
    def _validate_pseudonym(cls, v: str) -> str:
        if _EMAIL_LIKE_RE.match(v):
            raise ValueError(
                "reviewer must be a pseudonym; emails are not accepted"
            )
        if not _PSEUDONYM_RE.fullmatch(v):
            raise ValueError(
                f"reviewer pseudonym {v!r} does not match the required "
                r"pattern ^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$"
            )
        return v

    @field_validator("evidence_refs")
    @classmethod
    def _validate_evidence_refs(cls, v: list[str]) -> list[str]:
        for ref in v:
            if not isinstance(ref, str) or not ref.strip():
                raise ValueError("evidence_refs entries must be non-empty strings")
            if len(ref) > 1024:
                raise ValueError("evidence_refs entries must be at most 1024 chars")
        return v


class EvidenceBundle(BaseModel):
    """One reviewer-evidence bundle (taxonomy or annotation).

    The ``bundle_type`` discriminates the per-type fields:

    * ``taxonomy_promotion`` requires ``target_current_status`` and
      exactly two reviewers.
    * ``annotation_review`` requires ``task`` and at least one reviewer;
      ``proposed_label_ids`` arity depends on the task.

    The model enforces per-field shape; semantic consistency (e.g.
    task-arity match, proposer-not-reviewer, duplicate pseudonyms) is
    enforced by :func:`validate_bundle` so individual findings can be
    reported without raising.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    bundle_id: str = Field(min_length=1, max_length=200)
    bundle_type: BundleType
    target_id: str = Field(min_length=1, max_length=120)
    proposer: str | None = Field(default=None, max_length=64)
    reviewers: list[ReviewerSignOff] = Field(default_factory=list)

    # taxonomy_promotion-only fields
    target_current_status: TaxonomyStatus | None = None

    # annotation_review-only fields
    task: AnnotationTask | None = None
    proposed_label_ids: list[str] = Field(default_factory=list)

    @field_validator("proposer")
    @classmethod
    def _validate_proposer_pseudonym(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if _EMAIL_LIKE_RE.match(v):
            raise ValueError(
                "proposer must be a pseudonym; emails are not accepted"
            )
        if not _PSEUDONYM_RE.fullmatch(v):
            raise ValueError(
                f"proposer pseudonym {v!r} does not match the required "
                "pattern"
            )
        return v


# ---- Validation result model -----------------------------------------------


@dataclass(frozen=True)
class ValidationFinding:
    """One finding (fatal, advisory, or limitation)."""

    code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "field": self.field}


@dataclass(frozen=True)
class ValidationReport:
    """Return value of :func:`validate_bundle`.

    * ``structurally_valid`` is True iff ``fatal_errors`` is empty.
    * ``authenticated`` is always False by design — reviewer identity
      authentication is out of scope and is reported as a limitation.
    * ``to_dict()`` is JSON-serializable for the CLI.
    """

    bundle_id: str
    bundle_type: str
    target_id: str
    fatal_errors: list[ValidationFinding] = field(default_factory=list)
    advisories: list[ValidationFinding] = field(default_factory=list)
    limitations: list[ValidationFinding] = field(default_factory=list)
    checks_performed: list[str] = field(default_factory=list)

    @property
    def structurally_valid(self) -> bool:
        return not self.fatal_errors

    @property
    def authenticated(self) -> bool:
        """Always False. See IDENTITY_AUTHENTICATION_NOT_ESTABLISHED."""
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "bundle_type": self.bundle_type,
            "target_id": self.target_id,
            "structurally_valid": self.structurally_valid,
            "authenticated": self.authenticated,
            "fatal_count": len(self.fatal_errors),
            "advisory_count": len(self.advisories),
            "limitation_count": len(self.limitations),
            "fatal_errors": [f.to_dict() for f in self.fatal_errors],
            "advisories": [f.to_dict() for f in self.advisories],
            "limitations": [f.to_dict() for f in self.limitations],
            "checks_performed": list(self.checks_performed),
        }


# ---- Loader ----------------------------------------------------------------


class BundleLoadError(ValueError):
    """File-level issues: top-level YAML is not a mapping, missing file, etc.

    Per-entry format problems surface as :class:`pydantic.ValidationError`
    - same split as the Chunk 3 taxonomy loader and the Chunk 4 ingestion
    loaders, so error handling is consistent across the codebase.
    """


def load_bundle(path: str | Path) -> EvidenceBundle:
    """Load one evidence bundle from a YAML file.

    Returns the Pydantic-validated :class:`EvidenceBundle`.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise BundleLoadError(
            f"{p}: top-level YAML must be a mapping; got "
            f"{type(data).__name__}"
        )
    return EvidenceBundle(**data)


# ---- Validation ------------------------------------------------------------


def validate_bundle(bundle: EvidenceBundle) -> ValidationReport:
    """Return a :class:`ValidationReport` for ``bundle``.

    The validator never raises on bundle content; findings are collected
    into the report. It never mutates ``bundle``. It never writes to any
    file. See the module docstring for the fail-closed contract.
    """
    fatal: list[ValidationFinding] = []
    advisories: list[ValidationFinding] = []
    limitations: list[ValidationFinding] = []
    checks: list[str] = []

    # Dispatch per bundle type for the per-type checks.
    if bundle.bundle_type == BundleType.TAXONOMY_PROMOTION:
        _validate_taxonomy_promotion(bundle, fatal, advisories, checks)
    elif bundle.bundle_type == BundleType.ANNOTATION_REVIEW:
        _validate_annotation_review(bundle, fatal, advisories, checks)
    else:
        # Should be unreachable given the Pydantic enum; defensive branch
        # so a future enum extension does not silently pass.
        fatal.append(
            ValidationFinding(
                code=ErrorCode.UNSUPPORTED_BUNDLE_TYPE,
                message=(
                    f"bundle_type {bundle.bundle_type!r} is not supported "
                    "by this validator"
                ),
                field="bundle_type",
            )
        )

    # Reviewer-level checks shared across bundle types
    _validate_reviewers(bundle, fatal, advisories, checks)

    # Unconditional authentication limitation — this is the fail-closed
    # anchor. Even a fully structurally valid bundle is NOT approval.
    limitations.append(
        ValidationFinding(
            code=ErrorCode.IDENTITY_AUTHENTICATION_NOT_ESTABLISHED,
            message=(
                "This validator checks structural requirements only. "
                "Reviewer pseudonyms are not authenticated; reviewer "
                "independence is procedurally required but cannot be "
                "verified from the bundle alone. Structural validity "
                "does NOT imply: taxonomy approved, annotation verified, "
                "source verified, license approved, or record training-"
                "ready."
            ),
            field=None,
        )
    )
    checks.append("identity_authentication_scope_disclaimer")

    return ValidationReport(
        bundle_id=bundle.bundle_id,
        bundle_type=bundle.bundle_type.value,
        target_id=bundle.target_id,
        fatal_errors=fatal,
        advisories=advisories,
        limitations=limitations,
        checks_performed=checks,
    )


def _validate_taxonomy_promotion(
    bundle: EvidenceBundle,
    fatal: list[ValidationFinding],
    advisories: list[ValidationFinding],
    checks: list[str],
) -> None:
    """Taxonomy promotion-specific checks (TAXONOMY_APPROVAL_CHECKLIST)."""
    checks.append("taxonomy_promotion.target_id_shape")
    try:
        validate_label_id(bundle.target_id)
    except ValueError as e:
        fatal.append(
            ValidationFinding(
                code=ErrorCode.TARGET_ID_MISMATCH,
                message=(
                    f"target_id {bundle.target_id!r} is not a valid "
                    f"label_id for taxonomy_promotion: {e}"
                ),
                field="target_id",
            )
        )

    checks.append("taxonomy_promotion.target_current_status_present")
    if bundle.target_current_status is None:
        fatal.append(
            ValidationFinding(
                code=ErrorCode.MISSING_REQUIRED_FIELD,
                message=(
                    "target_current_status is required for "
                    "taxonomy_promotion"
                ),
                field="target_current_status",
            )
        )

    # Checklist §76-77: "two reviewer sign-offs" — hard requirement.
    checks.append("taxonomy_promotion.reviewer_count_is_two")
    if len(bundle.reviewers) != 2:
        fatal.append(
            ValidationFinding(
                code=ErrorCode.WRONG_REVIEWER_COUNT,
                message=(
                    "taxonomy_promotion requires exactly 2 reviewer sign-offs "
                    "per TAXONOMY_APPROVAL_CHECKLIST.md §76-77; got "
                    f"{len(bundle.reviewers)}"
                ),
                field="reviewers",
            )
        )

    # Checklist §104-106: proposer cannot be a reviewer. If no proposer
    # was supplied we can't check this; flag it as a limitation.
    checks.append("taxonomy_promotion.proposer_identity_present")
    if bundle.proposer is None:
        advisories.append(
            ValidationFinding(
                code=ErrorCode.REVIEWER_INDEPENDENCE_NOT_ESTABLISHED,
                message=(
                    "proposer is not set; "
                    "TAXONOMY_APPROVAL_CHECKLIST §104-106 requires that the "
                    "proposer not count as a reviewer, which cannot be "
                    "checked without a proposer identifier"
                ),
                field="proposer",
            )
        )

    # Annotation-only fields should not be set in a taxonomy bundle.
    checks.append("taxonomy_promotion.annotation_fields_absent")
    if bundle.task is not None:
        advisories.append(
            ValidationFinding(
                code=ErrorCode.MIXED_BUNDLE_FIELDS,
                message=(
                    "task is set on a taxonomy_promotion bundle; the "
                    "field is ignored for this bundle type"
                ),
                field="task",
            )
        )
    if bundle.proposed_label_ids:
        advisories.append(
            ValidationFinding(
                code=ErrorCode.MIXED_BUNDLE_FIELDS,
                message=(
                    "proposed_label_ids is non-empty on a "
                    "taxonomy_promotion bundle; the field is ignored for "
                    "this bundle type"
                ),
                field="proposed_label_ids",
            )
        )


def _validate_annotation_review(
    bundle: EvidenceBundle,
    fatal: list[ValidationFinding],
    advisories: list[ValidationFinding],
    checks: list[str],
) -> None:
    """Annotation review-specific checks (ANNOTATION_GUIDELINES)."""
    checks.append("annotation_review.target_id_shape")
    try:
        validate_prefixed_id(bundle.target_id, "ach")
    except ValueError as e:
        fatal.append(
            ValidationFinding(
                code=ErrorCode.TARGET_ID_MISMATCH,
                message=(
                    f"target_id {bundle.target_id!r} is not a valid "
                    f"achievement_id for annotation_review: {e}"
                ),
                field="target_id",
            )
        )

    checks.append("annotation_review.task_present")
    if bundle.task is None:
        fatal.append(
            ValidationFinding(
                code=ErrorCode.MISSING_REQUIRED_FIELD,
                message="task is required for annotation_review",
                field="task",
            )
        )
    else:
        checks.append(
            f"annotation_review.label_arity_for_{bundle.task.value}"
        )
        n = len(bundle.proposed_label_ids)
        if bundle.task == AnnotationTask.PRIMARY_TYPE and n != 1:
            fatal.append(
                ValidationFinding(
                    code=ErrorCode.INVALID_LABEL_ARITY,
                    message=(
                        "task=primary_type requires exactly 1 label_id in "
                        f"proposed_label_ids; got {n}"
                    ),
                    field="proposed_label_ids",
                )
            )
        elif bundle.task == AnnotationTask.EXTRACTION_REVIEW and n != 0:
            fatal.append(
                ValidationFinding(
                    code=ErrorCode.INVALID_LABEL_ARITY,
                    message=(
                        "task=extraction_review requires 0 label_ids in "
                        f"proposed_label_ids; got {n}"
                    ),
                    field="proposed_label_ids",
                )
            )
        # domain_tags allows 0..N; no arity check

    # Validate each proposed label_id has the correct lbl_... format.
    checks.append("annotation_review.proposed_label_id_shapes")
    for i, lid in enumerate(bundle.proposed_label_ids):
        try:
            validate_label_id(lid)
        except ValueError as e:
            fatal.append(
                ValidationFinding(
                    code=ErrorCode.TARGET_ID_MISMATCH,
                    message=(
                        f"proposed_label_ids[{i}] {lid!r} is not a valid "
                        f"label_id: {e}"
                    ),
                    field=f"proposed_label_ids[{i}]",
                )
            )

    # Single-review workflow permits >= 1 reviewer; dual review allowed.
    checks.append("annotation_review.reviewer_count_at_least_one")
    if len(bundle.reviewers) < 1:
        fatal.append(
            ValidationFinding(
                code=ErrorCode.WRONG_REVIEWER_COUNT,
                message=(
                    "annotation_review requires at least 1 reviewer "
                    f"sign-off; got {len(bundle.reviewers)}"
                ),
                field="reviewers",
            )
        )

    # Taxonomy-only field should not be set.
    checks.append("annotation_review.taxonomy_fields_absent")
    if bundle.target_current_status is not None:
        advisories.append(
            ValidationFinding(
                code=ErrorCode.MIXED_BUNDLE_FIELDS,
                message=(
                    "target_current_status is set on an annotation_review "
                    "bundle; the field is ignored for this bundle type"
                ),
                field="target_current_status",
            )
        )


def _validate_reviewers(
    bundle: EvidenceBundle,
    fatal: list[ValidationFinding],
    advisories: list[ValidationFinding],
    checks: list[str],
) -> None:
    """Reviewer-level checks shared by all bundle types."""
    checks.append("reviewers.pseudonyms_distinct")
    pseudonyms = [r.reviewer for r in bundle.reviewers]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for p in pseudonyms:
        if p in seen:
            duplicates.add(p)
        else:
            seen.add(p)
    for dup in sorted(duplicates):
        fatal.append(
            ValidationFinding(
                code=ErrorCode.DUPLICATE_REVIEWER,
                message=(
                    f"reviewer pseudonym {dup!r} appears "
                    f"{pseudonyms.count(dup)} times; "
                    "TAXONOMY_APPROVAL_CHECKLIST §84-107 requires distinct "
                    "reviewer identities"
                ),
                field="reviewers",
            )
        )

    checks.append("reviewers.proposer_not_in_reviewers")
    if bundle.proposer is not None and bundle.proposer in pseudonyms:
        fatal.append(
            ValidationFinding(
                code=ErrorCode.PROPOSER_IS_REVIEWER,
                message=(
                    f"proposer {bundle.proposer!r} must not also appear "
                    "as a reviewer per TAXONOMY_APPROVAL_CHECKLIST §104-106"
                ),
                field="proposer",
            )
        )

    # Advisory: evidence refs recommended but not required
    checks.append("reviewers.evidence_refs_recommended")
    for i, r in enumerate(bundle.reviewers):
        if not r.evidence_refs:
            advisories.append(
                ValidationFinding(
                    code=ErrorCode.MISSING_EVIDENCE_REFERENCE,
                    message=(
                        f"reviewers[{i}] has no evidence_refs; linking the "
                        "promotion packet or source materials is "
                        "recommended for the audit trail (not required by "
                        "the checklist template, so this is advisory)"
                    ),
                    field=f"reviewers[{i}].evidence_refs",
                )
            )


__all__ = [
    "BundleType",
    "Decision",
    "ErrorCode",
    "ReviewerSignOff",
    "EvidenceBundle",
    "ValidationFinding",
    "ValidationReport",
    "BundleLoadError",
    "load_bundle",
    "validate_bundle",
]
