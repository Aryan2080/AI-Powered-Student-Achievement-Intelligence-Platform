"""
src/database/models/saved_opportunity.py
========================================
Student saved bookmarks and application status tracker.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class SavedOpportunityModel(Base):
    """Tracks whether an opportunity is SAVED, APPLIED, ACCEPTED, or ARCHIVED."""
    __tablename__ = "saved_opportunities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    opportunity_id: Mapped[str] = mapped_column(String(64), ForeignKey("opportunities.opportunity_id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="SAVED", nullable=False)  # SAVED, APPLIED, ACCEPTED, REJECTED
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=True)

    # Relationships
    student = relationship("StudentModel", back_populates="saved_opportunities")
    opportunity = relationship("OpportunityModel", back_populates="saved_by")

    __table_args__ = (
        UniqueConstraint("student_id", "opportunity_id", name="uq_student_opportunity"),
    )
