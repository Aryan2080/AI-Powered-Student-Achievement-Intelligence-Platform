"""
tests/test_annotation_workflow.py
=================================
Unit & Quality Control Tests for Gold Annotation Workflow (Step 13)
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
from typing import Any, Dict, List

import pytest

from src.nlp.annotation_workflow import (
    AnnotatorReviewStatus,
    AnnotationStatus,
    DisagreementStatus,
    GoldAnnotationItem,
    adjudicate_record,
    compute_inter_annotator_agreement,
    detect_disagreements,
    export_annotation_task_csv,
    import_annotation_task_csv,
    safe_import_annotation_csv,
    triage_annotation_record,
    validate_annotation_corpus,
    validate_annotation_record,
    verify_consensus_record,
)
from src.nlp.categorization import DOMAIN_TAGS
from src.nlp.evaluate_gold_categorization import evaluate_gold_categorization


# ==============================================================================
# 1. SCHEMA & RECORD VALIDATION TESTS
# ==============================================================================

def test_valid_record_passes_validation():
    """Verify that a compliant verified record passes validation with zero errors."""
    record = {
        "achievement_id": "ACH000364",
        "achievement_text": "Patent publication for fault-tolerant robotics using AWS.",
        "primary_category": "PATENT",
        "split": "test",
        "annotator_a_tags": ["lbl_domain_systems"],
        "annotator_b_tags": ["lbl_domain_systems"],
        "adjudicated_tags": ["lbl_domain_systems"],
        "adjudicator": "Member 1",
        "adjudication_notes": "Ground truth verified.",
        "annotation_status": "VERIFIED",
    }
    errors = validate_annotation_record(record)
    assert len(errors) == 0, f"Expected no errors, got: {errors}"


def test_invalid_tag_detected():
    """Verify that unrecognized or hallucinated domain tags are caught."""
    record = {
        "achievement_id": "ACH000100",
        "achievement_text": "Sample text",
        "split": "test",
        "adjudicated_tags": ["lbl_domain_invalid_tag", "lbl_domain_ai"],
        "adjudicator": "Lead",
        "adjudication_notes": "Reviewed",
        "annotation_status": "VERIFIED",
    }
    errors = validate_annotation_record(record)
    assert any("Invalid domain tag 'lbl_domain_invalid_tag'" in e for e in errors)


def test_missing_required_fields():
    """Verify that missing ID or text triggers validation errors."""
    record = {
        "achievement_id": "",
        "achievement_text": None,
        "split": "test",
        "annotation_status": "PENDING_HUMAN_REVIEW",
    }
    errors = validate_annotation_record(record)
    assert any("Missing or empty 'achievement_id'" in e for e in errors)
    assert any("Missing or non-string 'achievement_text'" in e for e in errors)


def test_split_isolation_safeguard():
    """Verify that records not in the 'test' split are rejected from gold evaluation."""
    record = {
        "achievement_id": "ACH000200",
        "achievement_text": "Sample text",
        "split": "train",
        "annotation_status": "PENDING_HUMAN_REVIEW",
    }
    errors = validate_annotation_record(record)
    assert any("Invalid split 'train'" in e for e in errors)


def test_anti_fabrication_safeguard_for_pending_records():
    """Verify that pending records cannot carry premature or fabricated adjudicated tags."""
    record = {
        "achievement_id": "ACH000300",
        "achievement_text": "Pending hackathon record",
        "split": "test",
        "adjudicated_tags": ["lbl_domain_web"],  # Premature label!
        "annotation_status": "PENDING_HUMAN_REVIEW",
    }
    errors = validate_annotation_record(record)
    assert any("PENDING_HUMAN_REVIEW record has non-null 'adjudicated_tags'" in e for e in errors)


def test_premature_verification_safeguard():
    """Verify that marking a record VERIFIED without adjudicator and notes is blocked."""
    record = {
        "achievement_id": "ACH000400",
        "achievement_text": "Sample text",
        "split": "test",
        "adjudicated_tags": ["lbl_domain_ai"],
        "adjudicator": None,
        "adjudication_notes": "",
        "annotation_status": "VERIFIED",
    }
    errors = validate_annotation_record(record)
    assert any("missing 'adjudicator'" in e for e in errors)
    assert any("missing 'adjudication_notes'" in e for e in errors)


# ==============================================================================
# 2. CORPUS VALIDATION & DUPLICATE ID TESTS
# ==============================================================================

def test_duplicate_id_detection_in_corpus():
    """Verify that duplicate achievement IDs are flagged corpus-wide."""
    records = [
        {
            "achievement_id": "ACH000001",
            "achievement_text": "Text 1",
            "split": "test",
            "annotation_status": "PENDING_HUMAN_REVIEW",
        },
        {
            "achievement_id": "ACH000001",  # Duplicate!
            "achievement_text": "Text 2",
            "split": "test",
            "annotation_status": "PENDING_HUMAN_REVIEW",
        },
    ]
    res = validate_annotation_corpus(records)
    assert not res["is_valid"]
    assert "ACH000001" in res["duplicate_ids"]


def test_master_gold_task_file_integrity():
    """Verify the real master gold task file passes all quality checks."""
    task_p = Path("data/annotations/domain_categorization_gold_annotation_task.jsonl")
    assert task_p.exists()

    records = []
    with open(task_p, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    assert len(records) == 175
    val_res = validate_annotation_corpus(records, expected_count=175)
    assert val_res["is_valid"], f"Master gold task corpus failed validation: {val_res['record_errors']}"
    assert val_res["status_counts"]["VERIFIED"] == 7
    assert val_res["status_counts"]["PENDING_HUMAN_REVIEW"] == 168


# ==============================================================================
# 3. BLIND ANNOTATION & CSV IMPORT / EXPORT TESTS
# ==============================================================================

def test_blind_csv_export_and_import_roundtrip():
    """Verify that CSV export enforces blind annotation and imports cleanly."""
    task_records = [
        {
            "achievement_id": "ACH_TEST_01",
            "achievement_text": "Developed neural network using PyTorch.",
            "primary_category": "PROJECT",
            "split": "test",
            "annotator_a_name": "Reviewer A",
            "annotator_a_tags": ["lbl_domain_ai", "lbl_domain_ml"],
            "annotator_a_notes": "Explicit PyTorch mention",
            "annotator_a_status": "COMPLETED",
            "annotator_b_name": "Reviewer B",
            "annotator_b_tags": ["lbl_domain_ai", "lbl_domain_ml"],
            "annotator_b_notes": "Agreed",
            "annotator_b_status": "COMPLETED",
            "disagreement_status": "AGREED",
            "adjudicated_tags": ["lbl_domain_ai", "lbl_domain_ml"],
            "adjudication_notes": "Consensus",
            "adjudicator": "Lead",
            "annotation_status": "VERIFIED",
        },
        {
            "achievement_id": "ACH_TEST_02",
            "achievement_text": "Pending achievement description.",
            "primary_category": "HACKATHON",
            "split": "test",
            "annotator_a_name": None,
            "annotator_a_tags": None,
            "annotator_a_notes": None,
            "annotator_a_status": "PENDING",
            "annotator_b_name": None,
            "annotator_b_tags": None,
            "annotator_b_notes": None,
            "annotator_b_status": "PENDING",
            "disagreement_status": "AWAITING_REVIEWS",
            "adjudicated_tags": None,
            "adjudication_notes": None,
            "adjudicator": None,
            "annotation_status": "PENDING_HUMAN_REVIEW",
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_p = Path(tmpdir) / "test_tasks.csv"
        export_annotation_task_csv(task_records, csv_p, blind=True)
        assert csv_p.exists()

        # Check CSV headers ensure blind annotation (no provisional_heuristic_tags column)
        with open(csv_p, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert "provisional_heuristic_tags" not in header
            assert "predicted_tags" not in header
            assert "achievement_text" in header
            assert "annotator_a_tags" in header
            assert "annotator_b_tags" in header

        imported = import_annotation_task_csv(csv_p)
        assert len(imported) == 2
        assert imported[0]["achievement_id"] == "ACH_TEST_01"
        assert imported[0]["annotator_a_tags"] == ["lbl_domain_ai", "lbl_domain_ml"]
        assert imported[0]["annotation_status"] == "VERIFIED"

        # Pending record must preserve null tags
        assert imported[1]["achievement_id"] == "ACH_TEST_02"
        assert imported[1]["annotator_a_tags"] is None
        assert imported[1]["adjudicated_tags"] is None
        assert imported[1]["annotation_status"] == "PENDING_HUMAN_REVIEW"


# ==============================================================================
# 4. DISAGREEMENT & INTER-ANNOTATOR AGREEMENT TESTS
# ==============================================================================

def test_disagreement_detection_and_adjudication_queue():
    """Verify that differing annotator tags are placed in the adjudication queue."""
    records = [
        {
            "achievement_id": "ACH_DIS_01",
            "achievement_text": "IoT edge sensor system with microcontrollers and cloud sync.",
            "annotator_a_status": "COMPLETED",
            "annotator_b_status": "COMPLETED",
            "annotator_a_tags": ["lbl_domain_hardware", "lbl_domain_systems"],
            "annotator_b_tags": ["lbl_domain_hardware"],  # Omitted systems!
            "annotation_status": "AWAITING_ADJUDICATION",
        },
        {
            "achievement_id": "ACH_AGR_01",
            "achievement_text": "Robotics vision using OpenCV.",
            "annotator_a_status": "COMPLETED",
            "annotator_b_status": "COMPLETED",
            "annotator_a_tags": ["lbl_domain_cv"],
            "annotator_b_tags": ["lbl_domain_cv"],  # Complete agreement
            "annotation_status": "AWAITING_ADJUDICATION",
        },
    ]

    res = detect_disagreements(records)
    assert res["agreed_count"] == 1
    assert res["disagreed_count"] == 1
    queue = res["awaiting_adjudication_queue"]
    assert len(queue) == 1
    assert queue[0]["achievement_id"] == "ACH_DIS_01"
    assert queue[0]["annotator_a_only"] == ["lbl_domain_systems"]
    assert queue[0]["intersection"] == ["lbl_domain_hardware"]


def test_inter_annotator_agreement_insufficient_data_guard():
    """Verify that absence of completed dual annotations explicitly reports insufficient data."""
    pending_records = [
        {
            "achievement_id": f"ACH_{i}",
            "annotator_a_status": "PENDING",
            "annotator_b_status": "PENDING",
            "annotator_a_tags": None,
            "annotator_b_tags": None,
        }
        for i in range(10)
    ]
    iaa = compute_inter_annotator_agreement(pending_records)
    assert not iaa["has_sufficient_data"]
    assert "Insufficient completed dual annotations" in iaa["message"]
    assert iaa["macro_kappa"] is None


def test_inter_annotator_agreement_calculation():
    """Verify mathematically correct multi-label Jaccard and Cohen's Kappa calculations."""
    dual_records = [
        {
            "achievement_id": "1",
            "annotator_a_status": "COMPLETED",
            "annotator_b_status": "COMPLETED",
            "annotator_a_tags": ["lbl_domain_ai", "lbl_domain_ml"],
            "annotator_b_tags": ["lbl_domain_ai", "lbl_domain_ml"],  # Jaccard = 1.0
        },
        {
            "achievement_id": "2",
            "annotator_a_status": "COMPLETED",
            "annotator_b_status": "COMPLETED",
            "annotator_a_tags": ["lbl_domain_ai"],
            "annotator_b_tags": ["lbl_domain_ai", "lbl_domain_cv"],  # Jaccard = 0.5
        },
    ]
    iaa = compute_inter_annotator_agreement(dual_records)
    assert iaa["has_sufficient_data"]
    assert iaa["completed_dual_annotations"] == 2
    assert iaa["mean_jaccard_similarity"] == 0.75  # (1.0 + 0.5) / 2
    assert "lbl_domain_ai" in iaa["per_tag_kappa"]
    assert iaa["per_tag_kappa"]["lbl_domain_ai"] == 1.0  # Both agreed on AI


