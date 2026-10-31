"""
src/nlp/evaluate_gold_categorization.py
======================================
Independent Gold Evaluation Subsystem (Step 13)
AI-Powered Student Achievement Intelligence Platform — Member 1

Provides reproducible, audit-safe evaluation of the multi-label achievement categorizer
against human-verified gold ground truth records. Enforces strict safeguards:
- Isolates gold evaluation data from training and tuning.
- Prevents evaluation on unverified or fabricated annotations.
- Flags inadequate sample size when human review queue is incomplete.
- Calculates per-tag metrics, confidence tier stratifications, Hamming loss,
  exact match ratio, and inter-annotator agreement statistics.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.nlp.annotation_workflow import (
        AnnotationStatus,
        compute_inter_annotator_agreement,
        detect_disagreements,
        validate_annotation_corpus,
    )
    from src.nlp.categorization import (
        DOMAIN_TAGS,
        DOMAIN_TAG_NAMES,
        AchievementCategorizer,
        CategorizationResult,
    )
else:
    from .annotation_workflow import (
        AnnotationStatus,
        compute_inter_annotator_agreement,
        detect_disagreements,
        validate_annotation_corpus,
    )
    from .categorization import (
        DOMAIN_TAGS,
        DOMAIN_TAG_NAMES,
        AchievementCategorizer,
        CategorizationResult,
    )


def evaluate_gold_categorization(
    gold_task_path: Union[str, Path] = "data/annotations/domain_categorization_gold_annotation_task.jsonl",
    model_path: Union[str, Path] = "models/achievement_categorizer_v1.0.1.joblib",
    output_summary_path: Optional[Union[str, Path]] = "reports/step13_annotation_status_summary.json",
    min_stat_sample_size: int = 50,
) -> Dict[str, Any]:
    """
    Execute reproducible evaluation against human-verified gold records.
    """
    task_p = Path(gold_task_path)
    if not task_p.exists():
        raise FileNotFoundError(f"Gold annotation task file not found at: {task_p}")

    model_p = Path(model_path)
    if not model_p.exists():
        raise FileNotFoundError(f"Categorizer model artifact not found at: {model_p}")

    # 1. Load and validate task records
    all_records: List[Dict[str, Any]] = []
    with open(task_p, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_records.append(json.loads(line))

    val_res = validate_annotation_corpus(all_records, expected_count=len(all_records))
    if not val_res["is_valid"]:
        raise ValueError(f"Corpus validation failed with {val_res['error_count']} errors: {val_res['record_errors']}")

    # 2. Filter genuine verified records (strictly human-adjudicated)
    verified_records = [
        r for r in all_records
        if r.get("annotation_status") == AnnotationStatus.VERIFIED.value
        and r.get("adjudicated_tags") is not None
    ]
    pending_records = [
        r for r in all_records
        if r.get("annotation_status") == AnnotationStatus.PENDING_HUMAN_REVIEW.value
    ]

    n_total = len(all_records)
    n_verified = len(verified_records)
    n_pending = len(pending_records)

    is_provisional = n_verified < min_stat_sample_size
    sample_warning = (
        f"Evaluated on N={n_verified} verified records. Sample size is below the recommended threshold "
        f"(N={min_stat_sample_size}) for statistically significant production sign-off. "
        f"A total of {n_pending} records remain pending human review."
        if is_provisional else None
    )

    # 3. Inter-annotator agreement and disagreement stats
    iaa_stats = compute_inter_annotator_agreement(all_records)
    disagreement_stats = detect_disagreements(all_records)

    # 4. Model Prediction and Scoring
    categorizer = AchievementCategorizer.load(model_p)

    y_true_binary: List[List[int]] = []
    y_pred_binary: List[List[int]] = []
    predictions: List[CategorizationResult] = []

    for r in verified_records:
        text = r["achievement_text"]
        true_tags = set(r["adjudicated_tags"])

        pred_res = categorizer.predict_record({"achievement_text": text, "achievement_id": r["achievement_id"]})
        predictions.append(pred_res)
        pred_tags = set(pred_res.predicted_tags)

        # Binary vector per tag
        y_true_binary.append([1 if t in true_tags else 0 for t in DOMAIN_TAGS])
        y_pred_binary.append([1 if t in pred_tags else 0 for t in DOMAIN_TAGS])

    Y_true = np.array(y_true_binary, dtype=int) if y_true_binary else np.zeros((0, len(DOMAIN_TAGS)), dtype=int)
    Y_pred = np.array(y_pred_binary, dtype=int) if y_pred_binary else np.zeros((0, len(DOMAIN_TAGS)), dtype=int)

    # 5. Compute Per-Tag Metrics
    per_tag_metrics: List[Dict[str, Any]] = []
    tag_tp = [0] * len(DOMAIN_TAGS)
    tag_fp = [0] * len(DOMAIN_TAGS)
    tag_fn = [0] * len(DOMAIN_TAGS)
    tag_tn = [0] * len(DOMAIN_TAGS)

    for i, tag in enumerate(DOMAIN_TAGS):
        if n_verified > 0:
            yt = Y_true[:, i]
            yp = Y_pred[:, i]

            tp = int(np.sum((yt == 1) & (yp == 1)))
            fp = int(np.sum((yt == 0) & (yp == 1)))
            fn = int(np.sum((yt == 1) & (yp == 0)))
            tn = int(np.sum((yt == 0) & (yp == 0)))
            support = int(np.sum(yt == 1))
        else:
            tp = fp = fn = tn = support = 0

        tag_tp[i] = tp
        tag_fp[i] = fp
        tag_fn[i] = fn
        tag_tn[i] = tn

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_tag_metrics.append({
            "tag": tag,
            "name": DOMAIN_TAG_NAMES.get(tag, tag),
            "support": support,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "threshold": categorizer.thresholds.get(tag, 0.50),
        })

    # 6. Global Multi-Label Aggregate Metrics
    total_tp = sum(tag_tp)
    total_fp = sum(tag_fp)
    total_fn = sum(tag_fn)

    micro_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (2 * micro_prec * micro_rec) / (micro_prec + micro_rec) if (micro_prec + micro_rec) > 0 else 0.0

    valid_f1s = [m["f1_score"] for m in per_tag_metrics if m["support"] > 0]
    macro_f1 = sum(valid_f1s) / len(valid_f1s) if valid_f1s else 0.0

    valid_precs = [m["precision"] for m in per_tag_metrics if m["support"] > 0]
    macro_prec = sum(valid_precs) / len(valid_precs) if valid_precs else 0.0

    valid_recs = [m["recall"] for m in per_tag_metrics if m["support"] > 0]
    macro_rec = sum(valid_recs) / len(valid_recs) if valid_recs else 0.0

    if n_verified > 0:
        hamming_loss = float(np.mean(Y_true != Y_pred))
        exact_matches = int(np.sum(np.all(Y_true == Y_pred, axis=1)))
        exact_match_ratio = exact_matches / n_verified
    else:
        hamming_loss = 0.0
        exact_matches = 0
        exact_match_ratio = 0.0

    # 7. Confidence Tier Stratification
    tier_counts = {"HIGH": 0, "MEDIUM": 0, "LOW_MARGIN": 0}
    tier_correct = {"HIGH": 0, "MEDIUM": 0, "LOW_MARGIN": 0}

    for idx, (r, pred) in enumerate(zip(verified_records, predictions)):
        true_tags = set(r["adjudicated_tags"])
        for tag, tier in pred.confidence_tier.items():
            if tier in tier_counts:
                tier_counts[tier] += 1
                if tag in true_tags:
                    tier_correct[tier] += 1

    tier_precision = {
        tier: round(tier_correct[tier] / tier_counts[tier], 4) if tier_counts[tier] > 0 else 0.0
        for tier in ("HIGH", "MEDIUM", "LOW_MARGIN")
    }

    # 8. Compile Comprehensive Summary
    summary: Dict[str, Any] = {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": "c8c1b80",
        "task_file": str(task_p),
        "model_file": str(model_p),
        "model_version": categorizer.model_version,
        "corpus_status": {
            "total_records": n_total,
            "verified_records": n_verified,
            "pending_records": n_pending,
            "is_provisional_sample": is_provisional,
            "sample_size_assessment": "PROVISIONAL_INADEQUATE" if is_provisional else "STATISTICALLY_ADEQUATE",
            "warning": sample_warning,
        },
        "overall_metrics": {
            "micro_precision": round(micro_prec, 4),
            "micro_recall": round(micro_rec, 4),
            "micro_f1": round(micro_f1, 4),
            "macro_precision": round(macro_prec, 4),
            "macro_recall": round(macro_rec, 4),
            "macro_f1": round(macro_f1, 4),
            "hamming_loss": round(hamming_loss, 4),
            "exact_matches": exact_matches,
            "exact_match_ratio": round(exact_match_ratio, 4),
        },
        "confidence_tier_performance": {
            "tier_predictions": tier_counts,
            "tier_precision": tier_precision,
        },
        "per_tag_metrics": per_tag_metrics,
        "inter_annotator_agreement": iaa_stats,
        "disagreement_and_queue": {
            "resolved_verified_count": disagreement_stats["resolved_verified_count"],
            "awaiting_reviews_count": disagreement_stats["awaiting_reviews_count"],
            "unreviewed_count": disagreement_stats.get("unreviewed_count", 0),
            "partial_review_count": disagreement_stats.get("partial_review_count", 0),
            "agreed_count": disagreement_stats["agreed_count"],
            "disagreed_count": disagreement_stats["disagreed_count"],
            "queue_length": len(disagreement_stats["awaiting_adjudication_queue"]),
        },
    }

    if output_summary_path:
        out_p = Path(output_summary_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate multi-label categorizer against gold annotations.")
    parser.add_argument("--task-file", default="data/annotations/domain_categorization_gold_annotation_task.jsonl")
    parser.add_argument("--model-file", default="models/achievement_categorizer_v1.0.1.joblib")
    parser.add_argument("--output-json", default="reports/step13_annotation_status_summary.json")
    args = parser.parse_args()

    res = evaluate_gold_categorization(
        gold_task_path=args.task_file,
        model_path=args.model_file,
        output_summary_path=args.output_json,
    )
    print(f"Evaluation completed. Verified records: {res['corpus_status']['verified_records']}")
    print(f"Micro F1: {res['overall_metrics']['micro_f1']}, Macro F1: {res['overall_metrics']['macro_f1']}")
    if res["corpus_status"]["warning"]:
        print(f"Warning: {res['corpus_status']['warning']}")
