"""
src/database/models/student.py
==============================
Student academic standing and profile entity.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import List
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


class StudentModel(Base, TimestampMixin):
    """Student profile capturing academic year, GPA, skills, and preferences."""
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(128), default="Computer Science", nullable=False)
    program: Mapped[str] = mapped_column(String(64), default="B.Tech", nullable=False)
    year_of_study: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    gpa: Mapped[float] = mapped_column(Float, default=8.0, nullable=False)
    declared_skills: Mapped[str] = mapped_column(Text, default="", nullable=False)  # Semicolon-delimited
    declared_interests: Mapped[str] = mapped_column(Text, default="", nullable=False)  # Semicolon-delimited
    career_goals: Mapped[str] = mapped_column(String(255), default="", nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="student_profile")
    achievements = relationship("AchievementModel", back_populates="student", cascade="all, delete-orphan")
    saved_opportunities = relationship("SavedOpportunityModel", back_populates="student", cascade="all, delete-orphan")
    notifications = relationship("NotificationModel", back_populates="student", cascade="all, delete-orphan")

    def get_declared_skills_list(self) -> List[str]:
        return [s.strip() for s in self.declared_skills.split(";") if s.strip()]

    def get_declared_interests_list(self) -> List[str]:
        return [i.strip() for i in self.declared_interests.split(";") if i.strip()]
