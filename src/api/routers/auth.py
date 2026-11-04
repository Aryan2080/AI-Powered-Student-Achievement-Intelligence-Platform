"""
src/api/routers/auth.py
=======================
Authentication endpoints: Registration, Login (JWT Token Issuance), and Session Introspection.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.api.schemas.auth import Token, UserLogin, UserRegister, UserResponse
from src.core.security import create_access_token, get_password_hash, verify_password
from src.database.connection import get_db
from src.database.models.faculty import FacultyModel
from src.database.models.student import StudentModel
from src.database.models.user import UserModel

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new student, faculty, or administrator."""
    existing = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{payload.email}' already exists.",
        )

    user_id = f"USR-{uuid.uuid4().hex[:10]}"
    hashed_pwd = get_password_hash(payload.password)

    user = UserModel(
        id=user_id,
        email=payload.email,
        hashed_password=hashed_pwd,
        role=payload.role.upper(),
        full_name=payload.full_name,
        department=payload.department,
        is_active=True,
    )
    db.add(user)
    db.flush()

    student_id = None
    faculty_id = None

    if payload.role.upper() == "STUDENT":
        student_id = f"STU-{uuid.uuid4().hex[:8]}"
        stu = StudentModel(
            student_id=student_id,
            user_id=user_id,
            department=payload.department,
            program=payload.program or "B.Tech",
            year_of_study=payload.year_of_study or 3,
            gpa=payload.gpa or 8.0,
            declared_skills="Python;Git",
            declared_interests="Artificial Intelligence;Web Development",
        )
        db.add(stu)
    elif payload.role.upper() == "FACULTY":
        faculty_id = f"FAC-{uuid.uuid4().hex[:8]}"
        fac = FacultyModel(
            faculty_id=faculty_id,
            user_id=user_id,
            department=payload.department,
            title="Assistant Professor",
        )
        db.add(fac)

    db.commit()

    token_data = {"sub": user_id, "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        student_id=student_id,
        faculty_id=faculty_id,
    )


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate credentials and issue JWT bearer token."""
    user = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    student_id = user.student_profile.student_id if user.student_profile else None
    faculty_id = user.faculty_profile.faculty_id if user.faculty_profile else None

    token_data = {"sub": user.id, "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        student_id=student_id,
        faculty_id=faculty_id,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserModel = Depends(get_current_user)):
    """Retrieve claims and profile identity for authenticated caller."""
    student_id = current_user.student_profile.student_id if current_user.student_profile else None
    faculty_id = current_user.faculty_profile.faculty_id if current_user.faculty_profile else None

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department=current_user.department,
        is_active=current_user.is_active,
        student_id=student_id,
        faculty_id=faculty_id,
    )
