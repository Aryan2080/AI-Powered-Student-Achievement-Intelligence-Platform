"""
tests/test_expansion_queue.py
==============================
Unit tests for the Remaining 113-Record Expansion Queue Subsystem (Step 26)
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

import csv
import json
from pathlib import Path
import pytest

from src.nlp.expansion_queue_manager import (
    DOMAIN_TAGS,
    parse_tags,
    validate_remaining_113_queue,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

QUEUE_CSV = REPO_ROOT / "data/annotations/ai_assisted/pilot/domain_categorization_remaining_113_queue.csv"
MANIFEST_JSON = REPO_ROOT / "data/annotations/ai_assisted/pilot/domain_categorization_remaining_113_manifest.json"
GOLD_TASK_JSONL = REPO_ROOT / "data/annotations/domain_categorization_gold_annotation_task.jsonl"
BLIND_SAMPLE_CSV = REPO_ROOT / "data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv"
PILOT_QUEUE_CSV = REPO_ROOT / "data/annotations/ai_assisted/pilot/domain_categorization_pilot_queue.csv"
PROPOSALS_CSV = REPO_ROOT / "data/annotations/ai_assisted/domain_categorization_ai_proposals.csv"
TEST_SPLIT_CSV = REPO_ROOT / "data/splits/test.csv"


def test_remaining_113_manifest_structure():
    assert MANIFEST_JSON.exists(), f"Manifest missing: {MANIFEST_JSON}"
    with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["manifest_id"] == "step26_remaining_113_manifest_v1.0"
    assert manifest["batch_metadata"]["total_records"] == 113
    assert manifest["batch_metadata"]["master_gold_task_total"] == 175
    assert len(manifest["selected_record_ids"]) == 113
    assert len(set(manifest["selected_record_ids"])) == 113


def test_remaining_113_queue_schema_and_size():
    assert QUEUE_CSV.exists(), f"Queue missing: {QUEUE_CSV}"
    with open(QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 113

    expected_headers = [
        "queue_record_id",
        "achievement_id",
        "achievement_text",
        "primary_category",
        "ai_proposed_tags",
        "ai_evidence_snippets",
        "ai_uncertainty_flag",
        "ai_annotation_rationale",
        "reviewer_name",
        "reviewer_decision",
        "reviewer_final_tags",
        "reviewer_rationale",
        "review_time_seconds",
        "review_status",
    ]
    assert reader.fieldnames == expected_headers

    # Reviewer fields must be 100% blank / pending
    for i, r in enumerate(rows, 1):
        assert int(r["queue_record_id"]) == i
        assert r["reviewer_name"] == ""
        assert r["reviewer_decision"] == ""
        assert r["reviewer_final_tags"] == ""
        assert r["reviewer_rationale"] == ""
        assert r["review_time_seconds"] == ""
        assert r["review_status"] == "PENDING_REVIEW"


def test_remaining_113_disjointness_from_all_cohorts():
    with open(QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        queue_ids = set(r["achievement_id"] for r in csv.DictReader(f))

    # 1. References
    with open(GOLD_TASK_JSONL, "r", encoding="utf-8") as f:
        ref_ids = {json.loads(line)["achievement_id"] for line in f if line.strip() and json.loads(line).get("annotation_status") == "VERIFIED"}

    # 2. Blind sample
    with open(BLIND_SAMPLE_CSV, "r", encoding="utf-8-sig") as f:
        blind_ids = {r["achievement_id"] for r in csv.DictReader(f)}

    # 3. Pilot queue
    with open(PILOT_QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        pilot_ids = {r["achievement_id"] for r in csv.DictReader(f)}

    assert len(queue_ids & ref_ids) == 0, f"Overlap with references: {queue_ids & ref_ids}"
    assert len(queue_ids & blind_ids) == 0, f"Overlap with blind sample: {queue_ids & blind_ids}"
    assert len(queue_ids & pilot_ids) == 0, f"Overlap with pilot queue: {queue_ids & pilot_ids}"


def test_remaining_113_split_confinement():
    with open(QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        queue_ids = set(r["achievement_id"] for r in csv.DictReader(f))

    with open(TEST_SPLIT_CSV, "r", encoding="utf-8") as f:
        test_ids = set(r["achievement_id"] for r in csv.DictReader(f))

    assert queue_ids.issubset(test_ids), "Queue records not strictly confined to test split!"


def test_remaining_113_proposal_concordance():
    with open(PROPOSALS_CSV, "r", encoding="utf-8-sig") as f:
        proposals_map = {r["achievement_id"]: r for r in csv.DictReader(f)}

    with open(QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        aid = r["achievement_id"]
        assert aid in proposals_map
        orig = proposals_map[aid]

        assert r["achievement_text"] == orig["achievement_text"]
        assert r["primary_category"] == orig["primary_category"]
        assert parse_tags(r["ai_proposed_tags"]) == parse_tags(orig["proposed_tags"])
        assert r["ai_uncertainty_flag"].upper() == orig["uncertainty_flag"].upper()


def test_remaining_113_taxonomy_compliance():
    with open(QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        raw = r["ai_proposed_tags"]
        parsed = parse_tags(raw)
        for t in parsed:
            assert t in DOMAIN_TAGS, f"Invalid tag '{t}' in record {r['achievement_id']}"


def test_remaining_113_partition_census():
    with open(GOLD_TASK_JSONL, "r", encoding="utf-8") as f:
        gold = [json.loads(line) for line in f if line.strip()]
    gold_ids = set(r["achievement_id"] for r in gold)
    ref_ids = set(r["achievement_id"] for r in gold if r.get("annotation_status") == "VERIFIED")

    with open(BLIND_SAMPLE_CSV, "r", encoding="utf-8-sig") as f:
        blind_ids = set(r["achievement_id"] for r in csv.DictReader(f))

    with open(PILOT_QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        pilot_ids = set(r["achievement_id"] for r in csv.DictReader(f))

    with open(QUEUE_CSV, "r", encoding="utf-8-sig") as f:
        queue_ids = set(r["achievement_id"] for r in csv.DictReader(f))

    assert len(ref_ids) == 7
    assert len(blind_ids) == 30
    assert len(pilot_ids) == 25
    assert len(queue_ids) == 113
    assert len(gold_ids) == 175
    assert (ref_ids | blind_ids | pilot_ids | queue_ids) == gold_ids


def test_expansion_queue_manager_preflight_validation():
    res = validate_remaining_113_queue(
        queue_csv_path=QUEUE_CSV,
        manifest_json_path=MANIFEST_JSON,
        gold_task_jsonl_path=GOLD_TASK_JSONL,
        blind_sample_csv_path=BLIND_SAMPLE_CSV,
        pilot_queue_csv_path=PILOT_QUEUE_CSV,
        proposals_csv_path=PROPOSALS_CSV,
        test_split_csv_path=TEST_SPLIT_CSV,
    )
    assert res["verified"] is True
    assert res["sample_size"] == 113
    assert res["disjointness_proven"] is True
    assert res["reviewer_fields_blank_and_pending"] is True
    assert res["concordance_with_proposals_verified"] is True
