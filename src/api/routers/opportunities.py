"""
src/api/routers/opportunities.py
================================
Opportunity catalog browsing, bookmarking, and application tracking endpoints.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, require_student_role
from src.database.connection import get_db
from src.database.models.opportunity import OpportunityModel
from src.database.models.saved_opportunity import SavedOpportunityModel
from src.database.models.user import UserModel
from src.database.repositories.opportunity_repository import OpportunityRepository
from src.recommendation.schemas.opportunity import Opportunity

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])


@router.get("", response_model=List[Opportunity])
def list_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    opportunity_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query("ACTIVE", alias="status"),
    db: Session = Depends(get_db),
):
    """Browse catalog of verified hackathons, internships, grants, competitions, and conferences."""
    repo = OpportunityRepository(db)
    items = repo.list_all(skip=skip, limit=limit, opportunity_type=opportunity_type, status=status_filter)
    
    # If database catalog is empty, read directly from memory service / JSON
    if not items:
        from src.recommendation.engine.recommendation_service import RecommendationService
        service = RecommendationService()
        filtered = service.opportunities
        if opportunity_type:
            filtered = [o for o in filtered if o.opportunity_type == opportunity_type or o.opportunity_type.value == opportunity_type]
        return filtered[skip : skip + limit]

    return [
        Opportunity(
            opportunity_id=o.opportunity_id,
            title=o.title,
            description=o.description,
            opportunity_type=o.opportunity_type,
            organization=o.organization,
            eligible_departments=o.get_eligible_departments_list(),
            eligible_years=o.get_eligible_years_list(),
            eligible_degree=o.eligible_degree.split(";"),
            min_gpa=o.min_gpa,
            required_skills=o.get_required_skills_list(),
            preferred_skills=o.preferred_skills.split(";") if o.preferred_skills else [],
            domain_tags=o.get_domain_tags_list(),
            deadline=o.deadline,
            start_date=o.start_date,
            end_date=o.end_date,
            reward_or_stipend=o.reward_or_stipend,
            location_type=o.location_type,
            location=o.location,
            external_url=o.external_url,
            status=o.status,
            source_name=o.source_name,
            text_hash=o.text_hash,
            embedding_version=o.embedding_version,
        )
        for o in items
    ]


@router.get("/{opportunity_id}", response_model=Opportunity)
def get_opportunity(opportunity_id: str, db: Session = Depends(get_db)):
    """Retrieve full eligibility criteria and details for a single opportunity."""
    repo = OpportunityRepository(db)
    o = repo.get_by_id(opportunity_id)
    if not o:
        from src.recommendation.engine.recommendation_service import RecommendationService
        service = RecommendationService()
        opp = service.opportunity_map.get(opportunity_id)
        if opp:
            return opp
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity '{opportunity_id}' not found.",
        )

    return Opportunity(
        opportunity_id=o.opportunity_id,
        title=o.title,
        description=o.description,
        opportunity_type=o.opportunity_type,
        organization=o.organization,
        eligible_departments=o.get_eligible_departments_list(),
        eligible_years=o.get_eligible_years_list(),
        eligible_degree=o.eligible_degree.split(";"),
        min_gpa=o.min_gpa,
        required_skills=o.get_required_skills_list(),
        preferred_skills=o.preferred_skills.split(";") if o.preferred_skills else [],
        domain_tags=o.get_domain_tags_list(),
        deadline=o.deadline,
        start_date=o.start_date,
        end_date=o.end_date,
        reward_or_stipend=o.reward_or_stipend,
        location_type=o.location_type,
        location=o.location,
        external_url=o.external_url,
        status=o.status,
        source_name=o.source_name,
        text_hash=o.text_hash,
        embedding_version=o.embedding_version,
    )


@router.post("/{opportunity_id}/save")
def save_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_student_role),
):
    """Bookmark an opportunity to track deadlines and receive alert nudges."""
    student = current_user.student_profile
    if not student:
        raise HTTPException(status_code=400, detail="Student profile missing.")

    existing = (
        db.query(SavedOpportunityModel)
        .filter(
            SavedOpportunityModel.student_id == student.student_id,
            SavedOpportunityModel.opportunity_id == opportunity_id,
        )
        .first()
    )

    if existing:
        existing.status = "SAVED"
    else:
        saved_rec = SavedOpportunityModel(
            student_id=student.student_id,
            opportunity_id=opportunity_id,
            status="SAVED",
            saved_at=datetime.now(timezone.utc),
        )
        db.add(saved_rec)

    db.commit()
    return {"status": "SUCCESS", "message": f"Opportunity {opportunity_id} saved."}


@router.post("/{opportunity_id}/apply")
def apply_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_student_role),
):
    """Mark an opportunity as applied for portfolio tracking."""
    student = current_user.student_profile
    if not student:
        raise HTTPException(status_code=400, detail="Student profile missing.")

    existing = (
        db.query(SavedOpportunityModel)
        .filter(
            SavedOpportunityModel.student_id == student.student_id,
            SavedOpportunityModel.opportunity_id == opportunity_id,
        )
        .first()
    )

    now = datetime.now(timezone.utc)
    if existing:
        existing.status = "APPLIED"
        existing.applied_at = now
    else:
        applied_rec = SavedOpportunityModel(
            student_id=student.student_id,
            opportunity_id=opportunity_id,
            status="APPLIED",
            saved_at=now,
            applied_at=now,
        )
        db.add(applied_rec)

    db.commit()
    return {"status": "SUCCESS", "message": f"Applied to opportunity {opportunity_id}."}


@router.get("/saved/student/{student_id}")
def get_saved_opportunities(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """List bookmarked and applied opportunities for a student."""
    saved_items = (
        db.query(SavedOpportunityModel)
        .filter(SavedOpportunityModel.student_id == student_id)
        .all()
    )
    return [
        {
            "opportunity_id": s.opportunity_id,
            "status": s.status,
            "saved_at": s.saved_at,
            "applied_at": s.applied_at,
        }
        for s in saved_items
    ]
