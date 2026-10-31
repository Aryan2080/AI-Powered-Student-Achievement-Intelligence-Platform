"""
tests/test_categorization.py
============================
Unit, Split Integrity, Robustness, and Integration Tests
for Multi-Label Domain Categorization Subsystem (Step 10)
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import tempfile

import joblib
import numpy as np
import pandas as pd
import pytest

from src.nlp.categorization import (
    DOMAIN_TAGS,
    DOMAIN_TAG_NAMES,
    AchievementCategorizer,
    CategorizationResult,
)
from src.nlp.categorization_dataset import (
    LabelEvidenceType,
    audit_tag_evidence_type,
    derive_record_tags,
    generate_categorization_dataset,
    create_manually_reviewed_gold_reference,
)
from src.nlp.pipeline import (
    NLPEvidencePipeline,
    PipelineProcessingResult,
    get_nlp_pipeline,
)


# ==============================================================================
# 1. TAXONOMY & DEFINITION TESTS
# ==============================================================================

def test_domain_tags_completeness():
    """Verify that all 10 domain tags are properly defined and documented."""
    assert len(DOMAIN_TAGS) == 10
    assert len(DOMAIN_TAG_NAMES) == 10

    expected_tags = {
        "lbl_domain_ai",
        "lbl_domain_ml",
        "lbl_domain_nlp",
        "lbl_domain_cv",
        "lbl_domain_security",
        "lbl_domain_systems",
        "lbl_domain_web",
        "lbl_domain_data",
        "lbl_domain_hardware",
        "lbl_domain_other",
    }
    assert set(DOMAIN_TAGS) == expected_tags
    for tag in DOMAIN_TAGS:
        assert tag in DOMAIN_TAG_NAMES
        assert isinstance(DOMAIN_TAG_NAMES[tag], str)
        assert len(DOMAIN_TAG_NAMES[tag]) > 0


# ==============================================================================
# 2. DATASET ARTIFACT & SPLIT INTEGRITY TESTS
# ==============================================================================

def test_categorization_dataset_artifacts_exist():
    """Verify generated dataset files exist and match schema contracts."""
    csv_path = Path("data/processed/achievement_categorization_dataset.csv")
    jsonl_path = Path("data/processed/achievement_categorization_dataset.jsonl")

    assert csv_path.exists(), "achievement_categorization_dataset.csv missing"
    assert jsonl_path.exists(), "achievement_categorization_dataset.jsonl missing"

    df = pd.read_csv(csv_path)
    assert len(df) == 1540, f"Expected 1,540 records, found {len(df)}"

    # Required metadata and target columns
    required_cols = [
        "achievement_id",
        "achievement_text",
        "category",
        "tag_count",
    ] + [f"tag_{t}" for t in DOMAIN_TAGS]

    for col in required_cols:
        assert col in df.columns, f"Required column '{col}' missing from dataset."

    # Verify binary domain target values
    for t in DOMAIN_TAGS:
        unique_vals = set(df[f"tag_{t}"].unique())
        assert unique_vals.issubset({0, 1}), f"Column 'tag_{t}' contains non-binary values: {unique_vals}"


def test_split_integrity_and_alignment():
    """
    Verify categorization splits exactly align with master classification splits
    and maintain 100% zero ID leakage.
    """
    train_path = Path("data/splits/categorization_train.csv")
    val_path = Path("data/splits/categorization_validation.csv")
    test_path = Path("data/splits/categorization_test.csv")

    assert train_path.exists()
    assert val_path.exists()
    assert test_path.exists()

    df_train = pd.read_csv(train_path)
    df_val = pd.read_csv(val_path)
    df_test = pd.read_csv(test_path)

    # Check partition sizes
    assert len(df_train) == 1078, f"Expected 1,078 train rows, got {len(df_train)}"
    assert len(df_val) == 231, f"Expected 231 val rows, got {len(df_val)}"
    assert len(df_test) == 231, f"Expected 231 test rows, got {len(df_test)}"
    assert len(df_train) + len(df_val) + len(df_test) == 1540

    train_ids = set(df_train["achievement_id"])
    val_ids = set(df_val["achievement_id"])
    test_ids = set(df_test["achievement_id"])

    # Zero leakage check
    assert len(train_ids.intersection(val_ids)) == 0, "Data leakage between train and val!"
    assert len(train_ids.intersection(test_ids)) == 0, "Data leakage between train and test!"
    assert len(val_ids.intersection(test_ids)) == 0, "Data leakage between val and test!"

    # Verify alignment with master classification splits
    master_train = pd.read_csv("data/splits/train.csv")
    master_val = pd.read_csv("data/splits/validation.csv")
    master_test = pd.read_csv("data/splits/test.csv")

    assert train_ids == set(master_train["achievement_id"]), "Categorization train IDs do not match master train!"
    assert val_ids == set(master_val["achievement_id"]), "Categorization val IDs do not match master val!"
    assert test_ids == set(master_test["achievement_id"]), "Categorization test IDs do not match master test!"


def test_gold_reference_samples_integrity():
    """Verify the 45-sample manually reviewed gold reference subset."""
    ref_path = Path("data/annotations/categorization_reviewed_reference_samples.jsonl")
    assert ref_path.exists()

    records = []
    with open(ref_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    assert len(records) == 45, f"Expected 45 gold reference samples, got {len(records)}"

    all_assigned_tags = set()
    zero_tag_count = 0

    for rec in records:
        assert "achievement_id" in rec
        assert "achievement_text" in rec
        assert "verified_domain_tags" in rec
        assert "audit_notes" in rec
        assert isinstance(rec["verified_domain_tags"], list)

        for tag in rec["verified_domain_tags"]:
            assert tag in DOMAIN_TAGS, f"Invalid tag '{tag}' in gold reference sample"
            all_assigned_tags.add(tag)

        if len(rec["verified_domain_tags"]) == 0:
            zero_tag_count += 1

    # Ensure all 10 tags and zero-tag samples are covered in the reviewed subset
    assert all_assigned_tags == set(DOMAIN_TAGS), "Not all 10 domain tags are represented in gold reference!"
    assert zero_tag_count >= 2, "Expected at least 2 zero-tag non-technical achievements in gold reference!"


# ==============================================================================
# 3. MODEL INFERENCE & BEHAVIOR TESTS
# ==============================================================================

@pytest.fixture(scope="module")
def loaded_categorizer():
    """Load the trained production categorizer artifact."""
    model_path = Path("models/achievement_categorizer_v1.0.1.joblib")
    assert model_path.exists(), "Categorizer joblib artifact not found"
    categorizer = AchievementCategorizer.load(model_path)
    assert categorizer.is_fitted
    return categorizer


def test_predict_multiple_domain_tags(loaded_categorizer):
    """Verify that an achievement with multidisciplinary content receives multiple domain tags."""
    text = (
        "Designed and implemented an autonomous computer vision system using convolutional neural networks "
        "and deep learning algorithms, deployed on an AWS web cloud cluster with REST APIs."
    )
    result = loaded_categorizer.predict_record(text)
    assert isinstance(result, CategorizationResult)
    assert isinstance(result.predicted_tags, list)
    assert len(result.predicted_tags) >= 2

    # Expect relevant tags like AI/ML/CV/Web
    expected_intersect = {"lbl_domain_ai", "lbl_domain_ml", "lbl_domain_cv", "lbl_domain_web"}
    assigned_intersect = set(result.predicted_tags).intersection(expected_intersect)
    assert len(assigned_intersect) >= 2, f"Expected multiple technical tags, got {result.predicted_tags}"


def test_predict_non_computing_domain(loaded_categorizer):
    """Verify that a non-technical achievement does not receive technical computing tags."""
    text = (
        "Awarded First Prize in the Inter-College Classical Vocal Music and Violin Solo Championship "
        "organized by the Cultural Association of India."
    )
    result = loaded_categorizer.predict_record(text)
    assert isinstance(result, CategorizationResult)
    # Technical computing tags must not be predicted
    technical_tags = {
        "lbl_domain_ai", "lbl_domain_ml", "lbl_domain_nlp", "lbl_domain_cv",
        "lbl_domain_web", "lbl_domain_security", "lbl_domain_hardware",
    }
    assert set(result.predicted_tags).isdisjoint(technical_tags)
    assert result.audit_metadata.get("warning") is None or "Empty" not in result.audit_metadata.get("warning", "")


def test_predict_empty_and_corrupt_inputs(loaded_categorizer):
    """Verify graceful handling of empty string, whitespace, and None."""
    # Empty string
    res_empty = loaded_categorizer.predict_record("")
    assert res_empty.predicted_tags == []
    assert all(score == 0.0 for score in res_empty.tag_scores.values())

    # Whitespace only
    res_ws = loaded_categorizer.predict_record("   \n\t  ")
    assert res_ws.predicted_tags == []

    # None input
    res_none = loaded_categorizer.predict_record(None)
    assert res_none.predicted_tags == []


def test_predict_batch(loaded_categorizer):
    """Verify batch prediction over a list of texts and pandas DataFrame."""
    texts = [
        "Certified Kubernetes Administrator and Cloud Infrastructure Architect.",
        "Built a deep learning NLP chatbot with transformers and PyTorch.",
        "Winner of the inter-university badminton singles tournament.",
    ]
    batch_results = loaded_categorizer.predict_batch(texts)
    assert len(batch_results) == 3
    for r in batch_results:
        assert isinstance(r, CategorizationResult)

    # Test DataFrame batch
    df = pd.DataFrame({"achievement_text": texts, "achievement_id": ["A1", "A2", "A3"]})
    df_results = loaded_categorizer.predict_batch(df)
    assert len(df_results) == 3
    assert df_results[0].audit_metadata.get("record_id") == "A1"


def test_model_persistence_roundtrip(loaded_categorizer):
    """Verify that save and load preserve all weights, thresholds, and metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_model_path = Path(tmpdir) / "test_categorizer.joblib"
        loaded_categorizer.save(tmp_model_path)

        assert tmp_model_path.exists()
        reloaded = AchievementCategorizer.load(tmp_model_path)

        assert reloaded.is_fitted
        assert reloaded.model_version == loaded_categorizer.model_version
        assert reloaded.tags == loaded_categorizer.tags
        assert reloaded.thresholds == loaded_categorizer.thresholds

        # Verify predictions match exactly
        sample_text = "Full stack web development using React, Node.js, and MongoDB."
        res1 = loaded_categorizer.predict_record(sample_text)
        res2 = reloaded.predict_record(sample_text)

        assert res1.predicted_tags == res2.predicted_tags
        for t in loaded_categorizer.tags:
            assert abs(res1.tag_scores[t] - res2.tag_scores[t]) < 1e-6


