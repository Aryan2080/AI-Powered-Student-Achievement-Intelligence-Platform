"""
src/database/models/recommendation.py
=====================================
Persistence of recommendation snapshots and score attributions for auditing and tracking.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class RecommendationSnapshotModel(Base):
    """Historical snapshot of a recommendation request for a student."""
    __tablename__ = "recommendation_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    profile_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(32), default="v1.2.0-hybrid", nullable=False)
    encoder_version: Mapped[str] = mapped_column(String(64), default="all-MiniLM-L6-v2", nullable=False)

    # Relationships
    items = relationship("RecommendationItemModel", back_populates="snapshot", cascade="all, delete-orphan")


class RecommendationItemModel(Base):
    """Specific ranked item within a recommendation snapshot."""
    __tablename__ = "recommendation_snapshot_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), ForeignKey("recommendation_snapshots.snapshot_id"), nullable=False)
    opportunity_id: Mapped[str] = mapped_column(String(64), ForeignKey("opportunities.opportunity_id"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Detailed scoring breakdown
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    skill_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    domain_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    urgency_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    matched_skills: Mapped[str] = mapped_column(Text, default="", nullable=False)
    missing_skills: Mapped[str] = mapped_column(Text, default="", nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    snapshot = relationship("RecommendationSnapshotModel", back_populates="items")
