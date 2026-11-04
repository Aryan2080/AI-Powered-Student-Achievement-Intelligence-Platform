"""
src/api/routers/achievements.py
===============================
Achievement intake, idempotent upstream ingestion, and student achievement query routes.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, require_student_role
from src.api.schemas.achievement import (
    AchievementCreate,
    AchievementIngestDTO,
    AchievementResponse,
)
from src.database.connection import get_db
from src.database.models.achievement import AchievementModel
from src.database.models.user import UserModel
from src.database.repositories.achievement_repository import AchievementRepository
from src.database.repositories.student_repository import StudentRepository
from src.integration.full_pipeline_adapter import FullPipelineAdapter

router = APIRouter(prefix="/achievements", tags=["Achievements"])
pipeline = FullPipelineAdapter()


@router.post("", response_model=AchievementResponse, status_code=status.HTTP_201_CREATED)
def submit_achievement(
    payload: AchievementCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_student_role),
):
    """Submit a student achievement for NLP entity extraction, ML categorization, and faculty audit."""
    stu_repo = StudentRepository(db)
    student = stu_repo.get_by_user_id(current_user.id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found for authenticated user.",
        )

    created_ach = pipeline.process_and_ingest_achievement(
        db=db,
        student_id=student.student_id,
        title=payload.title,
        description=payload.description,
        level=payload.level,
        achievement_date=payload.achievement_date,
        evidence_url=payload.evidence_url,
        verified_flag=False,  # Submissions enter PENDING review queue
    )
    db.commit()

    return AchievementResponse(
        achievement_id=created_ach.achievement_id,
        student_id=created_ach.student_id,
        source_achievement_id=created_ach.source_achievement_id,
        title=created_ach.title,
        description=created_ach.description,
        normalized_text=created_ach.normalized_text,
        category=created_ach.category,
        domain_tags=created_ach.get_domain_tags_list(),
        skills=created_ach.get_skills_list(),
        level=created_ach.level,
        achievement_date=created_ach.achievement_date,
        evidence_status=created_ach.evidence_status,
        evidence_url=created_ach.evidence_url,
        verification_remarks=created_ach.verification_remarks,
        extraction_confidence=created_ach.extraction_confidence,
        classifier_confidence=created_ach.classifier_confidence,
        source_pipeline_version=created_ach.source_pipeline_version,
        classifier_model_version=created_ach.classifier_model_version,
        created_at=created_ach.created_at,
    )


@router.post("/ingest", response_model=AchievementResponse, status_code=status.HTTP_200_OK)
def ingest_upstream_achievement(
    payload: AchievementIngestDTO,
    db: Session = Depends(get_db),
):
    """Idempotent ingestion endpoint consuming upstream verified records from Member 1 or Member 2."""
    ach_repo = AchievementRepository(db)
    stu_repo = StudentRepository(db)

    student = stu_repo.get_by_id(payload.student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target student '{payload.student_id}' does not exist.",
        )

    # Check idempotency key
    existing = ach_repo.get_by_student_and_source(payload.student_id, payload.source_achievement_id)
    if existing:
        return AchievementResponse(
            achievement_id=existing.achievement_id,
            student_id=existing.student_id,
            source_achievement_id=existing.source_achievement_id,
            title=existing.title,
            description=existing.description,
            normalized_text=existing.normalized_text,
            category=existing.category,
            domain_tags=existing.get_domain_tags_list(),
            skills=existing.get_skills_list(),
            level=existing.level,
            achievement_date=existing.achievement_date,
            evidence_status=existing.evidence_status,
            evidence_url=existing.evidence_url,
            verification_remarks=existing.verification_remarks,
            extraction_confidence=existing.extraction_confidence,
            classifier_confidence=existing.classifier_confidence,
            source_pipeline_version=existing.source_pipeline_version,
            classifier_model_version=existing.classifier_model_version,
            created_at=existing.created_at,
        )

    norm_text = pipeline.nlp.clean_and_normalize(f"{payload.title}. {payload.description}")
    ach_id = f"ACH-{payload.student_id[:8]}-{uuid.uuid4().hex[:6]}"

    record = AchievementModel(
        achievement_id=ach_id,
        student_id=payload.student_id,
        source_achievement_id=payload.source_achievement_id,
        title=payload.title,
        description=payload.description,
        normalized_text=norm_text,
        category=payload.category or "PROJECT",
        domain_tags=";".join(payload.domain_tags or []),
        skills=";".join(payload.skills or []),
        level=payload.level.upper(),
        achievement_date=payload.achievement_date,
        evidence_status=payload.evidence_status,
        evidence_url=payload.evidence_url or "",
        extraction_confidence=payload.extraction_confidence,
        classifier_confidence=payload.classifier_confidence,
        source_pipeline_version=payload.source_pipeline_version,
        classifier_model_version=payload.classifier_model_version,
    )

    created = ach_repo.create(record)
    db.commit()

    return AchievementResponse(
        achievement_id=created.achievement_id,
        student_id=created.student_id,
        source_achievement_id=created.source_achievement_id,
        title=created.title,
        description=created.description,
        normalized_text=created.normalized_text,
        category=created.category,
        domain_tags=created.get_domain_tags_list(),
        skills=created.get_skills_list(),
        level=created.level,
        achievement_date=created.achievement_date,
        evidence_status=created.evidence_status,
        evidence_url=created.evidence_url,
        verification_remarks=created.verification_remarks,
        extraction_confidence=created.extraction_confidence,
        classifier_confidence=created.classifier_confidence,
        source_pipeline_version=created.source_pipeline_version,
        classifier_model_version=created.classifier_model_version,
        created_at=created.created_at,
    )


@router.get("/student/{student_id}", response_model=List[AchievementResponse])
def get_student_achievements(
    student_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """List achievements for a specific student, separated by evidence verification status."""
    repo = AchievementRepository(db)
    items = repo.list_by_student(student_id, status=status_filter)

    return [
        AchievementResponse(
            achievement_id=a.achievement_id,
            student_id=a.student_id,
            source_achievement_id=a.source_achievement_id,
            title=a.title,
            description=a.description,
            normalized_text=a.normalized_text,
            category=a.category,
            domain_tags=a.get_domain_tags_list(),
            skills=a.get_skills_list(),
            level=a.level,
            achievement_date=a.achievement_date,
            evidence_status=a.evidence_status,
            evidence_url=a.evidence_url,
            verification_remarks=a.verification_remarks,
            extraction_confidence=a.extraction_confidence,
            classifier_confidence=a.classifier_confidence,
            source_pipeline_version=a.source_pipeline_version,
            classifier_model_version=a.classifier_model_version,
            created_at=a.created_at,
        )
        for a in items
    ]
