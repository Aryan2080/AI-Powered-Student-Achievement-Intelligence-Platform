"""
src/api/routers/students.py
===========================
Student profile management and academic intelligence endpoints.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, require_student_role
from src.api.schemas.student import StudentProfileResponse, StudentUpdate
from src.core.exceptions import EntityNotFoundException
from src.database.connection import get_db
from src.database.models.student import StudentModel
from src.database.models.user import UserModel
from src.database.repositories.achievement_repository import AchievementRepository
from src.database.repositories.student_repository import StudentRepository

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/profile/{student_id}", response_model=StudentProfileResponse)
def get_student_profile(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Retrieve verified profile, GPA, declared and verified skills for a student."""
    repo = StudentRepository(db)
    ach_repo = AchievementRepository(db)

    stu = repo.get_by_id(student_id)
    if not stu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found.",
        )

    achievements = ach_repo.list_by_student(student_id)
    verified_ach = [a for a in achievements if a.evidence_status == "VERIFIED"]

    # Deduplicate verified skills
    verified_skills = set()
    for a in verified_ach:
        for sk in a.get_skills_list():
            verified_skills.add(sk)

    return StudentProfileResponse(
        student_id=stu.student_id,
        user_id=stu.user_id,
        full_name=stu.user.full_name if stu.user else "Student",
        email=stu.user.email if stu.user else "",
        department=stu.department,
        program=stu.program,
        year_of_study=stu.year_of_study,
        gpa=stu.gpa,
        declared_skills=stu.get_declared_skills_list(),
        declared_interests=stu.get_declared_interests_list(),
        verified_skills=sorted(list(verified_skills)),
        career_goals=stu.career_goals,
        achievement_count=len(achievements),
        verified_achievement_count=len(verified_ach),
    )


@router.patch("/{student_id}", response_model=StudentProfileResponse)
def update_student_profile(
    student_id: str,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_student_role),
):
    """Update student declared skills, interests, GPA, or department preferences."""
    repo = StudentRepository(db)
    stu = repo.get_by_id(student_id)
    if not stu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found.",
        )

    if payload.department is not None:
        stu.department = payload.department
    if payload.year_of_study is not None:
        stu.year_of_study = payload.year_of_study
    if payload.gpa is not None:
        stu.gpa = payload.gpa
    if payload.declared_skills is not None:
        stu.declared_skills = ";".join(payload.declared_skills)
    if payload.declared_interests is not None:
        stu.declared_interests = ";".join(payload.declared_interests)
    if payload.career_goals is not None:
        stu.career_goals = payload.career_goals

    db.commit()
    return get_student_profile(student_id=student_id, db=db, current_user=current_user)