# ==============================================================================
# 5. ADJUDICATION & EVALUATION SAFEGUARDS
# ==============================================================================

def test_adjudicate_record_success():
    """Verify safe resolution of a disputed record into verified state."""
    raw = {
        "achievement_id": "ACH_DIS_01",
        "achievement_text": "IoT edge system.",
        "primary_category": "PROJECT",
        "split": "test",
        "annotation_status": "AWAITING_ADJUDICATION",
    }
    adjudicated = adjudicate_record(
        record=raw,
        adjudicated_tags=["lbl_domain_hardware", "lbl_domain_systems"],
        adjudicator="Senior NLP Engineer",
        notes="Reviewed hardware schematics and cloud telemetry.",
    )
    assert adjudicated["annotation_status"] == "VERIFIED"
    assert adjudicated["disagreement_status"] == "RESOLVED"
    assert adjudicated["adjudicator"] == "Senior NLP Engineer"
    assert sorted(adjudicated["adjudicated_tags"]) == ["lbl_domain_hardware", "lbl_domain_systems"]


def test_adjudicate_record_invalid_tag_rejection():
    """Verify that adjudication rejects non-taxonomy tags."""
    raw = {"achievement_id": "ACH_01"}
    with pytest.raises(ValueError, match="Invalid domain tag"):
        adjudicate_record(
            record=raw,
            adjudicated_tags=["lbl_domain_quantum_computing"],  # Not in taxonomy
            adjudicator="Admin",
            notes="Notes",
        )


