"""
src/recommendation/engine/ranker.py
==================================
Multi-objective hybrid ranker combining semantic similarity, skill overlap, domain affinity, and deadline urgency.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.config import settings
from src.recommendation.domain.student_profile import StudentProfile
from src.recommendation.schemas.opportunity import Opportunity
from src.recommendation.schemas.recommendation import ScoreBreakdown


class SkillDomainRanker:
    """Calculates canonical skill overlap, domain affinity, and deadline urgency."""

    def __init__(self, reference_date: Optional[date] = None):
        self.reference_date = reference_date or date.today()

    def calculate_skill_overlap(
        self, student: StudentProfile, opportunity: Opportunity
    ) -> Tuple[float, List[str], List[str]]:
        """Calculate skill match ratio, returning matched and missing skills."""
        student_skills = set(s.strip().lower() for s in (student.declared_skills + student.verified_skills))
        
        req_skills = opportunity.required_skills or []
        pref_skills = opportunity.preferred_skills or []

        matched: List[str] = []
        missing: List[str] = []

        for sk in req_skills:
            if sk.strip().lower() in student_skills:
                matched.append(sk)
            else:
                missing.append(sk)

        if not req_skills:
            # If no strict required skills, evaluate preferred skills or neutral
            if pref_skills:
                matched_pref = [sk for sk in pref_skills if sk.strip().lower() in student_skills]
                score = len(matched_pref) / len(pref_skills)
                return round(float(score), 4), matched_pref, []
            return 0.75, [], []

        base_ratio = len(matched) / len(req_skills)
        
        # Preferred skill bonus (up to +0.10)
        matched_pref = [sk for sk in pref_skills if sk.strip().lower() in student_skills]
        pref_bonus = 0.10 * (len(matched_pref) / max(1, len(pref_skills))) if pref_skills else 0.0

        skill_score = min(1.0, base_ratio + pref_bonus)
        return round(float(skill_score), 4), matched, missing

    def calculate_domain_score(self, student: StudentProfile, opportunity: Opportunity) -> float:
        """Compute student domain affinity alignment with opportunity domain tags."""
        opp_domains = opportunity.domain_tags or []
        if not opp_domains:
            return 0.50

        affinity_scores = []
        for tag in opp_domains:
            aff = student.domain_affinities.get(tag)
            affinity_scores.append(aff.score if aff else 0.0)

        # Max affinity across opportunity domains
        score = max(affinity_scores) if affinity_scores else 0.50
        return round(float(score), 4)

    def calculate_urgency_score(self, opportunity: Opportunity) -> float:
        """Compute bounded monotonic urgency score based on deadline."""
        if opportunity.deadline is None:
            return 0.50  # Ongoing / no deadline neutral

        opp_deadline = opportunity.deadline
        if isinstance(opp_deadline, str):
            opp_deadline = date.fromisoformat(opp_deadline)

        days_remaining = (opp_deadline - self.reference_date).days
        if days_remaining < 0:
            return 0.0  # Expired
        elif days_remaining <= 7:
            return 1.0  # High urgency
        elif days_remaining <= 14:
            return 0.85
        elif days_remaining <= 30:
            return 0.65
        elif days_remaining <= 60:
            return 0.45
        else:
            return 0.25  # Ample time remaining


class HybridRanker:
    """Configurable multi-objective ranker generating composite match scores."""

    def __init__(
        self,
        weight_semantic: Optional[float] = None,
        weight_skill: Optional[float] = None,
        weight_domain: Optional[float] = None,
        weight_urgency: Optional[float] = None,
        reference_date: Optional[date] = None,
    ):
        self.w_semantic = weight_semantic if weight_semantic is not None else settings.WEIGHT_SEMANTIC
        self.w_skill = weight_skill if weight_skill is not None else settings.WEIGHT_SKILL
        self.w_domain = weight_domain if weight_domain is not None else settings.WEIGHT_DOMAIN
        self.w_urgency = weight_urgency if weight_urgency is not None else settings.WEIGHT_URGENCY

        # Normalize weights so they sum to 1.0
        total_w = self.w_semantic + self.w_skill + self.w_domain + self.w_urgency
        if total_w > 0:
            self.w_semantic /= total_w
            self.w_skill /= total_w
            self.w_domain /= total_w
            self.w_urgency /= total_w

        self.skill_ranker = SkillDomainRanker(reference_date=reference_date)

    def score_opportunity(
        self,
        student: StudentProfile,
        opportunity: Opportunity,
        semantic_similarity: float,
    ) -> Tuple[ScoreBreakdown, List[str], List[str]]:
        """Compute complete score breakdown and skill attribution for an opportunity."""
        skill_score, matched_skills, missing_skills = self.skill_ranker.calculate_skill_overlap(
            student, opportunity
        )
        domain_score = self.skill_ranker.calculate_domain_score(student, opportunity)
        urgency_score = self.skill_ranker.calculate_urgency_score(opportunity)

        composite = (
            self.w_semantic * semantic_similarity
            + self.w_skill * skill_score
            + self.w_domain * domain_score
            + self.w_urgency * urgency_score
        )
        composite = round(max(0.0, min(1.0, float(composite))), 4)

        scores = ScoreBreakdown(
            semantic_similarity=round(semantic_similarity, 4),
            skill_match_score=skill_score,
            domain_match_score=domain_score,
            urgency_score=round(urgency_score, 4),
            composite_score=composite,
        )

        return scores, matched_skills, missing_skills