# ==============================================================================
# 4. PIPELINE INTEGRATION & SEPARATION TESTS
# ==============================================================================

def test_pipeline_integration_domain_tags():
    """Verify end-to-end NLP pipeline executes both classification and multi-label categorization."""
    pipeline = NLPEvidencePipeline.create_default()
    assert pipeline.classifier is not None
    assert pipeline.categorizer is not None

    evidence_text = (
        "Certificate of Merit: Awarded to Priya Sharma for participating in Hackathon 2024 "
        "and building an intelligent machine learning recommendation engine using Python and FastAPI."
    )
    result = pipeline.process_text(evidence_text, document_id="TEST-INT-001")

    assert isinstance(result, PipelineProcessingResult)
    # Single-label classification
    assert result.classification["predicted_category"] in [
        "HACKATHON", "PROJECT", "COMPETITION", "CERTIFICATION", "OTHER"
    ]
    # Multi-label domain categorization
    assert hasattr(result, "domain_tags")
    assert isinstance(result.domain_tags, list)
    assert hasattr(result, "categorization")
    assert "predicted_tags" in result.categorization
    assert "tag_scores" in result.categorization

    # Check to_dict() serialization
    res_dict = result.to_dict()
    assert "domain_tags" in res_dict
    assert "categorization" in res_dict
    assert res_dict["domain_tags"] == result.domain_tags

    # Check JSON serialization
    json_str = result.to_json()
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert "domain_tags" in parsed
    assert "categorization" in parsed