def test_gold_evaluation_script_execution():
    """Verify that evaluate_gold_categorization executes and produces valid summary output."""
    summary = evaluate_gold_categorization(
        gold_task_path="data/annotations/domain_categorization_gold_annotation_task.jsonl",
        model_path="models/achievement_categorizer_v1.0.1.joblib",
        output_summary_path=None,
    )
    assert "corpus_status" in summary
    assert summary["corpus_status"]["verified_records"] == 7
    assert summary["corpus_status"]["pending_records"] == 168
    assert summary["corpus_status"]["is_provisional_sample"] is True
    assert "overall_metrics" in summary
    assert "micro_f1" in summary["overall_metrics"]
    assert "confidence_tier_performance" in summary


def test_confirmed_zero_tag_token_handling():
    """Verify that explicit 'NONE' token parses to empty list [] and exports as 'NONE'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_p = Path(tmpdir) / "test_zero_tag.csv"
        records = [
            {
                "achievement_id": "ACH_ZERO_01",
                "achievement_text": "Participated in inter-college basketball championship.",
                "primary_category": "COMPETITION",
                "split": "test",
                "annotator_a_tags": [],
                "annotator_a_status": "COMPLETED",
                "annotator_b_tags": [],
                "annotator_b_status": "COMPLETED",
                "adjudicated_tags": [],
                "adjudicator": "Lead",
                "adjudication_notes": "Genuine sports achievement, confirmed zero technical tags.",
                "annotation_status": "VERIFIED",
            }
        ]
        export_annotation_task_csv(records, csv_p, blind=True)

        # Inspect raw CSV content has 'NONE'
        with open(csv_p, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert row["annotator_a_tags"] == "NONE"
            assert row["annotator_b_tags"] == "NONE"
            assert row["adjudicated_tags"] == "NONE"

        # Import back and verify parsed as empty list []
        imported = import_annotation_task_csv(csv_p)
        assert len(imported) == 1
        assert imported[0]["annotator_a_tags"] == []
        assert imported[0]["annotator_b_tags"] == []
        assert imported[0]["adjudicated_tags"] == []
        assert imported[0]["annotation_status"] == "VERIFIED"


def test_uncertainty_flag_triggers_adjudication_queue():
    """Verify that an annotator flagging uncertainty forces escalation to adjudication queue."""
    records = [
        {
            "achievement_id": "ACH_UNC_01",
            "achievement_text": "Built hybrid smart system for campus facility tracking.",
            "annotator_a_status": "COMPLETED",
            "annotator_b_status": "COMPLETED",
            "annotator_a_tags": ["lbl_domain_systems"],
            "annotator_b_tags": ["lbl_domain_systems"],  # Same tags!
            "annotator_a_uncertain": True,  # But Annotator A was uncertain
            "annotation_status": "AWAITING_ADJUDICATION",
        }
    ]
    res = detect_disagreements(records)
    assert res["agreed_count"] == 0
    assert res["disagreed_count"] == 1
    queue = res["awaiting_adjudication_queue"]
    assert len(queue) == 1
    assert queue[0]["achievement_id"] == "ACH_UNC_01"
    assert "Annotator A flagged uncertainty" in queue[0]["adjudication_reason"]


# ==============================================================================
# 6. STEP 15 SAFE IMPORT, PARTIAL REVIEW & CONFLICT TESTS
# ==============================================================================

def test_safe_import_csv_and_pristine_backup():
    """Verify safe_import_annotation_csv creates a pristine backup copy and parses correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_csv = Path(tmpdir) / "test_tasks.csv"
        records = [
            {
                "achievement_id": "ACH_SAFE_01",
                "achievement_text": "Sample text",
                "primary_category": "PROJECT",
                "split": "test",
                "annotator_a_status": "PENDING",
                "annotator_b_status": "PENDING",
                "annotation_status": "PENDING_HUMAN_REVIEW",
            }
        ]
        export_annotation_task_csv(records, tmp_csv, blind=True)
        assert tmp_csv.exists()

        imported_recs, summary = safe_import_annotation_csv(tmp_csv)
        assert summary["is_valid"] is True
        assert len(imported_recs) == 1
        assert imported_recs[0]["achievement_id"] == "ACH_SAFE_01"
        assert imported_recs[0]["annotator_a_tags"] is None  # Blank remains None, not []

        # Check that pristine backup was created automatically
        backup_p = Path(summary["pristine_backup_path"])
        assert backup_p.exists()


