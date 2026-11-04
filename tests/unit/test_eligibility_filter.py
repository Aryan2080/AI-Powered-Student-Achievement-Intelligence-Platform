"""Unit tests for hard eligibility filtering."""
from datetime import date, timedelta
import pytest
from src.recommendation.domain.student_profile import StudentProfile
from src.recommendation.engine.eligibility import EligibilityFilter
from src.recommendation.schemas.opportunity import Opportunity, OpportunityStatus, OpportunityType


def test_hard_eligibility_gpa_pruning():
    filter_engine = EligibilityFilter()
    student = StudentProfile(
        student_id="STU-01",
        department="Computer Science",
        gpa=7.2,
        year_of_study=3,
    )
    opp_high_gpa = Opportunity(
        opportunity_id="OPP-01",
        title="Merit Research Grant",
        description="High GPA required research grant.",
        opportunity_type=OpportunityType.RESEARCH_GRANT,
        organization="NSF",
        eligible_departments=["Computer Science"],
        eligible_years=[3],
        min_gpa=8.5,
    )
    res = filter_engine.evaluate(student, opp_high_gpa)
    assert res.is_eligible is False
    assert "Minimum GPA requirement" in res.reason


def test_expired_opportunity_pruning():
    filter_engine = EligibilityFilter(reference_date=date.today())
    student = StudentProfile(student_id="STU-01", department="Computer Science", gpa=8.5, year_of_study=3)
    opp_expired = Opportunity(
        opportunity_id="OPP-02",
        title="Past Hackathon",
        description="Event concluded last month.",
        opportunity_type=OpportunityType.HACKATHON,
        organization="MLH",
        eligible_departments=["Computer Science"],
        eligible_years=[3],
        deadline=date.today() - timedelta(days=10),
    )
    res = filter_engine.evaluate(student, opp_expired)
    assert res.is_eligible is False
    assert res.status == "EXPIRED"
