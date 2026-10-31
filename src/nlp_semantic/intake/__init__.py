"""Reviewer-gated evidence intake pipeline.

Public API: :class:`IntakeEntry`, :class:`AchievementCandidate`,
:class:`IntakeFinding`, :class:`IntakeStatus`, :class:`IntakeError`,
:func:`ingest_evidence`, :func:`load_intake_entry`,
:func:`list_intake_entries`, :func:`find_duplicate_hashes`,
:func:`validate_intake_entry`, plus the error-code string constants.

Scope: accept reviewer-supplied evidence files, record them with a
deterministic SHA-256 hash and provenance metadata, and provide
structural validation. This module **does not** promote taxonomy
labels, verify annotations, approve sources, or make reviewer
decisions; those remain upstream and downstream human workflows.

See :mod:`nlp_semantic.intake.pipeline` for the fail-closed contract.
"""
from __future__ import annotations

from .pipeline import (
    DEFAULT_EVIDENCE_ROOT,
    DEFAULT_MANIFEST_DIR,
    INTAKE_ROOT_PREFIX,
    SUPPORTED_EXTENSIONS,
    AchievementCandidate,
    IntakeEntry,
    IntakeError,
    IntakeFinding,
    IntakeIngestResult,
    IntakeStatus,
    IntakeValidationCode,
    classify_file_type,
    find_duplicate_hashes,
    ingest_evidence,
    list_intake_entries,
    load_intake_entry,
    make_candidate_id,
    make_intake_id,
    validate_candidate_id,
    validate_intake_entry,
    validate_intake_id,
)
from .create_achievement import (
    CreateAchievementError,
    CreateAchievementErrorCode,
    CreateAchievementFinding,
    CreateAchievementResult,
    create_achievement_from_review,
)
from .promote_evidence import (
    DEFAULT_EVIDENCE_DOCUMENTS_ROOT,
    DEFAULT_EVIDENCE_RECORD_DIR,
    PromoteEvidenceError,
    PromoteEvidenceErrorCode,
    PromoteEvidenceFinding,
    PromoteEvidenceResult,
    list_evidence_records,
    load_evidence_record,
    promote_evidence,
)
from .review import (
    CandidateDecision,
    CandidateReview,
    CandidateReviewError,
    ReviewErrorCode,
    ReviewFinding,
    list_candidate_reviews,
    load_candidate_review,
    make_review_id,
    review_candidate,
    validate_review_id,
)

__all__ = [
    "AchievementCandidate",
    "DEFAULT_EVIDENCE_ROOT",
    "DEFAULT_MANIFEST_DIR",
    "INTAKE_ROOT_PREFIX",
    "IntakeEntry",
    "IntakeError",
    "IntakeFinding",
    "IntakeIngestResult",
    "IntakeStatus",
    "IntakeValidationCode",
    "SUPPORTED_EXTENSIONS",
    "classify_file_type",
    "find_duplicate_hashes",
    "ingest_evidence",
    "list_intake_entries",
    "load_intake_entry",
    "make_candidate_id",
    "make_intake_id",
    "validate_candidate_id",
    "validate_intake_entry",
    "validate_intake_id",
    # Review workflow
    "CandidateDecision",
    "CandidateReview",
    "CandidateReviewError",
    "ReviewErrorCode",
    "ReviewFinding",
    "list_candidate_reviews",
    "load_candidate_review",
    "make_review_id",
    "review_candidate",
    "validate_review_id",
    # Evidence promotion
    "DEFAULT_EVIDENCE_DOCUMENTS_ROOT",
    "DEFAULT_EVIDENCE_RECORD_DIR",
    "PromoteEvidenceError",
    "PromoteEvidenceErrorCode",
    "PromoteEvidenceFinding",
    "PromoteEvidenceResult",
    "list_evidence_records",
    "load_evidence_record",
    "promote_evidence",
    # Candidate-to-Achievement conversion (Chunk 7.47)
    "CreateAchievementError",
    "CreateAchievementErrorCode",
    "CreateAchievementFinding",
    "CreateAchievementResult",
    "create_achievement_from_review",
]
