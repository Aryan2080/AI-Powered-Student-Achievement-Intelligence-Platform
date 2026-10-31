"""
tests/test_blind_sample_validator.py
====================================
Comprehensive Unit Tests for Step 18 Blind Sample Validation & Reviewer Auditing.
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

import csv
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set

import pytest

from src.nlp.blind_sample_validator import (
    DOMAIN_TAGS,
    DOMAIN_TAG_NAMES,
    parse_tag_string,
    verify_reviewer_completion,
    compute_multilabel_metrics,
    run_validation_audit,
    ReviewerIncompleteError,
)

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "data/processed/achievement_classification_dataset.csv"
EXPECTED_DATASET_SHA256 = "1a62b8d8b56bd94df27d8c40ff86ef892b7d50e0c6bb92ff4f69882596b27ddc"
GOLD_TASK_PATH = ROOT / "data/annotations/domain_categorization_gold_annotation_task.jsonl"
BLIND_CSV_PATH = ROOT / "data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv"
KEY_JSONL_PATH = ROOT / "data/annotations/ai_assisted/domain_categorization_validation_sample_key.jsonl"


def sha256_of_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ==============================================================================
# 1. TAG STRING PARSER & ZERO-TAG TESTS
# ==============================================================================

def test_parse_tag_string_missing_cases():
    """Verify empty/missing tag fields are distinguished from explicit zero-tag."""
    tags, is_zero, is_missing = parse_tag_string("")
    assert tags == []
    assert not is_zero
    assert is_missing

    tags, is_zero, is_missing = parse_tag_string(None)
    assert tags == []
    assert not is_zero
    assert is_missing

    tags, is_zero, is_missing = parse_tag_string("   ")
    assert tags == []
    assert not is_zero
    assert is_missing


def test_parse_tag_string_explicit_zero_tag():
    """Verify explicit zero-tag tokens are recognized as valid zero-tag answers."""
    for token in ["NONE", "none", "None", "[]", "[ZERO-TAG]", "[NONE]"]:
        tags, is_zero, is_missing = parse_tag_string(token)
        assert tags == [], f"Expected empty tags for token '{token}'"
        assert is_zero, f"Expected is_zero=True for token '{token}'"
        assert not is_missing, f"Expected is_missing=False for token '{token}'"


def test_parse_tag_string_valid_tags():
    """Verify delimiter handling (pipe, comma, quotes)."""
    tags, is_zero, is_missing = parse_tag_string("lbl_domain_ai|lbl_domain_ml")
    assert tags == ["lbl_domain_ai", "lbl_domain_ml"]
    assert not is_zero
    assert not is_missing

    tags, is_zero, is_missing = parse_tag_string("lbl_domain_systems, lbl_domain_web")
    assert tags == ["lbl_domain_systems", "lbl_domain_web"]


# ==============================================================================
# 2. REVIEWER COMPLETION AUDIT TESTS
# ==============================================================================

def test_verify_reviewer_completion_on_current_blind_sheet():
    """Ensure blind sheet audit verifies all 30 completed records once adjudicated, permitting scoring."""
    res = verify_reviewer_completion(BLIND_CSV_PATH, KEY_JSONL_PATH)
    assert res["is_complete"], "Blind sheet must be complete after all 30 records are adjudicated"
    assert res["can_score"], "Scoring must be permitted"
    assert res["total_expected"] == 30
    assert res["completed_count"] == 30
    assert res["incomplete_count"] == 0
    assert res["blocker_reason"] is None
    assert len(res["id_mismatches"]) == 0, "IDs must match key perfectly"
    assert len(res["incomplete_rows"]) == 0

    # Verify approved Step 20 adjudications
    completed_by_id = {r["achievement_id"]: r for r in res["completed_rows"]}
    assert completed_by_id["ACH000155"]["raw_tags"] == "lbl_domain_security"
    assert completed_by_id["ACH000537"]["raw_tags"] == "lbl_domain_systems"


def test_verify_reviewer_completion_blocks_on_incomplete_submission(tmp_path):
    """Ensure blind sheet audit correctly blocks scoring when incomplete records remain."""
    test_csv = tmp_path / "incomplete_blind.csv"
    with open(BLIND_CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Mark row 5 (ACH000155) as pending / missing tags
    rows[4]["validator_tags"] = ""
    rows[4]["validator_status"] = "PENDING"
    rows[4]["validator_uncertain"] = "TRUE"

    with open(test_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    res = verify_reviewer_completion(test_csv, KEY_JSONL_PATH)
    assert not res["is_complete"], "Must be incomplete when pending records exist"
    assert not res["can_score"], "Scoring must be blocked"
    assert res["completed_count"] == 29
    assert res["incomplete_count"] == 1
    assert "Validation blocked" in res["blocker_reason"]
    incomplete_ids = {r["achievement_id"] for r in res["incomplete_rows"]}
    assert incomplete_ids == {"ACH000155"}


def test_verify_reviewer_completion_detects_invalid_tag(tmp_path):
    """Ensure invalid domain tags are flagged."""
    test_csv = tmp_path / "test_blind.csv"
    with open(BLIND_CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Mark first row with invalid tag
    rows[0]["validator_name"] = "reviewer_test"
    rows[0]["validator_status"] = "COMPLETED"
    rows[0]["validator_tags"] = "invalid_nonexistent_tag"

    with open(test_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    res = verify_reviewer_completion(test_csv, KEY_JSONL_PATH)
    assert not res["is_complete"]
    assert res["invalid_tag_count"] > 0
    assert any("outside canonical 10-tag taxonomy" in e for e in res["incomplete_rows"][0]["errors"])


def test_verify_reviewer_completion_detects_mutual_exclusion_violation(tmp_path):
    """Ensure lbl_domain_other cannot be combined with technical tags."""
    test_csv = tmp_path / "test_blind.csv"
    with open(BLIND_CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    rows[0]["validator_name"] = "reviewer_test"
    rows[0]["validator_status"] = "COMPLETED"
    rows[0]["validator_tags"] = "lbl_domain_systems|lbl_domain_other"

    with open(test_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    res = verify_reviewer_completion(test_csv, KEY_JSONL_PATH)
    assert not res["is_complete"]
    assert any("Mutual exclusion violation" in e for e in res["incomplete_rows"][0]["errors"])


# ==============================================================================
# 3. METRICS CALCULATION ENGINE TESTS
# ==============================================================================

def test_compute_multilabel_metrics():
    """Verify multi-label metrics calculation logic with known synthetic inputs."""
    y_true = [
        ["lbl_domain_ai", "lbl_domain_ml"],
        ["lbl_domain_systems"],
        [],  # Zero-tag
        ["lbl_domain_web"],
    ]
    y_pred = [
        ["lbl_domain_ai", "lbl_domain_ml"],  # Exact match
        ["lbl_domain_systems", "lbl_domain_web"],  # 1 FP
        [],  # Exact zero-tag match
        ["lbl_domain_data"],  # 1 FN, 1 FP
    ]

    metrics = compute_multilabel_metrics(y_true, y_pred)
    assert metrics["sample_size"] == 4
    assert metrics["exact_match_ratio"] == 0.5  # 2 of 4 exact matches
    assert metrics["hamming_loss"] > 0.0
    assert metrics["zero_tag_metrics"]["support"] == 1
    assert metrics["zero_tag_metrics"]["tp"] == 1
    assert metrics["zero_tag_metrics"]["precision"] == 1.0


# ==============================================================================
# 4. STEP 18 AUDIT & ARTIFACT PRESERVATION TESTS
# ==============================================================================

def test_frozen_master_dataset_integrity():
    assert DATASET_PATH.exists()
    actual_hash = sha256_of_file(DATASET_PATH)
    assert actual_hash == EXPECTED_DATASET_SHA256, "Master dataset must remain bit-exact"


def test_verified_reference_records_preserved():
    assert GOLD_TASK_PATH.exists()
    verified_count = 0
    with open(GOLD_TASK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                if rec.get("annotation_status") == "VERIFIED":
                    verified_count += 1
    assert verified_count == 7, f"Expected 7 verified records, found {verified_count}"


def test_run_validation_audit_generates_comparison_csv(tmp_path):
    """Verify run_validation_audit produces completed evaluation comparison CSV when all records are finalized."""
    out_csv = tmp_path / "comparison.csv"
    res = run_validation_audit(
        blind_csv_path=BLIND_CSV_PATH,
        key_jsonl_path=KEY_JSONL_PATH,
        output_comparison_csv=out_csv,
    )
    assert res["status"] == "VALIDATION_COMPLETE"
    assert res["verification"]["can_score"]
    assert res["metrics"] is not None
    assert out_csv.exists()

    with open(out_csv, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert len(rows) == 31, f"Expected 31 lines (1 header + 30 records), got {len(rows)}"
    # Header check
    assert rows[0][0] == "achievement_id"
    # Row 1 (ACH000587) is VALIDATED
    assert rows[1][0] == "ACH000587"
    assert rows[1][8] == "VALIDATED"
    # Row 5 (ACH000155) is VALIDATED
    assert rows[5][0] == "ACH000155"
    assert rows[5][8] == "VALIDATED"
    assert rows[5][3] == "lbl_domain_security"


def test_run_validation_audit_blocks_on_incomplete_sheet(tmp_path):
    """Verify run_validation_audit halts with blocked status and writes BLOCKED comparison CSV when records are pending."""
    test_csv = tmp_path / "incomplete_blind.csv"
    out_csv = tmp_path / "blocked_comparison.csv"
    with open(BLIND_CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Mark row 5 (ACH000155) as pending
    rows[4]["validator_tags"] = ""
    rows[4]["validator_status"] = "PENDING"
    rows[4]["validator_uncertain"] = "TRUE"

    with open(test_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    res = run_validation_audit(
        blind_csv_path=test_csv,
        key_jsonl_path=KEY_JSONL_PATH,
        output_comparison_csv=out_csv,
    )
    assert res["status"] == "EVALUATION_BLOCKED_PENDING_REVIEWER_COMPLETION"
    assert res["metrics"] is None
    assert out_csv.exists()

    with open(out_csv, "r", encoding="utf-8") as f:
        comp_rows = list(csv.reader(f))

    assert len(comp_rows) == 31
    assert comp_rows[5][8] == "PENDING"
    assert comp_rows[5][7] == "BLOCKED_UNRESOLVED"
