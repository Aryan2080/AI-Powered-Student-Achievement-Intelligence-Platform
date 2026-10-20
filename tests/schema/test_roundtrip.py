"""JSON round-trip tests across every schema model."""
from __future__ import annotations

from datetime import date

from nlp_semantic.schema import (
    APPROVED_EVIDENCE_PREFIX,
    Achievement,
    Annotation,
    AnnotationStatus,
    AnnotationStatusMap,
    AnnotationTask,
    DocumentFileType,
    Evidence,
    ExtractionMethod,
    LabelTaxonomy,
    ReviewStatus,
    SourceRegistry,
    TaxonomyStatus,
    TaxonomyTask,
    UNKNOWN_LICENSE,
    make_id,
)


def test_achievement_round_trip() -> None:
    a = Achievement(
        achievement_id=make_id("ach"),
        source_id=make_id("src"),
        source_record_id="rec-7",
        achievement_text="Published 'Lightweight NLP' at ACL 2024.",
        primary_type="lbl_research_pub",
        domain_tags=["lbl_domain_nlp", "lbl_domain_ml"],
        organization="ACL",
        achievement_date=date(2024, 8, 11),
        rank=None,
        skills=["python", "pytorch"],
        annotation_status=AnnotationStatusMap(
            primary_type=AnnotationStatus.VERIFIED,
            domain_tags=AnnotationStatus.PENDING,
        ),
        is_synthetic=True,
    )
    assert Achievement.model_validate_json(a.model_dump_json()) == a


def test_evidence_round_trip() -> None:
    e = Evidence(
        evidence_id=make_id("evd"),
        relative_path=APPROVED_EVIDENCE_PREFIX + "cert.pdf",
        file_type=DocumentFileType.PDF,
        extraction_method=ExtractionMethod.OCR_TESSERACT,
        extracted_text_inline="scanned cert body",
        ocr_confidence=0.91,
        review_status=ReviewStatus.IN_REVIEW,
        is_synthetic=True,
    )
    assert Evidence.model_validate_json(e.model_dump_json()) == e


def test_annotation_round_trip() -> None:
    a = Annotation(
        annotation_id=make_id("ann"),
        achievement_id=make_id("ach"),
        task=AnnotationTask.DOMAIN_TAGS,
        label_ids=["lbl_domain_ai"],
        annotator="team_handle-A",
        review_status=AnnotationStatus.CONFLICTED,
        notes="disagreement between two reviewers",
        is_synthetic=True,
    )
    assert Annotation.model_validate_json(a.model_dump_json()) == a


def test_source_registry_round_trip() -> None:
    s = SourceRegistry(
        source_id=make_id("src"),
        source_name="Our Hand-labeled Set",
        source_url=None,
        license=UNKNOWN_LICENSE,
        collection_date=date(2024, 1, 15),
        original_labels=["winner", "runner-up"],
        intended_use="primary_type_training",
        is_synthetic=True,
    )
    assert SourceRegistry.model_validate_json(s.model_dump_json()) == s


def test_label_taxonomy_round_trip() -> None:
    t = LabelTaxonomy(
        label_id="lbl_patent",
        task_name=TaxonomyTask.PRIMARY_TYPE,
        display_name="Patent",
        definition="A granted or filed patent naming the student as inventor.",
        inclusion_rules=["Granted patents", "Filed patent applications"],
        exclusion_rules=["Trade secrets without filing"],
        examples=["US patent 10,000,000 inventor jane doe"],
        status=TaxonomyStatus.APPROVED,
    )
    assert LabelTaxonomy.model_validate_json(t.model_dump_json()) == t