def test_partial_annotations_queue_handling():
    """Verify that records with one completed review and one pending review are routed to partial queue."""
    records = [
        {
            "achievement_id": "ACH_PART_01",
            "achievement_text": "Completed by A, pending B",
            "annotator_a_status": "COMPLETED",
            "annotator_b_status": "PENDING",
            "annotator_a_tags": ["lbl_domain_ai"],
            "annotator_b_tags": None,
            "annotation_status": "PENDING_HUMAN_REVIEW",
        }
    ]
    res = detect_disagreements(records)
    assert res["partial_review_count"] == 1
    assert res["unreviewed_count"] == 0
    assert len(res["partial_reviews_queue"]) == 1
    assert res["partial_reviews_queue"][0]["achievement_id"] == "ACH_PART_01"
    assert res["partial_reviews_queue"][0]["pending_annotator"] == "Annotator B"


def test_conflicting_duplicate_submissions_rejected():
    """Verify that duplicate rows with differing tag submissions are detected and rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_p = Path(tmpdir) / "conflicts.csv"
        with open(csv_p, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "achievement_id", "achievement_text", "primary_category", "split",
                "annotator_a_name", "annotator_a_tags", "annotator_a_notes", "annotator_a_uncertain", "annotator_a_status",
                "annotator_b_name", "annotator_b_tags", "annotator_b_notes", "annotator_b_uncertain", "annotator_b_status",
                "disagreement_status", "adjudicated_tags", "adjudication_notes", "adjudicator", "annotation_status"
            ])
            # Submission 1: tag AI
            writer.writerow([
                "ACH_DUP_01", "Some robotics text", "PROJECT", "test",
                "A", "lbl_domain_ai", "", "FALSE", "COMPLETED",
                "B", "lbl_domain_ai", "", "FALSE", "COMPLETED",
                "AGREED", "", "", "", "PENDING_HUMAN_REVIEW"
            ])
            # Submission 2: tag WEB (conflicting!)
            writer.writerow([
                "ACH_DUP_01", "Some robotics text", "PROJECT", "test",
                "A", "lbl_domain_web", "", "FALSE", "COMPLETED",
                "B", "lbl_domain_web", "", "FALSE", "COMPLETED",
                "AGREED", "", "", "", "PENDING_HUMAN_REVIEW"
            ])

        imported, summary = safe_import_annotation_csv(csv_p)
        assert summary["is_valid"] is False
        assert summary["conflicting_submissions_count"] == 1
        assert "ACH_DUP_01" in summary["record_errors"]
        assert any("Conflicting duplicate submissions" in e for e in summary["record_errors"]["ACH_DUP_01"])


def test_unknown_and_malformed_tags_actionable_error():
    """Verify that unrecognized domain tags generate actionable error messages listing valid tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_p = Path(tmpdir) / "malformed.csv"
        with open(csv_p, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "achievement_id", "achievement_text", "primary_category", "split",
                "annotator_a_name", "annotator_a_tags", "annotator_a_notes", "annotator_a_uncertain", "annotator_a_status",
                "annotator_b_name", "annotator_b_tags", "annotator_b_notes", "annotator_b_uncertain", "annotator_b_status",
                "disagreement_status", "adjudicated_tags", "adjudication_notes", "adjudicator", "annotation_status"
            ])
            writer.writerow([
                "ACH_MAL_01", "Quantum computing experiment", "PROJECT", "test",
                "A", "lbl_domain_quantum", "", "FALSE", "COMPLETED",  # Invalid tag!
                "B", "lbl_domain_ai", "", "FALSE", "COMPLETED",
                "DISAGREED", "", "", "", "PENDING_HUMAN_REVIEW"
            ])

        imported, summary = safe_import_annotation_csv(csv_p)
        assert summary["is_valid"] is False
        assert "ACH_MAL_01" in summary["record_errors"]
        assert any("Malformed or unknown domain tag 'lbl_domain_quantum'" in e for e in summary["record_errors"]["ACH_MAL_01"])


