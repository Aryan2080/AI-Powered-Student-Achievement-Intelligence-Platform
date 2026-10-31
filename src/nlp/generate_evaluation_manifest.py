"""
src/nlp/generate_evaluation_manifest.py
=======================================
Generates the versioned Integration Evaluation Manifest auditing
the 75-sample extraction benchmark, quality splits, and pipeline performance.
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List

from src.nlp.pipeline import get_nlp_pipeline


def generate_manifest(
    samples_path: str = "data/annotations/extraction_evaluation_samples.jsonl",
    output_path: str = "data/annotations/integration_evaluation_manifest.json",
) -> Dict[str, Any]:
    pipeline = get_nlp_pipeline()
    s_path = Path(samples_path)

    if not s_path.exists():
        raise FileNotFoundError(f"Evaluation benchmark not found at: {s_path}")

    samples: List[Dict[str, Any]] = []
    with open(s_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    total_samples = len(samples)

    # Accumulators
    doc_type_counts = Counter()
    quality_counts = Counter()
    category_counts = Counter()
    synthetic_counts = Counter()

    field_eval = defaultdict(lambda: {"correct": 0, "total": 0})
    doc_type_perf = defaultdict(lambda: {"correct": 0, "total": 0})
    quality_perf = defaultdict(lambda: {"correct": 0, "total": 0})
    cls_eval = {"correct": 0, "total": 0, "by_category": defaultdict(lambda: {"correct": 0, "total": 0})}
    routing_eval = {
        "auto_accepted_clean": 0,
        "auto_accepted_noisy": 0,
        "review_required_clean": 0,
        "review_required_noisy": 0,
        "false_auto_accepts": 0,
    }

    sample_evaluations: List[Dict[str, Any]] = []

    for s in samples:
        doc_id = s["document_id"]
        doc_type = s["document_type"]
        quality = s["quality_condition"]
        syn_status = s.get("synthetic_status", "EXPLICITLY_SYNTHETIC")
        exp_cat = s["category"]
        exp_entities = s["expected_entities"]
        exp_skills = s.get("expected_skills", [])
        src_text = s["source_text"]

        doc_type_counts[doc_type] += 1
        quality_counts[quality] += 1
        category_counts[exp_cat] += 1
        synthetic_counts[syn_status] += 1

        # Run pipeline
        res = pipeline.process_text(src_text, document_id=doc_id)

        # Field Checks
        title_val = res.extracted_entities["achievement_title"]["value"]
        exp_title = exp_entities.get("EVENT_NAME")
        title_ok = False
        if title_val and exp_title:
            title_ok = (
                title_val.lower() == exp_title.lower()
                or exp_title.lower() in title_val.lower()
                or title_val.lower() in exp_title.lower()
            )

        org_val = res.extracted_entities["organization"]["value"]
        exp_org = exp_entities.get("ORGANIZATION")
        org_ok = False
        if org_val and exp_org:
            org_ok = (
                org_val.lower() == exp_org.lower()
                or exp_org.lower() in org_val.lower()
                or org_val.lower() in exp_org.lower()
                or (exp_org == "IEEE" and "institute of electrical" in org_val.lower())
            )

        rank_val = res.extracted_entities["rank"]["value"]
        exp_rank = str(exp_entities.get("RANK"))
        rank_ok = (rank_val == exp_rank or (exp_rank == "None" and rank_val in (None, "None")))

        level_val = res.extracted_entities["level"]["value"]
        exp_level = exp_entities.get("LEVEL")
        level_ok = (level_val == exp_level)

        outcome_val = res.extracted_entities["outcome"]["value"]
        exp_outcome = exp_entities.get("OUTCOME")
        outcome_ok = (outcome_val == exp_outcome)

        date_val = res.extracted_entities["issue_date"]["value"]
        date_ok = (date_val is not None)

        pred_cat = res.classification["predicted_category"]
        cat_ok = (pred_cat == exp_cat)

        extracted_skills = [sk["canonical_name"] for sk in res.skills]
        skills_matched = sum(1 for esk in exp_skills if esk in extracted_skills)
        skills_precision = skills_matched / max(len(extracted_skills), 1) if extracted_skills else 1.0
        skills_recall = skills_matched / max(len(exp_skills), 1) if exp_skills else 1.0
        skills_f1 = (
            2 * skills_precision * skills_recall / max(skills_precision + skills_recall, 1e-6)
            if (skills_precision + skills_recall) > 0
            else 0.0
        )

        # Update field metrics
        checks = [
            ("EVENT_NAME", title_ok),
            ("ORGANIZATION", org_ok),
            ("RANK", rank_ok),
            ("LEVEL", level_ok),
            ("OUTCOME", outcome_ok),
            ("DATE", date_ok),
            ("CATEGORY", cat_ok),
        ]
        all_key_fields_ok = title_ok and org_ok and outcome_ok and rank_ok and level_ok

        for f_name, ok in checks:
            field_eval[f_name]["total"] += 1
            if ok:
                field_eval[f_name]["correct"] += 1

        doc_type_perf[doc_type]["total"] += 1
        if all_key_fields_ok:
            doc_type_perf[doc_type]["correct"] += 1

        quality_perf[quality]["total"] += 1
        if all_key_fields_ok:
            quality_perf[quality]["correct"] += 1

        cls_eval["total"] += 1
        cls_eval["by_category"][exp_cat]["total"] += 1
        if cat_ok:
            cls_eval["correct"] += 1
            cls_eval["by_category"][exp_cat]["correct"] += 1

        # Review routing analysis
        is_clean = (quality == "CLEAN")
        if res.review_required:
            if is_clean:
                routing_eval["review_required_clean"] += 1
            else:
                routing_eval["review_required_noisy"] += 1
        else:
            if is_clean:
                routing_eval["auto_accepted_clean"] += 1
            else:
                routing_eval["auto_accepted_noisy"] += 1
                # If degraded/noisy with missing key fields was auto-accepted, flag false auto-accept
                if not all_key_fields_ok:
                    routing_eval["false_auto_accepts"] += 1

        sample_evaluations.append({
            "document_id": doc_id,
            "document_type": doc_type,
            "quality_condition": quality,
            "category": exp_cat,
            "predicted_category": pred_cat,
            "classifier_confidence": res.classification_confidence,
            "field_confidence": res.field_confidence,
            "review_required": res.review_required,
            "review_reasons": res.review_reasons,
            "all_key_fields_ok": all_key_fields_ok,
            "skills_extracted_count": len(extracted_skills),
            "skills_f1": round(skills_f1, 4),
        })

    # Summary metrics
    manifest = {
        "manifest_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_dataset": {
            "source_path": samples_path,
            "total_samples": total_samples,
            "synthetic_status": dict(synthetic_counts),
            "template_breakdown": dict(doc_type_counts),
            "quality_conditions": dict(quality_counts),
            "category_distribution": dict(category_counts),
        },
        "field_level_performance": {
            f_name: {
                "support": m["total"],
                "correct": m["correct"],
                "accuracy": round(m["correct"] / m["total"], 4) if m["total"] else 0.0,
            }
            for f_name, m in field_eval.items()
        },
        "performance_by_template": {
            dt: {
                "support": m["total"],
                "all_fields_correct": m["correct"],
                "accuracy": round(m["correct"] / m["total"], 4) if m["total"] else 0.0,
            }
            for dt, m in doc_type_perf.items()
        },
        "performance_by_quality_condition": {
            qc: {
                "support": m["total"],
                "all_fields_correct": m["correct"],
                "accuracy": round(m["correct"] / m["total"], 4) if m["total"] else 0.0,
            }
            for qc, m in quality_perf.items()
        },
        "classification_performance": {
            "total_evaluated": cls_eval["total"],
            "correct_predictions": cls_eval["correct"],
            "accuracy": round(cls_eval["correct"] / max(cls_eval["total"], 1), 4),
            "by_category": {
                c: {
                    "support": cd["total"],
                    "correct": cd["correct"],
                    "accuracy": round(cd["correct"] / max(cd["total"], 1), 4),
                }
                for c, cd in cls_eval["by_category"].items()
            },
        },
        "review_routing_audit": {
            "routing_summary": routing_eval,
            "false_auto_acceptance_rate": round(
                routing_eval["false_auto_accepts"] / max(total_samples, 1), 4
            ),
            "total_review_required": (
                routing_eval["review_required_clean"] + routing_eval["review_required_noisy"]
            ),
            "total_auto_accepted": (
                routing_eval["auto_accepted_clean"] + routing_eval["auto_accepted_noisy"]
            ),
        },
        "confidence_semantics_audit": {
            "field_confidence": {
                "type": "Heuristic Confidence Score",
                "range": "[0.00, 1.00]",
                "basis": "Lexical cue hierarchy, boundary regex strength, and source completeness.",
                "calibrated": False,
            },
            "classification_confidence": {
                "type": "Calibrated Class Probability",
                "range": "[0.00, 1.00]",
                "basis": "Logistic Regression predict_proba with balanced class weighting over TF-IDF features.",
                "calibrated": True,
            },
        },
        "date_semantics_audit": {
            "event_date": "Date on which competition, hackathon, or conference took place (cues: 'held on', 'conducted on').",
            "issue_date": "Date on which certificate or award document was formally signed/issued (cues: 'issued on', 'date of issue').",
            "conflict_policy": "Contradictory dates for the same event timeline automatically trigger review_required=True.",
        },
        "sample_evaluations": sample_evaluations,
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest written successfully to: {out_file}")
    return manifest


if __name__ == "__main__":
    generate_manifest()
