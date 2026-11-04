"""
src/database/models/user.py
===========================
User authentication and credential ORM model with Role-Based Access Control.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.security import UserRole
from src.database.base import Base, TimestampMixin


class UserModel(Base, TimestampMixin):
    """System user with cryptographic password hash and authorized access role."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default=UserRole.STUDENT.value, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(128), default="Computer Science", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    student_profile = relationship("StudentModel", back_populates="user", uselist=False, cascade="all, delete-orphan")
    faculty_profile = relationship("FacultyModel", back_populates="user", uselist=False, cascade="all, delete-orphan")
