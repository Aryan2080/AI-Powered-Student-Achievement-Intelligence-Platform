"""
src/nlp/build_gold_annotation_task.py
Build the 175-sample independent gold evaluation annotation task from the held-out test split.
Uses standard library csv/json to avoid OpenBLAS thread allocation issues.
"""
import csv
import json
import os
from pathlib import Path

# Ensure thread limit in case any underlying C-lib is invoked
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DOMAIN_TAGS = [
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
]

# 1. Load held-out test records using standard csv
test_csv_path = REPO_ROOT / "data" / "splits" / "categorization_test.csv"
test_records = []
with open(test_csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        test_records.append(row)

print(f"Total held-out test records available: {len(test_records)}")

# 2. Load existing verified reviewed reference samples
reviewed_path = REPO_ROOT / "data" / "annotations" / "categorization_reviewed_reference_samples.jsonl"
reviewed_map = {}
with open(reviewed_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            if rec.get("split") == "test":
                reviewed_map[rec["achievement_id"]] = rec

print(f"Existing verified held-out test samples: {len(reviewed_map)}")

# 3. Stratified selection of 175 records from test_records
# First include all existing reviewed test samples
candidate_ids = set(reviewed_map.keys())
selected_records = [r for r in test_records if r["achievement_id"] in candidate_ids]

# Add remaining records up to 175, sorted deterministically
remaining_records = [r for r in test_records if r["achievement_id"] not in candidate_ids]
remaining_records.sort(key=lambda x: x["achievement_id"])

needed = 175 - len(selected_records)
selected_records.extend(remaining_records[:needed])
assert len(selected_records) == 175, f"Expected 175 records, got {len(selected_records)}"

# 4. Construct annotation-ready corpus
gold_tasks = []
for row in selected_records:
    aid = row["achievement_id"]
    prov_tags = [t for t in DOMAIN_TAGS if str(row.get(f"tag_{t}", "0")) == "1"]

    if aid in reviewed_map:
        rev_info = reviewed_map[aid]
        task_entry = {
            "achievement_id": aid,
            "achievement_text": row["achievement_text"],
            "primary_category": row.get("category", row.get("primary_category", "")),
            "split": "test",
            "provisional_heuristic_tags": prov_tags,
            "annotation_status": "VERIFIED",
            "annotator_1": "Member 1 — NLP & Semantic Intelligence Engineer",
            "annotator_2": "Member 2 — Backend & ML Engineer (Cross-Auditor)",
            "adjudicated_tags": rev_info["verified_domain_tags"],
            "adjudication_notes": rev_info["audit_notes"],
            "adjudicator": rev_info.get("auditor", "Member 1"),
        }
    else:
        task_entry = {
            "achievement_id": aid,
            "achievement_text": row["achievement_text"],
            "primary_category": row.get("category", row.get("primary_category", "")),
            "split": "test",
            "provisional_heuristic_tags": prov_tags,
            "annotation_status": "PENDING_HUMAN_REVIEW",
            "annotator_1": None,
            "annotator_2": None,
            "adjudicated_tags": None,
            "adjudication_notes": "Awaiting blind dual-annotation according to domain_categorization_annotation_guide.md.",
            "adjudicator": None,
        }
    gold_tasks.append(task_entry)

out_file = REPO_ROOT / "data" / "annotations" / "domain_categorization_gold_annotation_task.jsonl"
with open(out_file, "w", encoding="utf-8") as f:
    for t in gold_tasks:
        f.write(json.dumps(t) + "\n")

verified_count = sum(1 for t in gold_tasks if t["annotation_status"] == "VERIFIED")
pending_count = sum(1 for t in gold_tasks if t["annotation_status"] == "PENDING_HUMAN_REVIEW")

print(f"\n[OK] Built {out_file.name}:")
print(f"  Total candidate evaluation samples: {len(gold_tasks)}")
print(f"  Verified human annotations:        {verified_count}")
print(f"  Pending blind dual-review:         {pending_count}")
