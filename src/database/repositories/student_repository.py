"""
src/database/repositories/student_repository.py
===============================================
Persistence and lookup operations for student profiles and academic data.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models.student import StudentModel
from src.database.models.user import UserModel


class StudentRepository:
    """Repository handling Student database operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, student_id: str) -> Optional[StudentModel]:
        stmt = select(StudentModel).where(StudentModel.student_id == student_id)
        return self.db.scalars(stmt).first()

    def get_by_user_id(self, user_id: str) -> Optional[StudentModel]:
        stmt = select(StudentModel).where(StudentModel.user_id == user_id)
        return self.db.scalars(stmt).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[StudentModel]:
        stmt = select(StudentModel).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def list_by_department(self, department: str) -> List[StudentModel]:
        stmt = select(StudentModel).where(StudentModel.department == department)
        return list(self.db.scalars(stmt).all())

    def create(self, student: StudentModel) -> StudentModel:
        self.db.add(student)
        self.db.flush()
        return student

    def update(self, student: StudentModel) -> StudentModel:
        self.db.flush()
        return student
