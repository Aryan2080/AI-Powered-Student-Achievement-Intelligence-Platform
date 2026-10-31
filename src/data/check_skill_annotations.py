"""
check_skill_annotations.py
==========================
Verify skill annotations against the primary achievement dataset.
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = REPO_ROOT / "data" / "processed" / "achievement_classification_dataset.csv"
SKILLS_CSV = REPO_ROOT / "data" / "annotations" / "achievement_skill_annotations.csv"
VOCAB_CSV = REPO_ROOT / "data" / "annotations" / "canonical_skill_vocabulary.csv"

def verify():
    # Load primary dataset
    records = {}
    with open(DATA_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            records[r["achievement_id"]] = r["achievement_text"]

    # Load canonical vocabulary
    canonical_skills = set()
    with open(VOCAB_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            canonical_skills.add(r["canonical_skill"])

    annotations = []
    with open(SKILLS_CSV, "r", encoding="utf-8") as f:
        annotations = list(csv.DictReader(f))

    print(f"Total annotations to verify: {len(annotations)}")

    missing_ach_ids = 0
    span_mismatches = 0
    out_of_bounds = 0
    invalid_canonical = 0
    duplicate_annotations = 0
    seen_spans = set()

    for i, a in enumerate(annotations):
        aid = a["achievement_id"]
        mention = a["skill_mention"]
        canon = a["canonical_skill"]
        s_off = int(a["start_offset"])
        e_off = int(a["end_offset"])

        if aid not in records:
            missing_ach_ids += 1
            continue

        text = records[aid]

        if s_off < 0 or e_off > len(text) or s_off >= e_off:
            out_of_bounds += 1
            continue

        extracted = text[s_off:e_off]
        if extracted != mention:
            span_mismatches += 1
            if span_mismatches <= 5:
                print(f"Mismatch row {i}: expected '{mention}', got '{extracted}' (span {s_off}:{e_off})")

        if canon not in canonical_skills:
            invalid_canonical += 1

        span_key = (aid, s_off, e_off)
        if span_key in seen_spans:
            duplicate_annotations += 1
        seen_spans.add(span_key)

    print("\n--- SKILL ANNOTATION VERIFICATION RESULTS ---")
    print(f"Total rows audited:           {len(annotations)}")
    print(f"Missing achievement_ids:      {missing_ach_ids}")
    print(f"Out of bounds offsets:        {out_of_bounds}")
    print(f"Span text mismatches:         {span_mismatches}")
    print(f"Invalid canonical skill refs: {invalid_canonical}")
    print(f"Duplicate span annotations:   {duplicate_annotations}")

if __name__ == "__main__":
    verify()