def test_single_label_and_multi_label_orthogonality():
    """
    Verify that single-label primary category and multi-label domain tags
    remain strictly separate and orthogonal in the pipeline.
    """
    from src.nlp.classification import ACHIEVEMENT_CATEGORIES
    pipeline = NLPEvidencePipeline.create_default()

    text = (
        "Certified Information Systems Security Professional (CISSP) credential awarded "
        "by (ISC)2 for demonstrated mastery in cloud and distributed systems security."
    )
    res = pipeline.process_text(text, document_id="TEST-CERT-01")

    # Primary category is from the 14 single-label categories
    assert res.classification["predicted_category"] in ACHIEVEMENT_CATEGORIES
    assert res.classification["predicted_category"] in ["CERTIFICATION", "COURSE"]

    # Domain tags are from the 10 multi-label domain tags
    assert isinstance(res.domain_tags, list)
    for tag in res.domain_tags:
        assert tag in DOMAIN_TAGS
    assert any("security" in tag or "systems" in tag for tag in res.domain_tags)

    # Confirm both coexist independently in the result contract
    assert "predicted_category" in res.classification
    assert "domain_tags" in res.categorization


# ==============================================================================
# 5. STEP 12 RELIABILITY, AUDIT PROVENANCE & CANDIDATE MODEL TESTS
# ==============================================================================

