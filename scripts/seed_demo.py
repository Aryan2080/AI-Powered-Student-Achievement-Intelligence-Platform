"""
scripts/seed_demo.py
====================
Database seeder initializing demo accounts (Student, Faculty, Admin),
verified & pending student achievements, saved opportunities, and notifications.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.core.config import settings
from src.core.logging import logger
from src.core.security import UserRole, get_password_hash
from src.database.connection import SessionLocal, init_db
from src.database.models.achievement import AchievementModel
from src.database.models.faculty import FacultyModel
from src.database.models.notification import NotificationModel
from src.database.models.opportunity import OpportunityModel
from src.database.models.saved_opportunity import SavedOpportunityModel
from src.database.models.student import StudentModel
from src.database.models.user import UserModel


def seed_database():
    """Seed comprehensive initial demo data into the relational database."""
    print("Initializing database tables...")
    init_db()
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(UserModel).filter(UserModel.email == "student@university.edu").first():
            print("Database is already seeded with demo accounts.")
            return

        print("Creating demo users (Student, Faculty, Admin)...")

        # 1. Student User 1: Active Achiever
        user_stu1 = UserModel(
            id="USR-STU-0001",
            email="student@university.edu",
            hashed_password=get_password_hash("student123"),
            role=UserRole.STUDENT.value,
            full_name="Aarav Sharma",
            department="Computer Science",
            is_active=True,
        )
        db.add(user_stu1)
        db.flush()

        student_1 = StudentModel(
            student_id="STU-2026-0001",
            user_id=user_stu1.id,
            department="Computer Science",
            program="B.Tech",
            year_of_study=3,
            gpa=8.85,
            declared_skills="Python;PyTorch;OpenCV;Git;Docker;SQL",
            declared_interests="Artificial Intelligence;Computer Vision;Autonomous Systems",
            career_goals="Aspiring AI Research & Robotics Engineer",
        )
        db.add(student_1)

        # 2. Student User 2: Cold-Start Freshman
        user_stu2 = UserModel(
            id="USR-STU-0002",
            email="coldstart@university.edu",
            hashed_password=get_password_hash("student123"),
            role=UserRole.STUDENT.value,
            full_name="Priya Patel",
            department="Information Technology",
            is_active=True,
        )
        db.add(user_stu2)
        db.flush()

        student_2 = StudentModel(
            student_id="STU-2026-0002",
            user_id=user_stu2.id,
            department="Information Technology",
            program="B.Tech",
            year_of_study=1,
            gpa=7.80,
            declared_skills="Python;JavaScript;HTML",
            declared_interests="Web Development;Cloud Infrastructure",
            career_goals="Full-Stack Cloud Developer",
        )
        db.add(student_2)

        # 3. Faculty User: Reviewer & Department Chair
        user_fac = UserModel(
            id="USR-FAC-0001",
            email="faculty@university.edu",
            hashed_password=get_password_hash("faculty123"),
            role=UserRole.FACULTY.value,
            full_name="Dr. Rajesh Raman",
            department="Computer Science",
            is_active=True,
        )
        db.add(user_fac)
        db.flush()

        faculty_1 = FacultyModel(
            faculty_id="FAC-2026-0001",
            user_id=user_fac.id,
            department="Computer Science",
            title="Professor & Head of Department",
            permissions="VERIFY_ACHIEVEMENTS;VIEW_ANALYTICS;BROADCAST_OPPORTUNITY",
        )
        db.add(faculty_1)

        # 4. Administrator User
        user_admin = UserModel(
            id="USR-ADM-0001",
            email="admin@university.edu",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN.value,
            full_name="System Administrator",
            department="Academic Affairs",
            is_active=True,
        )
        db.add(user_admin)

        print("Seeding achievements for Student 1...")
        # Achievements for Student 1
        ach_1 = AchievementModel(
            achievement_id="ACH-2026-0001",
            student_id=student_1.student_id,
            source_achievement_id="SRC-SIH2024-WIN",
            title="Winner (1st Prize) at Smart India Hackathon 2024",
            description="Developed an automated traffic violation and emergency vehicle green-corridor management system using YOLOv8, OpenCV, and FastAPI under the Ministry of Road Transport problem statement.",
            normalized_text="winner 1st prize at smart india hackathon 2024 developed traffic violation emergency vehicle management yolov8 opencv fastapi",
            category="HACKATHON",
            domain_tags="lbl_domain_cv;lbl_domain_ai;lbl_domain_systems",
            skills="Python;PyTorch;OpenCV;FastAPI;Docker",
            level="NATIONAL",
            achievement_date=date(2024, 12, 20),
            evidence_status="VERIFIED",
            evidence_url="https://sih.gov.in/certificate/SIH2024-WIN-8912",
            verification_remarks="Verified by Dr. Rajesh Raman with official certificate copy.",
            verified_by_faculty_id=faculty_1.faculty_id,
            extraction_confidence=0.98,
            classifier_confidence=0.96,
            source_pipeline_version="v1.0.1",
            classifier_model_version="v1.0.1",
        )
        db.add(ach_1)

        ach_2 = AchievementModel(
            achievement_id="ACH-2026-0002",
            student_id=student_1.student_id,
            source_achievement_id="SRC-IEEE-PAPER-01",
            title="Research Publication: 'Edge-Optimized Vision Transformers for Real-Time Weed Detection'",
            description="Published as first author in IEEE International Conference on Advanced Robotics & AI. Proposed lightweight attention distillation running at 45 FPS on NVIDIA Jetson.",
            normalized_text="research publication edge-optimized vision transformers for real-time weed detection published first author ieee conference",
            category="RESEARCH_PUBLICATION",
            domain_tags="lbl_domain_ai;lbl_domain_cv;lbl_domain_hardware",
            skills="Python;PyTorch;Computer Vision;Deep Learning",
            level="INTERNATIONAL",
            achievement_date=date(2025, 4, 15),
            evidence_status="VERIFIED",
            evidence_url="https://doi.org/10.1109/ICARAI.2025.10928",
            verification_remarks="Verified via IEEE Xplore DOI index.",
            verified_by_faculty_id=faculty_1.faculty_id,
            extraction_confidence=0.99,
            classifier_confidence=0.97,
            source_pipeline_version="v1.0.1",
            classifier_model_version="v1.0.1",
        )
        db.add(ach_2)

        ach_3 = AchievementModel(
            achievement_id="ACH-2026-0003",
            student_id=student_1.student_id,
            source_achievement_id="SRC-PROJECT-CV-SUBMITTED",
            title="Autonomous Drone Obstacle Avoidance Prototype using ROS2 and LiDAR",
            description="Designed and built a functional quadcopter obstacle avoidance system integrating ROS2, SLAM navigation, and depth camera sensor fusion. Tested in indoor obstacle course.",
            normalized_text="autonomous drone obstacle avoidance prototype using ros2 lidar designed functional quadcopter slam depth camera",
            category="PROJECT",
            domain_tags="lbl_domain_hardware;lbl_domain_systems;lbl_domain_cv",
            skills="C++;Python;Linux;Git;ROS2",
            level="COLLEGE",
            achievement_date=date(2025, 10, 5),
            evidence_status="PENDING",  # Awaiting faculty audit
            evidence_url="https://github.com/student/drone-ros2-obstacle-avoidance",
            verification_remarks="",
            extraction_confidence=0.92,
            classifier_confidence=0.91,
            source_pipeline_version="v1.0.1",
            classifier_model_version="v1.0.1",
        )
        db.add(ach_3)

        print("Importing canonical opportunities from opportunity_dataset.json...")
        if settings.OPPORTUNITIES_JSON_PATH.exists():
            with open(settings.OPPORTUNITIES_JSON_PATH, "r", encoding="utf-8") as f:
                opp_list = json.load(f)

            for item in opp_list:
                opp_m = OpportunityModel(
                    opportunity_id=item["opportunity_id"],
                    title=item["title"],
                    description=item["description"],
                    opportunity_type=item["opportunity_type"],
                    organization=item["organization"],
                    eligible_departments=";".join(item["eligible_departments"]),
                    eligible_years=";".join(str(y) for y in item["eligible_years"]),
                    eligible_degree=";".join(item["eligible_degree"]),
                    min_gpa=item["min_gpa"],
                    required_skills=";".join(item["required_skills"]),
                    preferred_skills=";".join(item["preferred_skills"]),
                    domain_tags=";".join(item["domain_tags"]),
                    deadline=date.fromisoformat(item["deadline"]) if item.get("deadline") else None,
                    start_date=date.fromisoformat(item["start_date"]) if item.get("start_date") else None,
                    end_date=date.fromisoformat(item["end_date"]) if item.get("end_date") else None,
                    reward_or_stipend=item.get("reward_or_stipend", ""),
                    location_type=item.get("location_type", "REMOTE"),
                    location=item.get("location", ""),
                    external_url=item.get("external_url", ""),
                    status=item.get("status", "ACTIVE"),
                    source_name=item.get("source_name", "Portal"),
                    text_hash=item.get("text_hash", ""),
                    embedding_version=item.get("embedding_version", "all-MiniLM-L6-v2"),
                )
                db.add(opp_m)

        print("Seeding saved opportunity and initial notifications...")
        saved_opp = SavedOpportunityModel(
            student_id=student_1.student_id,
            opportunity_id="OPP-2026-HACK-0001",
            status="SAVED",
            saved_at=datetime.now(timezone.utc),
        )
        db.add(saved_opp)

        notif = NotificationModel(
            notification_id="NOTIF-INIT-001",
            student_id=student_1.student_id,
            title="Welcome to Student Achievement Intelligence Platform",
            message="Your verified profile is active. Browse your top personalized opportunities in the Recommendations tab.",
            notification_type="SYSTEM",
            dedupe_key=f"WELCOME-{student_1.student_id}",
            is_read=False,
            created_at=datetime.now(timezone.utc),
            scheduled_at=datetime.now(timezone.utc),
        )
        db.add(notif)

        db.commit()
        print("Demo database seeding completed successfully!")
        print("  - Student Login: student@university.edu / student123")
        print("  - Cold-Start Student: coldstart@university.edu / student123")
        print("  - Faculty Login: faculty@university.edu / faculty123")
        print("  - Admin Login:   admin@university.edu / admin123")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