def test_evaluation_strictly_excludes_unverified_records():
    """Verify that evaluate_gold_categorization excludes pending/unreviewed records from scoring."""
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_p = Path(tmpdir) / "mixed_corpus.jsonl"
        mixed_items = [
            {
                "achievement_id": "ACH_VER_01",
                "achievement_text": "Published machine learning paper with PyTorch.",
                "primary_category": "RESEARCH_PUBLICATION",
                "split": "test",
                "adjudicated_tags": ["lbl_domain_ml"],
                "adjudicator": "Lead",
                "adjudication_notes": "Verified",
                "annotation_status": "VERIFIED",
            },
            {
                "achievement_id": "ACH_PEND_01",
                "achievement_text": "Pending hackathon record.",
                "primary_category": "HACKATHON",
                "split": "test",
                "adjudicated_tags": None,  # Pending!
                "annotation_status": "PENDING_HUMAN_REVIEW",
            },
        ]
        with open(jsonl_p, "w", encoding="utf-8") as f:
            for item in mixed_items:
                f.write(json.dumps(item) + "\n")

        summary = evaluate_gold_categorization(
            gold_task_path=jsonl_p,
            model_path="models/achievement_categorizer_v1.0.1.joblib",
            output_summary_path=None,
        )
        assert summary["corpus_status"]["total_records"] == 2
        assert summary["corpus_status"]["verified_records"] == 1
        assert summary["corpus_status"]["pending_records"] == 1


