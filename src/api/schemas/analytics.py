"""
src/api/schemas/analytics.py
============================
Institutional analytics and student intelligence response schemas.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CategoryCount(BaseModel):
    category: str
    count: int


class SkillDistribution(BaseModel):
    skill: str
    count: int
    verified_ratio: float


class StudentAnalyticsResponse(BaseModel):
    student_id: str
    total_achievements: int
    verified_achievements: int
    pending_achievements: int
    category_breakdown: List[CategoryCount]
    top_verified_skills: List[str]
    domain_affinity_scores: Dict[str, float]
    opportunity_match_count: int
    profile_completion_percentage: int


class DepartmentAnalyticsResponse(BaseModel):
    department: str
    total_students: int
    total_achievements: int
    verified_achievements: int
    category_distribution: List[CategoryCount]
    top_in_demand_skills: List[SkillDistribution]
    top_skill_gaps: List[SkillDistribution]
    average_gpa: float
    engagement_rate: float
    data_suppressed: bool = False  # Set to True if cell threshold <= 3


class InstitutionalOverviewResponse(BaseModel):
    total_students: int
    total_faculty: int
    total_achievements: int
    total_opportunities: int
    department_participation: Dict[str, int]
    top_achievement_categories: List[CategoryCount]
    system_health: str = "HEALTHY"
