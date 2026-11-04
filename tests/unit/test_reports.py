"""Unit tests for transcript and report generation."""
from src.database.models.achievement import AchievementModel
from src.database.models.student import StudentModel
from src.services.report_generator import ReportGenerator


def test_pdf_transcript_starts_with_valid_pdf_magic():
    gen = ReportGenerator()
    student = StudentModel(
        student_id="STU-TEST-01",
        user_id="USR-01",
        department="Computer Science",
        program="B.Tech",
        year_of_study=3,
        gpa=8.9,
    )
    achievements = [
        AchievementModel(
            achievement_id="ACH-01",
            student_id="STU-TEST-01",
            title="Winner SIH 2024",
            description="Built emergency vehicle corridor system.",
            normalized_text="winner sih 2024",
            category="HACKATHON",
            level="NATIONAL",
            evidence_status="VERIFIED",
        )
    ]

    pdf_bytes = gen.generate_student_transcript_pdf(student, achievements)
    assert len(pdf_bytes) > 200
    assert pdf_bytes.startswith(b"%PDF-1.")