def test_frozen_dataset_and_production_model_preservation():
    """Verify bitwise SHA-256 preservation of the frozen dataset and production categorizer integrity."""
    import hashlib
    dataset_p = Path("data/processed/achievement_classification_dataset.csv")
    assert dataset_p.exists()
    d_hash = hashlib.sha256(dataset_p.read_bytes()).hexdigest()
    assert d_hash == "1a62b8d8b56bd94df27d8c40ff86ef892b7d50e0c6bb92ff4f69882596b27ddc"

    model_p = Path("models/achievement_categorizer_v1.0.1.joblib")
    assert model_p.exists()
    assert model_p.stat().st_size == 296149
    c_hash = hashlib.sha256(model_p.read_bytes()).hexdigest()
    assert c_hash == "e0f514a4286752948c069c43dda6626af9e4ace926ab899334d12af77353ddb3"


def test_annotator_agreement_distinguished_from_verified():
    """Verify that matching dual annotations transition to ANNOTATOR_AGREEMENT, not VERIFIED."""
    raw_item = {
        "achievement_id": "ACH_TEST_AGR_01",
        "achievement_text": "Built a scalable Kubernetes cluster on AWS for real-time inference.",
        "primary_category": "PROJECT",
        "split": "test",
        "annotator_a_name": "Reviewer 1",
        "annotator_a_tags": ["lbl_domain_systems"],
        "annotator_a_status": "COMPLETED",
        "annotator_a_uncertain": False,
        "annotator_b_name": "Reviewer 2",
        "annotator_b_tags": ["lbl_domain_systems"],
        "annotator_b_status": "COMPLETED",
        "annotator_b_uncertain": False,
        "adjudicated_tags": None,
        "adjudicator": None,
        "annotation_status": "PENDING_HUMAN_REVIEW",
    }

    triaged = triage_annotation_record(raw_item)
    assert triaged["annotation_status"] == AnnotationStatus.ANNOTATOR_AGREEMENT.value
    assert triaged["disagreement_status"] == DisagreementStatus.AGREED.value
    assert triaged["adjudicated_tags"] is None
    assert triaged["adjudicator"] is None

    # ANNOTATOR_AGREEMENT passes record validation
    errs = validate_annotation_record(triaged)
    assert errs == []


