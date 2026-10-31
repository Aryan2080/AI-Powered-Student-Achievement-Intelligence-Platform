"""
tests/test_duplicate_detection.py
=================================
Unit tests for the Advanced Duplicate Detection & Structured Verification Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

import pytest
import pandas as pd

from src.nlp.duplicate_detection import (
    DuplicateDecision,
    FieldStatus,
    compare_field,
    extract_entities_from_text,
    verify_duplicate_candidate,
    batch_verify_duplicate_pairs,
)


def test_same_student_and_same_achievement() -> None:
    """Condition 1: Same student, same event, same rank, high similarity -> DUPLICATE."""
    rec1 = {
        "achievement_id": "ACH-001",
        "student_id": "STU-999",
        "achievement_text": "Won 1st place in National AI Hackathon 2023.",
        "event_name": "National AI Hackathon",
        "organization": "AI Society",
        "rank": "1st Place",
        "achievement_date": "2023-11-15",
        "category": "COMPETITIVE_PROGRAMMING",
    }
    rec2 = {
        "achievement_id": "ACH-001_V2",
        "student_id": "STU-999",
        "achievement_text": "Secured 1st place at the National AI Hackathon in 2023.",
        "event_name": "National AI Hackathon",
        "organization": "AI Society",
        "rank": "1st Place",
        "achievement_date": "2023-11-15",
        "category": "COMPETITIVE_PROGRAMMING",
    }
    res = verify_duplicate_candidate(rec1, rec2, cosine_similarity=0.85)
    assert res.decision == DuplicateDecision.DUPLICATE
    assert res.passed_candidate_retrieval is True
    assert "Student identity matches: 'STU-999'." in res.matching_evidence
    assert len(res.contradictions) == 0


def test_different_student_identities() -> None:
    """Condition 2: Different student identities must prevent duplicate declaration -> DISTINCT."""
    rec1 = {
        "achievement_id": "ACH-001",
        "student_id": "STU-101",
        "achievement_text": "Won 1st place in National AI Hackathon 2023.",
        "event_name": "National AI Hackathon",
        "rank": "1st Place",
        "achievement_date": "2023-11-15",
    }
    rec2 = {
        "achievement_id": "ACH-002",
        "student_id": "STU-102",  # Different student!
        "achievement_text": "Won 1st place in National AI Hackathon 2023.",
        "event_name": "National AI Hackathon",
        "rank": "1st Place",
        "achievement_date": "2023-11-15",
    }
    res = verify_duplicate_candidate(rec1, rec2, cosine_similarity=0.95)
    assert res.decision == DuplicateDecision.DISTINCT
    assert any("Student identity conflict" in c for c in res.contradictions)


def test_same_event_different_ranks() -> None:
    """Condition 3: Same event but different ranks (e.g. Winner vs Runner-up) -> DISTINCT."""
    rec1 = {
        "achievement_id": "ACH-010",
        "achievement_text": "Won 1st place in Smart India Hackathon 2023.",
        "event_name": "Smart India Hackathon",
        "rank": "1st Place",
        "achievement_date": "2023-08-20",
    }
    rec2 = {
        "achievement_id": "ACH-011",
        "achievement_text": "Secured Runner-Up in Smart India Hackathon 2023.",
        "event_name": "Smart India Hackathon",
        "rank": "Runner-Up",
        "achievement_date": "2023-08-20",
    }
    res = verify_duplicate_candidate(rec1, rec2, cosine_similarity=0.75)
    assert res.decision == DuplicateDecision.DISTINCT
    assert any("Placement rank conflict" in c for c in res.contradictions)


def test_same_event_different_years() -> None:
    """Condition 4: Same event in different academic/calendar years -> DISTINCT."""
    rec1 = {
        "achievement_id": "ACH-020",
        "achievement_text": "Gold Medalist at Inter-Collegiate Athletic Meet (2022).",
        "event_name": "Inter-Collegiate Athletic Meet",
        "rank": "Gold Medal",
        "achievement_date": "2022-04-10",
    }
    rec2 = {
        "achievement_id": "ACH-021",
        "achievement_text": "Gold Medalist at Inter-Collegiate Athletic Meet (2023).",
        "event_name": "Inter-Collegiate Athletic Meet",
        "rank": "Gold Medal",
        "achievement_date": "2023-04-12",
    }
    res = verify_duplicate_candidate(rec1, rec2, cosine_similarity=0.88)
    assert res.decision == DuplicateDecision.DISTINCT
    assert any("Achievement year conflict" in c for c in res.contradictions)


def test_missing_student_identity() -> None:
    """Condition 5: Missing student identity is handled explicitly without assuming match."""
    rec1 = {
        "achievement_id": "ACH-030",
        "achievement_text": "Presented research on Deep Learning at IEEE Conference.",
        "event_name": "IEEE Conference",
        # student_id missing
    }
    rec2 = {
        "achievement_id": "ACH-031",
        "achievement_text": "Presented technical paper at IEEE Conference.",
        "event_name": "IEEE Conference",
        # student_id missing
    }
    res = verify_duplicate_candidate(rec1, rec2, cosine_similarity=0.60)
    # Without student ID and with moderate similarity, does NOT jump to DUPLICATE
    assert "student_id" in res.field_comparisons
    assert res.field_comparisons["student_id"].status == FieldStatus.MISSING_BOTH
    assert "Student identity not available in records." in res.missing_evidence


def test_missing_rank() -> None:
    """Condition 6: Missing rank in one or both records does not trigger false conflict or false match."""
    rec1 = {
        "achievement_id": "ACH-040",
        "achievement_text": "Participated in Robotics Workshop.",
        "rank": None,
    }
    rec2 = {
        "achievement_id": "ACH-041",
        "achievement_text": "Attended Robotics Workshop.",
        "rank": "Participant",
    }
    comp = compare_field("rank", rec1["rank"], rec2["rank"], is_rank=True)
    assert comp.status == FieldStatus.MISSING_ONE
    assert "missing" in comp.note


def test_missing_event_identity() -> None:
    """Condition 7: Missing event identity handled gracefully without crashing or assuming match."""
    rec1 = {"achievement_id": "ACH-050", "event_name": None}
    rec2 = {"achievement_id": "ACH-051", "event_name": "Tech Expo"}
    comp = compare_field("event_name", rec1["event_name"], rec2["event_name"])
    assert comp.status == FieldStatus.MISSING_ONE


def test_conflicting_evidence_identifiers() -> None:
    """Condition 8: Conflicting certificate or evidence IDs trigger DISTINCT decision."""
    rec1 = {
        "achievement_id": "ACH-060",
        "achievement_text": "AWS Solutions Architect Associate.",
        "evidence_id": "AWS-CERT-00123",
    }
    rec2 = {
        "achievement_id": "ACH-061",
        "achievement_text": "AWS Solutions Architect Associate.",
        "evidence_id": "AWS-CERT-00999",  # Conflicting certificate ID!
    }
    res = verify_duplicate_candidate(rec1, rec2, cosine_similarity=0.92)
    assert res.decision == DuplicateDecision.DISTINCT
    assert any("Certificate identifier conflict" in c for c in res.contradictions)


def test_semantically_similar_but_distinct_records() -> None:
    """Condition 9: Hard negative with high cosine similarity but different organizations -> DISTINCT."""
    rec1 = {
        "achievement_id": "ACH-070",
        "achievement_text": "Completed Cloud Engineering Bootcamp with Google Cloud.",
        "event_name": "Cloud Bootcamp",
        "organization": "Google Cloud",
    }
    rec2 = {
        "achievement_id": "ACH-071",
        "achievement_text": "Completed Cloud Engineering Bootcamp with Microsoft Azure.",
        "event_name": "Cloud Bootcamp",
        "organization": "Microsoft Azure",
    }
    res = verify_duplicate_candidate(rec1, rec2, cosine_similarity=0.78)
    assert res.decision == DuplicateDecision.DISTINCT
    assert any("Issuing organization conflict" in c for c in res.contradictions)


def test_exact_duplicate_descriptions() -> None:
    """Condition 10: Byte-identical normalized text with zero contradictions -> DUPLICATE."""
    rec1 = {
        "achievement_id": "ACH-080",
        "achievement_text": "Awarded 1st place in Collegiate Coding Challenge 2023.",
    }
    rec2 = {
        "achievement_id": "ACH-081",
        "achievement_text": "Awarded 1st place in Collegiate Coding Challenge 2023.",
    }
    res = verify_duplicate_candidate(rec1, rec2, cosine_similarity=1.0)
    assert res.decision == DuplicateDecision.DUPLICATE
    assert res.confidence == 1.0


def test_invalid_input_guards() -> None:
    """Condition 11: Invalid inputs raise TypeError or return safe null handling."""
    with pytest.raises(TypeError):
        verify_duplicate_candidate("not a dict", {"achievement_text": "valid"})  # type: ignore


def test_reproducible_decisions() -> None:
    """Condition 12: Decisions must be 100% deterministic and reproducible."""
    rec1 = {
        "achievement_id": "ACH-090",
        "achievement_text": "Elected as President of IEEE Student Branch (2023).",
        "event_name": "IEEE Annual Elections",
        "achievement_date": "2023-05-01",
        "rank": "President",
    }
    rec2 = {
        "achievement_id": "ACH-090_V2",
        "achievement_text": "Served as President for IEEE Student Branch during 2023 term.",
        "event_name": "IEEE Annual Elections",
        "achievement_date": "2023-05-01",
        "rank": "President",
    }
    run1 = verify_duplicate_candidate(rec1, rec2, cosine_similarity=0.79)
    run2 = verify_duplicate_candidate(rec1, rec2, cosine_similarity=0.79)
    assert run1.decision == run2.decision
    assert run1.confidence == run2.confidence
    assert run1.explanation == run2.explanation
    assert run1.contradictions == run2.contradictions
    assert run1.matching_evidence == run2.matching_evidence


def test_text_entity_extraction() -> None:
    """Helper test: extract_entities_from_text accurately extracts year, rank, and certificate."""
    text = "Won 1st place in Smart India Hackathon 2023. Credential ID: MET-508926."
    entities = extract_entities_from_text(text)
    assert entities.get("year") == "2023"
    assert entities.get("rank") == "RANK_1_WINNER"
    assert entities.get("certificate_id") == "MET-508926"
