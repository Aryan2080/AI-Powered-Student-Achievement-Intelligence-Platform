"""
src/api/main.py
===============
FastAPI Application Entry Point & Router Assembly.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routers import (
    achievements_router,
    analytics_router,
    auth_router,
    faculty_router,
    notifications_router,
    opportunities_router,
    recommendations_router,
    reports_router,
    students_router,
)
from src.core.config import settings
from src.core.exceptions import (
    BasePlatformException,
    DuplicateRecordException,
    EntityNotFoundException,
    IneligibleOpportunityException,
    UnauthorizedAccessException,
)
from src.core.logging import logger
from src.database.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and teardown events."""
    logger.info("Starting up %s (Version %s)...", settings.PROJECT_NAME, settings.APP_VERSION)
    try:
        init_db()
    except Exception as e:
        logger.error("Failed to initialize database schema: %s", e)
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.APP_VERSION,
        description=(
            "Enterprise backend API for Personalized Opportunity Recommendations, "
            "Achievement Intelligence, and Institutional Verification."
        ),
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request Processing Time Middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(process_time)
        return response

    # Global Exception Handlers
    @app.exception_handler(EntityNotFoundException)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundException):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Not Found", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(DuplicateRecordException)
    async def duplicate_record_handler(request: Request, exc: DuplicateRecordException):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "Conflict", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(UnauthorizedAccessException)
    async def unauthorized_handler(request: Request, exc: UnauthorizedAccessException):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "Forbidden", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(BasePlatformException)
    async def base_exception_handler(request: Request, exc: BasePlatformException):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Bad Request", "message": exc.message, "details": exc.details},
        )

    # Health Check Endpoint
    @app.get("/health", tags=["Health"])
    def health_check():
        """Liveness probe verifying service health and version metadata."""
        return {
            "status": "UP",
            "service": settings.PROJECT_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Mount Versioned API Routers
    api_prefix = settings.API_V1_STR
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(students_router, prefix=api_prefix)
    app.include_router(achievements_router, prefix=api_prefix)
    app.include_router(opportunities_router, prefix=api_prefix)
    app.include_router(recommendations_router, prefix=api_prefix)
    app.include_router(faculty_router, prefix=api_prefix)
    app.include_router(analytics_router, prefix=api_prefix)
    app.include_router(notifications_router, prefix=api_prefix)
    app.include_router(reports_router, prefix=api_prefix)

    return app


app = create_application()
