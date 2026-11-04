"""
src/database/base.py
====================
SQLAlchemy 2.0 DeclarativeBase with standard audit timestamp mixins.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all relational database models."""
    pass


class TimestampMixin:
    """Standard created_at and updated_at UTC timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
