"""
src/database/models/achievement.py
==================================
Student achievement persistence model with provenance, confidence scores, and idempotency key.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import date
from typing import List
from sqlalchemy import Date, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


class AchievementModel(Base, TimestampMixin):
    """Normalized achievement record with Member 1 & Member 2 provenance tracking."""
    __tablename__ = "achievements"

    achievement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    source_achievement_id: Mapped[str] = mapped_column(String(64), nullable=True)  # Upstream idempotency key
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="PROJECT", nullable=False)
    domain_tags: Mapped[str] = mapped_column(String(255), default="", nullable=False)  # Semicolon-delimited
    skills: Mapped[str] = mapped_column(Text, default="", nullable=False)  # Semicolon-delimited
    level: Mapped[str] = mapped_column(String(32), default="COLLEGE", nullable=False)
    achievement_date: Mapped[date] = mapped_column(Date, nullable=True)
    
    # Evidence & Verification Workflow
    evidence_status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)  # VERIFIED, PENDING, REJECTED
    evidence_url: Mapped[str] = mapped_column(String(512), default="", nullable=True)
    verification_remarks: Mapped[str] = mapped_column(Text, default="", nullable=True)
    verified_by_faculty_id: Mapped[str] = mapped_column(String(64), nullable=True)
    
    # Model & Extraction Provenance
    extraction_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    classifier_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_pipeline_version: Mapped[str] = mapped_column(String(32), default="v1.0.1", nullable=False)
    classifier_model_version: Mapped[str] = mapped_column(String(32), default="v1.0.1", nullable=False)

    # Relationships
    student = relationship("StudentModel", back_populates="achievements")

    __table_args__ = (
        UniqueConstraint("student_id", "source_achievement_id", name="uq_student_source_achievement"),
        Index("idx_student_status", "student_id", "evidence_status"),
    )

    def get_skills_list(self) -> List[str]:
        return [s.strip() for s in self.skills.split(";") if s.strip()]

    def get_domain_tags_list(self) -> List[str]:
        return [d.strip() for d in self.domain_tags.split(";") if d.strip()]
