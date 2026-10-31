"""
src/nlp/blind_sample_validator.py
=================================
Blind Sample Validation & AI Annotation Quality Audit Subsystem (Step 18)
AI-Powered Student Achievement Intelligence Platform — Member 1

Provides rigorous pre-scoring verification, reviewer completion auditing,
error categorization, and multi-label comparison metrics for the 30-record
validation sample.

Enforces zero tolerance for fabricated reviewer labels:
- Blocks scoring immediately if reviewer sheet is incomplete.
- Distinguishes explicit zero-tag tokens ('NONE') from missing fields.
- Rejects invalid tags outside the canonical 10-tag taxonomy.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

# Canonical 10-tag taxonomy
DOMAIN_TAGS: List[str] = [
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

DOMAIN_TAG_NAMES: Dict[str, str] = {
    "lbl_domain_ai": "Artificial Intelligence",
    "lbl_domain_ml": "Machine Learning",
    "lbl_domain_nlp": "Natural Language Processing",
    "lbl_domain_cv": "Computer Vision",
    "lbl_domain_security": "Cybersecurity & Privacy",
    "lbl_domain_systems": "Systems, Cloud & Architecture",
    "lbl_domain_web": "Web Development & APIs",
    "lbl_domain_data": "Data Engineering & Analytics",
    "lbl_domain_hardware": "Hardware & IoT",
    "lbl_domain_other": "Other Domain (Non-Computing)",
}

VALID_STATUSES: Set[str] = {"COMPLETED", "VERIFIED", "VALIDATED", "HUMAN_APPROVED"}
EXPLICIT_ZERO_TAG_TOKENS: Set[str] = {"NONE", "[]", "[ZERO-TAG]", "[NONE]", "NO_DOMAIN", "ZERO_TAG"}


class ReviewerIncompleteError(Exception):
    """Raised when evaluation is attempted on an incomplete reviewer submission."""
    pass


def parse_tag_string(raw: Optional[str]) -> Tuple[List[str], bool, bool]:
    """
    Parse raw tag string from spreadsheet or JSON.
    Returns:
        (tags_list, is_explicit_zero_tag, is_missing)
    """
    if raw is None:
        return [], False, True

    cleaned = raw.strip().replace(r"\|", "|")
    if not cleaned:
        return [], False, True

    # Strip trailing pipe if present
    if cleaned.endswith("|"):
        cleaned = cleaned[:-1].strip()

    upper = cleaned.upper()
    if upper in EXPLICIT_ZERO_TAG_TOKENS:
        return [], True, False

    if cleaned == "[]":
        return [], True, False

    # Split on pipe, comma, or whitespace
    delimiters = ["|", ","]
    tokens = [cleaned]
    for d in delimiters:
        new_tokens = []
        for t in tokens:
            new_tokens.extend(t.split(d))
        tokens = new_tokens

    parsed: List[str] = []
    for tok in tokens:
        item = tok.strip().strip("'\"[]")
        if item and item.upper() not in EXPLICIT_ZERO_TAG_TOKENS:
            parsed.append(item)

    if not parsed:
        return [], True, False

    return parsed, False, False


@dataclass
class ReviewerRowAudit:
    row_index: int
    achievement_id: str
    primary_category: str
    validator_name: str
    validator_status: str
    validator_tags_raw: str
    parsed_tags: List[str]
    is_explicit_zero_tag: bool
    is_missing: bool
    is_valid: bool
    validation_errors: List[str] = field(default_factory=list)


def verify_reviewer_completion(
    blind_csv_path: Union[str, Path] = "data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv",
    key_jsonl_path: Union[str, Path] = "data/annotations/ai_assisted/domain_categorization_validation_sample_key.jsonl",
) -> Dict[str, Any]:
    """
    Verify completion and validity of reviewer submission before scoring.
    """
    csv_p = Path(blind_csv_path)
    key_p = Path(key_jsonl_path)

    if not csv_p.exists():
        raise FileNotFoundError(f"Blind CSV not found: {csv_p}")
    if not key_p.exists():
        raise FileNotFoundError(f"Key JSONL not found: {key_p}")

    # 1. Load reference key records
    key_records: List[Dict[str, Any]] = []
    with open(key_p, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                key_records.append(json.loads(line))

    key_ids = [k["achievement_id"] for k in key_records]
    key_ids_set = set(key_ids)

    if len(key_ids) != 30 or len(key_ids_set) != 30:
        raise ValueError(f"Expected 30 unique sample IDs in key, found {len(key_ids)} (unique: {len(key_ids_set)})")

    # 2. Read submission CSV
    with open(csv_p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    required_fields = ["achievement_id", "validator_tags", "validator_status"]
    missing_fields = [f for f in required_fields if f not in fieldnames]
    if missing_fields:
        return {
            "is_complete": False,
            "can_score": False,
            "blocker_type": "SCHEMA_ERROR",
            "blocker_reason": f"Blind CSV missing required headers: {missing_fields}",
            "total_rows": len(rows),
            "completed_count": 0,
            "incomplete_count": len(rows),
            "details": [],
        }

    # 3. Check row IDs against key
    submission_ids = [r.get("achievement_id", "").strip() for r in rows]
    submission_ids_set = set(submission_ids)

    id_mismatches = []
    if len(submission_ids) != 30:
        id_mismatches.append(f"Expected 30 rows, found {len(submission_ids)}")
    if submission_ids_set != key_ids_set:
        diff_missing = key_ids_set - submission_ids_set
        diff_extra = submission_ids_set - key_ids_set
        if diff_missing:
            id_mismatches.append(f"Missing sample IDs: {sorted(list(diff_missing))}")
        if diff_extra:
            id_mismatches.append(f"Unexpected IDs in submission: {sorted(list(diff_extra))}")

    # 4. Audit each row
    audits: List[ReviewerRowAudit] = []
    incomplete_rows: List[Dict[str, Any]] = []
    invalid_tag_rows: List[Dict[str, Any]] = []
    completed_rows: List[Dict[str, Any]] = []

    for idx, r in enumerate(rows, 1):
        aid = r.get("achievement_id", "").strip()
        cat = r.get("primary_category", "").strip()
        val_name = r.get("validator_name", "").strip()
        val_status = r.get("validator_status", "").strip().upper()
        raw_tags = r.get("validator_tags", "")

        parsed_tags, is_zero_tag, is_missing = parse_tag_string(raw_tags)
        errors: List[str] = []

        # Check completeness
        if is_missing:
            errors.append("Missing reviewer labels (validator_tags is blank). Must provide domain tags or explicit 'NONE'.")

        if val_status not in VALID_STATUSES:
            if not is_missing:
                # If tags provided but status still pending
                errors.append(f"validator_status is '{val_status}', expected COMPLETED or VERIFIED")
            else:
                errors.append("Review status is PENDING; human validation not performed.")

        # Check tag validity
        for t in parsed_tags:
            if t not in DOMAIN_TAGS:
                errors.append(f"Invalid tag '{t}' outside canonical 10-tag taxonomy.")

        # Mutual exclusion
        if "lbl_domain_other" in parsed_tags and len(parsed_tags) > 1:
            errors.append("Mutual exclusion violation: lbl_domain_other cannot be combined with technical computing tags.")

        is_valid = len(errors) == 0

        audit = ReviewerRowAudit(
            row_index=idx,
            achievement_id=aid,
            primary_category=cat,
            validator_name=val_name,
            validator_status=val_status,
            validator_tags_raw=raw_tags,
            parsed_tags=parsed_tags,
            is_explicit_zero_tag=is_zero_tag,
            is_missing=is_missing,
            is_valid=is_valid,
            validation_errors=errors,
        )
        audits.append(audit)

        row_info = {
            "row_index": idx,
            "achievement_id": aid,
            "primary_category": cat,
            "status": val_status,
            "raw_tags": raw_tags,
            "errors": errors,
        }

        if is_valid:
            completed_rows.append(row_info)
        else:
            incomplete_rows.append(row_info)
            if any("Invalid tag" in e for e in errors):
                invalid_tag_rows.append(row_info)

    is_complete = (len(completed_rows) == 30) and (len(id_mismatches) == 0)

    blocker_reason = None
    if not is_complete:
        if len(completed_rows) == 0:
            blocker_reason = (
                f"Validation blocked: All 30 validation sample records are unreviewed (validator_tags is blank, "
                f"validator_status is PENDING). No independent reviewer labels have been provided."
            )
        else:
            blocker_reason = (
                f"Validation blocked: Reviewer submission is incomplete. "
                f"{len(completed_rows)}/30 rows complete, {len(incomplete_rows)}/30 rows require attention."
            )

    return {
        "is_complete": is_complete,
        "can_score": is_complete,
        "total_expected": 30,
        "total_rows_found": len(rows),
        "completed_count": len(completed_rows),
        "incomplete_count": len(incomplete_rows),
        "invalid_tag_count": len(invalid_tag_rows),
        "id_mismatches": id_mismatches,
        "blocker_reason": blocker_reason,
        "completed_rows": completed_rows,
        "incomplete_rows": incomplete_rows,
        "audits": audits,
    }


# ==============================================================================
# MULTI-LABEL METRICS CALCULATION (FOR VALID SUBMISSIONS)
# ==============================================================================

def compute_multilabel_metrics(
    y_true: List[List[str]],
    y_pred: List[List[str]],
    all_tags: List[str] = DOMAIN_TAGS,
) -> Dict[str, Any]:
    """
    Compute standard multi-label classification metrics across all records.
    """
    n = len(y_true)
    if n == 0:
        return {}

    # Binary matrices
    tag_to_idx = {t: i for i, t in enumerate(all_tags)}
    l = len(all_tags)

    yt_mat = np.zeros((n, l), dtype=int)
    yp_mat = np.zeros((n, l), dtype=int)

    for i, tags in enumerate(y_true):
        for t in tags:
            if t in tag_to_idx:
                yt_mat[i, tag_to_idx[t]] = 1

    for i, tags in enumerate(y_pred):
        for t in tags:
            if t in tag_to_idx:
                yp_mat[i, tag_to_idx[t]] = 1

    # Exact match ratio
    exact_matches = np.all(yt_mat == yp_mat, axis=1)
    exact_match_ratio = float(np.mean(exact_matches))

    # Hamming loss
    hamming_loss = float(np.mean(yt_mat != yp_mat))

    # Per-tag metrics
    per_tag: Dict[str, Dict[str, Any]] = {}
    tp_list, fp_list, fn_list = [], [], []

    for idx, tag in enumerate(all_tags):
        yt_col = yt_mat[:, idx]
        yp_col = yp_mat[:, idx]

        tp = int(np.sum((yt_col == 1) & (yp_col == 1)))
        fp = int(np.sum((yt_col == 0) & (yp_col == 1)))
        fn = int(np.sum((yt_col == 1) & (yp_col == 0)))
        tn = int(np.sum((yt_col == 0) & (yp_col == 0)))
        support = int(np.sum(yt_col == 1))

        prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if support == 0 and fp == 0 else 0.0)
        rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if support == 0 else 0.0)
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        per_tag[tag] = {
            "tag_name": DOMAIN_TAG_NAMES.get(tag, tag),
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
        }
        tp_list.append(tp)
        fp_list.append(fp)
        fn_list.append(fn)

    # Macro metrics (unweighted mean across classes with support > 0, or all classes)
    macro_f1 = float(np.mean([m["f1"] for m in per_tag.values()]))
    macro_prec = float(np.mean([m["precision"] for m in per_tag.values()]))
    macro_rec = float(np.mean([m["recall"] for m in per_tag.values()]))

    # Micro metrics
    total_tp = sum(tp_list)
    total_fp = sum(fp_list)
    total_fn = sum(fn_list)
    micro_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = 2 * micro_prec * micro_rec / (micro_prec + micro_rec) if (micro_prec + micro_rec) > 0 else 0.0

    # Zero-tag agreement
    true_zero = [len(tags) == 0 for tags in y_true]
    pred_zero = [len(tags) == 0 for tags in y_pred]

    zero_tp = sum(1 for tz, pz in zip(true_zero, pred_zero) if tz and pz)
    zero_fp = sum(1 for tz, pz in zip(true_zero, pred_zero) if not tz and pz)
    zero_fn = sum(1 for tz, pz in zip(true_zero, pred_zero) if tz and not pz)
    zero_tn = sum(1 for tz, pz in zip(true_zero, pred_zero) if not tz and not pz)
    zero_support = sum(true_zero)

    zero_prec = zero_tp / (zero_tp + zero_fp) if (zero_tp + zero_fp) > 0 else 0.0
    zero_rec = zero_tp / (zero_tp + zero_fn) if (zero_tp + zero_fn) > 0 else 0.0
    zero_f1 = 2 * zero_prec * zero_rec / (zero_prec + zero_rec) if (zero_prec + zero_rec) > 0 else 0.0

    return {
        "sample_size": n,
        "exact_match_ratio": round(exact_match_ratio, 4),
        "hamming_loss": round(hamming_loss, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "macro_f1": round(macro_f1, 4),
        "micro_precision": round(micro_prec, 4),
        "micro_recall": round(micro_rec, 4),
        "micro_f1": round(micro_f1, 4),
        "per_tag": per_tag,
        "zero_tag_metrics": {
            "support": zero_support,
            "tp": zero_tp,
            "fp": zero_fp,
            "fn": zero_fn,
            "tn": zero_tn,
            "precision": round(zero_prec, 4),
            "recall": round(zero_rec, 4),
            "f1": round(zero_f1, 4),
        },
    }


# ==============================================================================
# AUDIT & REPORT GENERATION RUNNER
# ==============================================================================

COMPARISON_CSV_HEADERS: List[str] = [
    "achievement_id",
    "primary_category",
    "ai_proposed_tags",
    "reviewer_tags",
    "exact_match",
    "hamming_distance",
    "jaccard_similarity",
    "error_category",
    "review_status",
    "notes",
]


def run_validation_audit(
    blind_csv_path: Union[str, Path] = "data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv",
    key_jsonl_path: Union[str, Path] = "data/annotations/ai_assisted/domain_categorization_validation_sample_key.jsonl",
    output_comparison_csv: Union[str, Path] = "reports/step18_validation_record_comparison.csv",
) -> Dict[str, Any]:
    """
    Execute Step 18 Validation Audit.
    Verifies reviewer completion; halts with blocked status if incomplete.
    """
    verification = verify_reviewer_completion(blind_csv_path, key_jsonl_path)

    comp_csv_p = Path(output_comparison_csv)
    comp_csv_p.parent.mkdir(parents=True, exist_ok=True)

    if not verification["is_complete"]:
        # Blocked state: Write comparison CSV header with record rows noting evaluation state
        with open(comp_csv_p, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(COMPARISON_CSV_HEADERS)
            for audit in verification["audits"]:
                if audit.is_valid:
                    rev_tags_str = "|".join(audit.parsed_tags) if audit.parsed_tags else "NONE"
                    writer.writerow([
                        audit.achievement_id,
                        audit.primary_category,
                        "N/A (BLOCKED)",
                        rev_tags_str,
                        "N/A",
                        "N/A",
                        "N/A",
                        "EVALUATION_BLOCKED",
                        audit.validator_status,
                        "Reviewer tags recorded; full evaluation blocked pending 2 unresolved records.",
                    ])
                else:
                    rev_tags_str = "PENDING_HUMAN_INPUT" if audit.is_missing else ("|".join(audit.parsed_tags) if audit.parsed_tags else "NONE")
                    writer.writerow([
                        audit.achievement_id,
                        audit.primary_category,
                        "N/A (BLOCKED)",
                        rev_tags_str,
                        "N/A",
                        "N/A",
                        "N/A",
                        "BLOCKED_UNRESOLVED",
                        audit.validator_status,
                        f"Evaluation halted: {'; '.join(audit.validation_errors)}",
                    ])

        return {
            "status": "EVALUATION_BLOCKED_PENDING_REVIEWER_COMPLETION",
            "verification": verification,
            "metrics": None,
            "comparison_csv_path": str(comp_csv_p),
        }

    # If completed: Compute metrics and output evaluated comparison rows
    # (Future-proof execution once human labels are supplied)
    key_p = Path(key_jsonl_path)
    with open(key_p, "r", encoding="utf-8") as f:
        key_records = {r["achievement_id"]: r for r in (json.loads(line) for line in f if line.strip())}

    y_true = []
    y_pred = []
    comparison_rows = []

    for audit in verification["audits"]:
        aid = audit.achievement_id
        rev_tags = audit.parsed_tags
        key_rec = key_records[aid]
        ai_tags = key_rec["proposed_tags"]

        y_true.append(rev_tags)
        y_pred.append(ai_tags)

        exact = (sorted(rev_tags) == sorted(ai_tags))
        set_true = set(rev_tags)
        set_pred = set(ai_tags)
        union = set_true | set_pred
        inter = set_true & set_pred
        jaccard = len(inter) / len(union) if union else 1.0
        hamming_dist = len(set_true ^ set_pred)

        error_cat = "EXACT_MATCH" if exact else "DISCREPANCY"
        if not exact:
            if not ai_tags and rev_tags:
                error_cat = "INCORRECT_ZERO_TAG"
            elif ai_tags and not rev_tags:
                error_cat = "UNSUPPORTED_TAG"
            elif set_pred - set_true:
                error_cat = "UNSUPPORTED_TAG"
            elif set_true - set_pred:
                error_cat = "MISSED_APPLICABLE_TAG"

        comparison_rows.append([
            aid,
            audit.primary_category,
            "|".join(ai_tags) if ai_tags else "[]",
            "|".join(rev_tags) if rev_tags else "[]",
            "TRUE" if exact else "FALSE",
            hamming_dist,
            round(jaccard, 4),
            error_cat,
            "VALIDATED",
            f"Reviewer: {audit.validator_name or 'Independent Reviewer'}",
        ])

    with open(comp_csv_p, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COMPARISON_CSV_HEADERS)
        for row in comparison_rows:
            writer.writerow(row)

    metrics = compute_multilabel_metrics(y_true, y_pred)

    return {
        "status": "VALIDATION_COMPLETE",
        "verification": verification,
        "metrics": metrics,
        "comparison_csv_path": str(comp_csv_p),
    }
