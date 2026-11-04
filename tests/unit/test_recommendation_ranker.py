"""Unit tests for hybrid ranking algorithms."""
import pytest
from src.recommendation.domain.student_profile import StudentProfile
from src.recommendation.engine.ranker import HybridRanker
from src.recommendation.schemas.opportunity import Opportunity, OpportunityType


def test_hybrid_score_bounding_and_components():
    ranker = HybridRanker(weight_semantic=0.45, weight_skill=0.30, weight_domain=0.15, weight_urgency=0.10)
    student = StudentProfile(
        student_id="STU-01",
        department="Computer Science",
        declared_skills=["Python", "PyTorch"],
        verified_skills=["OpenCV"],
    )
    opp = Opportunity(
        opportunity_id="OPP-01",
        title="AI Vision Sprint",
        description="Build state of the art vision pipelines.",
        opportunity_type=OpportunityType.HACKATHON,
        organization="OpenAI",
        required_skills=["Python", "PyTorch", "OpenCV"],
        domain_tags=["lbl_domain_ai"],
    )

    scores, matched, missing = ranker.score_opportunity(student, opp, semantic_similarity=0.90)

    assert 0.0 <= scores.composite_score <= 1.0
    assert scores.skill_match_score == pytest.approx(1.0, rel=1e-2)
    assert len(matched) == 3
    assert len(missing) == 0
