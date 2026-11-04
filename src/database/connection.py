"""
src/database/connection.py
==========================
Synchronous and asynchronous SQLAlchemy database connection factories and session scopes.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings
from src.core.logging import logger
from src.database.base import Base

# Sync Engine & Session
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables according to declared ORM models."""
    logger.info("Initializing relational database schema at %s...", settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")


def get_db() -> Generator[Session, None, None]:
    """Dependency provider yielding transactional database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
