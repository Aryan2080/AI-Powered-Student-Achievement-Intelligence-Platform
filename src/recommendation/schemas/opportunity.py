"""
src/recommendation/schemas/opportunity.py
=========================================
Pydantic v2 schemas and validation for opportunity corpus entities.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from src.nlp.taxonomy import DOMAIN_TAGS, is_valid_domain_tag


class OpportunityType(str, Enum):
    """Categorical classification of student opportunities."""
    HACKATHON = "HACKATHON"
    INTERNSHIP = "INTERNSHIP"
    RESEARCH_GRANT = "RESEARCH_GRANT"
    COMPETITION = "COMPETITION"
    SCHOLARSHIP = "SCHOLARSHIP"
    CONFERENCE = "CONFERENCE"


class LocationType(str, Enum):
    """Execution modality of opportunity."""
    REMOTE = "REMOTE"
    ON_SITE = "ON_SITE"
    HYBRID = "HYBRID"


class OpportunityStatus(str, Enum):
    """Lifecycle status of opportunity."""
    ACTIVE = "ACTIVE"
    UPCOMING = "UPCOMING"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class OpportunityBase(BaseModel):
    """Core attributes defining an opportunity."""
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    opportunity_type: OpportunityType
    organization: str = Field(..., min_length=2, max_length=200)
    eligible_departments: List[str] = Field(default_factory=lambda: ["Computer Science", "Information Technology"])
    eligible_years: List[int] = Field(default_factory=lambda: [1, 2, 3, 4])
    eligible_degree: List[str] = Field(default_factory=lambda: ["B.Tech", "B.S.", "B.E.", "M.Tech"])
    min_gpa: float = Field(default=0.0, ge=0.0, le=10.0)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    domain_tags: List[str] = Field(default_factory=list)
    deadline: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reward_or_stipend: Optional[str] = None
    location_type: LocationType = LocationType.REMOTE
    location: Optional[str] = None
    external_url: str = Field(default="https://opportunity.university.edu")
    status: OpportunityStatus = OpportunityStatus.ACTIVE
    source_name: str = Field(default="University Portal")

    @field_validator("domain_tags")
    @classmethod
    def validate_domain_tags(cls, v: List[str]) -> List[str]:
        for tag in v:
            if tag not in DOMAIN_TAGS:
                raise ValueError(f"Invalid domain tag '{tag}'. Must be one of {DOMAIN_TAGS}")
        return v


class OpportunityCreate(OpportunityBase):
    """Payload for creating a new opportunity."""
    opportunity_id: Optional[str] = None


class Opportunity(OpportunityBase):
    """Full Opportunity record with system metadata."""
    opportunity_id: str
    collected_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    text_hash: Optional[str] = None
    embedding_version: Optional[str] = "all-MiniLM-L6-v2"

    class Config:
        from_attributes = True
