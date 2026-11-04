"""
src/api/schemas/notification.py
================================
Notification DTO schemas.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    notification_id: str
    student_id: str
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime
    scheduled_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True
