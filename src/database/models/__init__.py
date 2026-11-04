"""Database models package."""
from src.database.models.user import UserModel
from src.database.models.student import StudentModel
from src.database.models.faculty import FacultyModel
from src.database.models.achievement import AchievementModel
from src.database.models.opportunity import OpportunityModel
from src.database.models.recommendation import RecommendationSnapshotModel, RecommendationItemModel
from src.database.models.saved_opportunity import SavedOpportunityModel
from src.database.models.notification import NotificationModel
from src.database.models.audit_event import AuditEventModel

__all__ = [
    "UserModel",
    "StudentModel",
    "FacultyModel",
    "AchievementModel",
    "OpportunityModel",
    "RecommendationSnapshotModel",
    "RecommendationItemModel",
    "SavedOpportunityModel",
    "NotificationModel",
    "AuditEventModel",
]
