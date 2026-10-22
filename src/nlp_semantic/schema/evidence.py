"""Evidence model.

Path-safety rules for ``relative_path`` and ``extracted_text_ref`` live in
:mod:`nlp_semantic.schema.path_safety` and are reused by the Chunk 4
manifest module. Evidence's public behavior, API, and error messages are
unchanged by that extraction.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import DocumentFileType, ExtractionMethod, ReviewStatus
from .identifiers import validate_prefixed_id
from .path_safety import (
    APPROVED_EVIDENCE_PREFIX,
    PROCESSED_TEXT_PREFIX,
    reject_unsafe_relative_path,
)

MAX_INLINE_TEXT = 2000

OCR_METHODS = {ExtractionMethod.OCR_TESSERACT, ExtractionMethod.OCR_OTHER}


def _validate_original_filename(v: str | None) -> str | None:
    if v is None:
        return v
    if not v:
        raise ValueError("original_filename must be non-empty")
    if "/" in v or "\\" in v:
        raise ValueError("original_filename must not contain path separators")
    if v in {".", ".."}:
        raise ValueError("original_filename must not be '.' or '..'")
    return v


class Evidence(BaseModel):
    """One evidence artifact (PDF, image, text) with extraction metadata.

    Linked to zero or one ``Achievement``. The schema stores metadata and a
    reference to the file; the raw file itself stays under
    ``hybrid_dataset/raw/evidence_documents/`` and is never committed.

    Privacy note: ``original_filename`` and ``extracted_text_inline`` may
    contain personal information. Downstream code must not log these
    fields indiscriminately. See ``schema/README.md``.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    evidence_id: str
    linked_achievement_id: str | None = None
    relative_path: str
    original_filename: str | None = None
    file_type: DocumentFileType
    document_type: str | None = Field(default=None, max_length=120)
    extraction_method: ExtractionMethod = ExtractionMethod.NONE_YET
    extracted_text_ref: str | None = None
    extracted_text_inline: str | None = Field(default=None, max_length=MAX_INLINE_TEXT)
    ocr_confidence: float | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    is_synthetic: bool = False

    @field_validator("evidence_id")
    @classmethod
    def _validate_evidence_id(cls, v: str) -> str:
        return validate_prefixed_id(v, "evd")

    @field_validator("linked_achievement_id")
    @classmethod
    def _validate_linked_achievement_id(cls, v: str | None) -> str | None:
        return v if v is None else validate_prefixed_id(v, "ach")

    @field_validator("relative_path")
    @classmethod
    def _validate_relative_path(cls, v: str) -> str:
        return reject_unsafe_relative_path(v, must_start_with=APPROVED_EVIDENCE_PREFIX)

    @field_validator("original_filename")
    @classmethod
    def _validate_original_filename(cls, v: str | None) -> str | None:
        return _validate_original_filename(v)

    @field_validator("extracted_text_ref")
    @classmethod
    def _validate_extracted_text_ref(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return reject_unsafe_relative_path(v, must_start_with=PROCESSED_TEXT_PREFIX)

    @field_validator("ocr_confidence")
    @classmethod
    def _validate_ocr_confidence(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if not (0.0 <= v <= 1.0):
            raise ValueError("ocr_confidence must be in [0.0, 1.0]")
        return v

    @model_validator(mode="after")
    def _check_cross_fields(self) -> "Evidence":
        if (
            self.extracted_text_ref is not None
            and self.extracted_text_inline is not None
        ):
            raise ValueError(
                "extracted_text_ref and extracted_text_inline are mutually "
                "exclusive; set at most one."
            )
        if self.ocr_confidence is not None and self.extraction_method not in OCR_METHODS:
            raise ValueError(
                "ocr_confidence may only be set when extraction_method is an "
                "OCR method (ocr_tesseract or ocr_other)."
            )
        return self
