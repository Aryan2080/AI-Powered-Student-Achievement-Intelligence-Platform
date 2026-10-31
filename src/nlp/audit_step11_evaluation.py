"""
src/nlp/audit_step11_evaluation.py
Comprehensive analysis script for Step 11 independent evaluation & label-quality audit.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, hamming_loss

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.nlp.categorization import DOMAIN_TAGS, DOMAIN_TAG_NAMES, AchievementCategorizer

def audit_reviewed_subset():
    ref_path = REPO_ROOT / "data" / "annotations" / "categorization_reviewed_reference_samples.jsonl"
    records = []
    with open(ref_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    df_ref = pd.DataFrame(records)
    print(f"Total reviewed samples: {len(df_ref)}")
    print(f"Unique achievement IDs: {df_ref['achievement_id'].nunique()}")
    duplicates = len(df_ref) - df_ref["achievement_id"].nunique()
    print(f"Duplicate IDs: {duplicates}")

    # Split breakdown
    split_counts = df_ref["split"].value_counts().to_dict()
    print("\nSplit Distribution in Reviewed Subset:")
    for s, c in split_counts.items():
        print(f"  Split '{s}': {c} samples ({c/len(df_ref)*100:.1f}%)")

    # Annotation status & notes
    statuses = df_ref["annotation_status"].value_counts().to_dict()
    print("\nAnnotation Status Distribution:")
    for s, c in statuses.items():
        print(f"  {s}: {c}")

    # Zero-tag count
    df_ref["tag_count"] = df_ref["verified_domain_tags"].apply(len)
    zero_tags = (df_ref["tag_count"] == 0).sum()
    print(f"\nZero-tag achievements in reviewed subset: {zero_tags} ({zero_tags/len(df_ref)*100:.1f}%)")

    # Support per tag across splits
    print("\nSupport per Tag by Split:")
    support_by_split = {t: {"train": 0, "validation": 0, "test": 0, "total": 0} for t in DOMAIN_TAGS}
    for _, row in df_ref.iterrows():
        s = row["split"]
        for tag in row["verified_domain_tags"]:
            support_by_split[tag][s] += 1
            support_by_split[tag]["total"] += 1

    df_support = pd.DataFrame.from_dict(support_by_split, orient="index")
    print(df_support.to_string())

    return df_ref

def evaluate_splits():
    model_path = REPO_ROOT / "models" / "achievement_categorizer_v1.0.1.joblib"
    categorizer = AchievementCategorizer.load(model_path)
    print(f"\nLoaded categorizer model version: {categorizer.model_version}")

    # 1. Automatically derived test split (231 records)
    test_csv_path = REPO_ROOT / "data" / "splits" / "categorization_test.csv"
    test_df = pd.read_csv(test_csv_path)

    X_test_auto = test_df["achievement_text"].tolist()
    Y_test_auto = np.zeros((len(test_df), len(DOMAIN_TAGS)), dtype=int)
    for i, t in enumerate(DOMAIN_TAGS):
        Y_test_auto[:, i] = test_df[f"tag_{t}"].values

    res_auto = categorizer.predict_batch(X_test_auto)
    Y_pred_auto = np.zeros_like(Y_test_auto)
    for row_idx, r in enumerate(res_auto):
        for t in r.predicted_tags:
            Y_pred_auto[row_idx, DOMAIN_TAGS.index(t)] = 1

    # 2. Reviewed reference samples
    ref_path = REPO_ROOT / "data" / "annotations" / "categorization_reviewed_reference_samples.jsonl"
    with open(ref_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    df_ref = pd.DataFrame(records)

    # Subsets of reviewed reference samples
    subsets = {
        "auto_test_231": (test_df["achievement_text"].tolist(), Y_test_auto),
        "reviewed_all_45": None,
        "reviewed_test_only": None,
        "reviewed_train_only": None,
        "reviewed_val_only": None,
    }

    for name, s_filter in [
        ("reviewed_all_45", None),
        ("reviewed_test_only", "test"),
        ("reviewed_train_only", "train"),
        ("reviewed_val_only", "validation"),
    ]:
        sub_df = df_ref if s_filter is None else df_ref[df_ref["split"] == s_filter]
        texts = sub_df["achievement_text"].tolist()
        Y_true = np.zeros((len(sub_df), len(DOMAIN_TAGS)), dtype=int)
        for row_idx, (_, r) in enumerate(sub_df.iterrows()):
            for t in r["verified_domain_tags"]:
                Y_true[row_idx, DOMAIN_TAGS.index(t)] = 1
        subsets[name] = (texts, Y_true, sub_df)

    # Metrics evaluation function
    results_summary = {}
    detailed_per_tag = {}

    for name, data in subsets.items():
        if name == "auto_test_231":
            texts, Y_true = data
        else:
            texts, Y_true, sub_df = data

        preds = categorizer.predict_batch(texts)
        Y_pred = np.zeros_like(Y_true)
        for row_idx, r in enumerate(preds):
            for t in r.predicted_tags:
                Y_pred[row_idx, DOMAIN_TAGS.index(t)] = 1

        hl = float(hamming_loss(Y_true, Y_pred))
        em = float(np.mean(np.all(Y_true == Y_pred, axis=1)))
        micro_p = float(precision_score(Y_true, Y_pred, average="micro", zero_division=0))
        micro_r = float(recall_score(Y_true, Y_pred, average="micro", zero_division=0))
        micro_f1 = float(f1_score(Y_true, Y_pred, average="micro", zero_division=0))
        macro_f1 = float(f1_score(Y_true, Y_pred, average="macro", zero_division=0))

        results_summary[name] = {
            "n_samples": len(texts),
            "hamming_loss": hl,
            "exact_match": em,
            "micro_precision": micro_p,
            "micro_recall": micro_r,
            "micro_f1": micro_f1,
            "macro_f1": macro_f1,
        }

        # Per-tag metrics
        tag_metrics = {}
        for i, t in enumerate(DOMAIN_TAGS):
            yt = Y_true[:, i]
            yp = Y_pred[:, i]
            p = float(precision_score(yt, yp, zero_division=0))
            r = float(recall_score(yt, yp, zero_division=0))
            f = float(f1_score(yt, yp, zero_division=0))
            supp = int(yt.sum())
            neg_supp = int((yt == 0).sum())

            # Confusion counts
            tp = int(((yt == 1) & (yp == 1)).sum())
            fp = int(((yt == 0) & (yp == 1)).sum())
            fn = int(((yt == 1) & (yp == 0)).sum())
            tn = int(((yt == 0) & (yp == 0)).sum())

            tag_metrics[t] = {
                "name": DOMAIN_TAG_NAMES[t],
                "support": supp,
                "neg_support": neg_supp,
                "precision": p,
                "recall": r,
                "f1": f,
                "threshold": categorizer.thresholds.get(t, 0.5),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
            }
        detailed_per_tag[name] = tag_metrics

    print("\n=== OVERALL SUBSET METRICS COMPARISON ===")
    df_comp = pd.DataFrame(results_summary).T
    print(df_comp.to_string())

    return results_summary, detailed_per_tag

if __name__ == "__main__":
    df_ref = audit_reviewed_subset()
    summary, per_tag = evaluate_splits()

    out_file = REPO_ROOT / "reports" / "step11_per_tag_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "per_tag": per_tag}, f, indent=2)
    print(f"\n[OK] Saved detailed metrics to {out_file}")
