"""
src/api/routers/faculty.py
==========================
Faculty institutional portal: Verification Queue, Achievement Review, and Talent Discovery Search.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies import require_faculty_role
from src.api.schemas.achievement import AchievementResponse, VerificationUpdateDTO
from src.database.connection import get_db
from src.database.models.achievement import AchievementModel
from src.database.models.student import StudentModel
from src.database.models.user import UserModel
from src.database.repositories.achievement_repository import AchievementRepository
from src.database.repositories.student_repository import StudentRepository
from src.services.notification_service import NotificationService

router = APIRouter(prefix="/faculty", tags=["Faculty"])


@router.get("/verification-queue", response_model=List[AchievementResponse])
def get_verification_queue(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_faculty_role),
):
    """Retrieve pending achievement submissions awaiting departmental audit."""
    repo = AchievementRepository(db)
    pending = repo.list_pending(skip=skip, limit=limit)

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
        for a in pending
    ]


@router.post("/verify/{achievement_id}", response_model=AchievementResponse)
def verify_achievement(
    achievement_id: str,
    payload: VerificationUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_faculty_role),
):
    """Approve or Reject an achievement submission, dispatching an audit notification to the student."""
    repo = AchievementRepository(db)
    fac_id = current_user.faculty_profile.faculty_id if current_user.faculty_profile else current_user.id

    updated = repo.update_verification(
        achievement_id=achievement_id,
        status=payload.status.upper(),
        remarks=payload.remarks or "",
        faculty_id=fac_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Achievement '{achievement_id}' not found.",
        )

    db.commit()

    # Trigger notification
    notif_service = NotificationService(db)
    notif_service.dispatch_verification_alert(
        student_id=updated.student_id,
        achievement_title=updated.title,
        status=updated.evidence_status,
        remarks=payload.remarks,
    )
    db.commit()

    return AchievementResponse(
        achievement_id=updated.achievement_id,
        student_id=updated.student_id,
        source_achievement_id=updated.source_achievement_id,
        title=updated.title,
        description=updated.description,
        normalized_text=updated.normalized_text,
        category=updated.category,
        domain_tags=updated.get_domain_tags_list(),
        skills=updated.get_skills_list(),
        level=updated.level,
        achievement_date=updated.achievement_date,
        evidence_status=updated.evidence_status,
        evidence_url=updated.evidence_url,
        verification_remarks=updated.verification_remarks,
        extraction_confidence=updated.extraction_confidence,
        classifier_confidence=updated.classifier_confidence,
        source_pipeline_version=updated.source_pipeline_version,
        classifier_model_version=updated.classifier_model_version,
        created_at=updated.created_at,
    )


@router.get("/talent-search")
def search_student_talent(
    skill: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    min_gpa: Optional[float] = Query(0.0),
    min_year: Optional[int] = Query(1),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_faculty_role),
):
    """Filter students by verified skills, domain competence, GPA, and academic year."""
    stu_repo = StudentRepository(db)
    ach_repo = AchievementRepository(db)

    students = stu_repo.list_all(skip=0, limit=200)
    matched_results = []

    for s in students:
        if department and s.department.lower() != department.lower():
            continue
        if s.gpa < min_gpa or s.year_of_study < min_year:
            continue

        achievements = ach_repo.list_by_student(s.student_id, status="VERIFIED")
        verified_skills = set()
        for a in achievements:
            for sk in a.get_skills_list():
                verified_skills.add(sk.lower())

        if skill and skill.lower() not in verified_skills and skill.lower() not in s.declared_skills.lower():
            continue

        matched_results.append({
            "student_id": s.student_id,
            "full_name": s.user.full_name if s.user else "Student",
            "department": s.department,
            "year": s.year_of_study,
            "gpa": s.gpa,
            "verified_achievements_count": len(achievements),
            "verified_skills": sorted(list(verified_skills)),
            "declared_skills": s.get_declared_skills_list(),
        })

    return matched_results
