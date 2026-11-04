"""
src/api/routers/recommendations.py
==================================
Personalized opportunity recommendation API exposing top-k ranked matches and grounded XAI explanations.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.database.connection import get_db
from src.database.models.user import UserModel
from src.database.repositories.achievement_repository import AchievementRepository
from src.database.repositories.student_repository import StudentRepository
from src.integration.full_pipeline_adapter import FullPipelineAdapter
from src.recommendation.domain.student_profile import AchievementLevel, AchievementSummary, StudentProfile
from src.recommendation.engine.recommendation_service import RecommendationService
from src.recommendation.profile_aggregator import StudentProfileAggregator
from src.recommendation.schemas.recommendation import RecommendationResponse

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

rec_service = RecommendationService()
profile_aggregator = StudentProfileAggregator()


@router.get("/{student_id}", response_model=RecommendationResponse)
def get_recommendations_for_student(
    student_id: str,
    top_k: int = Query(10, ge=1, le=50),
    opportunity_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Generate personalized, eligible, ranked recommendations with grounded justifications."""
    stu_repo = StudentRepository(db)
    ach_repo = AchievementRepository(db)

    stu = stu_repo.get_by_id(student_id)
    if not stu:
        # Fallback to benchmark profiles in development
        import json
        from src.core.config import settings
        if settings.BENCHMARK_PROFILES_PATH.exists():
            with open(settings.BENCHMARK_PROFILES_PATH, "r", encoding="utf-8") as f:
                benchmarks = json.load(f)
            matching = [p for p in benchmarks if p["student_id"] == student_id]
            if matching:
                bench_profile = StudentProfile(**matching[0])
                return rec_service.recommend(bench_profile, top_k=top_k, filter_type=opportunity_type)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' does not exist.",
        )

    # Load achievements
    achievements_db = ach_repo.list_by_student(student_id)
    summaries = []
    for a in achievements_db:
        lvl = AchievementLevel.COLLEGE
        if hasattr(AchievementLevel, a.level.upper()):
            lvl = AchievementLevel[a.level.upper()]
        summaries.append(
            AchievementSummary(
                achievement_id=a.achievement_id,
                title=a.title,
                category=a.category,
                domain_tags=a.get_domain_tags_list(),
                skills=a.get_skills_list(),
                level=lvl,
                achievement_date=a.achievement_date,
                verified_flag=(a.evidence_status == "VERIFIED"),
                confidence=a.classifier_confidence,
            )
        )

    # Synthesize dynamic profile
    profile = profile_aggregator.aggregate_profile(
        student_id=stu.student_id,
        department=stu.department,
        program=stu.program,
        year_of_study=stu.year_of_study,
        gpa=stu.gpa,
        declared_skills=stu.get_declared_skills_list(),
        declared_interests=stu.get_declared_interests_list(),
        achievements=summaries,
        career_goals=stu.career_goals,
    )

    # Compute recommendations
    return rec_service.recommend(profile, top_k=top_k, filter_type=opportunity_type)
