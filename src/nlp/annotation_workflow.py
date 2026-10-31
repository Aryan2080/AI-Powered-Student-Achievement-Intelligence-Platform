"""
src/nlp/annotation_workflow.py
==============================
Gold Annotation Workflow & Quality Control Subsystem (Step 13)
AI-Powered Student Achievement Intelligence Platform — Member 1

Implements a robust, auditable human-annotation workflow for multi-label domain
categorization. Ensures strict quality controls, blind dual-annotation protocol,
disagreement detection, inter-annotator agreement computation, and evaluation safeguards.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.nlp.categorization import DOMAIN_TAGS, DOMAIN_TAG_NAMES
else:
    from .categorization import DOMAIN_TAGS, DOMAIN_TAG_NAMES


class AnnotatorReviewStatus(str, Enum):
    """Review completion status for an individual annotator."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class DisagreementStatus(str, Enum):
    """Disagreement and adjudication state between annotators."""
    AWAITING_REVIEWS = "AWAITING_REVIEWS"
    AGREED = "AGREED"
    DISAGREED = "DISAGREED"
    RESOLVED = "RESOLVED"


class AnnotationStatus(str, Enum):
    """Overall status of a gold annotation task item."""
    PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"
    ANNOTATOR_AGREEMENT = "ANNOTATOR_AGREEMENT"
    AWAITING_ADJUDICATION = "AWAITING_ADJUDICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


@dataclass
class GoldAnnotationItem:
    """Standardized contract for an auditable gold annotation task record."""
    achievement_id: str
    achievement_text: str
    primary_category: str
    split: str = "test"
    annotator_a_name: Optional[str] = None
    annotator_a_tags: Optional[List[str]] = None
    annotator_a_notes: Optional[str] = None
    annotator_a_uncertain: bool = False
    annotator_a_status: AnnotatorReviewStatus = AnnotatorReviewStatus.PENDING
    annotator_b_name: Optional[str] = None
    annotator_b_tags: Optional[List[str]] = None
    annotator_b_notes: Optional[str] = None
    annotator_b_uncertain: bool = False
    annotator_b_status: AnnotatorReviewStatus = AnnotatorReviewStatus.PENDING
    disagreement_status: DisagreementStatus = DisagreementStatus.AWAITING_REVIEWS
    adjudicated_tags: Optional[List[str]] = None
    adjudication_notes: Optional[str] = None
    adjudicator: Optional[str] = None
    annotation_status: AnnotationStatus = AnnotationStatus.PENDING_HUMAN_REVIEW

    def to_dict(self) -> Dict[str, Any]:
        """Convert item to dictionary with serialization safeguards."""
        return {
            "achievement_id": self.achievement_id,
            "achievement_text": self.achievement_text,
            "primary_category": self.primary_category,
            "split": self.split,
            "annotator_a_name": self.annotator_a_name,
            "annotator_a_tags": self.annotator_a_tags,
            "annotator_a_notes": self.annotator_a_notes,
            "annotator_a_uncertain": bool(self.annotator_a_uncertain),
            "annotator_a_status": self.annotator_a_status.value if isinstance(self.annotator_a_status, Enum) else self.annotator_a_status,
            "annotator_b_name": self.annotator_b_name,
            "annotator_b_tags": self.annotator_b_tags,
            "annotator_b_notes": self.annotator_b_notes,
            "annotator_b_uncertain": bool(self.annotator_b_uncertain),
            "annotator_b_status": self.annotator_b_status.value if isinstance(self.annotator_b_status, Enum) else self.annotator_b_status,
            "disagreement_status": self.disagreement_status.value if isinstance(self.disagreement_status, Enum) else self.disagreement_status,
            "adjudicated_tags": self.adjudicated_tags,
            "adjudication_notes": self.adjudication_notes,
            "adjudicator": self.adjudicator,
            "annotation_status": self.annotation_status.value if isinstance(self.annotation_status, Enum) else self.annotation_status,
            # Backward-compatibility alias keys for Step 11/12 consumers:
            "annotator_1": self.annotator_a_name,
            "annotator_2": self.annotator_b_name,
        }


