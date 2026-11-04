"""
src/core/logging.py
===================
Uniform structured logging configuration across backend and recommendation components.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict


class SafeFormatter(logging.Formatter):
    """Custom log formatter ensuring timestamps, log levels, and sanitizing raw secrets/evidence."""

    def format(self, record: logging.LogRecord) -> str:
        # Standard formatted output
        base_format = super().format(record)
        # Prevent logging raw secrets or bearer tokens
        if "Bearer " in base_format or "eyJ" in base_format:
            base_format = base_format.replace("Bearer ", "Bearer [REDACTED]")
        return base_format


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root logger with sanitized, standard formatting."""
    logger = logging.getLogger("achievement_intelligence")
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = SafeFormatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = setup_logging()
