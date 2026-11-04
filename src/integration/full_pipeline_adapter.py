"""
src/integration/full_pipeline_adapter.py
========================================
End-to-end integration orchestrator connecting Member 1 (NLP), Member 2 (ML),
and Member 3 (Persistence, Profile Aggregation, Recommendations, Notifications).
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from src.core.exceptions import DuplicateRecordException, EntityNotFoundException
from src.core.logging import logger
from src.database.models.achievement import AchievementModel
from src.database.repositories.achievement_repository import AchievementRepository
from src.database.repositories.student_repository import StudentRepository
from src.integration.ml_model_adapter import Member2PredictorAdapter
from src.integration.nlp_adapter import Member1NLPAdapter
from src.recommendation.domain.student_profile import AchievementLevel, AchievementSummary, StudentProfile
from src.recommendation.engine.recommendation_service import RecommendationService
from src.recommendation.profile_aggregator import StudentProfileAggregator
from src.recommendation.schemas.recommendation import RecommendationResponse


class FullPipelineAdapter:
    """Orchestrates end-to-end flow from raw achievement intake through recommendation refresh."""

    def __init__(
        self,
        nlp_adapter: Optional[Member1NLPAdapter] = None,
        ml_adapter: Optional[Member2PredictorAdapter] = None,
        profile_aggregator: Optional[StudentProfileAggregator] = None,
        recommendation_service: Optional[RecommendationService] = None,
    ):
        self.nlp = nlp_adapter or Member1NLPAdapter()
        self.ml = ml_adapter or Member2PredictorAdapter()
        self.aggregator = profile_aggregator or StudentProfileAggregator()
        self.rec_service = recommendation_service or RecommendationService()

    def process_and_ingest_achievement(
        self,
        db: Session,
        student_id: str,
        title: str,
        description: str,
        level: str = "COLLEGE",
        achievement_date: Optional[date] = None,
        source_achievement_id: Optional[str] = None,
        evidence_url: Optional[str] = None,
        verified_flag: bool = False,
    ) -> AchievementModel:
        """End-to-end processing and idempotent ingestion of an achievement."""
        ach_repo = AchievementRepository(db)
        stu_repo = StudentRepository(db)

        student = stu_repo.get_by_id(student_id)
        if not student:
            raise EntityNotFoundException(f"Student '{student_id}' does not exist.")

        # Idempotency check
        if source_achievement_id:
            existing = ach_repo.get_by_student_and_source(student_id, source_achievement_id)
            if existing:
                logger.info(
                    "Duplicate achievement detected for student %s, source %s. Returning existing.",
                    student_id, source_achievement_id
                )
                return existing

        # 1. Member 1 NLP Normalization & Canonical Skill Extraction
        raw_text = f"{title}. {description}"
        norm_text = self.nlp.clean_and_normalize(raw_text)
        extracted_skills = self.nlp.extract_canonical_skills(raw_text)

        # 2. Member 2 ML Model Prediction
        prediction = self.ml.predict(norm_text)
        primary_cat = prediction["primary_classification"]["category"]
        conf = float(prediction["primary_classification"]["confidence"])
        domain_tags = prediction["domain_categorization"]["tags"]
        model_ver = prediction["model_version"]

        # 3. Relational Persistence
        ach_id = f"ACH-{student_id[:8]}-{uuid.uuid4().hex[:6]}"
        record = AchievementModel(
            achievement_id=ach_id,
            student_id=student_id,
            source_achievement_id=source_achievement_id or ach_id,
            title=title,
            description=description,
            normalized_text=norm_text,
            category=primary_cat,
            domain_tags=";".join(domain_tags),
            skills=";".join(extracted_skills),
            level=level.upper(),
            achievement_date=achievement_date or date.today(),
            evidence_status="VERIFIED" if verified_flag else "PENDING",
            evidence_url=evidence_url or "",
            extraction_confidence=0.95,
            classifier_confidence=conf,
            source_pipeline_version="v1.0.1",
            classifier_model_version=model_ver,
        )

        created_ach = ach_repo.create(record)
        logger.info(
            "Achievement %s successfully ingested for student %s (Category: %s, Model: %s)",
            created_ach.achievement_id, student_id, primary_cat, model_ver
        )
        return created_ach

    def get_refreshed_recommendations(
        self, db: Session, student_id: str, top_k: int = 10
    ) -> RecommendationResponse:
        """Re-aggregate student profile from all achievements and compute fresh recommendations."""
        stu_repo = StudentRepository(db)
        ach_repo = AchievementRepository(db)

        student_db = stu_repo.get_by_id(student_id)
        if not student_db:
            raise EntityNotFoundException(f"Student '{student_id}' does not exist.")

        achievements_db = ach_repo.list_by_student(student_id)

        # Map to domain AchievementSummary entities
        ach_summaries = []
        for a in achievements_db:
            lvl = AchievementLevel.COLLEGE
            if hasattr(AchievementLevel, a.level.upper()):
                lvl = AchievementLevel[a.level.upper()]

            ach_summaries.append(
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

        # Aggregate profile
        profile = self.aggregator.aggregate_profile(
            student_id=student_id,
            department=student_db.department,
            program=student_db.program,
            year_of_study=student_db.year_of_study,
            gpa=student_db.gpa,
            declared_skills=student_db.get_declared_skills_list(),
            declared_interests=student_db.get_declared_interests_list(),
            achievements=ach_summaries,
            career_goals=student_db.career_goals,
        )

        # Generate recommendations
        return self.rec_service.recommend(profile, top_k=top_k)
