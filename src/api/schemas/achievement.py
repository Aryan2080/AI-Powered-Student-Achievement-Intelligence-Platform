"""
src/api/schemas/achievement.py
==============================
Achievement intake, ingestion DTOs, and verification schemas.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AchievementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    level: str = Field(default="COLLEGE")  # COLLEGE, STATE, NATIONAL, INTERNATIONAL
    achievement_date: Optional[date] = None
    evidence_url: Optional[str] = None
    skills: Optional[List[str]] = Field(default_factory=list)


class AchievementIngestDTO(BaseModel):
    """Canonical DTO for idempotent ingestion from Member 1 / Member 2 pipelines."""
    student_id: str
    source_achievement_id: str
    title: str
    description: str
    category: Optional[str] = "PROJECT"
    domain_tags: Optional[List[str]] = Field(default_factory=list)
    skills: Optional[List[str]] = Field(default_factory=list)
    level: str = "COLLEGE"
    achievement_date: Optional[date] = None
    evidence_status: str = "PENDING"
    evidence_url: Optional[str] = None
    extraction_confidence: float = 1.0
    classifier_confidence: float = 1.0
    source_pipeline_version: str = "v1.0.1"
    classifier_model_version: str = "v1.0.1"


class VerificationUpdateDTO(BaseModel):
    status: str = Field(..., description="VERIFIED or REJECTED")
    remarks: Optional[str] = Field(default="", description="Audit comments from reviewing faculty")


class AchievementResponse(BaseModel):
    achievement_id: str
    student_id: str
    source_achievement_id: Optional[str]
    title: str
    description: str
    normalized_text: str
    category: str
    domain_tags: List[str]
    skills: List[str]
    level: str
    achievement_date: Optional[date]
    evidence_status: str
    evidence_url: Optional[str]
    verification_remarks: Optional[str]
    extraction_confidence: float
    classifier_confidence: float
    source_pipeline_version: str
    classifier_model_version: str
    created_at: datetime

    class Config:
        from_attributes = True
