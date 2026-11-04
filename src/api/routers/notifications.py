"""
src/api/routers/notifications.py
================================
Notification alerts, unread counters, and automated dispatch triggers.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, require_student_role
from src.api.schemas.notification import NotificationResponse
from src.database.connection import get_db
from src.database.models.opportunity import OpportunityModel
from src.database.models.saved_opportunity import SavedOpportunityModel
from src.database.models.user import UserModel
from src.database.repositories.notification_repository import NotificationRepository
from src.recommendation.schemas.opportunity import Opportunity
from src.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/{student_id}", response_model=List[NotificationResponse])
def get_student_notifications(
    student_id: str,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Retrieve notifications, deadline reminders, and verification updates."""
    repo = NotificationRepository(db)
    items = repo.list_by_student(student_id, unread_only=unread_only)
    return [
        NotificationResponse(
            notification_id=n.notification_id,
            student_id=n.student_id,
            title=n.title,
            message=n.message,
            notification_type=n.notification_type,
            is_read=n.is_read,
            created_at=n.created_at,
            scheduled_at=n.scheduled_at,
            sent_at=n.sent_at,
        )
        for n in items
    ]


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Mark a notification as read."""
    repo = NotificationRepository(db)
    success = repo.mark_as_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")
    db.commit()
    return {"status": "SUCCESS", "notification_id": notification_id}


@router.post("/generate/{student_id}")
def generate_student_notifications(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Idempotently evaluate upcoming deadlines and dispatch alert records."""
    notif_service = NotificationService(db)

    # Fetch saved opportunities
    saved_records = (
        db.query(SavedOpportunityModel)
        .filter(SavedOpportunityModel.student_id == student_id)
        .all()
    )
    opp_ids = [s.opportunity_id for s in saved_records]
    opp_models = (
        db.query(OpportunityModel)
        .filter(OpportunityModel.opportunity_id.in_(opp_ids))
        .all()
    )

    opp_schemas = []
    for o in opp_models:
        opp_schemas.append(
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
            )
        )

    dispatched = notif_service.dispatch_deadline_alerts(student_id, opp_schemas)
    db.commit()

    return {"status": "SUCCESS", "dispatched_count": len(dispatched)}
