"""
src/database/repositories/opportunity_repository.py
===================================================
Database queries and filters for the opportunity corpus.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models.opportunity import OpportunityModel


class OpportunityRepository:
    """Repository handling Opportunity catalog queries and filters."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, opportunity_id: str) -> Optional[OpportunityModel]:
        stmt = select(OpportunityModel).where(OpportunityModel.opportunity_id == opportunity_id)
        return self.db.scalars(stmt).first()

    def list_all(
        self,
        skip: int = 0,
        limit: int = 50,
        opportunity_type: Optional[str] = None,
        status: Optional[str] = "ACTIVE",
    ) -> List[OpportunityModel]:
        stmt = select(OpportunityModel)
        if status:
            stmt = stmt.where(OpportunityModel.status == status)
        if opportunity_type:
            stmt = stmt.where(OpportunityModel.opportunity_type == opportunity_type)
        stmt = stmt.order_by(OpportunityModel.deadline.asc().nullslast()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create(self, opportunity: OpportunityModel) -> OpportunityModel:
        self.db.add(opportunity)
        self.db.flush()
        return opportunity
