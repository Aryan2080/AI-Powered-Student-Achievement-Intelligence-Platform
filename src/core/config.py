"""
src/core/config.py
==================
Centralized application settings and configuration management using Pydantic Settings.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"


class Settings(BaseSettings):
    """Global configuration settings for the backend API and recommendation services."""

    # Application Information
    PROJECT_NAME: str = "AI-Powered Student Achievement Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", description="development, staging, or production")
    DEBUG: bool = Field(default=False, description="Enable debug mode and verbose logging")

    # Security & JWT Authentication
    SECRET_KEY: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        description="Cryptographic secret key for signing JWT tokens",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database Configuration
    DATABASE_URL: str = Field(
        default=f"sqlite:///{PROJECT_ROOT}/student_intelligence.db",
        description="Standard synchronous or async database connection URL",
    )
    ASYNC_DATABASE_URL: Optional[str] = None
    DB_ECHO: bool = False

    # CORS Allowlist
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8501",
    ]

    # Recommendation Weights & Parameters
    WEIGHT_SEMANTIC: float = 0.45
    WEIGHT_SKILL: float = 0.30
    WEIGHT_DOMAIN: float = 0.15
    WEIGHT_URGENCY: float = 0.10

    # Achievement Aggregation Parameters
    ACHIEVEMENT_HALF_LIFE_DAYS: float = 730.0  # 2 years
    VERIFIED_ACHIEVEMENT_MULTIPLIER: float = 1.25
    MIN_CELL_SUPPRESSION_THRESHOLD: int = 3  # Privacy threshold for faculty analytics

    # Embedding Vector Parameters
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # File Paths
    OPPORTUNITIES_CSV_PATH: Path = DATA_DIR / "opportunities" / "opportunity_dataset.csv"
    OPPORTUNITIES_JSON_PATH: Path = DATA_DIR / "opportunities" / "opportunity_dataset.json"
    OPPORTUNITY_EMBEDDINGS_PATH: Path = DATA_DIR / "embeddings" / "opportunity_embeddings_all_MiniLM_L6_v2.npy"
    BENCHMARK_PROFILES_PATH: Path = DATA_DIR / "profiles" / "student_profiles_benchmark.json"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_async_database_url(self) -> str:
        """Return proper async driver URL for SQLAlchemy."""
        if self.ASYNC_DATABASE_URL:
            return self.ASYNC_DATABASE_URL
        if self.DATABASE_URL.startswith("sqlite:///"):
            return self.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL


settings = Settings()
