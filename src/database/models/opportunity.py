"""
src/database/models/opportunity.py
==================================
Relational storage for the opportunity catalog.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import date
from typing import List
from sqlalchemy import Date, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


class OpportunityModel(Base, TimestampMixin):
    """Database entity representing an opportunity (Hackathon, Internship, Grant, etc.)."""
    __tablename__ = "opportunities"

    opportunity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    opportunity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    organization: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Eligibility Criteria
    eligible_departments: Mapped[str] = mapped_column(Text, default="", nullable=False)
    eligible_years: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    eligible_degree: Mapped[str] = mapped_column(String(128), default="B.Tech;B.E.;M.Tech", nullable=False)
    min_gpa: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Skills & Domains
    required_skills: Mapped[str] = mapped_column(Text, default="", nullable=False)
    preferred_skills: Mapped[str] = mapped_column(Text, default="", nullable=False)
    domain_tags: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    
    # Dates & Logistics
    deadline: Mapped[date] = mapped_column(Date, nullable=True, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    reward_or_stipend: Mapped[str] = mapped_column(String(128), default="", nullable=True)
    location_type: Mapped[str] = mapped_column(String(32), default="REMOTE", nullable=False)
    location: Mapped[str] = mapped_column(String(128), default="", nullable=True)
    external_url: Mapped[str] = mapped_column(String(512), nullable=False)
    
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(128), default="University Portal", nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    embedding_version: Mapped[str] = mapped_column(String(64), default="all-MiniLM-L6-v2", nullable=False)

    # Relationships
    saved_by = relationship("SavedOpportunityModel", back_populates="opportunity", cascade="all, delete-orphan")

    def get_eligible_departments_list(self) -> List[str]:
        return [d.strip() for d in self.eligible_departments.split(";") if d.strip()]

    def get_eligible_years_list(self) -> List[int]:
        return [int(y.strip()) for y in self.eligible_years.split(";") if y.strip().isdigit()]

    def get_required_skills_list(self) -> List[str]:
        return [s.strip() for s in self.required_skills.split(";") if s.strip()]

    def get_domain_tags_list(self) -> List[str]:
        return [d.strip() for d in self.domain_tags.split(";") if d.strip()]