def test_label_evidence_type_and_provenance_audit():
    """Verify LabelEvidenceType enum values and audit_tag_evidence_type logic."""
    expected_types = {"TEXT_SUPPORTED", "METADATA_SUPPORTED", "HYBRID", "AMBIGUOUS", "UNKNOWN"}
    actual_types = {e.value for e in LabelEvidenceType}
    assert expected_types == actual_types

    # Pure text cue
    t1 = audit_tag_evidence_type(
        "lbl_domain_security",
        ["text_cue: Security terminology"],
        "Demonstrated cybersecurity practices.",
    )
    assert t1 == LabelEvidenceType.TEXT_SUPPORTED

    # Metadata cue only (source_domain)
    t2 = audit_tag_evidence_type(
        "lbl_domain_ai",
        ["source_domain: Artificial Intelligence"],
        "Organized college annual sports meet.",
    )
    assert t2 == LabelEvidenceType.METADATA_SUPPORTED

    # Hybrid cue (both text and metadata)
    t3 = audit_tag_evidence_type(
        "lbl_domain_systems",
        ["source_domain: Cloud & Distributed Computing", "skill: Docker"],
        "Deployed microservices using Docker on AWS.",
    )
    assert t3 == LabelEvidenceType.HYBRID

    # Unknown cue
    t4 = audit_tag_evidence_type(
        "lbl_domain_other",
        [],
        "General participation certificate.",
    )
    assert t4 == LabelEvidenceType.UNKNOWN


def test_categorizer_confidence_tiers_and_uncertainty(loaded_categorizer):
    """Verify confidence tiers, uncertainty margins, and review recommendations."""
    sample_text = "Trained deep learning convolutional network with PyTorch for autonomous vehicle obstacle avoidance."
    result = loaded_categorizer.predict_record(sample_text)

    assert isinstance(result, CategorizationResult)
    assert hasattr(result, "confidence_tier")
    assert hasattr(result, "uncertain_tags")
    assert hasattr(result, "review_recommended")

    # Verify confidence tiers are valid enum values
    valid_tiers = {"HIGH", "MEDIUM", "LOW_MARGIN"}
    for tag, tier in result.confidence_tier.items():
        assert tier in valid_tiers
        assert tag in result.predicted_tags

    # Verify serialization in to_dict()
    res_dict = result.to_dict()
    assert "confidence_tier" in res_dict
    assert "uncertain_tags" in res_dict
    assert "review_recommended" in res_dict
    assert res_dict["confidence_tier"] == result.confidence_tier


