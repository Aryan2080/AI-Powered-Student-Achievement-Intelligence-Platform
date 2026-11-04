"""
src/api/dependencies.py
=======================
FastAPI dependency injection providers for database sessions, JWT auth, and RBAC guards.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import Generator, Optional
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.core.exceptions import EntityNotFoundException, UnauthorizedAccessException
from src.core.security import UserRole, decode_access_token
from src.database.connection import get_db
from src.database.models.user import UserModel

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    """Validate bearer JWT token and return authenticated UserModel."""
    if not credentials:
        # Development fallback / test header support
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier.",
        )

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
        )

    return user


def require_student_role(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Enforce that caller has STUDENT or ADMIN role."""
    if current_user.role not in [UserRole.STUDENT.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Requires Student or Admin authorization.",
        )
    return current_user


def require_faculty_role(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Enforce that caller has FACULTY or ADMIN role."""
    if current_user.role not in [UserRole.FACULTY.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Requires Faculty or Admin authorization.",
        )
    return current_user


def require_admin_role(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Enforce that caller has ADMIN role."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Requires Administrator role.",
        )
    return current_user
