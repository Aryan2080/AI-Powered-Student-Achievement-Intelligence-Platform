"""
src/integration/nlp_adapter.py
==============================
Integration adapter wrapping Member 1's completed NLP extraction and preprocessing pipeline.
Consumes approved canonical structured representations without modifying upstream modules.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.logging import logger
from src.nlp.taxonomy import ACHIEVEMENT_CATEGORIES, DOMAIN_TAGS, normalize_domain_tag


class Member1NLPAdapter:
    """Adapter consuming Member 1's text preprocessing, skill extraction, and normalization."""

    def __init__(self):
        self._load_dependencies()

    def _load_dependencies(self) -> None:
        """Attempt to load Member 1 upstream modules."""
        try:
            from src.nlp.text_preprocessing import (
                normalize_text_for_classification,
                normalize_whitespace,
                tokenize_words,
            )
            self._norm_text_fn = normalize_text_for_classification
            self._norm_ws_fn = normalize_whitespace
            self._tokenize_fn = tokenize_words
            logger.info("Successfully bound Member 1 NLP preprocessing modules.")
        except ImportError as e:
            logger.warning("Member 1 modules unavailable (%s). Using built-in fallback NLP.", e)
            self._norm_text_fn = lambda t: re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()
            self._norm_ws_fn = lambda t: re.sub(r"\s+", " ", t).strip()
            self._tokenize_fn = lambda t: t.split()

    def clean_and_normalize(self, text: str) -> str:
        """Produce canonical normalized text for classification and feature extraction."""
        if not text:
            return ""
        return self._norm_text_fn(text)

    def extract_canonical_skills(self, text: str) -> List[str]:
        """Extract canonical skills mentioned in text matching curated vocabulary."""
        text_lower = text.lower()
        skills_detected = []
        
        # Curated canonical skills list
        common_vocab = [
            "Python", "Java", "C++", "C#", "Rust", "Go", "TypeScript", "JavaScript",
            "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes",
            "AWS", "Azure", "GCP", "Linux", "Git", "PyTorch", "TensorFlow", "Scikit-learn",
            "OpenCV", "HuggingFace", "BERT", "LLM", "NLP", "Pandas", "NumPy",
            "FastAPI", "Flask", "Django", "React", "Node.js", "GraphQL", "REST API",
            "Cybersecurity", "Computer Vision", "Deep Learning", "Data Engineering"
        ]

        for sk in common_vocab:
            # Word boundary check
            pattern = rf"\b{re.escape(sk.lower())}\b"
            if re.search(pattern, text_lower):
                skills_detected.append(sk)

        return skills_detected

    def infer_domain_tags_from_text(self, text: str) -> List[str]:
        """Heuristic fallback for domain tags when Member 2 categorizer is unavailable."""
        text_lower = text.lower()
        tags = set()
        if any(w in text_lower for w in ["ai", "artificial intelligence", "agent", "planning"]):
            tags.add("lbl_domain_ai")
        if any(w in text_lower for w in ["ml", "machine learning", "supervised", "reinforcement"]):
            tags.add("lbl_domain_ml")
        if any(w in text_lower for w in ["nlp", "language", "bert", "llm", "text"]):
            tags.add("lbl_domain_nlp")
        if any(w in text_lower for w in ["cv", "vision", "opencv", "segmentation", "image"]):
            tags.add("lbl_domain_cv")
        if any(w in text_lower for w in ["security", "cipher", "crypto", "vulnerability"]):
            tags.add("lbl_domain_security")
        if any(w in text_lower for w in ["cloud", "systems", "docker", "kubernetes", "distributed"]):
            tags.add("lbl_domain_systems")
        if any(w in text_lower for w in ["web", "react", "frontend", "api", "mobile"]):
            tags.add("lbl_domain_web")
        if any(w in text_lower for w in ["data", "sql", "analytics", "spark", "pipeline"]):
            tags.add("lbl_domain_data")
        if any(w in text_lower for w in ["hardware", "fpga", "embedded", "robotics", "iot"]):
            tags.add("lbl_domain_hardware")

        if not tags:
            tags.add("lbl_domain_other")
        return sorted(list(tags))