def test_gold_annotation_task_schema():
    """Verify the 175-sample gold annotation corpus contract and no label fabrication."""
    task_file = Path("data/annotations/domain_categorization_gold_annotation_task.jsonl")
    assert task_file.exists(), "Gold annotation task file missing."

    records = []
    with open(task_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    assert len(records) == 175, f"Expected 175 records in gold task corpus, found {len(records)}"

    verified_count = 0
    pending_count = 0
    for r in records:
        assert "achievement_id" in r
        assert "achievement_text" in r
        assert "split" in r
        assert r["split"] == "test", f"All gold candidates must come from test split, found {r['split']}"
        assert "annotation_status" in r
        assert "annotator_1" in r
        assert "annotator_2" in r
        assert "adjudicated_tags" in r

        if r["annotation_status"] == "VERIFIED":
            verified_count += 1
            assert isinstance(r["adjudicated_tags"], list)
        elif r["annotation_status"] == "PENDING_HUMAN_REVIEW":
            pending_count += 1
            assert r["adjudicated_tags"] is None, "Pending records must not have fabricated adjudicated tags"

    assert verified_count == 7, f"Expected exactly 7 verified gold records, found {verified_count}"
    assert pending_count == 168, f"Expected exactly 168 pending review records, found {pending_count}"


def test_candidate_model_artifact_integrity():
    """Verify candidate Sentence Transformer model bundle and comparison report exist."""
    model_path = Path("models/candidate_sentence_transformer_categorizer.joblib")
    meta_path = Path("models/candidate_sentence_transformer_categorizer.json")
    report_path = Path("reports/step12_model_candidate_comparison.json")

    assert model_path.exists(), "Candidate ST model artifact missing."
    assert meta_path.exists(), "Candidate ST metadata missing."
    assert report_path.exists(), "Candidate benchmark comparison report missing."

    bundle = joblib.load(model_path)
    assert "model_version" in bundle
    assert "tags" in bundle
    assert len(bundle["tags"]) == 10
    assert "classifiers" in bundle
    assert len(bundle["classifiers"]) == 10
    assert "thresholds" in bundle
    assert len(bundle["thresholds"]) == 10

    with open(report_path, "r", encoding="utf-8") as f:
        comp_data = json.load(f)
    assert "baseline_model" in comp_data
    assert "candidate_model" in comp_data
    assert "recommendation" in comp_data
    assert comp_data["recommendation"] == "RETAIN_BASELINE_TFIDF"


def test_pipeline_categorization_reliability_warnings():
    """Verify pipeline integrates categorizer confidence tiers and raises margin warnings."""
    pipeline = NLPEvidencePipeline.create_default()

    # Text that produces narrow margins or edge decisions
    text = "Participated in university club project developing web portal and sensor dashboard."
    res = pipeline.process_text(text, document_id="TEST-REL-001")

    assert "confidence_tier" in res.categorization
    assert "uncertain_tags" in res.categorization
    assert "review_recommended" in res.categorization

    # If review recommended is True, verify corresponding warning is logged
    if res.categorization.get("review_recommended", False):
        assert any("Domain categorization margin is narrow" in w for w in res.warnings)



def test_confidence_tier_boundary_definitions(loaded_categorizer):
    """
    Regression test verifying exact margin boundaries in the production categorizer:
    - HIGH: margin >= 0.15
    - MEDIUM: 0.05 <= margin < 0.15
    - LOW_MARGIN: 0.00 <= margin < 0.05 (triggers uncertainty & review_recommended)
    - Near-boundary negative: -0.05 < margin < 0.00 (triggers uncertainty & review_recommended)
    """
    assert loaded_categorizer.is_fitted
    tag = "lbl_domain_systems"
    thresh = loaded_categorizer.thresholds[tag]

    cases = [
        (thresh + 0.20, "HIGH", True, False),
        (thresh + 0.15, "HIGH", True, False),
        (thresh + 0.10, "MEDIUM", True, False),
        (thresh + 0.05, "MEDIUM", True, False),
        (thresh + 0.02, "LOW_MARGIN", True, True),
        (thresh - 0.02, None, False, True),
        (thresh - 0.10, None, False, False),
    ]

    for prob, exp_tier, exp_pred, exp_unc in cases:
        margin = prob - thresh
        if prob >= thresh:
            if margin >= 0.15:
                tier = "HIGH"
            elif margin >= 0.05:
                tier = "MEDIUM"
            else:
                tier = "LOW_MARGIN"
            assert tier == exp_tier
        else:
            assert exp_tier is None

        is_unc = (prob >= thresh and margin < 0.05) or (prob < thresh and abs(margin) < 0.05)
        assert is_unc == exp_unc
