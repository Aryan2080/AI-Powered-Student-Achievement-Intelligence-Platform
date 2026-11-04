"""
tests/e2e/test_full_system_flow.py
==================================
End-to-end integration and system lifecycle test across Member 1, Member 2, and Member 3 subsystems.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

import uuid
from datetime import date
from src.database.connection import SessionLocal, init_db
from src.database.models.student import StudentModel
from src.database.models.user import UserModel
from src.integration.full_pipeline_adapter import FullPipelineAdapter
from src.services.notification_service import NotificationService
from src.services.report_generator import ReportGenerator


def test_full_system_lifecycle_e2e():
    init_db()
    db = SessionLocal()
    pipeline = FullPipelineAdapter()
    notif_service = NotificationService(db)
    report_gen = ReportGenerator()

    try:
        # 1. Create a Test Student
        uid = f"USR-E2E-{uuid.uuid4().hex[:6]}"
        sid = f"STU-E2E-{uuid.uuid4().hex[:6]}"

        user = UserModel(
            id=uid,
            email=f"{uid.lower()}@university.edu",
            hashed_password="hashed_secret",
            role="STUDENT",
            full_name="E2E Test Student",
            department="Computer Science",
            is_active=True,
        )
        db.add(user)
        db.flush()

        student = StudentModel(
            student_id=sid,
            user_id=uid,
            department="Computer Science",
            program="B.Tech",
            year_of_study=3,
            gpa=8.95,
            declared_skills="Python;PyTorch",
            declared_interests="Artificial Intelligence;Computer Vision",
        )
        db.add(student)
        db.commit()

        # 2. Ingest Raw Achievement Submission
        ach = pipeline.process_and_ingest_achievement(
            db=db,
            student_id=sid,
            title="Winner (1st Prize) at National Autonomous Robotics Hackathon",
            description="Built real-time drone obstacle navigation using Python, OpenCV, and PyTorch.",
            level="NATIONAL",
            achievement_date=date(2025, 11, 1),
            verified_flag=True,
        )
        db.commit()

        assert ach.achievement_id is not None
        assert ach.category in ["HACKATHON", "PROJECT"]
        assert "OpenCV" in ach.skills or "Python" in ach.skills

        # 3. Trigger Recommendation Refresh
        recs_response = pipeline.get_refreshed_recommendations(db=db, student_id=sid, top_k=5)
        assert recs_response.student_id == sid
        assert len(recs_response.recommendations) > 0

        first_rec = recs_response.recommendations[0]
        assert first_rec.match_score > 0.0
        assert first_rec.explanation is not None
        assert len(first_rec.explanation) > 10

        # 4. Trigger Notification Dispatch
        notif = notif_service.dispatch_verification_alert(
            student_id=sid,
            achievement_title=ach.title,
            status="VERIFIED",
            remarks="Verified by E2E Test Suite",
        )
        db.commit()
        assert notif.notification_id is not None

        # 5. Generate Official PDF Transcript
        pdf_bytes = report_gen.generate_student_transcript_pdf(student, [ach])
        assert pdf_bytes.startswith(b"%PDF-1.")
        assert len(pdf_bytes) > 200

        print(f"\n[E2E SUCCESS] Successfully verified full lifecycle for student {sid}")

    finally:
        db.close()
