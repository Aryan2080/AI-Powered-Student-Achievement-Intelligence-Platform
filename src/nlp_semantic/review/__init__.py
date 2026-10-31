"""Reviewer-evidence bundle validation (read-only, fail-closed).

Public API: :class:`EvidenceBundle`, :class:`ReviewerSignOff`,
:class:`ValidationReport`, :func:`validate_bundle`, :func:`load_bundle`,
plus the :class:`BundleType`, :class:`Decision`, and :class:`ErrorCode`
constants.

Scope: structural validation of taxonomy-promotion and
annotation-review evidence bundles against the shape mandated by
``hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md`` and
``hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md``. **Not** reviewer
identity authentication; **not** taxonomy promotion; **not**
annotation verification; **not** source approval. See the module
docstring in :mod:`nlp_semantic.review.evidence_bundle` for the
fail-closed contract.
"""
from __future__ import annotations

from .evidence_bundle import (
    BundleLoadError,
    BundleType,
    Decision,
    ErrorCode,
    EvidenceBundle,
    ReviewerSignOff,
    ValidationFinding,
    ValidationReport,
    load_bundle,
    validate_bundle,
)

__all__ = [
    "BundleLoadError",
    "BundleType",
    "Decision",
    "ErrorCode",
    "EvidenceBundle",
    "ReviewerSignOff",
    "ValidationFinding",
    "ValidationReport",
    "load_bundle",
    "validate_bundle",
]
