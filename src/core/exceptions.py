"""
src/core/exceptions.py
======================
Standard domain and business exception hierarchy for the application.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations
from typing import Any, Dict, Optional


class BasePlatformException(Exception):
    """Base exception for all domain-specific errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundException(BasePlatformException):
    """Raised when a requested resource is not found."""
    pass


class IneligibleOpportunityException(BasePlatformException):
    """Raised when student does not meet eligibility criteria for an opportunity."""
    pass


class ModelInferenceException(BasePlatformException):
    """Raised when an ML or NLP inference call fails."""
    pass


class DuplicateRecordException(BasePlatformException):
    """Raised when an idempotent ingestion check detects duplicate record."""
    pass


class UnauthorizedAccessException(BasePlatformException):
    """Raised when user lacks authentication or role privileges."""
    pass


class ProfileAggregationException(BasePlatformException):
    """Raised when student achievement profile aggregation fails."""
    pass
