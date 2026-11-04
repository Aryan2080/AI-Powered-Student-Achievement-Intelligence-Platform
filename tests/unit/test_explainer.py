"""Unit tests for XAI justification generation."""
from src.recommendation.domain.student_profile import AchievementSummary, StudentProfile
from src.recommendation.engine.explainer import RecommendationExplainer
from src.recommendation.schemas.opportunity import Opportunity, OpportunityType
from src.recommendation.schemas.recommendation import ScoreBreakdown


def test_explainer_generates_grounded_justification():
    explainer = RecommendationExplainer()
    ach = AchievementSummary(
        achievement_id="ACH-01",
        title="1st Place at Smart India Hackathon",
        category="HACKATHON",
        skills=["Python", "OpenCV"],
        verified_flag=True,
    )
    student = StudentProfile(
        student_id="STU-01",
        department="Computer Science",
        achievements=[ach],
        declared_skills=["Python"],
    )
    opp = Opportunity(
        opportunity_id="OPP-01",
        title="Vision Hackathon 2026",
        description="Build vision solutions.",
        opportunity_type=OpportunityType.HACKATHON,
        organization="MLH",
        required_skills=["Python", "OpenCV", "ROS2"],
    )
    scores = ScoreBreakdown(
        semantic_similarity=0.9, skill_match_score=0.66, domain_match_score=0.8, urgency_score=0.5, composite_score=0.8
    )

    explanation, closest_id, closest_title = explainer.explain(
        student, opp, scores, matched_skills=["Python", "OpenCV"], missing_skills=["ROS2"]
    )

    assert "Smart India Hackathon" in explanation
    assert "2 of 3 required skills" in explanation
    assert closest_id == "ACH-01"
