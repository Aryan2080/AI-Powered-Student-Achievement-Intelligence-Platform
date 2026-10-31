"""
src/nlp/audit_step11_detailed.py
Detailed analysis of provenance, circularity, feature importance, and sample-level errors.
"""
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.nlp.categorization import DOMAIN_TAGS, DOMAIN_TAG_NAMES, AchievementCategorizer

def inspect_feature_importance():
    model_path = REPO_ROOT / "models" / "achievement_categorizer_v1.0.1.joblib"
    clf = AchievementCategorizer.load(model_path)
    vocab = np.array(clf.vectorizer.get_feature_names_out())

    print("=== TOP POSITIVE TF-IDF FEATURES PER DOMAIN TAG ===")
    top_features = {}
    for t in DOMAIN_TAGS:
        coef = clf.classifiers[t].coef_[0]
        top_idx = np.argsort(coef)[-10:][::-1]
        top_words = [(vocab[i], round(float(coef[i]), 3)) for i in top_idx]
        top_features[t] = top_words
        print(f"\n{t} ({DOMAIN_TAG_NAMES[t]}):")
        print("  " + ", ".join([f"{w} ({c})" for w, c in top_words]))
    return top_features

def inspect_provenance_sources():
    jsonl_path = REPO_ROOT / "data" / "processed" / "achievement_categorization_dataset.jsonl"
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"\n=== PROVENANCE ANALYSIS ACROSS {len(records)} MASTER RECORDS ===")
    tag_source_counts = {t: {"source_domain": 0, "skill": 0, "text_cue": 0, "total_pos": 0} for t in DOMAIN_TAGS}
    source_domain_only = {t: 0 for t in DOMAIN_TAGS}

    for r in records:
        raw_tags = r.get("domain_tags", [])
        if isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags = raw_tags
        else:
            tags = []

        derivations = r.get("derivation_sources", {})
        if isinstance(derivations, str):
            try:
                derivations = json.loads(derivations)
            except Exception:
                derivations = {}

        for t in tags:
            if t not in tag_source_counts:
                continue
            tag_source_counts[t]["total_pos"] += 1
            sources = derivations.get(t, [])
            if isinstance(sources, str):
                sources = [sources]
            has_sd = any(s.startswith("source_domain") for s in sources)
            has_sk = any(s.startswith("skill") for s in sources)
            has_tc = any(s.startswith("text_cue") for s in sources)
            if has_sd:
                tag_source_counts[t]["source_domain"] += 1
            if has_sk:
                tag_source_counts[t]["skill"] += 1
            if has_tc:
                tag_source_counts[t]["text_cue"] += 1
            if has_sd and not has_sk and not has_tc:
                source_domain_only[t] += 1

    df_prov = pd.DataFrame.from_dict(tag_source_counts, orient="index")
    df_prov["source_domain_only"] = [source_domain_only[t] for t in DOMAIN_TAGS]
    df_prov["pct_source_domain_only"] = (df_prov["source_domain_only"] / df_prov["total_pos"] * 100).round(1)
    print(df_prov.to_string())
    return df_prov

def inspect_held_out_reviewed_samples():
    model_path = REPO_ROOT / "models" / "achievement_categorizer_v1.0.1.joblib"
    clf = AchievementCategorizer.load(model_path)

    ref_path = REPO_ROOT / "data" / "annotations" / "categorization_reviewed_reference_samples.jsonl"
    with open(ref_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    test_reviewed = [r for r in records if r["split"] == "test"]
    print(f"\n=== HELD-OUT TEST REVIEWED SAMPLES DISSECTION (N={len(test_reviewed)}) ===")

    dissection = []
    for i, r in enumerate(test_reviewed):
        text = r["achievement_text"]
        gold_tags = set(r["verified_domain_tags"])
        pred_res = clf.predict_record(text)
        pred_tags = set(pred_res.predicted_tags)

        # Compare
        tp = gold_tags.intersection(pred_tags)
        fp = pred_tags.difference(gold_tags)
        fn = gold_tags.difference(pred_tags)

        print(f"\n--- Sample {i+1} [{r['achievement_id']}] ---")
        print(f"Text: \"{text[:120]}...\"")
        print(f"Gold Tags:      {sorted(list(gold_tags)) if gold_tags else '[]'}")
        print(f"Predicted Tags: {sorted(list(pred_tags)) if pred_tags else '[]'}")
        print(f"Match: Exact={gold_tags == pred_tags} | TP={sorted(list(tp))} | FP={sorted(list(fp))} | FN={sorted(list(fn))}")
        print(f"Top Scores: " + ", ".join([f"{k.replace('lbl_domain_', '')}: {v:.3f} (thresh={clf.thresholds[k]:.2f})" for k, v in sorted(pred_res.tag_scores.items(), key=lambda kv: kv[1], reverse=True)[:4]]))

        dissection.append({
            "achievement_id": r["achievement_id"],
            "text": text,
            "gold_tags": sorted(list(gold_tags)),
            "pred_tags": sorted(list(pred_tags)),
            "exact_match": gold_tags == pred_tags,
            "tp": sorted(list(tp)),
            "fp": sorted(list(fp)),
            "fn": sorted(list(fn)),
            "tag_scores": {k: round(v, 4) for k, v in pred_res.tag_scores.items()},
        })

    return dissection

if __name__ == "__main__":
    top_features = inspect_feature_importance()
    df_prov = inspect_provenance_sources()
    dissection = inspect_held_out_reviewed_samples()

    # Save detailed audit data
    audit_data = {
        "top_features": top_features,
        "provenance_summary": df_prov.to_dict(orient="index"),
        "test_dissection": dissection,
    }
    with open(REPO_ROOT / "reports" / "step11_audit_data.json", "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
    print("\n[OK] Saved audit data to reports/step11_audit_data.json")
