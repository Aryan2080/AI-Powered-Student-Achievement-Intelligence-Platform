"""
src/services/notification_service.py
====================================
Automated event-driven notification dispatching with idempotent deduplication keys.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from src.core.logging import logger
from src.database.models.notification import NotificationModel
from src.database.repositories.notification_repository import NotificationRepository
from src.recommendation.schemas.opportunity import Opportunity


class NotificationService:
    """Dispatches in-app alerts and notifications with guaranteed idempotency."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = NotificationRepository(db)

    def dispatch_deadline_alerts(
        self,
        student_id: str,
        saved_opportunities: List[Opportunity],
        reference_date: Optional[date] = None,
    ) -> List[NotificationModel]:
        """Dispatch notifications for saved opportunities approaching deadline (7d, 2d, 24h)."""
        ref = reference_date or date.today()
        dispatched: List[NotificationModel] = []

        for opp in saved_opportunities:
            if not opp.deadline:
                continue

            opp_deadline = opp.deadline
            if isinstance(opp_deadline, str):
                opp_deadline = date.fromisoformat(opp_deadline)

            days_left = (opp_deadline - ref).days
            alert_type = None

            if days_left == 7:
                alert_type = "DEADLINE_7D"
                title = f"Reminder: 7 Days Left for {opp.title}"
                msg = f"The deadline for {opp.title} hosted by {opp.organization} is in 7 days ({opp_deadline}). Complete your application today."
            elif days_left == 2:
                alert_type = "DEADLINE_2D"
                title = f"Urgent: 2 Days Left for {opp.title}"
                msg = f"Only 2 days remaining to apply for {opp.title}! Deadline: {opp_deadline}."
            elif days_left == 1:
                alert_type = "DEADLINE_24H"
                title = f"Final Call: 24 Hours Left for {opp.title}"
                msg = f"Final 24 hours to submit your application for {opp.title}. Don't miss this opportunity!"

            if alert_type:
                dedupe = f"{alert_type}-{student_id}-{opp.opportunity_id}-{opp_deadline.isoformat()}"
                notif = NotificationModel(
                    notification_id=f"NOTIF-{uuid.uuid4().hex[:12]}",
                    student_id=student_id,
                    title=title,
                    message=msg,
                    notification_type=alert_type,
                    dedupe_key=dedupe,
                    is_read=False,
                    scheduled_at=datetime.now(timezone.utc),
                )
                saved = self.repo.create(notif)
                if saved:
                    dispatched.append(saved)

        return dispatched

    def dispatch_verification_alert(
        self,
        student_id: str,
        achievement_title: str,
        status: str,  # VERIFIED or REJECTED
        remarks: Optional[str] = None,
    ) -> NotificationModel:
        """Alert student when faculty updates achievement verification status."""
        is_verified = (status.upper() == "VERIFIED")
        title = f"Achievement {status.capitalize()}: {achievement_title}"
        msg = (
            f"Your submitted achievement '{achievement_title}' has been reviewed and marked as {status.upper()}."
        )
        if remarks:
            msg += f" Remarks: {remarks}"

        dedupe = f"VERIFY-{student_id}-{hash(achievement_title)}-{status}-{date.today().isoformat()}"
        notif = NotificationModel(
            notification_id=f"NOTIF-{uuid.uuid4().hex[:12]}",
            student_id=student_id,
            title=title,
            message=msg,
            notification_type="VERIFICATION_STATUS",
            dedupe_key=dedupe,
            is_read=False,
            scheduled_at=datetime.now(timezone.utc),
        )
        return self.repo.create(notif)

    def dispatch_high_match_alert(
        self, student_id: str, opportunity: Opportunity, match_score: float
    ) -> Optional[NotificationModel]:
        """Alert student when a new high-match opportunity (> 85%) is discovered."""
        if match_score < 0.85:
            return None

        pct = int(match_score * 100)
        title = f"New {pct}% Match Opportunity: {opportunity.title}"
        msg = (
            f"We found an exceptional opportunity matching your profile ({pct}% alignment): "
            f"{opportunity.title} by {opportunity.organization}."
        )
        dedupe = f"MATCH_HIGH-{student_id}-{opportunity.opportunity_id}"
        notif = NotificationModel(
            notification_id=f"NOTIF-{uuid.uuid4().hex[:12]}",
            student_id=student_id,
            title=title,
            message=msg,
            notification_type="HIGH_MATCH",
            dedupe_key=dedupe,
            is_read=False,
            scheduled_at=datetime.now(timezone.utc),
        )
        return self.repo.create(notif)
