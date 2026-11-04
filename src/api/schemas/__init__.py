"""API Schemas package."""
from .auth import Token, UserLogin, UserRegister, UserResponse
from .student import StudentUpdate, StudentProfileResponse
from .achievement import AchievementCreate, AchievementIngestDTO, VerificationUpdateDTO, AchievementResponse
from .analytics import StudentAnalyticsResponse, DepartmentAnalyticsResponse, InstitutionalOverviewResponse
from .notification import NotificationResponse

__all__ = [
    "Token",
    "UserLogin",
    "UserRegister",
    "UserResponse",
    "StudentUpdate",
    "StudentProfileResponse",
    "AchievementCreate",
    "AchievementIngestDTO",
    "VerificationUpdateDTO",
    "AchievementResponse",
    "StudentAnalyticsResponse",
    "DepartmentAnalyticsResponse",
    "InstitutionalOverviewResponse",
    "NotificationResponse",
]
