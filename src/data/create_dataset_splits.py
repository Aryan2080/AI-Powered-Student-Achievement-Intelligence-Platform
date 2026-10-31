"""
create_dataset_splits.py
========================
Stratified & Leakage-Aware Dataset Splitting Pipeline
AI-Powered Student Achievement Intelligence Platform — Member 1

Splits the primary achievement dataset into reproducible:
  - Train: 70.0% (1,078 records)
  - Validation: 15.0% (231 records)
  - Test: 15.0% (231 records)
Total: 1,540 records

Guarantees:
  1. Exact class balance preservation (stratified across all 14 taxonomy labels:
     each category has 77 train, and balanced 16/17 val & test so totals match exactly 231 each)
  2. Leakage prevention: Zero record overlap across partitions
  3. Deterministic execution governed by RANDOM_SEED = 42.

Outputs:
  - data/splits/train.csv
  - data/splits/validation.csv
  - data/splits/test.csv
  - data/splits/split_manifest.json

Usage:
    python src/data/create_dataset_splits.py
"""
from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

RANDOM_SEED = 42
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "processed" / "achievement_classification_dataset.csv"
SPLITS_DIR = REPO_ROOT / "data" / "splits"

TRAIN_TARGET = 1078
VAL_TARGET = 231
TEST_TARGET = 231

def create_splits() -> dict[str, Any]:
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(RANDOM_SEED)
    
    records: list[dict[str, str]] = []
    with open(DATA_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        for r in reader:
            records.append(r)
            
    total_records = len(records)
    print(f"Loaded {total_records} records for splitting...")
    
    # ── Grouping & Stratification ────────────────────────────────────────────
    by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in records:
        by_category[r["category"]].append(r)
        
    train_records: list[dict[str, str]] = []
    val_records: list[dict[str, str]] = []
    test_records: list[dict[str, str]] = []
    
    cat_distribution: dict[str, dict[str, int]] = {}
    
    sorted_categories = sorted(by_category.keys())
    
    for idx, cat in enumerate(sorted_categories):
        cat_records = by_category[cat]
        # Deterministic shuffle within category
        rng.shuffle(cat_records)
        n = len(cat_records)  # 110
        
        # 77 train records for all 14 categories (14 * 77 = 1,078)
        n_train = 77
        
        # Alternate 16 and 17 between val and test across the 14 categories
        # 7 categories get (val=16, test=17), 7 categories get (val=17, test=16)
        # Sum val = 7 * 16 + 7 * 17 = 112 + 119 = 231
        # Sum test = 7 * 17 + 7 * 16 = 119 + 112 = 231
        if idx % 2 == 0:
            n_val = 16
            n_test = 17
        else:
            n_val = 17
            n_test = 16
            
        c_train = cat_records[:n_train]
        c_val = cat_records[n_train:n_train + n_val]
        c_test = cat_records[n_train + n_val:]
        
        train_records.extend(c_train)
        val_records.extend(c_val)
        test_records.extend(c_test)
        
        cat_distribution[cat] = {
            "total": n,
            "train": len(c_train),
            "validation": len(c_val),
            "test": len(c_test),
        }
        
    # Shuffle splits to ensure random row ordering
    rng.shuffle(train_records)
    rng.shuffle(val_records)
    rng.shuffle(test_records)
    
    # ── Verify Zero Overlap & Exact Target Parity ────────────────────────────
    train_ids = {r["achievement_id"] for r in train_records}
    val_ids = {r["achievement_id"] for r in val_records}
    test_ids = {r["achievement_id"] for r in test_records}
    
    overlap_tv = train_ids.intersection(val_ids)
    overlap_tt = train_ids.intersection(test_ids)
    overlap_vt = val_ids.intersection(test_ids)
    
    if overlap_tv or overlap_tt or overlap_vt:
        raise ValueError(f"Partition leakage detected: {overlap_tv}, {overlap_tt}, {overlap_vt}")
        
    if len(train_records) != TRAIN_TARGET:
        raise ValueError(f"Train count mismatch: expected {TRAIN_TARGET}, got {len(train_records)}")
    if len(val_records) != VAL_TARGET:
        raise ValueError(f"Validation count mismatch: expected {VAL_TARGET}, got {len(val_records)}")
    if len(test_records) != TEST_TARGET:
        raise ValueError(f"Test count mismatch: expected {TEST_TARGET}, got {len(test_records)}")
        
    # ── Write CSV Files ──────────────────────────────────────────────────────
    def save_split_csv(split_data: list[dict[str, str]], filename: str) -> None:
        path = SPLITS_DIR / filename
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(split_data)
            
    save_split_csv(train_records, "train.csv")
    save_split_csv(val_records, "validation.csv")
    save_split_csv(test_records, "test.csv")
    
    # ── Write Split Manifest ─────────────────────────────────────────────────
    manifest = {
        "dataset_name": "Achievement Classification Dataset - Partition Manifest",
        "dataset_version": "achievement_dataset_v1.0.0",
        "split_generation_date": date.today().isoformat(),
        "random_seed": RANDOM_SEED,
        "split_ratios": {
            "train": 0.70,
            "validation": 0.15,
            "test": 0.15
        },
        "total_records": total_records,
        "split_counts": {
            "train": len(train_records),
            "validation": len(val_records),
            "test": len(test_records)
        },
        "exact_percentages": {
            "train": f"{len(train_records)/total_records:.2%}",
            "validation": f"{len(val_records)/total_records:.2%}",
            "test": f"{len(test_records)/total_records:.2%}"
        },
        "per_category_breakdown": cat_distribution,
        "leakage_verification": {
            "train_val_overlap": len(overlap_tv),
            "train_test_overlap": len(overlap_tt),
            "val_test_overlap": len(overlap_vt),
            "status": "PASSED_STRICT_ISOLATION"
        },
        "split_files": {
            "train_csv": "data/splits/train.csv",
            "validation_csv": "data/splits/validation.csv",
            "test_csv": "data/splits/test.csv"
        }
    }
    
    manifest_path = SPLITS_DIR / "split_manifest.json"
    with open(manifest_path, mode="w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Splits successfully created in '{SPLITS_DIR}':")
    print(f"  - Train:      {len(train_records)} records ({len(train_records)/total_records:.2%}) [Target: {TRAIN_TARGET}]")
    print(f"  - Validation: {len(val_records)} records ({len(val_records)/total_records:.2%}) [Target: {VAL_TARGET}]")
    print(f"  - Test:       {len(test_records)} records ({len(test_records)/total_records:.2%}) [Target: {TEST_TARGET}]")
    print(f"Manifest written to '{manifest_path}'.")
    
    return manifest

if __name__ == "__main__":
    create_splits()
