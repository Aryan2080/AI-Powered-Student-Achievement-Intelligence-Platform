"""
tests/test_skill_normalization.py
=================================
Unit tests for the Skill Extraction & Canonical Normalization Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.nlp.skill_normalization import (
    CanonicalSkillVocabulary,
    NormalizationStatus,
    SkillMention,
    SkillNormalizer,
    normalize_surface_text,
)

VOCAB_PATH = Path("data/annotations/canonical_skill_vocabulary.csv")


@pytest.fixture(scope="module")
def vocabulary() -> CanonicalSkillVocabulary:
    return CanonicalSkillVocabulary(VOCAB_PATH)


@pytest.fixture(scope="module")
def normalizer(vocabulary: CanonicalSkillVocabulary) -> SkillNormalizer:
    return SkillNormalizer(vocabulary)


def test_exact_canonical_skill_match(normalizer: SkillNormalizer) -> None:
    """Condition 1: Exact canonical skill matches with CANONICAL_MATCH status and confidence 1.0."""
    res = normalizer.normalize_mention("Python")
    assert res.normalization_status == NormalizationStatus.CANONICAL_MATCH
    assert res.canonical_skill == "Python"
    assert res.confidence == 1.0
    assert res.skill_domain == "Software Engineering"
    assert res.skill_id == "SKL_0001"


def test_alias_match(normalizer: SkillNormalizer) -> None:
    """Condition 2: Known alias matches to its canonical skill with ALIAS_MATCH status."""
    res1 = normalizer.normalize_mention("golang")
    assert res1.normalization_status == NormalizationStatus.ALIAS_MATCH
    assert res1.canonical_skill == "Go"
    assert res1.confidence == 0.95

    res2 = normalizer.normalize_mention("logistics")
    assert res2.normalization_status == NormalizationStatus.ALIAS_MATCH
    assert res2.canonical_skill == "Event Organization"


def test_case_normalization(normalizer: SkillNormalizer) -> None:
    """Condition 3: Case-insensitive matching across upper, lower, and mixed case."""
    for variant in ["python", "PYTHON", "PyThOn", "pYtHoN"]:
        res = normalizer.normalize_mention(variant)
        assert res.normalization_status == NormalizationStatus.CANONICAL_MATCH
        assert res.canonical_skill == "Python"


def test_whitespace_normalization(normalizer: SkillNormalizer) -> None:
    """Condition 4: Normalizes irregular whitespace, leading, and trailing spaces."""
    res = normalizer.normalize_mention("   deep    learning   ")
    assert res.normalization_status == NormalizationStatus.CANONICAL_MATCH
    assert res.canonical_skill == "Deep Learning"


def test_punctuation_variation(normalizer: SkillNormalizer) -> None:
    """Condition 5: Correctly extracts and normalizes punctuation-heavy technical terms."""
    # C++
    res_cpp = normalizer.normalize_mention("C++")
    assert res_cpp.canonical_skill == "C++"

    # C#
    res_cs = normalizer.normalize_mention("C#")
    assert res_cs.canonical_skill == "C#"

    # Next.js
    res_next = normalizer.normalize_mention("next.js")
    assert res_next.canonical_skill == "Next.js"

    # CI/CD
    res_cicd = normalizer.normalize_mention("ci/cd")
    assert res_cicd.canonical_skill == "CI/CD"


def test_unknown_skill_mention(normalizer: SkillNormalizer) -> None:
    """Condition 6: Unrecognized technical terms return UNMATCHED without crashing."""
    res = normalizer.normalize_mention("QuantumHyperdriveFramework")
    assert res.normalization_status == NormalizationStatus.UNMATCHED
    assert res.canonical_skill is None
    assert res.confidence == 0.0


def test_ambiguous_mapping(normalizer: SkillNormalizer) -> None:
    """Condition 7: Surface forms mapping to multiple canonical entries return AMBIGUOUS."""
    res = normalizer.normalize_mention("scrum")
    assert res.normalization_status == NormalizationStatus.AMBIGUOUS
    assert res.canonical_skill is None
    assert "Agile Project Management" in res.candidate_matches
    assert "Scrum" in res.candidate_matches


def test_multiple_skills_in_one_description(normalizer: SkillNormalizer) -> None:
    """Condition 8: Extracts multiple distinct skills from continuous prose."""
    text = "Engineered microservices with Python, containerized with Docker, and deployed on Kubernetes."
    results = normalizer.extract_and_normalize(text)
    extracted_canonical = [r.canonical_skill for r in results if r.canonical_skill]

    assert "Microservices" in extracted_canonical
    assert "Python" in extracted_canonical
    assert "Docker" in extracted_canonical
    assert "Kubernetes" in extracted_canonical


def test_repeated_skill_mentions(normalizer: SkillNormalizer) -> None:
    """Condition 9: Repeated mentions in the same text are extracted with distinct offsets."""
    text = "Python is our primary backend, and Python scripting powers our build tools."
    mentions = normalizer.extract_mentions(text)
    py_mentions = [m for m in mentions if m.mention_text.lower() == "python"]
    assert len(py_mentions) == 2
    assert py_mentions[0].start_offset != py_mentions[1].start_offset


def test_empty_text(normalizer: SkillNormalizer) -> None:
    """Condition 10: Empty or whitespace-only text returns an empty list cleanly."""
    assert normalizer.extract_mentions("") == []
    assert normalizer.extract_mentions("   ") == []
    assert normalizer.extract_and_normalize("") == []


def test_missing_vocabulary_entry(normalizer: SkillNormalizer) -> None:
    """Condition 11: Non-existent vocabulary entry handling."""
    res = normalizer.normalize_mention("UnrealEngine6Beta")
    assert res.normalization_status == NormalizationStatus.UNMATCHED
    assert res.canonical_skill is None


def test_invalid_input(normalizer: SkillNormalizer) -> None:
    """Condition 12: Invalid input types return safe fallbacks."""
    res = normalizer.normalize_mention("")
    assert res.normalization_status == NormalizationStatus.NOT_A_SKILL

    res_none = normalizer.normalize_mention(None)  # type: ignore
    assert res_none.normalization_status == NormalizationStatus.NOT_A_SKILL


def test_reproducible_output(normalizer: SkillNormalizer) -> None:
    """Condition 13: Deterministic outputs across multiple runs."""
    text = "Built real-time data streaming pipeline using Apache Kafka and Apache Flink with Scala."
    run1 = [r.to_dict() for r in normalizer.extract_and_normalize(text)]
    run2 = [r.to_dict() for r in normalizer.extract_and_normalize(text)]
    assert run1 == run2


def test_preservation_of_original_text(normalizer: SkillNormalizer) -> None:
    """Condition 14: Verbatim slice invariance: text[start:end] == mention_text."""
    text = "Implemented high-performance low-latency modules in Rust and C++ for robotics."
    mentions = normalizer.extract_mentions(text)
    for m in mentions:
        assert text[m.start_offset : m.end_offset] == m.mention_text


def test_correct_source_offsets(normalizer: SkillNormalizer) -> None:
    """Condition 15: Exact offset validation on complex sentence with punctuation."""
    text = "Lead contributor to React.js, TypeScript, and Tailwind CSS components."
    results = normalizer.extract_and_normalize(text)
    for res in results:
        s = res.mention.start_offset
        e = res.mention.end_offset
        assert text[s:e] == res.mention.mention_text


def test_controlled_fuzzy_match(normalizer: SkillNormalizer) -> None:
    """Helper condition: Controlled fuzzy matching for high-similarity typos."""
    res = normalizer.normalize_mention("kubernets")
    assert res.normalization_status == NormalizationStatus.FUZZY_MATCH
    assert res.canonical_skill == "Kubernetes"
    assert res.confidence > 0.80


def test_single_letter_r_guard(normalizer: SkillNormalizer) -> None:
    """Helper condition: R language is matched at word boundary but ignored in 'R&D'."""
    text_rd = "Worked in Texas Instruments Analog R&D team."
    mentions_rd = normalizer.extract_mentions(text_rd)
    assert not any(m.mention_text == "R" for m in mentions_rd)

    text_r_lang = "Conducted statistical analysis in R programming language."
    mentions_r = normalizer.extract_mentions(text_r_lang)
    assert any(m.mention_text == "R" for m in mentions_r)
