"""Data contract for the hybrid achievement dataset.

Public API: Pydantic v2 models and enums for ``Achievement``, ``Evidence``,
``Annotation``, ``SourceRegistry``, and ``LabelTaxonomy``, plus ID helpers
and small shared constants.

See ``schema/README.md`` for the full data dictionary, missing-value
conventions, and privacy notes.
"""
from __future__ import annotations

from .achievement import Achievement, AnnotationStatusMap
from .annotation import Annotation
from .enums import (
    AnnotationStatus,
    AnnotationTask,
    DocumentFileType,
    ExtractionMethod,
    ReviewStatus,
    TaxonomyStatus,
    TaxonomyTask,
)
from .evidence import (
    APPROVED_EVIDENCE_PREFIX,
    MAX_INLINE_TEXT,
    PROCESSED_TEXT_PREFIX,
    Evidence,
)
from .identifiers import make_id, validate_label_id, validate_prefixed_id
from .label_taxonomy import LabelTaxonomy
from .loader import (
    TaxonomyError,
    load_and_validate_taxonomy,
    load_taxonomy,
    validate_taxonomy,
)
from .source_registry import CredentialInUrlError, UNKNOWN_LICENSE, SourceRegistry

__all__ = [
    # Models
    "Achievement",
    "AnnotationStatusMap",
    "Annotation",
    "Evidence",
    "LabelTaxonomy",
    "SourceRegistry",
    # Enums
    "AnnotationStatus",
    "AnnotationTask",
    "DocumentFileType",
    "ExtractionMethod",
    "ReviewStatus",
    "TaxonomyStatus",
    "TaxonomyTask",
    # Exceptions
    "CredentialInUrlError",
    "TaxonomyError",
    # Helpers / loaders / constants
    "make_id",
    "validate_prefixed_id",
    "validate_label_id",
    "load_taxonomy",
    "validate_taxonomy",
    "load_and_validate_taxonomy",
    "APPROVED_EVIDENCE_PREFIX",
    "PROCESSED_TEXT_PREFIX",
    "MAX_INLINE_TEXT",
    "UNKNOWN_LICENSE",
]
