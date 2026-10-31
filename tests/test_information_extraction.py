"""
tests/test_information_extraction.py
====================================
Unit and Integration Tests for Structured Evidence Information Extraction
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from PIL import Image

from src.nlp.document_ingestion import (
    DocumentFormat,
    DocumentExtractionResult,
    ExtractionMethod,
    ExtractionStatus,
    PageExtractionResult,
    ingest_document,
)
from src.nlp.information_extraction import (
    ConfidenceStatus,
    ExtractionSource,
    ExtractedField,
    StructuredEvidenceExtraction,
    EvidenceInformationExtractor,
    extract_information_from_document,
    extract_information_from_text,
    get_default_extractor,
)
from src.nlp.create_test_fixtures import generate_all_fixtures

FIXTURES_DIR = Path("tests/fixtures/documents")
EVAL_SAMPLES_PATH = Path("data/annotations/extraction_evaluation_samples.jsonl")


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures():
    """Ensure document fixtures exist before tests run."""
    return generate_all_fixtures(FIXTURES_DIR)


@pytest.fixture(scope="session")
def extractor():
    """Shared default extractor with classifier and skill normalizer."""
    return get_default_extractor()


# ==============================================================================
# 1. VALID CERTIFICATE EXTRACTION
# ==============================================================================

def test_extract_from_valid_certificate_text(extractor):
    """Verify extraction from standard certificate text."""
    text = (
        "CERTIFICATE OF ACHIEVEMENT\n"
        "This certifies that Alex Rivera\n"
        "has achieved First Place in the National Collegiate Hackathon 2024\n"
        "Organized by the Association for Computing Machinery (ACM)\n"
        "Award Date: October 15, 2024\n"
        "Issued under Certificate ID: CERT-ACH-2024-9981"
    )
    result = extractor.extract_from_text(text)

    assert result.student_name.value == "Alex Rivera"
    assert result.student_name.confidence_status == ConfidenceStatus.HIGH
    assert result.achievement_title.value == "National Collegiate Hackathon 2024"
    assert result.organization.value == "Association for Computing Machinery"
    assert result.rank.value == "1st Place"
    assert result.outcome.value == "WINNER"
    assert result.level.value == "NATIONAL"
    assert result.issue_date.value == "2024-10-15"
    assert result.certificate_id.value == "CERT-ACH-2024-9981"
    assert result.category.value == "HACKATHON"
    assert not result.review_required


# ==============================================================================
# 2. INTEGRATION WITH STEP 6 DOCUMENT INGESTION
# ==============================================================================

def test_extract_from_document_result_native(extractor):
    """Verify end-to-end extraction from a native PDF DocumentExtractionResult."""
    doc_res = ingest_document(FIXTURES_DIR / "valid_certificate.pdf")
    ext_res = extractor.extract_from_document(doc_res)

    assert ext_res.document_id == doc_res.document_id
    assert ext_res.student_name.value == "Alex Rivera"
    assert ext_res.organization.value == "Association for Computing Machinery"
    assert ext_res.certificate_id.value == "CERT-ACH-2024-9981"
    assert ext_res.issue_date.value == "2024-10-15"
    assert ext_res.metadata["file_type"] == "PDF"
    assert not ext_res.review_required


# ==============================================================================
# 3. MULTI-PAGE TRANSCRIPT EXTRACTION
# ==============================================================================

def test_extract_from_multipage_document(extractor):
    """Verify extraction across multi-page transcript with student ID."""
    doc_res = ingest_document(FIXTURES_DIR / "multipage_transcript.pdf")
    ext_res = extractor.extract_from_document(doc_res)

    assert ext_res.student_id.value == "STU-8829"
    assert ext_res.student_id.confidence_status == ConfidenceStatus.HIGH
    assert ext_res.metadata["total_pages"] == 3
    assert len(doc_res.pages) == 3


# ==============================================================================
# 4. SCANNED DOCUMENT WITH OCR FALLBACK
# ==============================================================================

def test_extract_from_scanned_document_mock_ocr(extractor):
    """Verify extraction on scanned PDF ingested via OCR."""
    mock_ocr = lambda img: (
        "STATE ROBOTICS CHAMPIONSHIP 2024\n"
        "Excellence in Autonomous Navigation Award\n"
        "Awarded to Team Quantum Dynamics\n"
        "Verification Hash: ROB-9912-VERIFIED"
    )
    doc_res = ingest_document(FIXTURES_DIR / "scanned_award.pdf", ocr_callable=mock_ocr)
    ext_res = extractor.extract_from_document(doc_res)

    assert ext_res.student_name.value == "Team Quantum Dynamics"
    assert ext_res.achievement_title.value == "State Robotics Championship 2024"
    assert ext_res.certificate_id.value == "ROB-9912-VERIFIED"
    assert ext_res.metadata["is_scanned"] is True


# ==============================================================================
# 5. CREDENTIAL BADGE WITH SKILLS
# ==============================================================================

def test_extract_from_badge_image(extractor):
    """Verify extraction on PNG image with skill normalization."""
    mock_ocr = lambda img: (
        "CLOUD ARCHITECT CERTIFIED ASSOCIATE\n"
        "Student Credential ID: AWS-CCA-7719\n"
        "Skills: Cloud Computing, Docker, Kubernetes\n"
        "Score: 920 / 1000 - Pass with Distinction"
    )
    doc_res = ingest_document(FIXTURES_DIR / "certificate_badge.png", ocr_callable=mock_ocr)
    ext_res = extractor.extract_from_document(doc_res)

    assert ext_res.student_id.value == "AWS-CCA-7719"
    assert ext_res.category.value == "CERTIFICATION"
    assert ext_res.rank.value == "Pass with Distinction"
    assert "Cloud Infrastructure" in ext_res.skills.value
    assert "Docker" in ext_res.skills.value
    assert "Kubernetes" in ext_res.skills.value


# ==============================================================================
# 6. MISSING FIELDS HANDLING
# ==============================================================================

def test_missing_fields_handling(extractor):
    """Verify missing fields receive explicit MISSING status and None values."""
    sparse_text = "Participated in university coding seminar."
    result = extractor.extract_from_text(sparse_text)

    assert result.student_name.value is None
    assert result.student_name.confidence_status == ConfidenceStatus.MISSING
    assert result.student_id.value is None
    assert result.student_id.confidence_status == ConfidenceStatus.MISSING
    assert result.certificate_id.value is None
    assert result.certificate_id.confidence_status == ConfidenceStatus.MISSING
    assert result.issue_date.value is None
    assert result.issue_date.confidence_status == ConfidenceStatus.MISSING


# ==============================================================================
# 7. EMPTY AND CORRUPTED INPUTS
# ==============================================================================

def test_empty_text_handling(extractor):
    """Verify empty text returns structured empty result with review required."""
    res_empty = extractor.extract_from_text("")
    assert res_empty.review_required is True
    assert len(res_empty.review_reasons) > 0
    assert res_empty.overall_confidence == 0.0

    res_spaces = extractor.extract_from_text("     \n\t   ")
    assert res_spaces.review_required is True


def test_empty_document_result(extractor):
    """Verify 0-byte document result flags review_required."""
    empty_doc = DocumentExtractionResult(
        document_id="DOC-EMPTY",
        filename="empty.pdf",
        file_type=DocumentFormat.PDF,
        total_pages=0,
        pages=[],
        full_raw_text="",
        full_normalized_text="",
        primary_extraction_method=ExtractionMethod.NONE,
        overall_status=ExtractionStatus.EMPTY_DOCUMENT,
        is_scanned=False,
    )
    res = extractor.extract_from_document(empty_doc)
    assert res.review_required is True
    assert "EMPTY_DOCUMENT" in res.review_reasons[0]


def test_corrupted_document_result(extractor):
    """Verify corrupted file result triggers review_required."""
    corrupt_doc = DocumentExtractionResult(
        document_id="DOC-CORRUPT",
        filename="corrupt.pdf",
        file_type=DocumentFormat.PDF,
        total_pages=0,
        pages=[],
        full_raw_text="",
        full_normalized_text="",
        primary_extraction_method=ExtractionMethod.NONE,
        overall_status=ExtractionStatus.CORRUPTED_FILE,
        is_scanned=False,
    )
    res = extractor.extract_from_document(corrupt_doc)
    assert res.review_required is True
    assert "CORRUPTED_FILE" in res.review_reasons[0]


# ==============================================================================
# 8. OCR QUALITY WARNING PROPAGATION
# ==============================================================================

def test_ocr_unavailable_warning_propagation(extractor):
    """Verify OCR_UNAVAILABLE status on document triggers review."""
    doc_res = DocumentExtractionResult(
        document_id="DOC-SCANNED-NO-OCR",
        filename="scan.pdf",
        file_type=DocumentFormat.PDF,
        total_pages=1,
        pages=[],
        full_raw_text="",
        full_normalized_text="",
        primary_extraction_method=ExtractionMethod.NONE,
        overall_status=ExtractionStatus.OCR_UNAVAILABLE,
        is_scanned=True,
        warnings=["OCR engine unavailable."],
    )
    res = extractor.extract_from_document(doc_res)
    assert res.review_required is True
    assert any("OCR" in r for r in res.review_reasons)


# ==============================================================================
# 9. DATE EXTRACTION FORMATS
# ==============================================================================

def test_date_extraction_formats(extractor):
    """Verify extraction across ISO, named month, slash, and year-only dates."""
    # ISO
    r1 = extractor.extract_from_text("Awarded on 2023-11-25 for project.")
    assert r1.issue_date.value == "2023-11-25"
    assert r1.issue_date.confidence_status == ConfidenceStatus.HIGH

    # Named month
    r2 = extractor.extract_from_text("Issued on August 4th, 2022 by University.")
    assert r2.issue_date.value == "2022-08-04"
    assert r2.issue_date.confidence_status == ConfidenceStatus.HIGH

    # Slash format (DD/MM/YYYY)
    r3 = extractor.extract_from_text("Dated 15/05/2021.")
    assert r3.issue_date.value == "2021-05-15"

    # Year only
    r4 = extractor.extract_from_text("Achieved in the academic year 2020.")
    assert r4.issue_date.value == "2020"
    assert r4.issue_date.confidence_status == ConfidenceStatus.MEDIUM


# ==============================================================================
# 10. RANK AND OUTCOME CONSISTENCY
# ==============================================================================

def test_rank_and_outcome_consistency(extractor):
    """Verify ranks map logically to corresponding outcome states."""
    t1 = "Secured 1st Place in hackathon."
    assert extractor.extract_from_text(t1).outcome.value == "WINNER"

    t2 = "Secured 2nd Place in championship."
    assert extractor.extract_from_text(t2).outcome.value == "SECOND_PLACE"

    t3 = "Completed 12-week software engineering internship."
    assert extractor.extract_from_text(t3).outcome.value == "COMPLETION"

    t4 = "Manuscript accepted for publication in conference proceedings."
    assert extractor.extract_from_text(t4).outcome.value == "PUBLISHED"


# ==============================================================================
# 11. COMPETITION LEVEL CLASSIFICATION
# ==============================================================================

def test_level_classification(extractor):
    """Verify scope levels are accurately classified."""
    assert extractor.extract_from_text("Participated in IEEE International Conference.").level.value == "INTERNATIONAL"
    assert extractor.extract_from_text("Winner at Smart India National Hackathon.").level.value == "NATIONAL"
    assert extractor.extract_from_text("Inter-University Sports Championship.").level.value == "UNIVERSITY"
    assert extractor.extract_from_text("Siemens Corporate Professional Training.").level.value == "PROFESSIONAL"


# ==============================================================================
# 12. SERIALIZATION TO DICTIONARY
# ==============================================================================

def test_serialization_to_dict(extractor):
    """Verify complete JSON-serializability of StructuredEvidenceExtraction."""
    text = "This is to certify that Jordan Taylor achieved AWS Certified Solutions Architect - Associate on 2024-02-10."
    res = extractor.extract_from_text(text)
    d = res.to_dict()

    assert isinstance(d, dict)
    assert d["student_name"]["value"] == "Jordan Taylor"
    assert d["category"]["value"] == "CERTIFICATION"
    assert d["issue_date"]["value"] == "2024-02-10"
    assert isinstance(d["overall_confidence"], float)

    # Validate JSON serializability
    json_str = json.dumps(d)
    assert len(json_str) > 100


# ==============================================================================
# 13. REPRODUCIBILITY
# ==============================================================================

def test_reproducibility(extractor):
    """Verify extraction is 100% deterministic over identical inputs."""
    text = "Conferred upon Alex Rivera: Best Student Poster at IEEE ICAC 2024 on 2024-09-12."
    r1 = extractor.extract_from_text(text)
    r2 = extractor.extract_from_text(text)

    assert r1.to_dict() == r2.to_dict()


# ==============================================================================
# 14. EVALUATION SAMPLES GOLD BENCHMARK (75 SAMPLES)
# ==============================================================================

def test_gold_evaluation_samples_benchmark(extractor):
    """Verify extraction accuracy on the 75-sample gold evaluation dataset."""
    assert EVAL_SAMPLES_PATH.exists(), f"Evaluation samples not found at {EVAL_SAMPLES_PATH}"

    with open(EVAL_SAMPLES_PATH, "r", encoding="utf-8") as f:
        samples = [json.loads(l) for l in f if l.strip()]

    assert len(samples) == 75

    correct_counts = {
        "EVENT_NAME": 0,
        "ORGANIZATION": 0,
        "RANK": 0,
        "LEVEL": 0,
        "OUTCOME": 0,
        "CATEGORY": 0,
    }

    for s in samples:
        exp = s["expected_entities"]
        res = extractor.extract_from_text(s["source_text"], document_id=s["document_id"])

        # Event Name
        if res.achievement_title.value and (
            res.achievement_title.value.lower() == exp.get("EVENT_NAME", "").lower()
            or exp.get("EVENT_NAME", "").lower() in res.achievement_title.value.lower()
            or res.achievement_title.value.lower() in exp.get("EVENT_NAME", "").lower()
        ):
            correct_counts["EVENT_NAME"] += 1

        # Organization
        if res.organization.value and (
            res.organization.value.lower() == exp.get("ORGANIZATION", "").lower()
            or exp.get("ORGANIZATION", "").lower() in res.organization.value.lower()
            or res.organization.value.lower() in exp.get("ORGANIZATION", "").lower()
        ):
            correct_counts["ORGANIZATION"] += 1

        # Rank
        exp_rank = str(exp.get("RANK"))
        if res.rank.value == exp_rank:
            correct_counts["RANK"] += 1
        elif exp_rank == "None" and res.rank.value in (None, "None"):
            correct_counts["RANK"] += 1

        # Level
        if res.level.value == exp.get("LEVEL"):
            correct_counts["LEVEL"] += 1

        # Outcome
        if res.outcome.value == exp.get("OUTCOME"):
            correct_counts["OUTCOME"] += 1

        # Category
        if res.category.value == s.get("category"):
            correct_counts["CATEGORY"] += 1

    # Assert 100% on key fields
    assert correct_counts["EVENT_NAME"] == 75, "Event name accuracy below 100%"
    assert correct_counts["ORGANIZATION"] == 75, "Organization accuracy below 100%"
    assert correct_counts["RANK"] == 75, "Rank accuracy below 100%"
    assert correct_counts["LEVEL"] == 75, "Level accuracy below 100%"
    assert correct_counts["OUTCOME"] == 75, "Outcome accuracy below 100%"
    assert correct_counts["CATEGORY"] == 75, "Category accuracy below 100%"
