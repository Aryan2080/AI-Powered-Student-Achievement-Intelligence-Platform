"""API Routers package."""
from .auth import router as auth_router
from .students import router as students_router
from .achievements import router as achievements_router
from .opportunities import router as opportunities_router
from .recommendations import router as recommendations_router
from .faculty import router as faculty_router
from .analytics import router as analytics_router
from .notifications import router as notifications_router
from .reports import router as reports_router

__all__ = [
    "auth_router",
    "students_router",
    "achievements_router",
    "opportunities_router",
    "recommendations_router",
    "faculty_router",
    "analytics_router",
    "notifications_router",
    "reports_router",
]
