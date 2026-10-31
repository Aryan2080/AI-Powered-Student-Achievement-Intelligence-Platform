"""
tests/test_pilot_evaluator.py
==============================
Unit tests for AI-Assisted Annotation Pilot Evaluation Subsystem (Step 24)
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

import json
from pathlib import Path
import pytest

from src.nlp.pilot_evaluator import (
    DOMAIN_TAGS,
    VALID_DECISIONS,
    VALID_STATUSES,
    analyze_review_effort,
    compute_decision_metrics,
    compute_multilabel_metrics,
    generate_disagreement_analysis,
    parse_tags,
    verify_pilot_preflight,
    evaluate_pilot_queue,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PILOT_QUEUE_CSV = REPO_ROOT / "data/annotations/ai_assisted/pilot/domain_categorization_pilot_queue.csv"
PILOT_MANIFEST_JSON = REPO_ROOT / "data/annotations/ai_assisted/pilot/domain_categorization_pilot_manifest.json"
BLIND_SAMPLE_CSV = REPO_ROOT / "data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv"
GOLD_TASK_JSONL = REPO_ROOT / "data/annotations/domain_categorization_gold_annotation_task.jsonl"


def test_parse_tags_valid_and_zero_tokens():
    # Valid tags
    assert parse_tags("lbl_domain_ai|lbl_domain_ml") == ["lbl_domain_ai", "lbl_domain_ml"]
    assert parse_tags("lbl_domain_systems") == ["lbl_domain_systems"]
    assert parse_tags(" lbl_domain_web | lbl_domain_data ") == ["lbl_domain_data", "lbl_domain_web"]

    # Explicit zero tokens and empty
    assert parse_tags("NONE") == []
    assert parse_tags("[]") == []
    assert parse_tags("[NONE]") == []
    assert parse_tags("[ZERO-TAG]") == []
    assert parse_tags("NO_DOMAIN") == []
    assert parse_tags("") == []
    assert parse_tags(None) == []


def test_parse_tags_invalid_taxonomy():
    with pytest.raises(ValueError, match="outside canonical taxonomy"):
        parse_tags("lbl_domain_invalid_tag")
    with pytest.raises(ValueError, match="outside canonical taxonomy"):
        parse_tags("lbl_domain_ai|not_a_real_tag")


def test_decision_metrics_synthetic():
    rows = [
        {"reviewer_decision": "ACCEPT"},
        {"reviewer_decision": "ACCEPT"},
        {"reviewer_decision": "MODIFY"},
        {"reviewer_decision": "REJECT"},
    ]
    res = compute_decision_metrics(rows)
    assert res["total_records"] == 4
    assert res["accept_count"] == 2
    assert res["modify_count"] == 1
    assert res["reject_count"] == 1
    assert res["unresolved_count"] == 0
    assert res["accept_rate"] == 0.50
    assert res["modify_rate"] == 0.25
    assert res["reject_rate"] == 0.25


def test_multilabel_metrics_synthetic():
    # 2 samples, 3 tags: [tag0, tag1, tag2]
    tags = ["tag_a", "tag_b", "tag_c"]
    y_true = [["tag_a", "tag_b"], ["tag_c"]]
    y_pred = [["tag_a"], ["tag_b", "tag_c"]]

    # Sample 0: true=[1,1,0], pred=[1,0,0] -> mismatch, 1 binary error (tag_b FN)
    # Sample 1: true=[0,0,1], pred=[0,1,1] -> mismatch, 1 binary error (tag_b FP)
    # Total decisions = 6, total errors = 2, Hamming loss = 2/6 = 0.3333
    # Exact match = 0/2 = 0.0
    res = compute_multilabel_metrics(y_true, y_pred, domain_tags=tags)

    assert res["sample_size"] == 2
    assert res["total_binary_decisions"] == 6
    assert res["total_binary_errors"] == 2
    assert res["exact_match_count"] == 0
    assert pytest.approx(res["hamming_loss"], abs=1e-4) == 0.3333
    # Tag breakdown:
    # tag_a: true=[1,0], pred=[1,0] -> tp=1, fp=0, fn=0, tn=1 -> prec=1, rec=1, f1=1
    # tag_b: true=[1,0], pred=[0,1] -> tp=0, fp=1, fn=1, tn=0 -> prec=0, rec=0, f1=0
    # tag_c: true=[0,1], pred=[0,1] -> tp=1, fp=0, fn=0, tn=1 -> prec=1, rec=1, f1=1
    # Micro: tp=2, fp=1, fn=1 -> micro_p = 2/3, micro_r = 2/3, micro_f1 = 2/3 = 0.6667
    assert res["micro_metrics"]["tp"] == 2
    assert res["micro_metrics"]["fp"] == 1
    assert res["micro_metrics"]["fn"] == 1
    assert pytest.approx(res["micro_metrics"]["f1"], abs=1e-4) == 0.6667


def test_preflight_on_live_repository():
    preflight = verify_pilot_preflight(
        queue_path=PILOT_QUEUE_CSV,
        manifest_path=PILOT_MANIFEST_JSON,
        blind_sample_csv_path=BLIND_SAMPLE_CSV,
        gold_task_jsonl_path=GOLD_TASK_JSONL,
        expected_reviewer="Aryan",
    )
    assert preflight["verified"] is True
    assert preflight["sample_size"] == 25
    assert preflight["disjoint_from_blind_eval"] is True
    assert preflight["disjoint_from_verified_ref"] is True


def test_preflight_disjointness_violation(tmp_path):
    # Create invalid queue overlapping with blind evaluation sample
    bad_queue = tmp_path / "bad_queue.csv"
    manifest_p = tmp_path / "manifest.json"

    with open(PILOT_MANIFEST_JSON, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    first_id = manifest["selected_record_ids"][0]
    bad_manifest = json.loads(json.dumps(manifest))
    bad_manifest["selected_record_ids"][0] = "ACH000587"  # ACH000587 is in blind sample!

    with open(manifest_p, "w", encoding="utf-8") as f:
        json.dump(bad_manifest, f)

    with open(PILOT_QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        content = f.read()
    # Replace first ID with ACH000587
    bad_content = content.replace(first_id, "ACH000587")
    with open(bad_queue, "w", encoding="utf-8") as f:
        f.write(bad_content)

    with pytest.raises(ValueError, match="overlaps with blind evaluation sample"):
        verify_pilot_preflight(
            queue_path=bad_queue,
            manifest_path=manifest_p,
            blind_sample_csv_path=BLIND_SAMPLE_CSV,
            gold_task_jsonl_path=GOLD_TASK_JSONL,
            expected_reviewer="Aryan",
        )


def test_preflight_invalid_reviewer_decision(tmp_path):
    bad_queue = tmp_path / "bad_dec_queue.csv"
    with open(PILOT_QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        content = f.read()
    bad_content = content.replace(",ACCEPT,", ",MAYBE,")
    with open(bad_queue, "w", encoding="utf-8") as f:
        f.write(bad_content)

    with pytest.raises(ValueError, match="invalid reviewer_decision 'MAYBE'"):
        verify_pilot_preflight(
            queue_path=bad_queue,
            manifest_path=PILOT_MANIFEST_JSON,
            blind_sample_csv_path=BLIND_SAMPLE_CSV,
            gold_task_jsonl_path=GOLD_TASK_JSONL,
            expected_reviewer="Aryan",
        )


def test_review_effort_analysis_unrecorded():
    rows = [{"review_time_seconds": ""}, {"review_time_seconds": None}]
    effort = analyze_review_effort(rows)
    assert effort["timing_data_present"] is False
    assert effort["status"] == "UNAVAILABLE_NOT_RECORDED"
    assert effort["total_records_timed"] == 0
    assert effort["mean_seconds_per_record"] is None


def test_live_pilot_evaluation_metrics_precision():
    # Run complete evaluation on live files
    res = evaluate_pilot_queue(
        queue_path=PILOT_QUEUE_CSV,
        manifest_path=PILOT_MANIFEST_JSON,
        blind_sample_csv_path=BLIND_SAMPLE_CSV,
        gold_task_jsonl_path=GOLD_TASK_JSONL,
    )

    # Preflight
    assert res["sample_size"] == 25
    assert res["reviewer"] == "Aryan"

    # Decision metrics
    dec = res["decision_metrics"]
    assert dec["total_records"] == 25
    assert dec["accept_count"] == 12
    assert dec["modify_count"] == 13
    assert dec["reject_count"] == 0
    assert dec["unresolved_count"] == 0
    assert dec["accept_rate"] == 0.48
    assert dec["modify_rate"] == 0.52

    # Multilabel metrics
    ml = res["multilabel_metrics"]
    assert ml["sample_size"] == 25
    assert ml["total_binary_decisions"] == 250
    assert ml["total_binary_errors"] == 22
    assert ml["exact_match_count"] == 12
    assert ml["exact_match_ratio"] == 0.48
    assert ml["hamming_loss"] == 0.0880

    # Micro metrics
    micro = ml["micro_metrics"]
    assert micro["tp"] == 34
    assert micro["fp"] == 12
    assert micro["fn"] == 10
    assert micro["tn"] == 194
    assert pytest.approx(micro["precision"], abs=1e-4) == 0.7391
    assert pytest.approx(micro["recall"], abs=1e-4) == 0.7727
    assert pytest.approx(micro["f1"], abs=1e-4) == 0.7556

    # Macro metrics
    macro_act = ml["macro_metrics"]["active_classes"]
    assert macro_act["active_class_count"] == 10
    assert pytest.approx(macro_act["f1"], abs=1e-4) == 0.5662

    # Weighted F1
    weighted = ml["macro_metrics"]["support_weighted"]
    assert weighted["total_support_instances"] == 44
    assert pytest.approx(weighted["f1"], abs=1e-4) == 0.7472

    # Per-tag high performers
    pt = ml["per_tag_metrics"]
    assert pt["lbl_domain_hardware"]["f1"] == 1.0000
    assert pt["lbl_domain_systems"]["f1"] == 0.9565
    assert pt["lbl_domain_data"]["f1"] == 0.9091
    assert pt["lbl_domain_security"]["f1"] == 0.8000

    # Disagreement summary
    dis_sum = res["disagreement_summary"]
    assert dis_sum["total_disagreements"] == 13
    assert dis_sum["tags_removed_by_reviewer_ai_false_alarms"]["lbl_domain_web"] == 3
    assert dis_sum["tags_removed_by_reviewer_ai_false_alarms"]["lbl_domain_ai"] == 3
    assert dis_sum["tags_added_by_reviewer_ai_misses"]["lbl_domain_ml"] == 3
    assert dis_sum["tags_added_by_reviewer_ai_misses"]["lbl_domain_ai"] == 2


def test_step25_frozen_assets_and_splits_preservation():
    import hashlib

    def get_hash(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    expected = {
        "dataset": (REPO_ROOT / "data/processed/achievement_classification_dataset.csv", "1a62b8d8b56bd94df27d8c40ff86ef892b7d50e0c6bb92ff4f69882596b27ddc"),
        "categorizer": (REPO_ROOT / "models/achievement_categorizer_v1.0.1.joblib", "e0f514a4286752948c069c43dda6626af9e4ace926ab899334d12af77353ddb3"),
        "classifier": (REPO_ROOT / "models/achievement_classifier_v1.0.1.joblib", "1359534562ced43eca0309c33a25cc630ad1eef95f1a94a8e7ffdc9fc7eed2cd"),
        "blind_sample_csv": (REPO_ROOT / "data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv", "7c2fd5f04bddc938d4b4f42ad8b9fbe94ee09aa250fb3bcc20d0d7d4fd70a4e2"),
        "blind_sample_key": (REPO_ROOT / "data/annotations/ai_assisted/domain_categorization_validation_sample_key.jsonl", "831ae47d2af689a3d9ff31c8288647eb6226c2a97cd87478ed63d284b94b7011"),
        "gold_task_jsonl": (REPO_ROOT / "data/annotations/domain_categorization_gold_annotation_task.jsonl", "34b6fd7007c738fff120631e5203a479401cebc72406d102d9f86e09163e2fb7"),
        "train_split": (REPO_ROOT / "data/splits/train.csv", "c5dc7c224cd98f17760f391cfb096867f50110860c8cf7341c5780eab371b635"),
        "validation_split": (REPO_ROOT / "data/splits/validation.csv", "2b1afd584020ab234a4d3794ca99585ffdd640999fe188ccde73969216c337c9"),
        "test_split": (REPO_ROOT / "data/splits/test.csv", "88445ea36d71223d8943e14aa96c30818f0682db5c9b32a82aa6ddba53120ac5"),
    }

    for name, (path, exp_hash) in expected.items():
        assert path.exists(), f"File missing: {path}"
        actual = get_hash(path)
        assert actual == exp_hash, f"Hash mismatch on {name}: {actual} != {exp_hash}"


def test_step25_concordance_with_original_ai_proposals():
    import csv

    proposals_p = REPO_ROOT / "data/annotations/ai_assisted/domain_categorization_ai_proposals.csv"
    with open(proposals_p, "r", encoding="utf-8-sig") as f:
        prop_map = {r["achievement_id"]: r for r in csv.DictReader(f)}

    with open(PILOT_QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        queue_rows = list(csv.DictReader(f))

    assert len(queue_rows) == 25
    for r in queue_rows:
        aid = r["achievement_id"]
        assert aid in prop_map
        orig = prop_map[aid]
        # Parsed tags must match identically
        assert parse_tags(r["ai_proposed_tags"]) == parse_tags(orig["proposed_tags"])
        assert r["ai_uncertainty_flag"].upper() == orig["uncertainty_flag"].upper()


def test_step25_disagreement_csv_and_none_semantics():
    import csv

    dis_p = REPO_ROOT / "reports/step24_pilot_disagreement_analysis.csv"
    with open(dis_p, "r", encoding="utf-8-sig") as f:
        dis_rows = list(csv.DictReader(f))

    with open(PILOT_QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        queue_rows = list(csv.DictReader(f))

    assert len(dis_rows) == 25
    for i, r in enumerate(queue_rows):
        d = dis_rows[i]
        assert d["achievement_id"] == r["achievement_id"]
        assert d["reviewer_decision"] == r["reviewer_decision"]

        # Semantic check: NONE is empty tag set, never confused with lbl_domain_other
        raw_final = r["reviewer_final_tags"].strip()
        parsed = parse_tags(raw_final)
        if raw_final == "NONE":
            assert parsed == []
            assert "lbl_domain_other" not in parsed
        if "lbl_domain_other" in parsed:
            assert raw_final != "NONE"
