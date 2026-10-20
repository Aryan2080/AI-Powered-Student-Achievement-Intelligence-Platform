"""Tests for Evidence model and path-safety validators."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from nlp_semantic.schema import (
    APPROVED_EVIDENCE_PREFIX,
    DocumentFileType,
    Evidence,
    ExtractionMethod,
    PROCESSED_TEXT_PREFIX,
    ReviewStatus,
    make_id,
)

VALID_PATH = APPROVED_EVIDENCE_PREFIX + "cert_001.pdf"


def _minimal(**overrides) -> dict:
    base = {
        "evidence_id": make_id("evd"),
        "relative_path": VALID_PATH,
        "file_type": DocumentFileType.PDF,
        "is_synthetic": True,
    }
    base.update(overrides)
    return base


def test_minimal_valid() -> None:
    e = Evidence(**_minimal())
    assert e.extraction_method == ExtractionMethod.NONE_YET
    assert e.review_status == ReviewStatus.UNREVIEWED
    assert e.ocr_confidence is None


@pytest.mark.parametrize(
    "bad_path",
    [
        "/absolute/path.pdf",                                              # POSIX absolute
        "C:/windows.pdf",                                                   # Windows absolute
        "..\\escape.pdf",                                                   # backslash + .. (backslash rejected first)
        "hybrid_dataset/raw/evidence_documents/../secret.pdf",              # path traversal
        "hybrid_dataset/raw/other/wrong.pdf",                               # outside approved prefix
        "evidence/cert.pdf",                                                # outside approved prefix
        "hybrid_dataset/raw/evidence_documents//double_slash.pdf",          # empty segment
        "hybrid_dataset/raw/evidence_documents/\\mixed.pdf",                # backslash
    ],
)
def test_unsafe_paths_rejected(bad_path: str) -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(relative_path=bad_path))


def test_safe_subpath_allowed() -> None:
    e = Evidence(**_minimal(
        relative_path=APPROVED_EVIDENCE_PREFIX + "2024/batch1/cert.pdf"
    ))
    assert e.relative_path.startswith(APPROVED_EVIDENCE_PREFIX)


def test_original_filename_slash_rejected() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(original_filename="dir/file.pdf"))


def test_original_filename_backslash_rejected() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(original_filename="dir\\file.pdf"))


def test_original_filename_dotdot_rejected() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(original_filename=".."))


def test_original_filename_valid_allowed() -> None:
    e = Evidence(**_minimal(original_filename="cert_001.pdf"))
    assert e.original_filename == "cert_001.pdf"


def test_mutually_exclusive_text_fields() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(
            extracted_text_inline="hello",
            extracted_text_ref=PROCESSED_TEXT_PREFIX + "extracted/x.txt",
        ))


def test_inline_only_allowed() -> None:
    e = Evidence(**_minimal(extracted_text_inline="short cert body"))
    assert e.extracted_text_inline == "short cert body"


def test_inline_text_length_cap() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(extracted_text_inline="x" * 2001))


def test_ref_only_allowed() -> None:
    ref = PROCESSED_TEXT_PREFIX + "extracted/x.txt"
    e = Evidence(**_minimal(extracted_text_ref=ref))
    assert e.extracted_text_ref == ref


def test_ref_outside_processed_rejected() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(extracted_text_ref="hybrid_dataset/raw/other.txt"))


def test_ref_with_traversal_rejected() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(extracted_text_ref=PROCESSED_TEXT_PREFIX + "../x.txt"))


def test_ocr_confidence_without_ocr_method_rejected() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(
            extraction_method=ExtractionMethod.DIGITAL_TEXT,
            ocr_confidence=0.9,
        ))


def test_ocr_confidence_with_ocr_method_allowed() -> None:
    e = Evidence(**_minimal(
        extraction_method=ExtractionMethod.OCR_TESSERACT,
        ocr_confidence=0.87,
    ))
    assert e.ocr_confidence == 0.87


def test_ocr_confidence_none_with_ocr_method_allowed() -> None:
    e = Evidence(**_minimal(
        extraction_method=ExtractionMethod.OCR_OTHER,
        ocr_confidence=None,
    ))
    assert e.ocr_confidence is None


@pytest.mark.parametrize("bad", [-0.1, 1.1, 2.0, -0.0001])
def test_ocr_confidence_range(bad: float) -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(
            extraction_method=ExtractionMethod.OCR_TESSERACT,
            ocr_confidence=bad,
        ))


def test_linked_achievement_prefix_checked() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(linked_achievement_id="src_" + "a" * 32))


def test_linked_achievement_valid_allowed() -> None:
    aid = make_id("ach")
    e = Evidence(**_minimal(linked_achievement_id=aid))
    assert e.linked_achievement_id == aid


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(mystery="x"))


def test_evidence_id_prefix_checked() -> None:
    with pytest.raises(ValidationError):
        Evidence(**_minimal(evidence_id=make_id("ach")))
