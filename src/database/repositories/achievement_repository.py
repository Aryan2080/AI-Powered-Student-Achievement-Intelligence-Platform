"""
src/database/repositories/achievement_repository.py
===================================================
Persistence, idempotent ingestion, and faculty verification workflows for achievements.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models.achievement import AchievementModel


class AchievementRepository:
    """Repository handling Achievement database operations and idempotency."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, achievement_id: str) -> Optional[AchievementModel]:
        stmt = select(AchievementModel).where(AchievementModel.achievement_id == achievement_id)
        return self.db.scalars(stmt).first()

    def get_by_student_and_source(
        self, student_id: str, source_achievement_id: str
    ) -> Optional[AchievementModel]:
        """Idempotency check: retrieve record if already ingested for this student."""
        stmt = select(AchievementModel).where(
            AchievementModel.student_id == student_id,
            AchievementModel.source_achievement_id == source_achievement_id,
        )
        return self.db.scalars(stmt).first()

    def list_by_student(
        self, student_id: str, status: Optional[str] = None
    ) -> List[AchievementModel]:
        stmt = select(AchievementModel).where(AchievementModel.student_id == student_id)
        if status:
            stmt = stmt.where(AchievementModel.evidence_status == status)
        stmt = stmt.order_by(AchievementModel.achievement_date.desc().nullslast())
        return list(self.db.scalars(stmt).all())

    def list_pending(self, skip: int = 0, limit: int = 50) -> List[AchievementModel]:
        """List achievements awaiting faculty verification."""
        stmt = (
            select(AchievementModel)
            .where(AchievementModel.evidence_status == "PENDING")
            .order_by(AchievementModel.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def create(self, achievement: AchievementModel) -> AchievementModel:
        self.db.add(achievement)
        self.db.flush()
        return achievement

    def update_verification(
        self,
        achievement_id: str,
        status: str,
        remarks: str = "",
        faculty_id: Optional[str] = None,
    ) -> Optional[AchievementModel]:
        ach = self.get_by_id(achievement_id)
        if not ach:
            return None
        ach.evidence_status = status
        ach.verification_remarks = remarks
        ach.verified_by_faculty_id = faculty_id
        self.db.flush()
        return ach
