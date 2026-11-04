"""
src/core/security.py
====================
Authentication, JWT token lifecycle, password hashing, and role definition utilities.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings

# Passlib CryptContext for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """User access roles adhering to Role-Based Access Control (RBAC)."""
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    ADMIN = "ADMIN"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hashed string."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback for SHA256 hashed passwords in lightweight/test scenarios
        if hashed_password.startswith("sha256$"):
            _, salt, h = hashed_password.split("$")
            computed = hashlib.sha256((salt + plain_password).encode()).hexdigest()
            return secrets.compare_digest(computed, h)
        return False


def get_password_hash(password: str) -> str:
    """Generate secure password hash."""
    try:
        return pwd_context.hash(password)
    except Exception:
        # Fallback secure SHA-256 with random salt
        salt = secrets.token_hex(8)
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"sha256${salt}${h}"


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate signed JWT access token containing user claims and expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token, returning payload claims."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