# ==============================================================================
# QUALITY CONTROL & VALIDATION LOGIC
# ==============================================================================

def validate_annotation_record(record: Dict[str, Any]) -> List[str]:
    """
    Validate a single annotation record against strict taxonomy and integrity rules.
    Returns a list of error descriptions (empty list if completely valid).
    """
    errors: List[str] = []
    aid = record.get("achievement_id")

    # 1. Mandatory Identity and Text
    if not aid or not isinstance(aid, str) or not aid.strip():
        errors.append("Missing or empty 'achievement_id'.")
    if not record.get("achievement_text") or not isinstance(record.get("achievement_text"), str):
        errors.append(f"Record '{aid}': Missing or non-string 'achievement_text'.")

    # 2. Split Boundary Validation
    split = record.get("split")
    if split != "test":
        errors.append(f"Record '{aid}': Invalid split '{split}'. Gold evaluation items must belong strictly to 'test'.")

    # 3. Status Validation
    status = record.get("annotation_status")
    valid_statuses = {s.value for s in AnnotationStatus}
    if status not in valid_statuses:
        errors.append(f"Record '{aid}': Unknown annotation_status '{status}'.")

    # 4. Tag Validation for Adjudicated Tags
    adjudicated = record.get("adjudicated_tags")
    if adjudicated is not None:
        if not isinstance(adjudicated, list):
            errors.append(f"Record '{aid}': 'adjudicated_tags' must be a list or null, got {type(adjudicated).__name__}.")
        else:
            for t in adjudicated:
                if t not in DOMAIN_TAGS:
                    errors.append(f"Record '{aid}': Invalid domain tag '{t}' in adjudicated_tags.")

    # 5. Tag Validation for Annotator Tags
    for annotator_key in ("annotator_a_tags", "annotator_b_tags"):
        tags = record.get(annotator_key)
        if tags is not None:
            if not isinstance(tags, list):
                errors.append(f"Record '{aid}': '{annotator_key}' must be a list or null, got {type(tags).__name__}.")
            else:
                for t in tags:
                    if t not in DOMAIN_TAGS:
                        errors.append(f"Record '{aid}': Invalid domain tag '{t}' in '{annotator_key}'.")

    # 6. Verification Safeguards (Anti-Fabrication & Completeness)
    if status == AnnotationStatus.VERIFIED.value:
        if adjudicated is None:
            errors.append(f"Record '{aid}': Cannot mark as VERIFIED with null 'adjudicated_tags'.")
        if not record.get("adjudicator"):
            errors.append(f"Record '{aid}': VERIFIED record is missing 'adjudicator'.")
        if not record.get("adjudication_notes"):
            errors.append(f"Record '{aid}': VERIFIED record is missing 'adjudication_notes'.")
    elif status == AnnotationStatus.ANNOTATOR_AGREEMENT.value:
        st_a = record.get("annotator_a_status")
        st_b = record.get("annotator_b_status")
        tags_a = record.get("annotator_a_tags")
        tags_b = record.get("annotator_b_tags")
        unc_a = bool(record.get("annotator_a_uncertain", False))
        unc_b = bool(record.get("annotator_b_uncertain", False))
        if st_a != AnnotatorReviewStatus.COMPLETED.value or st_b != AnnotatorReviewStatus.COMPLETED.value:
            errors.append(f"Record '{aid}': ANNOTATOR_AGREEMENT requires both annotators to be COMPLETED.")
        if unc_a or unc_b:
            errors.append(f"Record '{aid}': ANNOTATOR_AGREEMENT cannot have uncertainty flagged.")
        if tags_a is None or tags_b is None or set(tags_a) != set(tags_b):
            errors.append(f"Record '{aid}': ANNOTATOR_AGREEMENT requires matching tag sets between annotators.")
    elif status in (AnnotationStatus.PENDING_HUMAN_REVIEW.value, AnnotationStatus.AWAITING_ADJUDICATION.value):
        if adjudicated is not None:
            errors.append(
                f"Record '{aid}': {status} record has non-null 'adjudicated_tags' ({adjudicated}). "
                "Pending and unadjudicated records must not carry premature adjudicated labels."
            )

    return errors


