"""
audit_near_duplicates.py
========================
Deep audit of near-duplicate candidate pairs in reports/near_duplicate_candidates.csv.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NEAR_CSV = REPO_ROOT / "reports" / "near_duplicate_candidates.csv"
DATA_CSV = REPO_ROOT / "data" / "processed" / "achievement_classification_dataset.csv"

def audit():
    # Load primary dataset for reference
    records = {}
    with open(DATA_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            records[r["achievement_id"]] = r

    candidates = []
    with open(NEAR_CSV, "r", encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))

    print(f"Total candidate pairs: {len(candidates)}")
    type_counts = Counter(c["candidate_type"] for c in candidates)
    res_counts = Counter(c["resolution_status"] for c in candidates)
    cat_counts = Counter(c["category"] for c in candidates)

    print("\nCandidate Type Distribution:")
    for k, v in type_counts.items():
        print(f"  {k}: {v}")

    print("\nResolution Status Distribution:")
    for k, v in res_counts.items():
        print(f"  {k}: {v}")

    print("\nCategory Distribution:")
    for k, v in cat_counts.most_common():
        print(f"  {k}: {v}")

    # Inspect the highest-similarity candidates
    candidates.sort(key=lambda x: float(x["similarity_score"]), reverse=True)
    print("\nTop 10 Highest Similarity Pairs:")
    for c in candidates[:10]:
        r1 = records.get(c["record_id_1"], {})
        r2 = records.get(c["record_id_2"], {})
        print(f"\n[{c['candidate_type']}] Sim: {c['similarity_score']} ({c['category']})")
        print(f"  ID1 ({c['record_id_1']}): {r1.get('achievement_text', '')}")
        print(f"  ID2 ({c['record_id_2']}): {r2.get('achievement_text', '')}")

if __name__ == "__main__":
    audit()