def test_triage_routing_and_uncertainty_escalation():
    """Verify that uncertainty flag routes matching tags to AWAITING_ADJUDICATION."""
    item = {
        "achievement_id": "ACH_TEST_UNC_01",
        "achievement_text": "Built an ambiguous smart IoT hardware node.",
        "primary_category": "PROJECT",
        "split": "test",
        "annotator_a_name": "Reviewer 1",
        "annotator_a_tags": ["lbl_domain_hardware"],
        "annotator_a_status": "COMPLETED",
        "annotator_a_uncertain": True,  # Flagged uncertainty!
        "annotator_b_name": "Reviewer 2",
        "annotator_b_tags": ["lbl_domain_hardware"],
        "annotator_b_status": "COMPLETED",
        "annotator_b_uncertain": False,
        "adjudicated_tags": None,
        "adjudicator": None,
        "annotation_status": "PENDING_HUMAN_REVIEW",
    }

    triaged = triage_annotation_record(item)
    assert triaged["annotation_status"] == AnnotationStatus.AWAITING_ADJUDICATION.value
    assert triaged["disagreement_status"] == DisagreementStatus.DISAGREED.value

    # detect_disagreements routes it to awaiting_adjudication_queue
    res = detect_disagreements([triaged])
    assert res["disagreed_count"] == 1
    assert len(res["awaiting_adjudication_queue"]) == 1
    assert "uncertainty" in res["awaiting_adjudication_queue"][0]["adjudication_reason"].lower()


def test_verify_consensus_record_promotes_to_verified():
    """Verify that verify_consensus_record promotes ANNOTATOR_AGREEMENT to VERIFIED."""
    raw_item = {
        "achievement_id": "ACH_TEST_AGR_02",
        "achievement_text": "Developed an NLP sentiment analysis model using BERT.",
        "primary_category": "PROJECT",
        "split": "test",
        "annotator_a_name": "Reviewer 1",
        "annotator_a_tags": ["lbl_domain_ai", "lbl_domain_nlp"],
        "annotator_a_status": "COMPLETED",
        "annotator_a_uncertain": False,
        "annotator_b_name": "Reviewer 2",
        "annotator_b_tags": ["lbl_domain_ai", "lbl_domain_nlp"],
        "annotator_b_status": "COMPLETED",
        "annotator_b_uncertain": False,
        "adjudicated_tags": None,
        "adjudicator": None,
        "annotation_status": "ANNOTATOR_AGREEMENT",
    }

    verified = verify_consensus_record(
        raw_item,
        adjudicator="Lead Adjudicator",
        notes="Consensus verified against taxonomy guidelines.",
    )
    assert verified["annotation_status"] == AnnotationStatus.VERIFIED.value
    assert verified["disagreement_status"] == DisagreementStatus.RESOLVED.value
    assert set(verified["adjudicated_tags"]) == {"lbl_domain_ai", "lbl_domain_nlp"}
    assert verified["adjudicator"] == "Lead Adjudicator"
    assert "adjudication_timestamp" in verified

    # Verified item passes full validation
    errs = validate_annotation_record(verified)
    assert errs == []


def test_verify_consensus_refuses_disagreed_or_uncertain():
    """Verify that verify_consensus_record rejects incomplete, uncertain, or mismatched records."""
    incomplete = {
        "achievement_id": "ACH_INC_01",
        "achievement_text": "Robotics project",
        "annotator_a_status": "COMPLETED",
        "annotator_b_status": "PENDING",
        "annotator_a_tags": ["lbl_domain_hardware"],
        "annotator_b_tags": None,
        "annotator_a_uncertain": False,
        "annotator_b_uncertain": False,
    }
    with pytest.raises(ValueError, match="incomplete"):
        verify_consensus_record(incomplete, adjudicator="Lead")

    uncertain = {
        "achievement_id": "ACH_UNC_02",
        "achievement_text": "Robotics project",
        "annotator_a_status": "COMPLETED",
        "annotator_b_status": "COMPLETED",
        "annotator_a_tags": ["lbl_domain_hardware"],
        "annotator_b_tags": ["lbl_domain_hardware"],
        "annotator_a_uncertain": True,
        "annotator_b_uncertain": False,
    }
    with pytest.raises(ValueError, match="uncertainty"):
        verify_consensus_record(uncertain, adjudicator="Lead")

    mismatch = {
        "achievement_id": "ACH_MIS_01",
        "achievement_text": "Robotics project",
        "annotator_a_status": "COMPLETED",
        "annotator_b_status": "COMPLETED",
        "annotator_a_tags": ["lbl_domain_hardware"],
        "annotator_b_tags": ["lbl_domain_ai"],
        "annotator_a_uncertain": False,
        "annotator_b_uncertain": False,
    }
    with pytest.raises(ValueError, match="mismatch"):
        verify_consensus_record(mismatch, adjudicator="Lead")



