"""
tests/test_document_ingestion.py
================================
Unit and Integration Tests for Evidence Document Ingestion & Text Extraction
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

import io
from pathlib import Path
import pytest
from PIL import Image

from src.nlp.document_ingestion import (
    DocumentFormat,
    ExtractionMethod,
    ExtractionStatus,
    PageExtractionResult,
    DocumentExtractionResult,
    detect_document_format,
    is_ocr_available,
    get_ocr_engine_info,
    normalize_extracted_text,
    compute_levenshtein_distance,
    compute_ocr_metrics,
    extract_text_from_pdf,
    extract_text_from_image,
    ingest_document,
    batch_ingest_documents,
)
from src.nlp.create_test_fixtures import generate_all_fixtures

FIXTURES_DIR = Path("tests/fixtures/documents")


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures():
    """Ensure test fixtures exist before running tests."""
    return generate_all_fixtures(FIXTURES_DIR)


# Mock OCR callable for predictable test transcribing
def mock_ocr_transcriber(img: Image.Image) -> str:
    """Mock OCR callable returning synthetic certificate text."""
    return "STATE ROBOTICS CHAMPIONSHIP 2024\nExcellence in Autonomous Navigation Award\nAwarded to Team Quantum Dynamics"


# ==============================================================================
# 1. VALID PDF (TEXT-BASED)
# ==============================================================================

def test_valid_text_pdf():
    """Verify single-page text PDF ingestion with native extraction."""
    pdf_path = FIXTURES_DIR / "valid_certificate.pdf"
    result = ingest_document(pdf_path)

    assert result.overall_status == ExtractionStatus.SUCCESS
    assert result.file_type == DocumentFormat.PDF
    assert result.total_pages == 1
    assert result.primary_extraction_method == ExtractionMethod.NATIVE_PDF
    assert not result.is_scanned
    assert "CERTIFICATE OF ACHIEVEMENT" in result.full_raw_text
    assert "Alex Rivera" in result.full_raw_text
    assert "ACM" in result.full_raw_text
    assert result.pages[0].char_count > 50
    assert result.pages[0].word_count > 10
    assert result.pages[0].page_number == 1


# ==============================================================================
# 2. TEXT-BASED PDF (MULTI-PAGE)
# ==============================================================================

def test_multipage_text_pdf():
    """Verify multi-page text PDF extracts all pages with 100% fidelity."""
    pdf_path = FIXTURES_DIR / "multipage_transcript.pdf"
    result = ingest_document(pdf_path)

    assert result.overall_status == ExtractionStatus.SUCCESS
    assert result.total_pages == 3
    assert len(result.pages) == 3
    assert result.primary_extraction_method == ExtractionMethod.NATIVE_PDF

    # Verify per-page contents
    assert "Academic Honors" in result.pages[0].raw_text
    assert "Research Fellowship" in result.pages[1].raw_text
    assert "Capstone Design" in result.pages[2].raw_text

    # Page numbering
    for idx, page in enumerate(result.pages):
        assert page.page_number == idx + 1
        assert page.status == ExtractionStatus.SUCCESS
        assert page.extraction_method == ExtractionMethod.NATIVE_PDF


# ==============================================================================
# 3. IMAGE-BASED PDF (SCANNED)
# ==============================================================================

def test_image_pdf_scanned():
    """Verify scanned PDF is recognized as scanned with embedded images."""
    pdf_path = FIXTURES_DIR / "scanned_award.pdf"
    result = ingest_document(pdf_path, ocr_callable=mock_ocr_transcriber)

    assert result.file_type == DocumentFormat.PDF
    assert result.total_pages == 1
    assert result.is_scanned is True
    assert result.primary_extraction_method == ExtractionMethod.OCR
    assert result.overall_status == ExtractionStatus.OCR_FALLBACK_APPLIED
    assert "STATE ROBOTICS CHAMPIONSHIP" in result.full_raw_text


# ==============================================================================
# 4. PNG INPUT
# ==============================================================================

def test_png_input():
    """Verify PNG certificate image ingestion with metadata capture."""
    png_path = FIXTURES_DIR / "certificate_badge.png"
    result = ingest_document(png_path, ocr_callable=lambda img: "CLOUD ARCHITECT CERTIFIED ASSOCIATE\nAWS-CCA-7719")

    assert result.file_type == DocumentFormat.PNG
    assert result.total_pages == 1
    assert result.is_scanned is True
    assert result.primary_extraction_method == ExtractionMethod.OCR
    assert result.overall_status == ExtractionStatus.SUCCESS
    assert "CLOUD ARCHITECT" in result.full_raw_text
    assert result.metadata["width"] == 800
    assert result.metadata["height"] == 500
    assert result.metadata["format"] == "PNG"


# ==============================================================================
# 5. JPEG INPUT
# ==============================================================================

def test_jpeg_input():
    """Verify JPEG image ingestion and dimensions."""
    jpg_path = FIXTURES_DIR / "honor_roll.jpg"
    result = ingest_document(jpg_path, ocr_callable=lambda img: "ANNUAL DEAN'S HONOR ROLL 2024")

    assert result.file_type == DocumentFormat.JPEG
    assert result.total_pages == 1
    assert result.is_scanned is True
    assert result.overall_status == ExtractionStatus.SUCCESS
    assert "DEAN'S HONOR ROLL" in result.full_raw_text
    assert result.metadata["format"] in ("JPEG", "JPG")


# ==============================================================================
# 6. UNSUPPORTED FILE FORMAT
# ==============================================================================

def test_unsupported_format():
    """Verify explicit structured rejection of unsupported file extensions."""
    docx_path = FIXTURES_DIR / "unsupported_report.docx"
    result = ingest_document(docx_path)

    assert result.file_type == DocumentFormat.UNSUPPORTED
    assert result.overall_status == ExtractionStatus.UNSUPPORTED_FORMAT
    assert result.total_pages == 0
    assert result.full_raw_text == ""
    assert len(result.warnings) > 0
    assert "Unsupported evidence document format" in result.warnings[0]


# ==============================================================================
# 7. EMPTY DOCUMENT (0 BYTES)
# ==============================================================================

def test_empty_document():
    """Verify 0-byte document is flagged as EMPTY_DOCUMENT without error."""
    empty_path = FIXTURES_DIR / "empty_doc.pdf"
    result = ingest_document(empty_path)

    assert result.overall_status == ExtractionStatus.EMPTY_DOCUMENT
    assert result.total_pages == 0
    assert result.full_raw_text == ""
    assert "empty" in result.warnings[0].lower()


# ==============================================================================
# 8. CORRUPTED DOCUMENT
# ==============================================================================

def test_corrupted_document():
    """Verify corrupted file is safely intercepted and flagged."""
    corrupt_path = FIXTURES_DIR / "corrupt_doc.pdf"
    result = ingest_document(corrupt_path)

    assert result.overall_status == ExtractionStatus.CORRUPTED_FILE
    assert result.total_pages == 0
    assert result.full_raw_text == ""
    assert len(result.warnings) > 0


# ==============================================================================
# 9. MULTI-PAGE DOCUMENT PROVENANCE
# ==============================================================================

def test_multipage_document_provenance():
    """Verify page-level character and word count provenance."""
    pdf_path = FIXTURES_DIR / "multipage_transcript.pdf"
    result = ingest_document(pdf_path)

    for page in result.pages:
        assert page.page_number in (1, 2, 3)
        assert page.char_count == len(page.normalized_text)
        assert page.word_count == len(page.normalized_text.split())
        assert page.char_count > 0
        assert page.word_count > 0


# ==============================================================================
# 10. OCR FALLBACK APPLIED
# ==============================================================================

def test_ocr_fallback_applied():
    """Verify OCR fallback is triggered when native text extraction is sparse."""
    pdf_path = FIXTURES_DIR / "scanned_award.pdf"
    result = ingest_document(
        pdf_path,
        ocr_fallback=True,
        ocr_callable=mock_ocr_transcriber,
    )

    assert result.pages[0].status == ExtractionStatus.OCR_FALLBACK_APPLIED
    assert result.pages[0].extraction_method == ExtractionMethod.OCR
    assert "ROBOTICS" in result.pages[0].raw_text


# ==============================================================================
# 11. MISSING OCR DEPENDENCY HANDLING
# ==============================================================================

def test_missing_ocr_dependency_handling(monkeypatch):
    """Verify graceful status when OCR engine is missing."""
    import src.nlp.document_ingestion as di
    # Force OCR available check to return False
    monkeypatch.setattr(di, "is_ocr_available", lambda: False)

    pdf_path = FIXTURES_DIR / "scanned_award.pdf"
    result = di.ingest_document(pdf_path, ocr_callable=None)

    assert result.overall_status == ExtractionStatus.OCR_UNAVAILABLE
    assert any("OCR engine is unavailable" in w for w in result.warnings)


# ==============================================================================
# 12. EXTRACTION FAILURE HANDLING
# ==============================================================================

def test_extraction_failure_handling():
    """Verify unhandled stream reading returns CORRUPTED_FILE."""
    fake_stream = io.BytesIO(b"%PDF-1.4\nBROKEN_INTERNAL_STREAM_DATA_HERE\n%%EOF")
    result = extract_text_from_pdf(fake_stream)

    assert result.overall_status in (ExtractionStatus.CORRUPTED_FILE, ExtractionStatus.EMPTY_DOCUMENT)


# ==============================================================================
# 13. PAGE-LEVEL PROVENANCE
# ==============================================================================

def test_page_level_provenance():
    """Verify each page has independent provenance, metadata, and serialization."""
    pdf_path = FIXTURES_DIR / "multipage_transcript.pdf"
    result = ingest_document(pdf_path)

    d = result.to_dict()
    assert isinstance(d["pages"], list)
    assert len(d["pages"]) == 3
    assert d["pages"][0]["page_number"] == 1
    assert d["pages"][1]["page_number"] == 2
    assert d["pages"][2]["page_number"] == 3


# ==============================================================================
# 14. ORIGINAL TEXT PRESERVATION
# ==============================================================================

def test_original_text_preservation():
    """Verify full_raw_text preserves exact text casing and symbols."""
    pdf_path = FIXTURES_DIR / "valid_certificate.pdf"
    result = ingest_document(pdf_path)

    # Raw text preserves exact capital letters and punctuation
    assert "CERTIFICATE OF ACHIEVEMENT" in result.full_raw_text
    assert "ACM" in result.full_raw_text
    assert "CERT-ACH-2024-9981" in result.full_raw_text


# ==============================================================================
# 15. REPRODUCIBLE OUTPUT
# ==============================================================================

def test_reproducible_output():
    """Verify multiple ingestions of the same file yield identical results."""
    pdf_path = FIXTURES_DIR / "valid_certificate.pdf"
    res1 = ingest_document(pdf_path, document_id="FIXED-DOC-001")
    res2 = ingest_document(pdf_path, document_id="FIXED-DOC-001")

    assert res1.to_dict() == res2.to_dict()


# ==============================================================================
# 16. INVALID INPUT
# ==============================================================================

def test_invalid_input():
    """Verify None raises ValueError and non-existent path returns FILE_NOT_FOUND."""
    with pytest.raises(ValueError):
        ingest_document(None)

    non_existent = Path("non_existent_certificate_file_99999.pdf")
    res = ingest_document(non_existent)
    assert res.overall_status == ExtractionStatus.FILE_NOT_FOUND
    assert "File does not exist" in res.warnings[0]


# ==============================================================================
# 17. HYBRID PDF (PAGE 1 TEXT, PAGE 2 SCANNED)
# ==============================================================================

def test_hybrid_pdf_extraction():
    """Verify hybrid PDF correctly identifies mixed extraction methods."""
    hybrid_path = FIXTURES_DIR / "hybrid_portfolio.pdf"
    result = ingest_document(hybrid_path, ocr_callable=mock_ocr_transcriber)

    assert result.total_pages == 2
    assert result.primary_extraction_method == ExtractionMethod.HYBRID
    assert result.pages[0].extraction_method == ExtractionMethod.NATIVE_PDF
    assert result.pages[1].extraction_method == ExtractionMethod.OCR
    assert "PORTFOLIO COVER SHEET" in result.pages[0].raw_text
    assert "STATE ROBOTICS CHAMPIONSHIP" in result.pages[1].raw_text


# ==============================================================================
# 18. FORMAT DETECTION TESTS
# ==============================================================================

def test_detect_document_format():
    """Verify magic bytes and extension detection for all formats."""
    assert detect_document_format(b"%PDF-1.4\n...") == DocumentFormat.PDF
    assert detect_document_format(b"\x89PNG\r\n\x1a\n\x00...") == DocumentFormat.PNG
    assert detect_document_format(b"\xff\xd8\xff\xe0\x00...") == DocumentFormat.JPEG
    assert detect_document_format(b"RANDOM_BYTES", filename="test.pdf") == DocumentFormat.PDF
    assert detect_document_format(b"RANDOM_BYTES", filename="badge.png") == DocumentFormat.PNG
    assert detect_document_format(b"RANDOM_BYTES", filename="photo.jpg") == DocumentFormat.JPEG
    assert detect_document_format(b"RANDOM_BYTES", filename="notes.docx") == DocumentFormat.UNSUPPORTED


# ==============================================================================
# 19. OCR METRICS (CER, WER, F1)
# ==============================================================================

def test_compute_ocr_metrics():
    """Verify Levenshtein CER, WER, and token overlap computation."""
    gt = "Certificate of Achievement Awarded to Alex Rivera"
    hyp_exact = "Certificate of Achievement Awarded to Alex Rivera"
    m_exact = compute_ocr_metrics(gt, hyp_exact)

    assert m_exact["cer"] == 0.0
    assert m_exact["wer"] == 0.0
    assert m_exact["word_f1"] == 1.0

    # Slight typo: 'Certificte' instead of 'Certificate'
    hyp_typo = "Certificte of Achievement Awarded to Alex Rivera"
    m_typo = compute_ocr_metrics(gt, hyp_typo)
    assert m_typo["cer"] > 0.0
    assert m_typo["cer"] < 0.05
    assert m_typo["wer"] > 0.0
    assert m_typo["word_f1"] > 0.85


# ==============================================================================
# 20. BATCH INGESTION
# ==============================================================================

def test_batch_ingest_documents():
    """Verify batch ingestion processes multiple documents correctly."""
    paths = [
        FIXTURES_DIR / "valid_certificate.pdf",
        FIXTURES_DIR / "multipage_transcript.pdf",
        FIXTURES_DIR / "unsupported_report.docx",
    ]
    results = batch_ingest_documents(paths)

    assert len(results) == 3
    assert results[0].overall_status == ExtractionStatus.SUCCESS
    assert results[1].overall_status == ExtractionStatus.SUCCESS
    assert results[2].overall_status == ExtractionStatus.UNSUPPORTED_FORMAT
