"""
src/recommendation/schemas/recommendation.py
============================================
Pydantic v2 schemas for recommendation results, score breakdowns, and explanations.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.recommendation.schemas.opportunity import Opportunity


class ScoreBreakdown(BaseModel):
    """Detailed multi-criteria scoring components."""
    semantic_similarity: float = Field(..., ge=0.0, le=1.0)
    skill_match_score: float = Field(..., ge=0.0, le=1.0)
    domain_match_score: float = Field(..., ge=0.0, le=1.0)
    urgency_score: float = Field(..., ge=0.0, le=1.0)
    composite_score: float = Field(..., ge=0.0, le=1.0)


class RecommendationItem(BaseModel):
    """Single personalized opportunity recommendation with grounded explanation."""
    rank: int = Field(..., ge=1)
    opportunity: Opportunity
    match_score: float = Field(..., ge=0.0, le=1.0)
    scores: ScoreBreakdown
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    eligibility_status: str = Field(default="ELIGIBLE")
    explanation: str = Field(..., description="Grounded, human-readable justification")
    closest_achievement_id: Optional[str] = None
    closest_achievement_title: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Container response for personalized student recommendations."""
    student_id: str
    generated_at: datetime
    total_recommendations: int
    algorithm_version: str = "v1.2.0-hybrid"
    encoder_model: str = "all-MiniLM-L6-v2"
    recommendations: List[RecommendationItem] = Field(default_factory=list)
