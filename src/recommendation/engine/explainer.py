"""
src/recommendation/engine/explainer.py
======================================
Explainable AI (XAI) justification engine for personalized recommendations.
Produces grounded, human-readable explanations based on skill matches, achievements, and deadlines.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from src.recommendation.domain.student_profile import AchievementSummary, StudentProfile
from src.recommendation.schemas.opportunity import Opportunity
from src.recommendation.schemas.recommendation import ScoreBreakdown


class RecommendationExplainer:
    """Generates transparent, auditable natural language explanations for recommended opportunities."""

    def find_closest_achievement(
        self, student: StudentProfile, opportunity: Opportunity
    ) -> Optional[AchievementSummary]:
        """Find the student achievement most aligned with the opportunity's required skills or domain."""
        if not student.achievements:
            return None

        opp_skills = set(s.lower() for s in (opportunity.required_skills or []))
        opp_domains = set(d.lower() for d in (opportunity.domain_tags or []))

        best_ach = None
        best_overlap = -1

        for ach in student.achievements:
            ach_skills = set(s.lower() for s in ach.skills)
            ach_domains = set(d.lower() for d in ach.domain_tags)
            overlap = len(ach_skills & opp_skills) * 2 + len(ach_domains & opp_domains)
            if overlap > best_overlap:
                best_overlap = overlap
                best_ach = ach

        return best_ach if best_overlap > 0 else student.achievements[0]

    def explain(
        self,
        student: StudentProfile,
        opportunity: Opportunity,
        scores: ScoreBreakdown,
        matched_skills: List[str],
        missing_skills: List[str],
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Generate grounded natural language justification string and closest achievement attribution."""
        closest_ach = self.find_closest_achievement(student, opportunity)
        closest_id = closest_ach.achievement_id if closest_ach else None
        closest_title = closest_ach.title if closest_ach else None

        # Build grounded justification sentences
        sentences: List[str] = []

        # 1. Core reason based on alignment or cold start
        if student.is_cold_start or not student.achievements:
            sentences.append(
                f"Recommended for your declared interest in {', '.join(student.declared_interests[:2])} "
                f"and academic standing in {student.department}."
            )
        elif closest_ach:
            status_text = "verified " if closest_ach.verified_flag else ""
            sentences.append(
                f"Recommended based on your {status_text}{closest_ach.category.lower().replace('_', ' ')} "
                f"achievement '{closest_ach.title}'."
            )
        else:
            sentences.append(
                f"Recommended based on your academic profile in {student.department} with a {student.gpa} GPA."
            )

        # 2. Skill match and gap statement
        total_req = len(opportunity.required_skills or [])
        if matched_skills and total_req > 0:
            skills_preview = ", ".join(matched_skills[:3])
            sentences.append(f"You match {len(matched_skills)} of {total_req} required skills ({skills_preview}).")
        elif matched_skills:
            sentences.append(f"You possess {len(matched_skills)} relevant skills ({', '.join(matched_skills[:3])}).")

        if missing_skills:
            gaps_preview = ", ".join(missing_skills[:2])
            sentences.append(f"Recommended growth area: gain experience in {gaps_preview}.")

        # 3. Urgency / Deadline note
        if scores.urgency_score >= 0.85 and opportunity.deadline:
            sentences.append(f"High urgency: Application deadline is approaching on {opportunity.deadline}.")

        explanation_text = " ".join(sentences)
        return explanation_text, closest_id, closest_title
