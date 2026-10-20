"""Controlled vocabularies for the schema.

All enums subclass ``(str, Enum)`` so values serialize to plain JSON strings
and remain compatible with Python 3.10+ (``enum.StrEnum`` is 3.11+).
"""
from __future__ import annotations

from enum import Enum


class AnnotationStatus(str, Enum):
    """Task-level annotation status.

    Used in ``Achievement.annotation_status.{primary_type, domain_tags}``
    (the current summary per task) and in ``Annotation.review_status``
    (the status of one individual decision).

    ``NOT_STARTED`` is valid on ``Achievement.annotation_status`` and means
    *no annotation has been performed for this task*. It is explicitly
    forbidden on ``Annotation.review_status``, because an ``Annotation``
    row represents a decision that was made.
    """

    NOT_STARTED = "not_started"
    DRAFT = "draft"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    CONFLICTED = "conflicted"


class ReviewStatus(str, Enum):
    """Record-level review state for artifacts (Evidence, SourceRegistry)."""

    UNREVIEWED = "unreviewed"
    IN_REVIEW = "in_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class AnnotationTask(str, Enum):
    """Tasks an ``Annotation`` record can describe."""

    PRIMARY_TYPE = "primary_type"
    DOMAIN_TAGS = "domain_tags"
    EXTRACTION_REVIEW = "extraction_review"


class TaxonomyTask(str, Enum):
    """Tasks whose labels live in ``LabelTaxonomy``.

    Strict subset of ``AnnotationTask`` — ``extraction_review`` has no
    taxonomy labels and is intentionally excluded here.
    """

    PRIMARY_TYPE = "primary_type"
    DOMAIN_TAGS = "domain_tags"


class TaxonomyStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class DocumentFileType(str, Enum):
    PDF = "pdf"
    IMAGE_JPG = "image_jpg"
    IMAGE_PNG = "image_png"
    IMAGE_TIFF = "image_tiff"
    TEXT = "text"
    OTHER = "other"


class ExtractionMethod(str, Enum):
    DIGITAL_TEXT = "digital_text"
    OCR_TESSERACT = "ocr_tesseract"
    OCR_OTHER = "ocr_other"
    NONE_YET = "none_yet"
