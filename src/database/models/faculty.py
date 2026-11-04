"""
src/database/models/faculty.py
==============================
Faculty member and department administrator entity.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


class FacultyModel(Base, TimestampMixin):
    """Faculty profile with departmental verification authorization."""
    __tablename__ = "faculty"

    faculty_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(128), default="Associate Professor", nullable=False)
    permissions: Mapped[str] = mapped_column(Text, default="VERIFY_ACHIEVEMENTS;VIEW_ANALYTICS", nullable=False)

    # Relationships
    user = relationship("UserModel", back_populates="faculty_profile")
