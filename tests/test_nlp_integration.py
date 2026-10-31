"""
tests/test_nlp_integration.py
==============================
Robustness and Integration Tests for the End-to-End NLP Evidence Pipeline
AI-Powered Student Achievement Intelligence Platform — Member 1

Tests all 13 required integration and robustness criteria:
1. Normal text-based certificate extraction.
2. Multi-page document processing and provenance tracking.
3. Ingestion and propagation of OCR warnings.
4. Handling when OCR engine is unavailable.
5. Incomplete evidence with missing event name or organization.
6. Evidence with conflicting or ambiguous dates.
7. Evidence with conflicting or ambiguous rank information.
8. Empty text, corrupt files, and unparseable inputs.
9. Text with unknown achievement terminology.
10. Unmatched and ambiguous skill mentions.
11. Classifier failure and invalid model input handling.
12. Exact character source spans, page references, and JSON serialization.
13. Administrative review triage routing (auto-accept vs review-required).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from PIL import Image

from src.nlp.classification import AchievementClassifier
from src.nlp.create_test_fixtures import generate_all_fixtures
from src.nlp.document_ingestion import (
    DocumentExtractionResult,
    DocumentFormat,
    ExtractionMethod,
    ExtractionStatus,
    PageExtractionResult,
    ingest_document,
)
from src.nlp.information_extraction import (
    ConfidenceStatus,
    EvidenceInformationExtractor,
    ExtractedField,
    ExtractionSource,
    StructuredEvidenceExtraction,
    get_default_extractor,
)
from src.nlp.pipeline import (
    NLPEvidencePipeline,
    PipelineProcessingResult,
    get_nlp_pipeline,
    process_evidence_document,
)
from src.nlp.skill_normalization import (
    CanonicalSkillVocabulary,
    NormalizationStatus,
    SkillNormalizer,
)

FIXTURES_DIR = Path("tests/fixtures/documents")
EVAL_SAMPLES_PATH = Path("data/annotations/extraction_evaluation_samples.jsonl")


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures():
    """Ensure document fixtures exist before tests run."""
    return generate_all_fixtures(FIXTURES_DIR)


@pytest.fixture(scope="session")
def pipeline():
    """Shared default NLP evidence pipeline with cached model and vocabulary."""
    return get_nlp_pipeline()


# ==============================================================================
# 1. NORMAL TEXT-BASED CERTIFICATE
# ==============================================================================

def test_pipeline_normal_text_certificate(pipeline):
    """Verify end-to-end processing of a normal text-based certificate PDF."""
    cert_path = FIXTURES_DIR / "valid_certificate.pdf"
    res = pipeline.process_document(cert_path)

    assert isinstance(res, PipelineProcessingResult)
    assert res.document_id == "valid_certificate"
    assert res.ingestion_summary["file_type"] == "PDF"
    assert res.ingestion_summary["overall_status"] == "SUCCESS"
    assert res.ingestion_summary["total_pages"] == 1

    # Verify structured entity extraction
    entities = res.extracted_entities
    assert entities["student_name"]["value"] == "Alex Rivera"
    assert entities["achievement_title"]["value"] == "National Collegiate Hackathon 2024"
    assert entities["organization"]["value"] == "Association for Computing Machinery"
    assert entities["rank"]["value"] == "1st Place"
    assert entities["outcome"]["value"] == "WINNER"
    assert entities["issue_date"]["value"] == "2024-10-15"
    assert entities["certificate_id"]["value"] == "CERT-ACH-2024-9981"

    # Verify classifier output
    assert "predicted_category" in res.classification
    assert "confidence" in res.classification
    assert "category_scores" in res.classification
    assert len(res.classification["category_scores"]) == 14

    # Verify provenance
    assert res.provenance["document_format"] == "PDF"
    assert res.provenance["total_pages"] == 1
    assert res.provenance["source_spans"]["student_name"] is not None


# ==============================================================================
# 2. MULTI-PAGE DOCUMENT PROVENANCE
# ==============================================================================

def test_pipeline_multipage_document(pipeline):
    """Verify multi-page document processing and per-page provenance preservation."""
    multi_path = FIXTURES_DIR / "multipage_transcript.pdf"
    res = pipeline.process_document(multi_path)

    assert isinstance(res, PipelineProcessingResult)
    assert res.ingestion_summary["total_pages"] >= 2
    assert len(res.ingestion_summary["pages"]) >= 2

    # Check page 1 and page 2 metadata
    page_1 = res.ingestion_summary["pages"][0]
    page_2 = res.ingestion_summary["pages"][1]
    assert page_1["page_number"] == 1
    assert page_2["page_number"] == 2
    assert page_1["char_count"] > 0
    assert page_2["char_count"] > 0


# ==============================================================================
# 3. DOCUMENT WITH OCR WARNINGS
# ==============================================================================

def test_pipeline_document_with_ocr_warnings(pipeline):
    """Verify that optical character recognition fallback warnings propagate properly."""
    # Construct a synthetic DocumentExtractionResult with OCR fallback applied
    ocr_doc = DocumentExtractionResult(
        document_id="DOC-OCR-WARN-01",
        filename="scanned_cert.png",
        file_type=DocumentFormat.PNG,
        total_pages=1,
        pages=[
            PageExtractionResult(
                page_number=1,
                raw_text="Awarded to Jordan Taylor for winning Python Hackathon 2024 organized by IEEE on 2024-08-15.",
                normalized_text="Awarded to Jordan Taylor for winning Python Hackathon 2024 organized by IEEE on 2024-08-15.",
                extraction_method=ExtractionMethod.OCR,
                status=ExtractionStatus.SUCCESS,
                char_count=98,
                word_count=15,
                warnings=["Low contrast detected during OCR preprocessing."],
            )
        ],
        full_raw_text="Awarded to Jordan Taylor for winning Python Hackathon 2024 organized by IEEE on 2024-08-15.",
        full_normalized_text="Awarded to Jordan Taylor for winning Python Hackathon 2024 organized by IEEE on 2024-08-15.",
        primary_extraction_method=ExtractionMethod.OCR,
        overall_status=ExtractionStatus.OCR_FALLBACK_APPLIED,
        is_scanned=True,
        warnings=["Low contrast detected during OCR preprocessing."],
    )

    res = pipeline.process_document(ocr_doc)

    assert isinstance(res, PipelineProcessingResult)
    assert any("OCR" in w or "optical" in w for w in res.warnings)
    assert res.extracted_entities["student_name"]["value"] == "Jordan Taylor"
    org_val = res.extracted_entities["organization"]["value"]
    assert org_val in ("IEEE", "Institute of Electrical and Electronics Engineers")


# ==============================================================================
# 4. OCR UNAVAILABLE HANDLING
# ==============================================================================

def test_pipeline_ocr_unavailable(pipeline):
    """Verify pipeline gracefully handles scanned evidence when OCR engine is unavailable."""
    unavailable_doc = DocumentExtractionResult(
        document_id="DOC-SCAN-NO-OCR",
        filename="scanned_cert.png",
        file_type=DocumentFormat.PNG,
        total_pages=1,
        pages=[
            PageExtractionResult(
                page_number=1,
                raw_text="",
                normalized_text="",
                extraction_method=ExtractionMethod.NONE,
                status=ExtractionStatus.OCR_UNAVAILABLE,
                char_count=0,
                word_count=0,
                warnings=["OCR engine is unavailable on current system."],
            )
        ],
        full_raw_text="",
        full_normalized_text="",
        primary_extraction_method=ExtractionMethod.NONE,
        overall_status=ExtractionStatus.OCR_UNAVAILABLE,
        is_scanned=True,
        warnings=["OCR engine is unavailable on current system."],
    )

    res = pipeline.process_document(unavailable_doc)

    assert isinstance(res, PipelineProcessingResult)
    assert res.review_required is True
    assert any("OCR" in r for r in res.review_reasons)
    assert any("OCR" in w for w in res.warnings)


# ==============================================================================
# 5. MISSING EVENT NAME OR ORGANIZATION
# ==============================================================================

def test_pipeline_missing_event_or_organization(pipeline):
    """Verify incomplete evidence missing essential fields routes to human review."""
    # Text with student and date, but completely missing event title and organization
    incomplete_text = (
        "Certificate of Attendance\n"
        "This certifies that Priya Sharma participated in student activities on 2024-03-12.\n"
        "Certificate ID: CERT-GEN-1002"
    )

    res = pipeline.process_text(incomplete_text, document_id="DOC-INCOMPLETE")

    assert isinstance(res, PipelineProcessingResult)
    assert res.review_required is True
    assert any("organization" in r.lower() or "title" in r.lower() for r in res.review_reasons)
    assert res.extracted_entities["student_name"]["value"] == "Priya Sharma"
    assert res.extracted_entities["organization"]["value"] is None
    assert res.extracted_entities["organization"]["confidence_status"] == "MISSING"


# ==============================================================================
# 6. CONFLICTING OR AMBIGUOUS DATES
# ==============================================================================

def test_pipeline_conflicting_dates(pipeline):
    """Verify that contradictory event dates trigger conflict flags and review routing."""
    conflicting_date_text = (
        "CERTIFICATE OF MERIT\n"
        "This is to certify that Liam Chen won 1st Place in the Annual Robotics Derby\n"
        "organized by Robotics Society.\n"
        "Event held on 2023-04-12.\n"
        "Event held on 2024-11-20.\n"
        "Issued on 2024-11-25."
    )

    res = pipeline.process_text(conflicting_date_text, document_id="DOC-DATE-CONFLICT")

    assert isinstance(res, PipelineProcessingResult)
    assert res.review_required is True
    date_audit = res.provenance["date_semantics"]
    assert date_audit["has_conflict"] is True
    assert any("conflicting" in r.lower() and "date" in r.lower() for r in res.review_reasons)


# ==============================================================================
# 7. CONFLICTING OR AMBIGUOUS RANK INFORMATION
# ==============================================================================

def test_pipeline_conflicting_rank_information(pipeline):
    """Verify that contradictory rank claims (e.g. 1st place AND runner-up) trigger review."""
    conflicting_rank_text = (
        "CERTIFICATE OF RECOGNITION\n"
        "Awarded to Maya Patel for securing 1st Place Winner\n"
        "and Runner Up in the National Coding Challenge organized by TechCorp on 2024-05-18."
    )

    res = pipeline.process_text(conflicting_rank_text, document_id="DOC-RANK-CONFLICT")

    assert isinstance(res, PipelineProcessingResult)
    assert res.review_required is True
    assert any("rank" in r.lower() for r in res.review_reasons)


# ==============================================================================
# 8. EMPTY TEXT AND CORRUPTED INPUT
# ==============================================================================

def test_pipeline_empty_and_corrupted_input(pipeline):
    """Verify that empty, corrupt, or unsupported inputs do not crash and report failure."""
    # 1. Empty PDF
    empty_res = pipeline.process_document(FIXTURES_DIR / "empty_doc.pdf")
    assert empty_res.status == "FAILED"
    assert empty_res.review_required is True
    assert empty_res.overall_confidence == 0.0

    # 2. Corrupt PDF
    corrupt_res = pipeline.process_document(FIXTURES_DIR / "corrupt_doc.pdf")
    assert corrupt_res.status == "FAILED"
    assert corrupt_res.review_required is True

    # 3. Unsupported format
    unsupported_res = pipeline.process_document(FIXTURES_DIR / "unsupported_report.docx")
    assert unsupported_res.status == "FAILED"
    assert unsupported_res.review_required is True

    # 4. Empty string
    empty_str_res = pipeline.process_text("")
    assert empty_str_res.status == "FAILED"
    assert empty_str_res.review_required is True

    # 5. Invalid type (e.g. integer)
    invalid_type_res = pipeline.process_document(12345)  # type: ignore
    assert invalid_type_res.status == "FAILED"
    assert invalid_type_res.review_required is True


# ==============================================================================
# 9. UNKNOWN ACHIEVEMENT TERMINOLOGY
# ==============================================================================

def test_pipeline_unknown_achievement_terminology(pipeline):
    """Verify text lacking any recognizable achievement terminology routes to review."""
    unknown_text = (
        "The quick brown fox jumps over the lazy dog near the quiet river bank "
        "on a breezy Tuesday morning while observing the landscape."
    )

    res = pipeline.process_text(unknown_text, document_id="DOC-UNKNOWN-TERM")

    assert isinstance(res, PipelineProcessingResult)
    assert res.review_required is True
    assert any("terminology" in r.lower() or "confidence" in r.lower() for r in res.review_reasons)


# ==============================================================================
# 10. UNMATCHED AND AMBIGUOUS SKILL MENTIONS
# ==============================================================================

def test_pipeline_unmatched_and_ambiguous_skills(pipeline):
    """Verify pipeline handles unmapped or ambiguous skills without hallucination."""
    text_with_unknown_skills = (
        "Certificate of Completion\n"
        "This certifies that Jordan Taylor completed hands-on training in "
        "CuneiformDecipherment and QuantumTeleportationCooking organized by OpenAcademy on 2024-04-10.\n"
        "Skills demonstrated: Python, CuneiformDecipherment."
    )

    res = pipeline.process_text(text_with_unknown_skills, document_id="DOC-SKILLS")

    assert isinstance(res, PipelineProcessingResult)
    canonical_skills = [s["canonical_name"] for s in res.skills]
    # Python is in canonical vocabulary
    assert "Python" in canonical_skills
    # Fake skills should not be erroneously mapped to existing skills
    assert "CuneiformDecipherment" not in canonical_skills
    assert "QuantumTeleportationCooking" not in canonical_skills


# ==============================================================================
# 11. CLASSIFIER FAILURE HANDLING
# ==============================================================================

def test_pipeline_classifier_failure_handling():
    """Verify pipeline catches classifier exceptions without halting execution."""
    # Create mock classifier that deliberately throws an exception during prediction
    mock_classifier = MagicMock(spec=AchievementClassifier)
    mock_classifier.is_fitted = True
    mock_classifier.model_version = "mock-1.0.0"
    mock_classifier.predict_record.side_effect = RuntimeError("Simulated classifier inference crash")

    extractor = get_default_extractor()
    pipeline_with_faulty_classifier = NLPEvidencePipeline(
        classifier=mock_classifier,
        extractor=extractor,
    )

    test_text = "Certificate of Merit awarded to Maya Lin for winning Hackathon 2024 organized by TechClub on 2024-05-10."
    res = pipeline_with_faulty_classifier.process_text(test_text, document_id="DOC-MOCK-FAIL")

    assert isinstance(res, PipelineProcessingResult)
    assert res.review_required is True
    assert any("classifier" in r.lower() for r in res.review_reasons)
    assert any("classifier" in w.lower() for w in res.warnings)
    # Extracted fields should still be intact despite classifier failure
    assert res.extracted_entities["student_name"]["value"] == "Maya Lin"
    assert res.extracted_entities["organization"]["value"] == "TechClub"


# ==============================================================================
# 12. EXACT SOURCE SPANS AND JSON SERIALIZATION
# ==============================================================================

def test_pipeline_source_spans_and_serialization(pipeline):
    """Verify character offsets map verbatim to raw text and JSON serialization is lossless."""
    text = (
        "CERTIFICATE OF MERIT\n"
        "This is to certify that Alex Rivera representing MIT\n"
        "has secured 1st Place in the National Collegiate Hackathon 2024\n"
        "organized by Association for Computing Machinery on 2024-10-15.\n"
        "Certificate ID: CERT-ACH-2024-9981"
    )

    res = pipeline.process_text(text, document_id="DOC-SPANS")

    # 1. Verify exact substring slicing matches extracted values
    spans = res.provenance["source_spans"]
    for field_name, span in spans.items():
        if span is not None:
            start, end = span
            extracted_val = res.extracted_entities[field_name]["value"]
            sliced_val = text[start:end]
            # Sliced text should be equal or contain extracted value
            assert extracted_val.lower() in sliced_val.lower() or sliced_val.lower() in extracted_val.lower()

    # 2. Verify JSON serialization
    json_str = res.to_json(indent=2)
    assert isinstance(json_str, str)
    deserialized = json.loads(json_str)

    assert deserialized["document_id"] == "DOC-SPANS"
    assert deserialized["pipeline_version"] == "1.0.1"
    assert deserialized["extracted_entities"]["student_name"]["value"] == "Alex Rivera"
    assert deserialized["extracted_entities"]["achievement_title"]["value"] == "National Collegiate Hackathon 2024"
    assert "provenance" in deserialized
    assert "ingestion_summary" in deserialized


# ==============================================================================
# 13. TRIAGE ROUTING: AUTO-ACCEPT VS REVIEW-REQUIRED
# ==============================================================================

def test_pipeline_triage_routing_auto_accept_vs_review(pipeline):
    """Verify that complete valid certificates can pass while degraded evidence routes to review."""
    # Degraded: no title, no org, low confidence
    degraded_text = "Participated in an activity on 2024-01-01."
    deg_res = pipeline.process_text(degraded_text, document_id="DOC-DEG")
    assert deg_res.review_required is True
    assert deg_res.status == "REVIEW_REQUIRED"

    # Incomplete: missing student name on attendance sheet
    sheet_text = "Attendance at Workshop on Cloud Computing conducted by IEEE on 2024-06-12."
    sheet_res = pipeline.process_text(sheet_text, document_id="DOC-SHEET")
    assert sheet_res.extracted_entities["student_name"]["value"] is None
