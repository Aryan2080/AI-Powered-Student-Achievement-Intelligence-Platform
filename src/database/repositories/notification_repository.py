"""
src/database/repositories/notification_repository.py
====================================================
Persistence and idempotency management for student notifications.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models.notification import NotificationModel


class NotificationRepository:
    """Repository handling student notifications with deduplication."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_dedupe_key(self, dedupe_key: str) -> Optional[NotificationModel]:
        stmt = select(NotificationModel).where(NotificationModel.dedupe_key == dedupe_key)
        return self.db.scalars(stmt).first()

    def list_by_student(
        self, student_id: str, unread_only: bool = False, limit: int = 20
    ) -> List[NotificationModel]:
        stmt = select(NotificationModel).where(NotificationModel.student_id == student_id)
        if unread_only:
            stmt = stmt.where(NotificationModel.is_read == False)
        stmt = stmt.order_by(NotificationModel.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create(self, notification: NotificationModel) -> Optional[NotificationModel]:
        """Insert notification idempotently using dedupe_key."""
        existing = self.get_by_dedupe_key(notification.dedupe_key)
        if existing:
            return existing
        self.db.add(notification)
        self.db.flush()
        return notification

    def mark_as_read(self, notification_id: str) -> bool:
        stmt = select(NotificationModel).where(NotificationModel.notification_id == notification_id)
        n = self.db.scalars(stmt).first()
        if n:
            n.is_read = True
            self.db.flush()
            return True
        return False
