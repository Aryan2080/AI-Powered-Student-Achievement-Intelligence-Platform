"""
src/database/models/notification.py
===================================
Notification persistence entity with unique deduplication keys.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class NotificationModel(Base):
    """In-app and dispatchable alert for upcoming deadlines, high matches, or verification updates."""
    __tablename__ = "notifications"

    notification_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(32), default="OPPORTUNITY_MATCH", nullable=False)
    # Deduplication key: e.g. "DEADLINE_7D-STU001-OPP004-2026-12-15"
    dedupe_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    student = relationship("StudentModel", back_populates="notifications")

    __table_args__ = (
        Index("idx_student_unread", "student_id", "is_read"),
    )
