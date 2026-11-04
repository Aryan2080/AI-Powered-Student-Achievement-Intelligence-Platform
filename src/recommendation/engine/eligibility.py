"""
src/recommendation/engine/eligibility.py
========================================
Hard eligibility constraint evaluation engine.
Enforces non-negotiable institutional and sponsor prerequisites (GPA, Major, Year, Deadline).
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from src.recommendation.domain.student_profile import StudentProfile
from src.recommendation.schemas.opportunity import Opportunity, OpportunityStatus


@dataclass
class EligibilityResult:
    """Outcome of hard eligibility check with diagnostic reason."""
    is_eligible: bool
    status: str  # "ELIGIBLE", "INELIGIBLE_GPA", "INELIGIBLE_DEPARTMENT", "INELIGIBLE_YEAR", "EXPIRED", "INACTIVE"
    reason: str
    failed_criteria: List[str] = field(default_factory=list)


class EligibilityFilter:
    """Enforces strict hard filtering before recommendation ranking."""

    def __init__(self, reference_date: Optional[date] = None):
        self.reference_date = reference_date or date.today()

    def evaluate(self, student: StudentProfile, opportunity: Opportunity) -> EligibilityResult:
        """Evaluate if student strictly meets all hard prerequisites for opportunity."""
        failed = []

        # 1. Opportunity lifecycle status
        if opportunity.status != OpportunityStatus.ACTIVE and opportunity.status != "ACTIVE":
            return EligibilityResult(
                is_eligible=False,
                status="INACTIVE",
                reason=f"Opportunity is {opportunity.status}, not open for applications.",
                failed_criteria=["status"],
            )

        # 2. Deadline expiration
        if opportunity.deadline is not None:
            opp_deadline = opportunity.deadline
            if isinstance(opp_deadline, str):
                opp_deadline = date.fromisoformat(opp_deadline)
            if opp_deadline < self.reference_date:
                return EligibilityResult(
                    is_eligible=False,
                    status="EXPIRED",
                    reason=f"Application deadline passed on {opp_deadline.isoformat()}.",
                    failed_criteria=["deadline"],
                )

        # 3. Minimum GPA check
        if opportunity.min_gpa > 0.0:
            if student.gpa < opportunity.min_gpa:
                failed.append(f"Minimum GPA requirement {opportunity.min_gpa} (Student GPA: {student.gpa})")

        # 4. Department / Major check
        if opportunity.eligible_departments:
            dept_lower = student.department.strip().lower()
            eligible_lower = [d.strip().lower() for d in opportunity.eligible_departments]
            if "all" not in eligible_lower and dept_lower not in eligible_lower:
                # Substring / partial match fallback
                match_found = any(dept_lower in el or el in dept_lower for el in eligible_lower)
                if not match_found:
                    failed.append(f"Department '{student.department}' not in eligible departments")

        # 5. Year of study check
        if opportunity.eligible_years:
            if student.year_of_study not in opportunity.eligible_years:
                failed.append(f"Year {student.year_of_study} not in eligible years {opportunity.eligible_years}")

        if failed:
            return EligibilityResult(
                is_eligible=False,
                status="INELIGIBLE",
                reason="; ".join(failed),
                failed_criteria=failed,
            )

        return EligibilityResult(
            is_eligible=True,
            status="ELIGIBLE",
            reason="Meets all academic standing, department, and deadline prerequisites.",
            failed_criteria=[],
        )

    def filter_opportunities(
        self, student: StudentProfile, opportunities: List[Opportunity]
    ) -> List[Opportunity]:
        """Prune all ineligible opportunities, returning only eligible items."""
        eligible_items = []
        for opp in opportunities:
            res = self.evaluate(student, opp)
            if res.is_eligible:
                eligible_items.append(opp)
        return eligible_items
