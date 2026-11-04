"""
src/recommendation/engine/matcher.py
====================================
Vector semantic similarity matcher operating on 384-dimensional dense embeddings.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import Dict, List, Optional
from src.recommendation.embeddings import compute_cosine_similarity


class SemanticMatcher:
    """Computes dense vector semantic alignment between student profile and opportunity."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def match(self, student_vector: List[float], opportunity_vector: List[float]) -> float:
        """Calculate cosine similarity score in [0.0, 1.0]."""
        if not student_vector or not opportunity_vector:
            return 0.50  # Neutral fallback for missing vector
        return compute_cosine_similarity(student_vector, opportunity_vector)

    def batch_match(
        self, student_vector: List[float], opportunity_vectors: List[List[float]]
    ) -> List[float]:
        """Compute match scores across a batch of opportunity vectors."""
        return [self.match(student_vector, vec) for vec in opportunity_vectors]
