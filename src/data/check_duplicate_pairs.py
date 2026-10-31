"""
check_duplicate_pairs.py
========================
Duplicate Pair Verification Script
Verifies:
- Unique pair IDs
- ID validity / provenance
- Positive vs. negative balance
- Text syntax anomalies (e.g. 'won None')
- Split boundary isolation and cross-split leakage
"""
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "processed" / "achievement_classification_dataset.csv"
PAIRS_PATH = REPO_ROOT / "data" / "annotations" / "achievement_duplicate_pairs.csv"
SPLITS_DIR = REPO_ROOT / "data" / "splits"

def audit():
    dataset_ids = set()
    with open(DATA_PATH, encoding="utf-8") as f:
        dataset_ids = {r["achievement_id"] for r in csv.DictReader(f)}

    split_map = {}
    for s_name in ["train", "validation", "test"]:
        with open(SPLITS_DIR / f"{s_name}.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                split_map[r["achievement_id"]] = s_name

    pairs = []
    with open(PAIRS_PATH, encoding="utf-8") as f:
        pairs = list(csv.DictReader(f))

    print(f"Total pairs audited: {len(pairs)}")

    unique_pair_ids = set()
    missing_id1 = 0
    missing_id2_neg = 0
    won_none_count = 0
    cross_split_leakage = 0
    label_counts = {0: 0, 1: 0}
    split_counts = {}

    for p in pairs:
        pid = p["pair_id"]
        unique_pair_ids.add(pid)
        lbl = int(p["duplicate_label"])
        label_counts[lbl] += 1
        
        split = p.get("split", "unknown")
        split_counts[split] = split_counts.get(split, 0) + 1

        aid1 = p["achievement_id_1"]
        aid2 = p["achievement_id_2"]

        if aid1 not in dataset_ids:
            missing_id1 += 1
            
        # In negative pairs, both IDs must exist in dataset
        if lbl == 0 and aid2 not in dataset_ids:
            missing_id2_neg += 1

        # Check for syntax anomalies
        for t in [p["text_1"], p["text_2"]]:
            if "won None" in t or "Awarded None" in t:
                won_none_count += 1

        # Check split leakage
        s1 = split_map.get(aid1)
        base_id2 = aid2.replace("_V2", "")
        s2 = split_map.get(base_id2)
        if s1 != s2 or s1 != split:
            cross_split_leakage += 1

    print("\n--- DUPLICATE PAIR AUDIT REPORT ---")
    print(f"Total Rows Audited:               {len(pairs)}")
    print(f"Unique Pair IDs:                  {len(unique_pair_ids)}")
    print(f"Positive Pairs (Label 1):         {label_counts[1]}")
    print(f"Negative Pairs (Label 0):         {label_counts[0]}")
    print(f"Pairs by Designated Split:        {split_counts}")
    print(f"Missing ID1 in Dataset:           {missing_id1}")
    print(f"Missing ID2 (Negatives) in DS:    {missing_id2_neg}")
    print(f"Syntax Glitches ('won None'):     {won_none_count}")
    print(f"Cross-Split Boundary Leakage:     {cross_split_leakage}")

if __name__ == "__main__":
    audit()
