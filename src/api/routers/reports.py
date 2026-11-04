"""
src/api/routers/reports.py
==========================
Document export endpoints: Official PDF Transcripts and Department CSV Analytics.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, require_faculty_role
from src.database.connection import get_db
from src.database.models.achievement import AchievementModel
from src.database.models.user import UserModel
from src.database.repositories.achievement_repository import AchievementRepository
from src.database.repositories.student_repository import StudentRepository
from src.services.report_generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["Reports"])
report_generator = ReportGenerator()


@router.get("/transcript/{student_id}")
def download_student_transcript(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Generate and download official, cryptographically signed Student Achievement Transcript (PDF)."""
    stu_repo = StudentRepository(db)
    ach_repo = AchievementRepository(db)

    student = stu_repo.get_by_id(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found.",
        )

    achievements = ach_repo.list_by_student(student_id)
    pdf_bytes = report_generator.generate_student_transcript_pdf(student, achievements)

    filename = f"Transcript_{student_id}_{student.department.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/department/{department}")
def download_department_report(
    department: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_faculty_role),
):
    """Download departmental achievement intelligence and skill distribution summary (CSV)."""
    stu_repo = StudentRepository(db)
    students = stu_repo.list_by_department(department)
    student_ids = [s.student_id for s in students]

    all_ach = (
        db.query(AchievementModel)
        .filter(AchievementModel.student_id.in_(student_ids))
        .all()
        if student_ids
        else []
    )

    cat_counts = dict(Counter(a.category for a in all_ach))
    
    skill_counts = Counter()
    for a in all_ach:
        for sk in a.get_skills_list():
            skill_counts[sk] += 1

    top_skills = [{"skill": k, "count": v} for k, v in skill_counts.most_common(15)]
    csv_str = report_generator.generate_department_analytics_csv(
        department=department,
        student_count=len(students),
        category_counts=cat_counts,
        top_skills=top_skills,
    )

    filename = f"Department_Report_{department.replace(' ', '_')}.csv"
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