def validate_annotation_corpus(
    records: List[Dict[str, Any]],
    expected_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Perform corpus-wide integrity, uniqueness, and completeness validation.
    """
    total = len(records)
    seen_ids: Set[str] = set()
    duplicate_ids: List[str] = []
    all_errors: Dict[str, List[str]] = {}

    status_counts = {s.value: 0 for s in AnnotationStatus}

    for idx, r in enumerate(records):
        aid = r.get("achievement_id", f"INDEX_{idx}")
        if aid in seen_ids:
            duplicate_ids.append(aid)
        seen_ids.add(aid)

        rec_errors = validate_annotation_record(r)
        if rec_errors:
            all_errors[aid] = rec_errors

        st = r.get("annotation_status")
        if st in status_counts:
            status_counts[st] += 1

    count_ok = True if expected_count is None else (total == expected_count)

    is_valid = (
        len(duplicate_ids) == 0
        and len(all_errors) == 0
        and count_ok
    )

    return {
        "is_valid": is_valid,
        "total_records": total,
        "unique_ids": len(seen_ids),
        "duplicate_ids": duplicate_ids,
        "expected_count": expected_count,
        "count_matches": count_ok,
        "status_counts": status_counts,
        "error_count": sum(len(errs) for errs in all_errors.values()),
        "record_errors": all_errors,
    }


# ==============================================================================
# DISAGREEMENT DETECTION & ADJUDICATION QUEUE
# ==============================================================================

def detect_disagreements(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze dual-annotator outputs to identify agreement vs disagreement.
    Produces an auditable summary, partial review queue, and pending adjudication queue.
    """
    unreviewed_records: List[str] = []
    partial_reviews: List[Dict[str, Any]] = []
    agreed_records: List[str] = []
    disagreed_records: List[Dict[str, Any]] = []
    resolved_records: List[str] = []

    for r in records:
        aid = r["achievement_id"]
        status = r.get("annotation_status", AnnotationStatus.PENDING_HUMAN_REVIEW.value)

        status_a = r.get("annotator_a_status", AnnotatorReviewStatus.PENDING.value)
        status_b = r.get("annotator_b_status", AnnotatorReviewStatus.PENDING.value)

        tags_a = r.get("annotator_a_tags")
        tags_b = r.get("annotator_b_tags")

        # If already verified
        if status == AnnotationStatus.VERIFIED.value:
            resolved_records.append(aid)
            continue

        # If neither annotator has completed
        if status_a != AnnotatorReviewStatus.COMPLETED.value and status_b != AnnotatorReviewStatus.COMPLETED.value:
            unreviewed_records.append(aid)
            continue

        # If only one annotator has completed (partial review)
        if (status_a == AnnotatorReviewStatus.COMPLETED.value) ^ (status_b == AnnotatorReviewStatus.COMPLETED.value):
            partial_reviews.append({
                "achievement_id": aid,
                "achievement_text": r.get("achievement_text", ""),
                "annotator_a_status": status_a,
                "annotator_b_status": status_b,
                "completed_annotator": "Annotator A" if status_a == AnnotatorReviewStatus.COMPLETED.value else "Annotator B",
                "pending_annotator": "Annotator B" if status_a == AnnotatorReviewStatus.COMPLETED.value else "Annotator A",
            })
            continue

        unc_a = bool(r.get("annotator_a_uncertain", False))
        unc_b = bool(r.get("annotator_b_uncertain", False))

        # Both completed: compare tag sets and uncertainty flags
        set_a = set(tags_a or [])
        set_b = set(tags_b or [])

        if unc_a or unc_b:
            reasons = []
            if unc_a:
                reasons.append("Annotator A flagged uncertainty")
            if unc_b:
                reasons.append("Annotator B flagged uncertainty")
            if set_a != set_b:
                reasons.append("Tag set mismatch")
            disagreed_records.append({
                "achievement_id": aid,
                "achievement_text": r.get("achievement_text", ""),
                "annotator_a_tags": sorted(list(set_a)),
                "annotator_b_tags": sorted(list(set_b)),
                "annotator_a_only": sorted(list(set_a - set_b)),
                "annotator_b_only": sorted(list(set_b - set_a)),
                "intersection": sorted(list(set_a & set_b)),
                "adjudication_reason": "; ".join(reasons),
            })
        elif set_a == set_b:
            agreed_records.append(aid)
        else:
            diff_a = sorted(list(set_a - set_b))
            diff_b = sorted(list(set_b - set_a))
            disagreed_records.append({
                "achievement_id": aid,
                "achievement_text": r.get("achievement_text", ""),
                "annotator_a_tags": sorted(list(set_a)),
                "annotator_b_tags": sorted(list(set_b)),
                "annotator_a_only": diff_a,
                "annotator_b_only": diff_b,
                "intersection": sorted(list(set_a & set_b)),
                "adjudication_reason": "Tag set mismatch between annotators",
            })

    awaiting_reviews_total = len(unreviewed_records) + len(partial_reviews)

    return {
        "total_records": len(records),
        "resolved_verified_count": len(resolved_records),
        "unreviewed_count": len(unreviewed_records),
        "partial_review_count": len(partial_reviews),
        "awaiting_reviews_count": awaiting_reviews_total,
        "agreed_count": len(agreed_records),
        "disagreed_count": len(disagreed_records),
        "awaiting_adjudication_queue": disagreed_records,
        "partial_reviews_queue": partial_reviews,
    }


# ==============================================================================
# INTER-ANNOTATOR AGREEMENT COMPUTATION
# ==============================================================================

def compute_inter_annotator_agreement(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute multi-label inter-annotator agreement across completed dual annotations.
    Strictly reports if dual annotations are insufficient rather than fabricating scores.
    """
    dual_reviewed = []
    for r in records:
        st_a = r.get("annotator_a_status")
        st_b = r.get("annotator_b_status")
        tags_a = r.get("annotator_a_tags")
        tags_b = r.get("annotator_b_tags")

        if (
            st_a == AnnotatorReviewStatus.COMPLETED.value
            and st_b == AnnotatorReviewStatus.COMPLETED.value
            and tags_a is not None
            and tags_b is not None
        ):
            dual_reviewed.append((set(tags_a), set(tags_b)))

    n = len(dual_reviewed)
    if n < 2:
        return {
            "has_sufficient_data": False,
            "completed_dual_annotations": n,
            "message": f"Insufficient completed dual annotations (N={n}). Minimum N=2 required; genuine human reviews pending.",
            "mean_jaccard_similarity": None,
            "exact_agreement_ratio": None,
            "per_tag_kappa": {},
            "macro_kappa": None,
        }

    # 1. Multi-label Jaccard Similarity per record
    jaccards: List[float] = []
    exact_matches = 0
    for set_a, set_b in dual_reviewed:
        if not set_a and not set_b:
            jaccards.append(1.0)
            exact_matches += 1
        else:
            jacc = len(set_a & set_b) / len(set_a | set_b)
            jaccards.append(jacc)
            if set_a == set_b:
                exact_matches += 1

    mean_jaccard = sum(jaccards) / n
    exact_ratio = exact_matches / n

    # 2. Per-Tag Cohen's Kappa
    per_tag_kappa: Dict[str, float] = {}
    valid_kappas: List[float] = []

    for tag in DOMAIN_TAGS:
        # Contingency table:
        # a=1,b=1 | a=1,b=0
        # a=0,b=1 | a=0,b=0
        n11 = sum(1 for set_a, set_b in dual_reviewed if tag in set_a and tag in set_b)
        n10 = sum(1 for set_a, set_b in dual_reviewed if tag in set_a and tag not in set_b)
        n01 = sum(1 for set_a, set_b in dual_reviewed if tag not in set_a and tag in set_b)
        n00 = sum(1 for set_a, set_b in dual_reviewed if tag not in set_a and tag not in set_b)

        po = (n11 + n00) / n
        pe = (((n11 + n10) / n) * ((n11 + n01) / n)) + (((n01 + n00) / n) * ((n10 + n00) / n))

        if abs(1.0 - pe) < 1e-9:
            # Complete agreement on invariant tag
            kappa = 1.0 if po == 1.0 else 0.0
        else:
            kappa = (po - pe) / (1.0 - pe)

        per_tag_kappa[tag] = round(kappa, 4)
        valid_kappas.append(kappa)

    macro_kappa = sum(valid_kappas) / len(valid_kappas) if valid_kappas else 0.0

    return {
        "has_sufficient_data": True,
        "completed_dual_annotations": n,
        "mean_jaccard_similarity": round(mean_jaccard, 4),
        "exact_agreement_ratio": round(exact_ratio, 4),
        "per_tag_kappa": per_tag_kappa,
        "macro_kappa": round(macro_kappa, 4),
    }


# ==============================================================================
# CSV IMPORT / EXPORT FOR HUMAN REVIEW INTERFACE
# ==============================================================================

CSV_HEADERS = [
    "achievement_id",
    "achievement_text",
    "primary_category",
    "split",
    "annotator_a_name",
    "annotator_a_tags",
    "annotator_a_notes",
    "annotator_a_uncertain",
    "annotator_a_status",
    "annotator_b_name",
    "annotator_b_tags",
    "annotator_b_notes",
    "annotator_b_uncertain",
    "annotator_b_status",
    "disagreement_status",
    "adjudicated_tags",
    "adjudication_notes",
    "adjudicator",
    "annotation_status",
]


def export_annotation_task_csv(
    task_records: List[Dict[str, Any]],
    output_csv_path: Union[str, Path],
    blind: bool = True,
) -> Path:
    """
    Export annotation items to a spreadsheet-ready CSV.
    If blind is True, strictly avoids writing any heuristic predictions or model guesses.
    Distinguishes confirmed zero-tag (NONE) from unreviewed/pending (blank).
    """
    out_path = Path(output_csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

        for r in task_records:
            # Format tags for Annotator A: distinguish confirmed zero-tag (NONE) vs pending (empty string)
            st_a = r.get("annotator_a_status") or AnnotatorReviewStatus.PENDING.value
            tags_a_raw = r.get("annotator_a_tags")
            if tags_a_raw is None:
                tags_a = ""
            elif len(tags_a_raw) == 0 and st_a == AnnotatorReviewStatus.COMPLETED.value:
                tags_a = "NONE"
            else:
                tags_a = "|".join(tags_a_raw)

            # Format tags for Annotator B
            st_b = r.get("annotator_b_status") or AnnotatorReviewStatus.PENDING.value
            tags_b_raw = r.get("annotator_b_tags")
            if tags_b_raw is None:
                tags_b = ""
            elif len(tags_b_raw) == 0 and st_b == AnnotatorReviewStatus.COMPLETED.value:
                tags_b = "NONE"
            else:
                tags_b = "|".join(tags_b_raw)

            # Format adjudicated tags
            st_overall = r.get("annotation_status") or AnnotationStatus.PENDING_HUMAN_REVIEW.value
            tags_adj_raw = r.get("adjudicated_tags")
            if tags_adj_raw is None:
                tags_adj = ""
            elif len(tags_adj_raw) == 0 and st_overall == AnnotationStatus.VERIFIED.value:
                tags_adj = "NONE"
            else:
                tags_adj = "|".join(tags_adj_raw)

            row = [
                r.get("achievement_id", ""),
                r.get("achievement_text", ""),
                r.get("primary_category", ""),
                r.get("split", "test"),
                r.get("annotator_a_name") or "",
                tags_a,
                r.get("annotator_a_notes") or "",
                "TRUE" if r.get("annotator_a_uncertain") else "FALSE",
                r.get("annotator_a_status") or AnnotatorReviewStatus.PENDING.value,
                r.get("annotator_b_name") or "",
                tags_b,
                r.get("annotator_b_notes") or "",
                "TRUE" if r.get("annotator_b_uncertain") else "FALSE",
                r.get("annotator_b_status") or AnnotatorReviewStatus.PENDING.value,
                r.get("disagreement_status") or DisagreementStatus.AWAITING_REVIEWS.value,
                tags_adj,
                r.get("adjudication_notes") or "",
                r.get("adjudicator") or "",
                r.get("annotation_status") or AnnotationStatus.PENDING_HUMAN_REVIEW.value,
            ]
            writer.writerow(row)

    return out_path


def safe_import_annotation_csv(
    csv_path: Union[str, Path],
    pristine_backup_path: Optional[Union[str, Path]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Safely import human annotations from review CSV with strict integrity validation:
    - Automatically preserves pristine read-only backup if not already present.
    - Validates record IDs, tags, uncertainty flags, and completion states.
    - Interprets blank cells as pending (None); interprets NONE/[NONE]/ZERO_TAG as explicit zero-tag ([]).
    - Detects duplicate records and conflicting duplicate submissions.
    - Rejects malformed or unknown tags with actionable error messages.
    - Preserves provenance, annotator identity, and timestamps if provided.
    - Returns (records, validation_summary).
    """
    in_path = Path(csv_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Annotation CSV not found at: {in_path}")

    # 1. Preserve pristine backup
    backup_target = Path(pristine_backup_path) if pristine_backup_path else in_path.with_name(f"{in_path.stem}_pristine{in_path.suffix}")
    if not backup_target.exists():
        import shutil
        shutil.copy2(in_path, backup_target)

    records: List[Dict[str, Any]] = []
    seen_submissions: Dict[str, Dict[str, Any]] = {}
    duplicate_ids: List[str] = []
    conflicting_submissions: List[Dict[str, Any]] = []
    validation_errors: Dict[str, List[str]] = {}

    with open(in_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        def parse_tags(val: Optional[str], aid: str, field_name: str) -> Optional[List[str]]:
            if val is None or val.strip() == "":
                return None
            cleaned = val.strip()
            if cleaned.upper() in ("NONE", "[NONE]", "ZERO_TAG", "[]"):
                return []
            tags = [t.strip() for t in cleaned.split("|") if t.strip()]
            for t in tags:
                if t not in DOMAIN_TAGS:
                    err = f"Record '{aid}': Malformed or unknown domain tag '{t}' in {field_name}. Allowed tags: {sorted(list(DOMAIN_TAGS))}"
                    validation_errors.setdefault(aid, []).append(err)
            return tags

        def parse_bool(val: Optional[str]) -> bool:
            if val is None:
                return False
            return val.strip().upper() in ("TRUE", "1", "YES", "Y")

        for row_idx, row in enumerate(reader, 1):
            aid = row.get("achievement_id", "").strip()
            if not aid:
                validation_errors.setdefault(f"ROW_{row_idx}", []).append("Missing 'achievement_id'.")
                continue

            tags_a = parse_tags(row.get("annotator_a_tags"), aid, "annotator_a_tags")
            tags_b = parse_tags(row.get("annotator_b_tags"), aid, "annotator_b_tags")
            tags_adj = parse_tags(row.get("adjudicated_tags"), aid, "adjudicated_tags")

            rec = {
                "achievement_id": aid,
                "achievement_text": row.get("achievement_text", "").strip(),
                "primary_category": row.get("primary_category", "").strip(),
                "split": row.get("split", "test").strip(),
                "annotator_a_name": row.get("annotator_a_name") or None,
                "annotator_a_tags": tags_a,
                "annotator_a_notes": row.get("annotator_a_notes") or None,
                "annotator_a_uncertain": parse_bool(row.get("annotator_a_uncertain")),
                "annotator_a_status": row.get("annotator_a_status", AnnotatorReviewStatus.PENDING.value),
                "annotator_b_name": row.get("annotator_b_name") or None,
                "annotator_b_tags": tags_b,
                "annotator_b_notes": row.get("annotator_b_notes") or None,
                "annotator_b_uncertain": parse_bool(row.get("annotator_b_uncertain")),
                "annotator_b_status": row.get("annotator_b_status", AnnotatorReviewStatus.PENDING.value),
                "disagreement_status": row.get("disagreement_status", DisagreementStatus.AWAITING_REVIEWS.value),
                "adjudicated_tags": tags_adj,
                "adjudication_notes": row.get("adjudication_notes") or None,
                "adjudicator": row.get("adjudicator") or None,
                "annotation_status": row.get("annotation_status", AnnotationStatus.PENDING_HUMAN_REVIEW.value),
                # Preserve timestamps if provided in CSV
                "annotator_a_timestamp": row.get("annotator_a_timestamp"),
                "annotator_b_timestamp": row.get("annotator_b_timestamp"),
                "adjudication_timestamp": row.get("adjudication_timestamp"),
            }

            # If not explicitly verified or rejected by an adjudicator, triage workflow state
            if rec.get("annotation_status") not in (AnnotationStatus.VERIFIED.value, AnnotationStatus.REJECTED.value):
                rec = triage_annotation_record(rec)

            # Check duplicate and conflicting submissions
            if aid in seen_submissions:
                duplicate_ids.append(aid)
                prev = seen_submissions[aid]
                if (
                    prev.get("annotator_a_tags") != rec["annotator_a_tags"]
                    or prev.get("annotator_b_tags") != rec["annotator_b_tags"]
                    or prev.get("adjudicated_tags") != rec["adjudicated_tags"]
                ):
                    conflicting_submissions.append({
                        "achievement_id": aid,
                        "submission_1": prev,
                        "submission_2": rec,
                    })
                    validation_errors.setdefault(aid, []).append(
                        f"Conflicting duplicate submissions detected for achievement_id '{aid}'."
                    )
            else:
                seen_submissions[aid] = rec
                records.append(rec)

    # Validate each imported record
    for r in records:
        errs = validate_annotation_record(r)
        if errs:
            validation_errors.setdefault(r["achievement_id"], []).extend(errs)

    is_valid = len(conflicting_submissions) == 0 and len(validation_errors) == 0

    validation_summary = {
        "is_valid": is_valid,
        "total_records": len(records),
        "unique_ids": len(seen_submissions),
        "duplicate_ids": duplicate_ids,
        "conflicting_submissions_count": len(conflicting_submissions),
        "conflicting_submissions": conflicting_submissions,
        "error_count": sum(len(errs) for errs in validation_errors.values()),
        "record_errors": validation_errors,
        "pristine_backup_path": str(backup_target),
    }

    return records, validation_summary


def import_annotation_task_csv(csv_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    Import human annotations from an edited review CSV.
    Parses pipe-separated tags, uncertainty flags, and confirmed zero-tag tokens (NONE).
    Uses safe_import_annotation_csv internally.
    """
    records, summary = safe_import_annotation_csv(csv_path)
    return records


def triage_annotation_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically triage an annotation record into its appropriate workflow status:
    - VERIFIED or REJECTED: preserved (adjudicated ground truth).
    - Both completed, matching tags, no uncertainty:
        -> disagreement_status = AGREED
        -> annotation_status = ANNOTATOR_AGREEMENT
    - Both completed, differing tags or either flagged uncertain:
        -> disagreement_status = DISAGREED
        -> annotation_status = AWAITING_ADJUDICATION
    - Incomplete reviews (partial or none):
        -> disagreement_status = AWAITING_REVIEWS
        -> annotation_status = PENDING_HUMAN_REVIEW
    """
    updated = dict(record)
    current_status = updated.get("annotation_status", AnnotationStatus.PENDING_HUMAN_REVIEW.value)
    if current_status in (AnnotationStatus.VERIFIED.value, AnnotationStatus.REJECTED.value):
        return updated

    st_a = updated.get("annotator_a_status", AnnotatorReviewStatus.PENDING.value)
    st_b = updated.get("annotator_b_status", AnnotatorReviewStatus.PENDING.value)
    tags_a = updated.get("annotator_a_tags")
    tags_b = updated.get("annotator_b_tags")
    unc_a = bool(updated.get("annotator_a_uncertain", False))
    unc_b = bool(updated.get("annotator_b_uncertain", False))

    if st_a == AnnotatorReviewStatus.COMPLETED.value and st_b == AnnotatorReviewStatus.COMPLETED.value:
        set_a = set(tags_a or [])
        set_b = set(tags_b or [])
        if unc_a or unc_b or set_a != set_b:
            updated["disagreement_status"] = DisagreementStatus.DISAGREED.value
            updated["annotation_status"] = AnnotationStatus.AWAITING_ADJUDICATION.value
        else:
            updated["disagreement_status"] = DisagreementStatus.AGREED.value
            updated["annotation_status"] = AnnotationStatus.ANNOTATOR_AGREEMENT.value
    else:
        updated["disagreement_status"] = DisagreementStatus.AWAITING_REVIEWS.value
        updated["annotation_status"] = AnnotationStatus.PENDING_HUMAN_REVIEW.value

    return updated


def verify_consensus_record(
    record: Dict[str, Any],
    adjudicator: str,
    notes: str = "Verified consensus from matching independent dual annotations.",
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Promote an agreed dual-annotation record (ANNOTATOR_AGREEMENT) to VERIFIED ground truth.
    Requires that both annotators have completed matching reviews without uncertainty flags.
    """
    st_a = record.get("annotator_a_status")
    st_b = record.get("annotator_b_status")
    tags_a = record.get("annotator_a_tags")
    tags_b = record.get("annotator_b_tags")
    unc_a = bool(record.get("annotator_a_uncertain", False))
    unc_b = bool(record.get("annotator_b_uncertain", False))

    if st_a != AnnotatorReviewStatus.COMPLETED.value or st_b != AnnotatorReviewStatus.COMPLETED.value:
        raise ValueError("Cannot verify consensus on incomplete dual annotations.")
    if unc_a or unc_b:
        raise ValueError("Cannot auto-verify consensus when uncertainty flag is raised. Record must undergo full adjudication.")
    if tags_a is None or tags_b is None or set(tags_a) != set(tags_b):
        raise ValueError(f"Cannot verify consensus: tags mismatch between annotators ({tags_a} vs {tags_b}).")

    return adjudicate_record(
        record=record,
        adjudicated_tags=list(set(tags_a)),
        adjudicator=adjudicator,
        notes=notes,
        timestamp=timestamp,
    )


def adjudicate_record(
    record: Dict[str, Any],
    adjudicated_tags: List[str],
    adjudicator: str,
    notes: str,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Safely adjudicate a disputed or reviewed record, promoting it to VERIFIED status.
    """
    for t in adjudicated_tags:
        if t not in DOMAIN_TAGS:
            raise ValueError(f"Invalid domain tag '{t}' in adjudication.")

    if not adjudicator or not adjudicator.strip():
        raise ValueError("Adjudicator identifier cannot be empty.")
    if not notes or not notes.strip():
        raise ValueError("Adjudication notes cannot be empty.")

    updated = dict(record)
    updated["adjudicated_tags"] = sorted(list(set(adjudicated_tags)))
    updated["adjudicator"] = adjudicator.strip()
    updated["adjudication_notes"] = notes.strip()
    updated["annotation_status"] = AnnotationStatus.VERIFIED.value
    updated["disagreement_status"] = DisagreementStatus.RESOLVED.value
    if timestamp:
        updated["adjudication_timestamp"] = timestamp
    elif "adjudication_timestamp" not in updated or not updated["adjudication_timestamp"]:
        updated["adjudication_timestamp"] = datetime.now(timezone.utc).isoformat()

    return updated
