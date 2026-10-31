"""
src/nlp/duplicate_detection.py
==============================
Advanced Duplicate Detection & Structured Verification Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1

This module provides a multi-stage duplicate verification pipeline combining:
1. Dense Semantic Candidate Retrieval (Sentence Transformers cosine similarity)
2. Structured Evidence Comparison (Student ID, Event, Rank, Year, Certificate, Category)
3. Transparent Decision Engine (DUPLICATE, DISTINCT, REVIEW_REQUIRED)
4. Comprehensive Evidence Auditing & Explanation Generation

Design Principles:
- Anti-Leakage & Non-Destructive: Original records are never mutated or merged destructively.
- Explicit Missing Value Handling: Missing values (NaN, None, empty) are never treated as matches.
- Contradiction-First Resolution: Semantic proximity cannot override factual contradictions.
- Deterministic & Explainable: Every decision includes full rationale and evidence logs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


class DuplicateDecision(str, Enum):
    """Possible outcomes of the duplicate verification pipeline."""
    DUPLICATE = "DUPLICATE"
    DISTINCT = "DISTINCT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class FieldStatus(str, Enum):
    """Status of an individual field comparison between two records."""
    MATCH = "MATCH"
    CONFLICT = "CONFLICT"
    MISSING_ONE = "MISSING_ONE"
    MISSING_BOTH = "MISSING_BOTH"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class FieldComparison:
    """Detailed result of comparing a single structured field."""
    field_name: str
    status: FieldStatus
    value_1: Any
    value_2: Any
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "status": self.status.value,
            "value_1": self.value_1,
            "value_2": self.value_2,
            "note": self.note,
        }


@dataclass
class DuplicateVerificationResult:
    """Comprehensive output of the duplicate verification process for a pair."""
    decision: DuplicateDecision
    confidence: float
    cosine_similarity: Optional[float]
    passed_candidate_retrieval: bool
    field_comparisons: Dict[str, FieldComparison] = field(default_factory=dict)
    matching_evidence: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    explanation: str = ""
    pair_id: Optional[str] = None
    record_id_1: Optional[str] = None
    record_id_2: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "record_id_1": self.record_id_1,
            "record_id_2": self.record_id_2,
            "decision": self.decision.value,
            "confidence": round(self.confidence, 4),
            "cosine_similarity": round(self.cosine_similarity, 4) if self.cosine_similarity is not None else None,
            "passed_candidate_retrieval": self.passed_candidate_retrieval,
            "matching_evidence": self.matching_evidence,
            "contradictions": self.contradictions,
            "missing_evidence": self.missing_evidence,
            "explanation": self.explanation,
            "field_comparisons": {k: v.to_dict() for k, v in self.field_comparisons.items()},
        }


def normalize_field_value(value: Any) -> Optional[str]:
    """
    Standardize a field value for robust comparison.
    Converts None, NaN, empty strings to None. Trims whitespace and normalizes case.
    """
    if value is None:
        return None
    if isinstance(value, float) and (np.isnan(value) or np.isneginf(value) or np.isposinf(value)):
        return None
    if pd.isna(value):
        return None
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ("nan", "none", "null", "n/a", "undefined"):
        return None
    # Collapse multiple whitespaces
    val_str = re.sub(r"\s+", " ", val_str)
    return val_str.lower()


def extract_year(date_or_year: Any) -> Optional[str]:
    """Extract a 4-digit academic or calendar year from a string or date object."""
    norm = normalize_field_value(date_or_year)
    if not norm:
        return None
    match = re.search(r"\b(20\d{2}|19\d{2})\b", norm)
    if match:
        return match.group(1)
    return None


def extract_rank_standard(rank_str: Any) -> Optional[str]:
    """
    Map diverse surface formulations of competitive placement into standardized buckets.
    E.g., '1st', 'first place', 'gold medal', 'winner' -> 'rank_1'
    """
    norm = normalize_field_value(rank_str)
    if not norm:
        return None

    # First place / Gold / Winner / Champion
    if re.search(r"\b(1st|first|gold|winner|champion|championship|top\s*1)\b", norm):
        return "RANK_1_WINNER"
    # Second place / Silver / Runner up
    if re.search(r"\b(2nd|second|silver|runner\s*-?\s*up|1st\s*runner\s*-?\s*up)\b", norm):
        return "RANK_2_RUNNER_UP"
    # Third place / Bronze / Second runner up
    if re.search(r"\b(3rd|third|bronze|2nd\s*runner\s*-?\s*up)\b", norm):
        return "RANK_3_BRONZE"
    # Finalist / Semi-finalist
    if re.search(r"\b(finalist|semi\s*-?\s*finalist)\b", norm):
        return "RANK_FINALIST"
    # Top 10 / Top 5 / Merit
    if re.search(r"\b(top\s*5|top\s*10|merit|honorable|mention)\b", norm):
        return "RANK_MERIT"
    # Participant / Attendee
    if re.search(r"\b(participant|participated|attendee|completed)\b", norm):
        return "RANK_PARTICIPANT"
    
    return norm


def compare_field(
    field_name: str,
    val1: Any,
    val2: Any,
    is_rank: bool = False,
    is_year: bool = False,
) -> FieldComparison:
    """
    Compare two values of a structured field with strict missing-value handling.
    Rule: Missing values are NEVER treated as a match.
    """
    if is_year:
        norm1 = extract_year(val1)
        norm2 = extract_year(val2)
    elif is_rank:
        norm1 = extract_rank_standard(val1)
        norm2 = extract_rank_standard(val2)
    else:
        norm1 = normalize_field_value(val1)
        norm2 = normalize_field_value(val2)

    if norm1 is None and norm2 is None:
        return FieldComparison(
            field_name=field_name,
            status=FieldStatus.MISSING_BOTH,
            value_1=val1,
            value_2=val2,
            note=f"Field '{field_name}' is missing in both records.",
        )
    if norm1 is None or norm2 is None:
        missing_side = "record 1" if norm1 is None else "record 2"
        present_val = norm2 if norm1 is None else norm1
        return FieldComparison(
            field_name=field_name,
            status=FieldStatus.MISSING_ONE,
            value_1=val1,
            value_2=val2,
            note=f"Field '{field_name}' is missing in {missing_side} (present value: '{present_val}'). Cannot assume match.",
        )

    # Both values present
    if norm1 == norm2:
        return FieldComparison(
            field_name=field_name,
            status=FieldStatus.MATCH,
            value_1=val1,
            value_2=val2,
            note=f"Field '{field_name}' exactly matches: '{norm1}'.",
        )
    
    # Check for substring match in organizational or event names (e.g. 'ACM Student Chapter' in 'ACM Student Chapter IIT')
    if field_name in ("event_name", "organization") and (norm1 in norm2 or norm2 in norm1):
        return FieldComparison(
            field_name=field_name,
            status=FieldStatus.MATCH,
            value_1=val1,
            value_2=val2,
            note=f"Field '{field_name}' has high substring alignment: '{norm1}' ~ '{norm2}'.",
        )

    return FieldComparison(
        field_name=field_name,
        status=FieldStatus.CONFLICT,
        value_1=val1,
        value_2=val2,
        note=f"Field '{field_name}' conflicts: '{norm1}' vs '{norm2}'.",
    )


def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """
    Extract structured entities embedded in freeform achievement text.
    Handles dates, ranks, competition keywords, and certificate identifiers.
    """
    extracted: Dict[str, Any] = {}
    if not isinstance(text, str) or not text.strip():
        return extracted

    # Extract 4-digit year
    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", text)
    if year_match:
        extracted["year"] = year_match.group(1)

    # Extract rank mentions
    rank_patterns = [
        (r"\b(1st\s*place|first\s*place|winner|gold\s*medal|champion)\b", "RANK_1_WINNER"),
        (r"\b(2nd\s*place|second\s*place|silver\s*medal|1st\s*runner\s*-?\s*up|runner\s*-?\s*up)\b", "RANK_2_RUNNER_UP"),
        (r"\b(3rd\s*place|third\s*place|bronze\s*medal|2nd\s*runner\s*-?\s*up)\b", "RANK_3_BRONZE"),
        (r"\b(finalist|semi\s*-?\s*finalist)\b", "RANK_FINALIST"),
        (r"\b(president|vice\s*president|secretary|treasurer|lead)\b", "ROLE_LEADERSHIP"),
    ]
    for pattern, rank_label in rank_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            extracted["rank"] = rank_label
            break

    # Extract certificate / credential identifiers (e.g. MET-508926, AWS-12345, #2021553873)
    cert_match = re.search(r"(?:credential\s*id:?\s*|license\s*(?:no\.?|id|#)?:?\s*)?([A-Z]{2,5}-\d{4,8}|#\d{6,12})\b", text, re.IGNORECASE)
    if cert_match:
        extracted["certificate_id"] = cert_match.group(1).upper()

    return extracted


def verify_duplicate_candidate(
    record_1: Union[Dict[str, Any], pd.Series],
    record_2: Union[Dict[str, Any], pd.Series],
    cosine_similarity: Optional[float] = None,
    retrieval_threshold: float = 0.50,
    high_similarity_threshold: float = 0.70,
    pair_id: Optional[str] = None,
) -> DuplicateVerificationResult:
    """
    Execute structured verification on a candidate pair of achievement records.

    Pipeline:
    1. Input Validation & Preparation
    2. Candidate Retrieval Verification (Cosine Similarity Guard)
    3. Structured Field Comparisons (Student ID, Rank, Year, Event, Organization, Category, Certificate)
    4. Contradiction Detection
    5. Rule-Based Synthesis & Decision (DUPLICATE, DISTINCT, REVIEW_REQUIRED)
    """
    if not isinstance(record_1, (dict, pd.Series)) or not isinstance(record_2, (dict, pd.Series)):
        raise TypeError(f"Records must be dict or pd.Series, got {type(record_1)} and {type(record_2)}")

    r1 = dict(record_1)
    r2 = dict(record_2)

    # Identifiers
    id_1 = str(r1.get("achievement_id", "REC1"))
    id_2 = str(r2.get("achievement_id", "REC2"))
    text_1 = str(r1.get("achievement_text", "")).strip()
    text_2 = str(r2.get("achievement_text", "")).strip()

    # Extract auxiliary structured info from text if metadata is sparse
    t_entities_1 = extract_entities_from_text(text_1)
    t_entities_2 = extract_entities_from_text(text_2)

    # Fallback to text entities if metadata field is null
    rank_1 = r1.get("rank") if pd.notna(r1.get("rank")) else t_entities_1.get("rank")
    rank_2 = r2.get("rank") if pd.notna(r2.get("rank")) else t_entities_2.get("rank")
    year_1 = r1.get("achievement_date") if pd.notna(r1.get("achievement_date")) else t_entities_1.get("year")
    year_2 = r2.get("achievement_date") if pd.notna(r2.get("achievement_date")) else t_entities_2.get("year")
    cert_1 = r1.get("evidence_id") if pd.notna(r1.get("evidence_id")) else t_entities_1.get("certificate_id")
    cert_2 = r2.get("evidence_id") if pd.notna(r2.get("evidence_id")) else t_entities_2.get("certificate_id")

    comparisons: Dict[str, FieldComparison] = {}
    contradictions: List[str] = []
    matching_evidence: List[str] = []
    missing_evidence: List[str] = []

    # 1. Compare Student Identity (Crucial boundary guard)
    student_comp = compare_field("student_id", r1.get("student_id"), r2.get("student_id"))
    comparisons["student_id"] = student_comp
    if student_comp.status == FieldStatus.CONFLICT:
        contradictions.append(f"Student identity conflict: '{student_comp.value_1}' != '{student_comp.value_2}'. Distinct students.")
    elif student_comp.status == FieldStatus.MATCH:
        matching_evidence.append(f"Student identity matches: '{student_comp.value_1}'.")
    else:
        missing_evidence.append("Student identity not available in records.")

    # 2. Compare Placement Rank
    rank_comp = compare_field("rank", rank_1, rank_2, is_rank=True)
    comparisons["rank"] = rank_comp
    if rank_comp.status == FieldStatus.CONFLICT:
        contradictions.append(f"Placement rank conflict: '{rank_comp.value_1}' vs '{rank_comp.value_2}'.")
    elif rank_comp.status == FieldStatus.MATCH:
        matching_evidence.append(f"Placement rank matches: '{rank_comp.value_1}'.")
    else:
        missing_evidence.append("Placement rank not available in one or both records.")

    # 3. Compare Academic / Achievement Year
    year_comp = compare_field("year", year_1, year_2, is_year=True)
    comparisons["year"] = year_comp
    if year_comp.status == FieldStatus.CONFLICT:
        contradictions.append(f"Achievement year conflict: '{year_comp.value_1}' vs '{year_comp.value_2}'. Distinct instances across years.")
    elif year_comp.status == FieldStatus.MATCH:
        matching_evidence.append(f"Achievement year matches: '{year_comp.value_1}'.")
    else:
        missing_evidence.append("Academic year not fully specified in records.")

    # 4. Compare Event / Competition Name
    event_comp = compare_field("event_name", r1.get("event_name"), r2.get("event_name"))
    comparisons["event_name"] = event_comp
    if event_comp.status == FieldStatus.CONFLICT:
        contradictions.append(f"Event name conflict: '{event_comp.value_1}' vs '{event_comp.value_2}'.")
    elif event_comp.status == FieldStatus.MATCH:
        matching_evidence.append(f"Event name matches: '{event_comp.value_1}'.")
    else:
        missing_evidence.append("Event name is missing in one or both records.")

    # 5. Compare Organization
    org_comp = compare_field("organization", r1.get("organization"), r2.get("organization"))
    comparisons["organization"] = org_comp
    if org_comp.status == FieldStatus.CONFLICT:
        contradictions.append(f"Issuing organization conflict: '{org_comp.value_1}' vs '{org_comp.value_2}'.")
    elif org_comp.status == FieldStatus.MATCH:
        matching_evidence.append(f"Issuing organization matches: '{org_comp.value_1}'.")
    else:
        missing_evidence.append("Issuing organization is missing in one or both records.")

    # 6. Compare Category
    cat_comp = compare_field("category", r1.get("category"), r2.get("category"))
    comparisons["category"] = cat_comp
    if cat_comp.status == FieldStatus.CONFLICT:
        contradictions.append(f"Achievement category conflict: '{cat_comp.value_1}' vs '{cat_comp.value_2}'.")
    elif cat_comp.status == FieldStatus.MATCH:
        matching_evidence.append(f"Achievement category matches: '{cat_comp.value_1}'.")

    # 7. Compare Certificate ID / Evidence Hash
    cert_comp = compare_field("certificate_id", cert_1, cert_2)
    comparisons["certificate_id"] = cert_comp
    if cert_comp.status == FieldStatus.CONFLICT:
        contradictions.append(f"Certificate identifier conflict: '{cert_comp.value_1}' != '{cert_comp.value_2}'.")
    elif cert_comp.status == FieldStatus.MATCH:
        matching_evidence.append(f"Certificate identifier exactly matches: '{cert_comp.value_1}'.")

    # Exact text match check
    exact_text_match = (normalize_field_value(text_1) == normalize_field_value(text_2)) and bool(normalize_field_value(text_1))

    # Evaluate Candidate Retrieval Threshold
    passed_retrieval = True
    if cosine_similarity is not None and cosine_similarity < retrieval_threshold:
        passed_retrieval = False

    # ---------------- DECISION SYNTHESIS ----------------
    decision: DuplicateDecision
    confidence: float
    explanation: str

    # Rule A: Candidate Retrieval Failure
    if not passed_retrieval:
        decision = DuplicateDecision.DISTINCT
        confidence = 0.95
        explanation = (
            f"Candidate retrieval rejected: Cosine similarity ({cosine_similarity:.4f}) is below "
            f"the candidate retrieval threshold ({retrieval_threshold:.2f}). Records are semantically unrelated."
        )

    # Rule B: Factual Contradictions Present
    elif len(contradictions) > 0:
        decision = DuplicateDecision.DISTINCT
        confidence = 0.90 if len(contradictions) == 1 else 0.98
        reasons = "; ".join(contradictions)
        explanation = (
            f"Structured verification identified {len(contradictions)} contradiction(s): {reasons}. "
            f"Factual contradictions refute duplicate identity despite semantic similarity."
        )

    # Rule C: Exact Byte / Normalized Text Duplicate
    elif exact_text_match:
        decision = DuplicateDecision.DUPLICATE
        confidence = 1.00
        explanation = "Identical normalized text description with no structured contradictions. Verified duplicate."

    # Rule D: Strong Semantic Similarity + Corroborating Structured Evidence
    elif (
        (cosine_similarity is not None and cosine_similarity >= high_similarity_threshold) or
        (len(matching_evidence) >= 3)
    ) and (
        event_comp.status == FieldStatus.MATCH or org_comp.status == FieldStatus.MATCH
    ):
        # Require that if rank was specified, it did not conflict
        if rank_comp.status != FieldStatus.CONFLICT and year_comp.status != FieldStatus.CONFLICT:
            decision = DuplicateDecision.DUPLICATE
            confidence = 0.88 if cosine_similarity is None else min(0.95, cosine_similarity)
            evidence_summary = "; ".join(matching_evidence)
            explanation = (
                f"Verified duplicate: High semantic similarity ({cosine_similarity if cosine_similarity is not None else 'N/A'}) "
                f"corroborated by matching structured evidence: {evidence_summary}."
            )
        else:
            decision = DuplicateDecision.REVIEW_REQUIRED
            confidence = 0.60
            explanation = "Moderate evidence of duplicate, but rank or year information is inconsistent."

    # Rule E: Candidate Passed Similarity but Missing Key Identifying Information
    elif cosine_similarity is not None and cosine_similarity >= retrieval_threshold:
        decision = DuplicateDecision.REVIEW_REQUIRED
        confidence = 0.50
        missing_summary = "; ".join(missing_evidence)
        explanation = (
            f"Candidate passed retrieval (similarity: {cosine_similarity:.4f}), but lacks conclusive structured evidence. "
            f"Missing fields: {missing_summary}. Flagged for manual human review."
        )

    # Rule F: Default Fallback
    else:
        decision = DuplicateDecision.REVIEW_REQUIRED
        confidence = 0.50
        explanation = "Insufficient structured evidence to confirm or refute duplicate identity."

    return DuplicateVerificationResult(
        decision=decision,
        confidence=confidence,
        cosine_similarity=cosine_similarity,
        passed_candidate_retrieval=passed_retrieval,
        field_comparisons=comparisons,
        matching_evidence=matching_evidence,
        contradictions=contradictions,
        missing_evidence=missing_evidence,
        explanation=explanation,
        pair_id=pair_id,
        record_id_1=id_1,
        record_id_2=id_2,
    )


def batch_verify_duplicate_pairs(
    pairs_df: pd.DataFrame,
    main_dataset_df: Optional[pd.DataFrame] = None,
    cosine_similarities: Optional[np.ndarray] = None,
    retrieval_threshold: float = 0.50,
    high_similarity_threshold: float = 0.70,
) -> List[DuplicateVerificationResult]:
    """
    Run the structured verification pipeline over a batch of candidate pairs.
    Looks up metadata from main_dataset_df when available.
    """
    results: List[DuplicateVerificationResult] = []
    metadata_map: Dict[str, Dict[str, Any]] = {}

    if main_dataset_df is not None:
        for _, row in main_dataset_df.iterrows():
            metadata_map[str(row["achievement_id"])] = row.to_dict()

    for idx, (_, row) in enumerate(pairs_df.iterrows()):
        pair_id = str(row.get("pair_id", f"PAIR_{idx+1:05d}"))
        id_1 = str(row.get("achievement_id_1", ""))
        id_2 = str(row.get("achievement_id_2", ""))
        
        # Build record 1
        rec1 = metadata_map.get(id_1, {}).copy()
        rec1["achievement_id"] = id_1
        rec1["achievement_text"] = row.get("text_1", rec1.get("achievement_text", ""))

        # Build record 2
        # If id_2 is a variant (e.g. ACH001074_V2), inherit metadata from base id_1
        if id_2 not in metadata_map and "_V" in id_2:
            base_id = re.sub(r"_V\d+", "", id_2)
            rec2 = metadata_map.get(base_id, {}).copy()
        else:
            rec2 = metadata_map.get(id_2, {}).copy()
        
        rec2["achievement_id"] = id_2
        rec2["achievement_text"] = row.get("text_2", rec2.get("achievement_text", ""))

        sim = float(cosine_similarities[idx]) if cosine_similarities is not None else None

        res = verify_duplicate_candidate(
            record_1=rec1,
            record_2=rec2,
            cosine_similarity=sim,
            retrieval_threshold=retrieval_threshold,
            high_similarity_threshold=high_similarity_threshold,
            pair_id=pair_id,
        )
        results.append(res)

    return results
