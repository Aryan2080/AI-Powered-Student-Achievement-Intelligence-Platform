"""
src/api/schemas/student.py
==========================
Student academic profile request and response DTOs.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StudentUpdate(BaseModel):
    department: Optional[str] = None
    year_of_study: Optional[int] = Field(None, ge=1, le=5)
    gpa: Optional[float] = Field(None, ge=0.0, le=10.0)
    declared_skills: Optional[List[str]] = None
    declared_interests: Optional[List[str]] = None
    career_goals: Optional[str] = None


class StudentProfileResponse(BaseModel):
    student_id: str
    user_id: str
    full_name: str
    email: str
    department: str
    program: str
    year_of_study: int
    gpa: float
    declared_skills: List[str]
    declared_interests: List[str]
    verified_skills: List[str]
    career_goals: Optional[str]
    achievement_count: int = 0
    verified_achievement_count: int = 0

    class Config:
        from_attributes = True
