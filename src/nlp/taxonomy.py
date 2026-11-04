"""
src/nlp/taxonomy.py
===================
Canonical taxonomies and validation for achievement categories and domain tags.
AI-Powered Student Achievement Intelligence Platform — Member 1 & Member 3 Facade
"""

from __future__ import annotations

from typing import Dict, List, Set

# Master 14-Category Primary Achievement Taxonomy
ACHIEVEMENT_CATEGORIES: List[str] = sorted([
    "CERTIFICATION",
    "COMPETITION",
    "CONFERENCE",
    "CULTURAL",
    "HACKATHON",
    "INTERNSHIP",
    "LEADERSHIP",
    "OTHER",
    "PATENT",
    "PROJECT",
    "RESEARCH_PUBLICATION",
    "SPORTS",
    "VOLUNTEERING",
    "WORKSHOP",
])

# Master 10 Multi-Label Domain Tags
DOMAIN_TAGS: List[str] = [
    "lbl_domain_ai",
    "lbl_domain_ml",
    "lbl_domain_nlp",
    "lbl_domain_cv",
    "lbl_domain_security",
    "lbl_domain_systems",
    "lbl_domain_web",
    "lbl_domain_data",
    "lbl_domain_hardware",
    "lbl_domain_other",
]

DOMAIN_TAG_NAMES: Dict[str, str] = {
    "lbl_domain_ai": "Artificial Intelligence",
    "lbl_domain_ml": "Machine Learning",
    "lbl_domain_nlp": "Natural Language Processing",
    "lbl_domain_cv": "Computer Vision",
    "lbl_domain_security": "Cybersecurity",
    "lbl_domain_systems": "Systems & Cloud",
    "lbl_domain_web": "Web & Mobile",
    "lbl_domain_data": "Data Science",
    "lbl_domain_hardware": "Hardware & IoT",
    "lbl_domain_other": "Other",
}

# Inverse mapping from display name or lowercase keyword to canonical tag ID
DOMAIN_NAME_TO_TAG: Dict[str, str] = {
    v.lower(): k for k, v in DOMAIN_TAG_NAMES.items()
}
DOMAIN_NAME_TO_TAG.update({
    "ai": "lbl_domain_ai",
    "artificial intelligence": "lbl_domain_ai",
    "ml": "lbl_domain_ml",
    "machine learning": "lbl_domain_ml",
    "nlp": "lbl_domain_nlp",
    "natural language processing": "lbl_domain_nlp",
    "cv": "lbl_domain_cv",
    "computer vision": "lbl_domain_cv",
    "security": "lbl_domain_security",
    "cybersecurity": "lbl_domain_security",
    "systems": "lbl_domain_systems",
    "cloud": "lbl_domain_systems",
    "web": "lbl_domain_web",
    "mobile": "lbl_domain_web",
    "data": "lbl_domain_data",
    "data science": "lbl_domain_data",
    "hardware": "lbl_domain_hardware",
    "iot": "lbl_domain_hardware",
    "other": "lbl_domain_other",
})


def is_valid_category(category: str) -> bool:
    """Check if category belongs to canonical 14-category primary taxonomy."""
    return category in ACHIEVEMENT_CATEGORIES


def is_valid_domain_tag(tag: str) -> bool:
    """Check if domain tag belongs to canonical 10-tag taxonomy."""
    return tag in DOMAIN_TAGS


def normalize_domain_tag(tag_or_name: str) -> str:
    """Convert a domain tag or alias string to canonical tag ID."""
    clean = tag_or_name.strip()
    if clean in DOMAIN_TAGS:
        return clean
    lower = clean.lower()
    return DOMAIN_NAME_TO_TAG.get(lower, "lbl_domain_other")
