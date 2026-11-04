"""
src/recommendation/profile_aggregator.py
========================================
Dynamic student achievement profile aggregation engine.
Computes time-decayed vector embeddings, domain affinities, and skill proficiency graphs.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Set

from src.core.config import settings
from src.core.logging import logger
from src.nlp.taxonomy import DOMAIN_TAGS
from src.recommendation.domain.student_profile import (
    AchievementLevel,
    AchievementSummary,
    DomainAffinity,
    SkillProficiency,
    StudentProfile,
)
from src.recommendation.embeddings import TextEmbeddingEngine

LEVEL_WEIGHTS: Dict[str, float] = {
    AchievementLevel.COLLEGE.value: 1.0,
    AchievementLevel.STATE.value: 1.5,
    AchievementLevel.NATIONAL.value: 2.0,
    AchievementLevel.INTERNATIONAL.value: 3.0,
}


class StudentProfileAggregator:
    """Aggregates student records, verified achievements, and skills into a cohesive vector profile."""

    def __init__(
        self,
        half_life_days: float = 730.0,
        verified_multiplier: float = 1.25,
        embedding_engine: Optional[TextEmbeddingEngine] = None,
    ):
        self.half_life_days = half_life_days
        self.verified_multiplier = verified_multiplier
        self.embedding_engine = embedding_engine or TextEmbeddingEngine(settings.EMBEDDING_MODEL_NAME)

    def calculate_recency_decay(self, achievement_date: Optional[date], reference_date: Optional[date] = None) -> float:
        """Compute exponential half-life recency decay: exp(-ln(2) * age_days / half_life_days)."""
        if achievement_date is None:
            return 0.75  # Default decay for undated historical records
        
        ref = reference_date or date.today()
        age_days = max(0, (ref - achievement_date).days)
        decay = math.exp(-math.log(2.0) * age_days / self.half_life_days)
        return float(decay)

    def calculate_achievement_weight(self, achievement: AchievementSummary) -> float:
        """Compute composite weighting for an individual achievement."""
        level_str = achievement.level.value if isinstance(achievement.level, AchievementLevel) else str(achievement.level)
        level_w = LEVEL_WEIGHTS.get(level_str.upper(), 1.0)
        recency_w = self.calculate_recency_decay(achievement.achievement_date)
        status_mult = self.verified_multiplier if achievement.verified_flag else 0.8
        conf_mult = max(0.2, min(1.0, achievement.confidence))
        return level_w * recency_w * status_mult * conf_mult

    def aggregate_profile(
        self,
        student_id: str,
        department: str,
        program: str,
        year_of_study: int,
        gpa: float,
        declared_skills: List[str],
        declared_interests: List[str],
        achievements: List[AchievementSummary],
        career_goals: Optional[str] = None,
    ) -> StudentProfile:
        """Synthesize dynamic StudentProfile from academic attributes and achievement history."""
        # Clean inputs
        declared_skills = [s.strip() for s in declared_skills if s.strip()]
        declared_interests = [i.strip() for i in declared_interests if i.strip()]
        
        # Skill proficiency graph
        skill_proficiencies: Dict[str, SkillProficiency] = {}
        for s in declared_skills:
            skill_proficiencies[s] = SkillProficiency(
                skill_name=s,
                proficiency_level="INTERMEDIATE",
                evidence_count=1,
                verified_count=0,
            )

        # Domain affinity map
        domain_weights: Dict[str, float] = {tag: 0.0 for tag in DOMAIN_TAGS}
        achievement_counts: Dict[str, int] = {tag: 0 for tag in DOMAIN_TAGS}

        weighted_vectors: List[List[float]] = []
        total_weight: float = 0.0

        for ach in achievements:
            weight = self.calculate_achievement_weight(ach)
            total_weight += weight

            # Aggregate skills from achievement
            for sk in ach.skills:
                sk_clean = sk.strip()
                if not sk_clean:
                    continue
                if sk_clean in skill_proficiencies:
                    p = skill_proficiencies[sk_clean]
                    p.evidence_count += 1
                    if ach.verified_flag:
                        p.verified_count += 1
                    p.proficiency_level = "ADVANCED" if p.verified_count >= 2 else "INTERMEDIATE"
                else:
                    skill_proficiencies[sk_clean] = SkillProficiency(
                        skill_name=sk_clean,
                        proficiency_level="INTERMEDIATE",
                        evidence_count=1,
                        verified_count=1 if ach.verified_flag else 0,
                        last_demonstrated=ach.achievement_date,
                    )

            # Aggregate domain affinity
            for dt in ach.domain_tags:
                if dt in domain_weights:
                    domain_weights[dt] += weight
                    achievement_counts[dt] += 1

            # Achievement embedding vector
            if ach.embedding is not None and len(ach.embedding) == 384:
                ach_vec = ach.embedding
            else:
                ach_text = f"{ach.title} | {ach.category} | Skills: {', '.join(ach.skills)} | Domains: {', '.join(ach.domain_tags)}"
                ach_vec = self.embedding_engine.encode(ach_text)

            weighted_vectors.append([v * weight for v in ach_vec])

        # Synthesize declared intent representation
        intent_text = (
            f"Department: {department} | Program: {program} | Year: {year_of_study} | "
            f"Skills: {', '.join(declared_skills)} | Interests: {', '.join(declared_interests)} | "
            f"Goals: {career_goals or 'None'}"
        )
        intent_vec = self.embedding_engine.encode(intent_text)

        dim = 384
        composite_vec = [0.0] * dim

        if not achievements or total_weight == 0.0:
            # Cold start: profile vector is purely intent
            composite_vec = intent_vec
            is_cold_start = True
        else:
            is_cold_start = False
            # Blend achievement vectors (weight 0.70) with declared intent (weight 0.30)
            ach_blend = [0.0] * dim
            for vec in weighted_vectors:
                for d in range(dim):
                    ach_blend[d] += vec[d]
            for d in range(dim):
                ach_blend[d] /= total_weight
                composite_vec[d] = 0.70 * ach_blend[d] + 0.30 * intent_vec[d]

        # L2-normalize final profile vector
        norm = math.sqrt(sum(x * x for x in composite_vec)) or 1.0
        final_profile_vector = [float(x / norm) for x in composite_vec]

        # Normalize domain affinities into [0.0, 1.0]
        max_domain_w = max(domain_weights.values()) if domain_weights else 1.0
        if max_domain_w <= 0.0:
            max_domain_w = 1.0

        domain_affinities = {
            tag: DomainAffinity(
                domain_tag=tag,
                score=round(min(1.0, domain_weights[tag] / max_domain_w), 4),
                achievement_count=achievement_counts[tag],
            )
            for tag in DOMAIN_TAGS
        }

        # Verified skills list
        verified_skills = [
            sk for sk, prof in skill_proficiencies.items() if prof.verified_count > 0
        ]

        # Profile text hash for cache invalidation
        hash_seed = f"{student_id}-{department}-{year_of_study}-{len(achievements)}-{','.join(sorted(verified_skills))}"
        profile_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()[:16]

        return StudentProfile(
            student_id=student_id,
            department=department,
            program=program,
            year_of_study=year_of_study,
            gpa=gpa,
            declared_skills=declared_skills,
            declared_interests=declared_interests,
            career_goals=career_goals,
            verified_skills=verified_skills,
            skill_proficiencies=skill_proficiencies,
            domain_affinities=domain_affinities,
            achievements=achievements,
            profile_vector=final_profile_vector,
            profile_text_hash=profile_hash,
            last_aggregated_at=datetime.now(timezone.utc),
            is_cold_start=is_cold_start,
        )
