"""
tests/test_ai_annotator.py
==========================
Comprehensive Unit Tests for Balanced AI-Assisted Domain Annotation Subsystem (Step 17).
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

import csv
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set

import pytest

from src.nlp.ai_annotator import (
    DOMAIN_TAGS,
    DOMAIN_TAG_NAMES,
    AIAnnotationProposal,
    AIAssistedDomainAnnotator,
    generate_validation_sample,
    validate_ai_proposals,
    run_ai_annotation_on_pending_records,
)

FROZEN_DATASET_PATH = Path("data/processed/achievement_classification_dataset.csv")
EXPECTED_DATASET_SHA256 = "1a62b8d8b56bd94df27d8c40ff86ef892b7d50e0c6bb92ff4f69882596b27ddc"
GOLD_TASK_PATH = Path("data/annotations/domain_categorization_gold_annotation_task.jsonl")
PROPOSALS_JSONL_PATH = Path("data/annotations/ai_assisted/domain_categorization_ai_proposals.jsonl")
PROPOSALS_CSV_PATH = Path("data/annotations/ai_assisted/domain_categorization_ai_proposals.csv")
BLIND_CSV_PATH = Path("data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv")
KEY_JSONL_PATH = Path("data/annotations/ai_assisted/domain_categorization_validation_sample_key.jsonl")
METADATA_JSON_PATH = Path("data/annotations/ai_assisted/ai_annotation_run_metadata.json")


def sha256_of_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ==============================================================================
# 1. CORE DATA STRUCTURE & SERIALIZATION TESTS
# ==============================================================================

def test_proposal_dataclass_and_serialization():
    prop = AIAnnotationProposal(
        achievement_id="ACH_TEST_001",
        primary_category="PROJECT",
        achievement_text="Developed a Kubernetes microservices application with Docker.",
        proposed_tags=["lbl_domain_systems"],
        evidence_snippets=["Kubernetes", "Docker", "microservices"],
        annotation_rationale="Explicit infrastructure and systems engineering evidence.",
        uncertainty_flag=False,
        uncertainty_reason=None,
    )
    d = prop.to_dict()
    assert d["achievement_id"] == "ACH_TEST_001"
    assert d["proposed_tags"] == ["lbl_domain_systems"]
    assert d["review_status"] == "PENDING_HUMAN_VALIDATION"
    assert d["annotation_source"] == "AI_PROPOSED"

    row = prop.to_csv_row()
    assert row[0] == "ACH_TEST_001"
    assert row[3] == "lbl_domain_systems"
    assert row[6] == "FALSE"
    assert row[11] == "PENDING_HUMAN_VALIDATION"


def test_zero_tag_serialization_convention():
    """Ensure empty tag sets serialize as [] in JSON and '[]' in CSV, never 'NONE'."""
    prop = AIAnnotationProposal(
        achievement_id="ACH_TEST_002",
        primary_category="LEADERSHIP",
        achievement_text="Elected class representative and organized blood donation camp.",
        proposed_tags=[],
        evidence_snippets=[],
        annotation_rationale="Zero-Tag Policy applied.",
        uncertainty_flag=False,
        uncertainty_reason=None,
    )
    d = prop.to_dict()
    assert d["proposed_tags"] == []

    row = prop.to_csv_row()
    # Proposed tags must be serialized as "[]", never "NONE"
    assert row[3] == "[]"
    assert "NONE" not in row[3]


# ==============================================================================
# 2. LEXICAL & BOUNDARY RULE TESTS
# ==============================================================================

def test_annotator_verbatim_snippets():
    annotator = AIAssistedDomainAnnotator(use_embeddings=False)
    text = "Implemented a real-time object detection pipeline using YOLOv8 and OpenCV on edge sensors."
    snippets = annotator.extract_verbatim_snippets(text)
    assert len(snippets["lbl_domain_cv"]) > 0
    assert any("yolov8" in s.lower() or "opencv" in s.lower() for s in snippets["lbl_domain_cv"])


def test_mutual_exclusion_rule():
    annotator = AIAssistedDomainAnnotator(use_embeddings=False)
    # Text mentions both badminton (other) and full-stack web application (technical)
    text = "Built a full-stack web platform using React and FastAPI for inter-college badminton tournaments."
    prop = annotator.propose_annotation(
        achievement_id="TEST_EXCLUSION",
        achievement_text=text,
        primary_category="PROJECT",
    )
    # lbl_domain_other must be suppressed because web technical tags are present
    assert "lbl_domain_other" not in prop.proposed_tags
    assert "lbl_domain_web" in prop.proposed_tags


def test_pure_non_computing_assigned_other():
    annotator = AIAssistedDomainAnnotator(use_embeddings=False)
    text = "Won gold medal in inter-university lawn tennis championship and state level badminton doubles."
    prop = annotator.propose_annotation(
        achievement_id="TEST_SPORTS",
        achievement_text=text,
        primary_category="SPORTS",
    )
    assert prop.proposed_tags == ["lbl_domain_other"]
    assert len(prop.evidence_snippets) > 0


def test_ai_ml_coupling_rule():
    annotator = AIAssistedDomainAnnotator(use_embeddings=False)
    text = "Trained a deep learning convolutional neural network using PyTorch with cross-validation."
    prop = annotator.propose_annotation(
        achievement_id="TEST_ML_AI",
        achievement_text=text,
        primary_category="PROJECT",
    )
    assert "lbl_domain_ml" in prop.proposed_tags
    assert "lbl_domain_ai" in prop.proposed_tags


def test_zero_tag_policy():
    annotator = AIAssistedDomainAnnotator(use_embeddings=False)
    text = "Served as student coordinator for annual cultural festival and managed volunteer registrations."
    prop = annotator.propose_annotation(
        achievement_id="TEST_ZERO",
        achievement_text=text,
        primary_category="LEADERSHIP",
    )
    assert prop.proposed_tags == []
    assert len(prop.evidence_snippets) == 0
    assert "Zero-Tag Policy" in prop.annotation_rationale


def test_uncertainty_flagging_and_reason():
    annotator = AIAssistedDomainAnnotator(use_embeddings=False)
    # Short ambiguous text
    text = "Attended national conference on futuristic technology trends."
    prop = annotator.propose_annotation(
        achievement_id="TEST_UNCERTAIN",
        achievement_text=text,
        primary_category="CONFERENCE",
    )
    if prop.uncertainty_flag:
        assert prop.uncertainty_reason is not None
        assert len(prop.uncertainty_reason) > 0


# ==============================================================================
# 3. PROPOSAL VALIDATION ENGINE TESTS
# ==============================================================================

def test_validate_ai_proposals_detects_flaws():
    pending_ids = {"ID_1", "ID_2"}

    # Flawed proposal: Invalid tag + invalid review_status + missing uncertainty reason
    flawed_proposal = AIAnnotationProposal(
        achievement_id="ID_1",
        primary_category="PROJECT",
        achievement_text="Some text",
        proposed_tags=["invalid_tag_xyz"],
        evidence_snippets=[],
        annotation_rationale="",
        uncertainty_flag=True,
        uncertainty_reason=None,
        review_status="VERIFIED",  # VIOLATION: cannot be VERIFIED
    )

    res = validate_ai_proposals([flawed_proposal], pending_ids)
    assert not res["is_valid"]
    assert res["error_count"] > 0
    assert any("invalid_tag_xyz" in err for err in res["errors"])
    assert any("PENDING_HUMAN_VALIDATION" in err for err in res["errors"])
    assert any("Uncertainty flagged without specifying" in err for err in res["errors"])
    assert any("Missing proposals for" in err for err in res["errors"])


# ==============================================================================
# 4. STEP 17 ARTIFACT & REPOSITORY INTEGRITY TESTS
# ==============================================================================

def test_frozen_master_dataset_integrity():
    assert FROZEN_DATASET_PATH.exists(), "Master frozen dataset not found"
    actual_hash = sha256_of_file(FROZEN_DATASET_PATH)
    assert actual_hash == EXPECTED_DATASET_SHA256, (
        f"Master dataset modified! Expected {EXPECTED_DATASET_SHA256}, got {actual_hash}"
    )


def test_verified_reference_records_preserved():
    assert GOLD_TASK_PATH.exists()
    verified_records = []
    with open(GOLD_TASK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r.get("annotation_status") == "VERIFIED":
                    verified_records.append(r)

    assert len(verified_records) == 7, f"Expected exactly 7 verified records, found {len(verified_records)}"
    expected_verified_ids = {
        "ACH000364", "ACH001075", "ACH000891", "ACH000645", "ACH000230", "ACH001538", "ACH000376"
    }
    actual_verified_ids = {r["achievement_id"] for r in verified_records}
    assert actual_verified_ids == expected_verified_ids


def test_generated_proposals_integrity():
    assert PROPOSALS_JSONL_PATH.exists()
    assert PROPOSALS_CSV_PATH.exists()

    with open(PROPOSALS_JSONL_PATH, "r", encoding="utf-8") as f:
        jsonl_records = [json.loads(line) for line in f if line.strip()]

    assert len(jsonl_records) == 168, f"Expected exactly 168 proposals in JSONL, got {len(jsonl_records)}"

    with open(PROPOSALS_CSV_PATH, "r", encoding="utf-8") as f:
        csv_rows = list(csv.reader(f))

    assert len(csv_rows) == 169, f"Expected 169 lines (header + 168 rows) in CSV, got {len(csv_rows)}"

    # Check that all records are PENDING_HUMAN_VALIDATION and AI_PROPOSED
    for rec in jsonl_records:
        assert rec["review_status"] == "PENDING_HUMAN_VALIDATION"
        assert rec["annotation_source"] == "AI_PROPOSED"
        for t in rec["proposed_tags"]:
            assert t in DOMAIN_TAGS, f"Tag {t} outside canonical taxonomy"
        if "lbl_domain_other" in rec["proposed_tags"]:
            assert len(rec["proposed_tags"]) == 1, "Mutual exclusion violation in output"
        if rec["uncertainty_flag"]:
            assert rec.get("uncertainty_reason"), "Uncertainty reason missing"


def test_blind_validation_sample_isolation(tmp_path):
    assert BLIND_CSV_PATH.exists()
    assert KEY_JSONL_PATH.exists()

    # Verify generate_validation_sample creates an uncompromised blind template with blank validator fields
    sample_res = generate_validation_sample(
        proposals=[
            AIAnnotationProposal(
                achievement_id=f"ACH_TEST_{i:03d}",
                primary_category="PROJECT",
                achievement_text="Test achievement description text.",
                proposed_tags=["lbl_domain_systems"],
                evidence_snippets=["systems"],
                annotation_rationale="Test rationale.",
                uncertainty_flag=False,
                uncertainty_reason=None,
            )
            for i in range(30)
        ],
        sample_size=30,
        output_dir=tmp_path,
    )
    test_blind_csv = Path(sample_res["blind_csv_path"])
    with open(test_blind_csv, "r", encoding="utf-8") as f:
        blind_rows = list(csv.reader(f))

    assert len(blind_rows) == 31, f"Expected 31 rows (1 header + 30 records), got {len(blind_rows)}"
    headers = blind_rows[0]
    assert headers == [
        "achievement_id", "achievement_text", "primary_category", "split",
        "validator_name", "validator_tags", "validator_notes", "validator_uncertain", "validator_status"
    ]

    # Verify that all validator fields in generated template are blank to ensure blind review
    for r in blind_rows[1:]:
        assert r[4] == "", "validator_name must be blank in blind CSV template"
        assert r[5] == "", "validator_tags must be blank in blind CSV template"
        assert r[6] == "", "validator_notes must be blank in blind CSV template"
        assert r[7] == "FALSE", "validator_uncertain default is FALSE"
        assert r[8] == "PENDING", "validator_status default is PENDING"

    # Also verify that on disk, the 30 sampled records match the key JSONL
    with open(KEY_JSONL_PATH, "r", encoding="utf-8") as f:
        key_records = [json.loads(line) for line in f if line.strip()]
    with open(BLIND_CSV_PATH, "r", encoding="utf-8") as f:
        disk_blind_rows = list(csv.reader(f))

    assert len(key_records) == 30, f"Expected exactly 30 records in key JSONL, got {len(key_records)}"
    assert len(disk_blind_rows) == 31
    blind_ids = [r[0] for r in disk_blind_rows[1:]]
    key_ids = [k["achievement_id"] for k in key_records]
    assert blind_ids == key_ids
