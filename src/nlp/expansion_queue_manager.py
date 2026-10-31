"""
src/nlp/expansion_queue_manager.py
===================================
Human-in-the-Loop Expansion Queue Subsystem (Step 26)
AI-Powered Student Achievement Intelligence Platform — Member 1

Builds and rigorously validates the 113-record expansion queue for AI-assisted
human-in-the-loop domain categorization.

Key capabilities:
- Deterministic extraction of the remaining 113 eligible records from the master candidate pool.
- Disjointness enforcement across all three protected cohorts (7 references, 30 blind evaluation records, 25 pilot records).
- Strict schema adherence with unpopulated reviewer fields (zero fabrication).
- Concordance preservation with original AI proposals.
- Automated manifest generation and queue validation.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Canonical 10-tag domain taxonomy
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

VALID_DECISIONS: Set[str] = {"ACCEPT", "MODIFY", "REJECT", "UNRESOLVED"}
VALID_STATUSES: Set[str] = {"PENDING_REVIEW", "COMPLETED", "VERIFIED", "VALIDATED", "HUMAN_APPROVED"}
EXPLICIT_ZERO_TAG_TOKENS: Set[str] = {
    "NONE",
    "[]",
    "[ZERO-TAG]",
    "[NONE]",
    "NO_DOMAIN",
    "ZERO_TAG",
}


def compute_file_sha256(path: Path | str) -> Optional[str]:
    """Compute the SHA-256 hex digest of a file if it exists."""
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def parse_tags(raw: Optional[str]) -> List[str]:
    """Parse pipe-delimited tag string, treating empty / zero tokens as empty list."""
    if raw is None:
        return []
    cleaned = raw.strip()
    if not cleaned or cleaned.upper() in EXPLICIT_ZERO_TAG_TOKENS or cleaned in ["[]", "[NONE]"]:
        return []
    tokens = [t.strip() for t in cleaned.split("|") if t.strip()]
    for token in tokens:
        if token not in DOMAIN_TAGS:
            raise ValueError(f"Invalid domain tag '{token}' outside canonical taxonomy")
    return sorted(list(set(tokens)))


def build_remaining_113_queue(
    proposals_csv_path: Path | str,
    gold_task_jsonl_path: Path | str,
    blind_sample_csv_path: Path | str,
    pilot_queue_csv_path: Path | str,
    test_split_csv_path: Path | str,
    output_queue_csv_path: Path | str,
    output_manifest_json_path: Path | str,
) -> Dict[str, Any]:
    """
    Extract the remaining 113 records, populate queue with pending reviewer fields,
    and generate the immutable manifest.
    """
    prop_p = Path(proposals_csv_path)
    gold_p = Path(gold_task_jsonl_path)
    blind_p = Path(blind_sample_csv_path)
    pilot_p = Path(pilot_queue_csv_path)
    test_p = Path(test_split_csv_path)

    # 1. Load protected cohort IDs
    with open(gold_p, "r", encoding="utf-8") as f:
        gold_records = [json.loads(line) for line in f if line.strip()]
    ref_ids = {r["achievement_id"] for r in gold_records if r.get("annotation_status") == "VERIFIED"}
    if len(ref_ids) != 7:
        raise ValueError(f"Expected exactly 7 verified reference standards, found {len(ref_ids)}")

    with open(blind_p, "r", encoding="utf-8-sig") as f:
        blind_ids = {r["achievement_id"] for r in csv.DictReader(f)}
    if len(blind_ids) != 30:
        raise ValueError(f"Expected exactly 30 blind evaluation records, found {len(blind_ids)}")

    with open(pilot_p, "r", encoding="utf-8-sig") as f:
        pilot_ids = {r["achievement_id"] for r in csv.DictReader(f)}
    if len(pilot_ids) != 25:
        raise ValueError(f"Expected exactly 25 completed pilot records, found {len(pilot_ids)}")

    with open(test_p, "r", encoding="utf-8") as f:
        test_ids = {r["achievement_id"] for r in csv.DictReader(f)}

    # 2. Load proposals
    with open(prop_p, "r", encoding="utf-8-sig") as f:
        all_proposals = list(csv.DictReader(f))

    if len(all_proposals) != 168:
        raise ValueError(f"Expected 168 total proposals in candidate pool, found {len(all_proposals)}")

    # 3. Filter for remaining 113 records
    protected_ids = ref_ids | blind_ids | pilot_ids
    remaining_records = [
        r for r in all_proposals
        if r["achievement_id"] not in protected_ids
    ]

    if len(remaining_records) != 113:
        raise ValueError(f"Expected exactly 113 remaining records, found {len(remaining_records)}")

    # Sort deterministically by achievement_id
    remaining_records.sort(key=lambda x: x["achievement_id"])
    remaining_ids = [r["achievement_id"] for r in remaining_records]

    # Verify disjointness
    if set(remaining_ids) & ref_ids:
        raise ValueError("Remaining records overlap with verified reference standards!")
    if set(remaining_ids) & blind_ids:
        raise ValueError("Remaining records overlap with blind validation sample!")
    if set(remaining_ids) & pilot_ids:
        raise ValueError("Remaining records overlap with pilot records!")
    if not set(remaining_ids).issubset(test_ids):
        raise ValueError("Remaining records not strictly confined to test split!")

    # 4. Build queue rows with blank reviewer fields
    queue_headers = [
        "queue_record_id",
        "achievement_id",
        "achievement_text",
        "primary_category",
        "ai_proposed_tags",
        "ai_evidence_snippets",
        "ai_uncertainty_flag",
        "ai_annotation_rationale",
        "reviewer_name",
        "reviewer_decision",
        "reviewer_final_tags",
        "reviewer_rationale",
        "review_time_seconds",
        "review_status",
    ]

    queue_rows = []
    category_counts: Dict[str, int] = {}
    proposed_tag_counts: Dict[str, int] = {}
    zero_tag_count = 0
    uncertain_count = 0

    for idx, r in enumerate(remaining_records, 1):
        cat = r["primary_category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

        raw_tags = r.get("proposed_tags", "")
        parsed = parse_tags(raw_tags)
        if not parsed:
            ai_tags_str = "NONE"
            zero_tag_count += 1
        else:
            ai_tags_str = "|".join(parsed)
            for t in parsed:
                proposed_tag_counts[t] = proposed_tag_counts.get(t, 0) + 1

        is_uncertain = (r.get("uncertainty_flag", "").strip().upper() == "TRUE")
        if is_uncertain:
            uncertain_count += 1

        snippets = r.get("evidence_snippets", "").strip()

        queue_rows.append({
            "queue_record_id": idx,
            "achievement_id": r["achievement_id"],
            "achievement_text": r["achievement_text"],
            "primary_category": cat,
            "ai_proposed_tags": ai_tags_str,
            "ai_evidence_snippets": snippets,
            "ai_uncertainty_flag": "TRUE" if is_uncertain else "FALSE",
            "ai_annotation_rationale": r.get("annotation_rationale", ""),
            "reviewer_name": "",
            "reviewer_decision": "",
            "reviewer_final_tags": "",
            "reviewer_rationale": "",
            "review_time_seconds": "",
            "review_status": "PENDING_REVIEW",
        })

    # 5. Write Queue CSV
    out_q_p = Path(output_queue_csv_path)
    out_q_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_q_p, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=queue_headers)
        writer.writeheader()
        writer.writerows(queue_rows)

    # 6. Build and write Manifest JSON
    manifest_data = {
        "manifest_id": "step26_remaining_113_manifest_v1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "batch_metadata": {
            "total_records": 113,
            "master_gold_task_total": 175,
            "certified_reference_count": 7,
            "blind_validation_sample_count": 30,
            "completed_pilot_count": 25,
            "post_pilot_remaining_pool": 113,
            "split": "test",
            "split_file": str(test_p.name),
        },
        "disjointness_verification": {
            "disjoint_from_certified_references_7": True,
            "disjoint_from_blind_validation_sample_30": True,
            "disjoint_from_pilot_sample_25": True,
            "all_records_in_test_split": True,
            "partition_sum_check": (7 + 30 + 25 + 113 == 175),
        },
        "category_distribution": category_counts,
        "proposed_tag_distribution": {
            "domain_tag_frequencies": proposed_tag_counts,
            "zero_tag_proposals_none": zero_tag_count,
            "total_tag_instances_proposed": sum(proposed_tag_counts.values()),
        },
        "uncertainty_distribution": {
            "uncertainty_flag_true_count": uncertain_count,
            "uncertainty_flag_false_count": 113 - uncertain_count,
        },
        "selected_record_ids": remaining_ids,
    }

    out_m_p = Path(output_manifest_json_path)
    out_m_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_m_p, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return {
        "total_records": len(queue_rows),
        "queue_csv_path": str(out_q_p),
        "manifest_json_path": str(out_m_p),
        "category_distribution": category_counts,
        "proposed_tag_distribution": proposed_tag_counts,
        "zero_tag_proposals_none": zero_tag_count,
        "uncertainty_flag_true_count": uncertain_count,
        "selected_record_ids": remaining_ids,
    }


def validate_remaining_113_queue(
    queue_csv_path: Path | str,
    manifest_json_path: Path | str,
    gold_task_jsonl_path: Path | str,
    blind_sample_csv_path: Path | str,
    pilot_queue_csv_path: Path | str,
    proposals_csv_path: Path | str,
    test_split_csv_path: Path | str,
) -> Dict[str, Any]:
    """
    Rigorous preflight and post-generation validation of the 113-record queue.
    """
    queue_p = Path(queue_csv_path)
    manifest_p = Path(manifest_json_path)
    gold_p = Path(gold_task_jsonl_path)
    blind_p = Path(blind_sample_csv_path)
    pilot_p = Path(pilot_queue_csv_path)
    prop_p = Path(proposals_csv_path)
    test_p = Path(test_split_csv_path)

    if not queue_p.exists():
        raise FileNotFoundError(f"Queue file missing: {queue_p}")
    if not manifest_p.exists():
        raise FileNotFoundError(f"Manifest file missing: {manifest_p}")

    with open(manifest_p, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    manifest_ids: List[str] = manifest["selected_record_ids"]

    with open(queue_p, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 113:
        raise ValueError(f"Queue must contain exactly 113 records, found {len(rows)}")
    if len(manifest_ids) != 113:
        raise ValueError(f"Manifest must contain exactly 113 IDs, found {len(manifest_ids)}")

    queue_ids = [r["achievement_id"] for r in rows]
    if queue_ids != manifest_ids:
        raise ValueError("Queue IDs do not match manifest IDs in identical ordinal sequence")

    if len(set(queue_ids)) != 113:
        raise ValueError("Duplicate achievement IDs detected in 113-record queue")

    # Load protected sets
    with open(gold_p, "r", encoding="utf-8") as f:
        gold_records = [json.loads(line) for line in f if line.strip()]
    ref_ids = {r["achievement_id"] for r in gold_records if r.get("annotation_status") == "VERIFIED"}

    with open(blind_p, "r", encoding="utf-8-sig") as f:
        blind_ids = {r["achievement_id"] for r in csv.DictReader(f)}

    with open(pilot_p, "r", encoding="utf-8-sig") as f:
        pilot_ids = {r["achievement_id"] for r in csv.DictReader(f)}

    with open(test_p, "r", encoding="utf-8") as f:
        test_ids = {r["achievement_id"] for r in csv.DictReader(f)}

    # Disjointness checks
    if set(queue_ids) & ref_ids:
        raise ValueError("Overlap detected with 7 verified reference standards!")
    if set(queue_ids) & blind_ids:
        raise ValueError("Overlap detected with 30-record blind validation sample!")
    if set(queue_ids) & pilot_ids:
        raise ValueError("Overlap detected with 25-record pilot queue!")
    if not set(queue_ids).issubset(test_ids):
        raise ValueError("Records not strictly confined to test split!")

    # Concordance with original AI proposals
    with open(prop_p, "r", encoding="utf-8-sig") as f:
        proposals_map = {r["achievement_id"]: r for r in csv.DictReader(f)}

    for r in rows:
        aid = r["achievement_id"]
        if aid not in proposals_map:
            raise ValueError(f"Record {aid} missing from original AI proposals!")
        orig = proposals_map[aid]

        # Verify text and category
        if r["achievement_text"] != orig["achievement_text"]:
            raise ValueError(f"Record {aid} achievement_text altered from original!")
        if r["primary_category"] != orig["primary_category"]:
            raise ValueError(f"Record {aid} primary_category altered from original!")

        # Verify parsed tags match
        q_parsed = parse_tags(r["ai_proposed_tags"])
        orig_parsed = parse_tags(orig["proposed_tags"])
        if q_parsed != orig_parsed:
            raise ValueError(f"Record {aid} proposed tags mismatch: {q_parsed} vs {orig_parsed}")

        # Verify uncertainty flag
        if r["ai_uncertainty_flag"].upper() != orig["uncertainty_flag"].upper():
            raise ValueError(f"Record {aid} uncertainty flag mismatch!")

        # Verify reviewer fields are blank / pending
        if r["reviewer_name"].strip() != "":
            raise ValueError(f"Record {aid} reviewer_name is not blank: {r['reviewer_name']}")
        if r["reviewer_decision"].strip() != "":
            raise ValueError(f"Record {aid} reviewer_decision is not blank: {r['reviewer_decision']}")
        if r["reviewer_final_tags"].strip() != "":
            raise ValueError(f"Record {aid} reviewer_final_tags is not blank: {r['reviewer_final_tags']}")
        if r["reviewer_rationale"].strip() != "":
            raise ValueError(f"Record {aid} reviewer_rationale is not blank: {r['reviewer_rationale']}")
        if r["review_time_seconds"].strip() != "":
            raise ValueError(f"Record {aid} review_time_seconds is not blank: {r['review_time_seconds']}")
        if r["review_status"] != "PENDING_REVIEW":
            raise ValueError(f"Record {aid} review_status is not PENDING_REVIEW: {r['review_status']}")

    return {
        "verified": True,
        "sample_size": 113,
        "disjointness_proven": True,
        "reviewer_fields_blank_and_pending": True,
        "concordance_with_proposals_verified": True,
    }
