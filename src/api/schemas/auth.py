"""
src/api/schemas/auth.py
=======================
Authentication request and response DTO schemas.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    student_id: Optional[str] = None
    faculty_id: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: str = "STUDENT"  # STUDENT, FACULTY, ADMIN
    department: str = "Computer Science"
    program: Optional[str] = "B.Tech"
    year_of_study: Optional[int] = 3
    gpa: Optional[float] = 8.0


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    department: str
    is_active: bool
    student_id: Optional[str] = None
    faculty_id: Optional[str] = None

    class Config:
        from_attributes = True
