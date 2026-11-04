"""
src/recommendation/domain/student_profile.py
============================================
Domain entities representing student academic standing, skills, and aggregate profile.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AchievementLevel(str, Enum):
    COLLEGE = "COLLEGE"
    STATE = "STATE"
    NATIONAL = "NATIONAL"
    INTERNATIONAL = "INTERNATIONAL"


class SkillProficiency(BaseModel):
    """Grounded skill proficiency based on verified achievement evidence."""
    skill_name: str
    proficiency_level: str = "INTERMEDIATE"  # BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
    evidence_count: int = 1
    verified_count: int = 1
    last_demonstrated: Optional[date] = None


class DomainAffinity(BaseModel):
    """Categorical domain affinity score derived from student achievement history."""
    domain_tag: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    achievement_count: int = 0


class AchievementSummary(BaseModel):
    """Canonical summary of an achievement for profile aggregation."""
    achievement_id: str
    title: str
    category: str
    domain_tags: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    level: AchievementLevel = AchievementLevel.COLLEGE
    achievement_date: Optional[date] = None
    verified_flag: bool = True
    confidence: float = 1.0
    embedding: Optional[List[float]] = None


class StudentProfile(BaseModel):
    """Dynamic, aggregated student profile feeding into the recommendation engine."""
    student_id: str
    department: str = "Computer Science"
    program: str = "B.Tech"
    year_of_study: int = 3
    gpa: float = 8.5
    declared_skills: List[str] = Field(default_factory=list)
    declared_interests: List[str] = Field(default_factory=list)
    career_goals: Optional[str] = None
    verified_skills: List[str] = Field(default_factory=list)
    skill_proficiencies: Dict[str, SkillProficiency] = Field(default_factory=dict)
    domain_affinities: Dict[str, DomainAffinity] = Field(default_factory=dict)
    achievements: List[AchievementSummary] = Field(default_factory=list)
    profile_vector: Optional[List[float]] = None
    profile_text_hash: Optional[str] = None
    last_aggregated_at: Optional[datetime] = None
    is_cold_start: bool = False
