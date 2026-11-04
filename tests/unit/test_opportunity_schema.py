"""Unit tests for opportunity schemas and validation."""
import pytest
from pydantic import ValidationError
from src.recommendation.schemas.opportunity import Opportunity, OpportunityType, OpportunityStatus


def test_valid_opportunity_creation():
    opp = Opportunity(
        opportunity_id="OPP-TEST-0001",
        title="Test Hackathon 2026",
        description="A competitive 48-hour buildathon for engineering students.",
        opportunity_type=OpportunityType.HACKATHON,
        organization="Major League Hacking",
        eligible_departments=["Computer Science"],
        eligible_years=[2, 3, 4],
        min_gpa=7.0,
        required_skills=["Python", "PyTorch"],
        domain_tags=["lbl_domain_ai", "lbl_domain_ml"],
    )
    assert opp.opportunity_id == "OPP-TEST-0001"
    assert opp.min_gpa == 7.0
    assert "lbl_domain_ai" in opp.domain_tags


def test_invalid_domain_tag_rejected():
    with pytest.raises(ValidationError):
        Opportunity(
            opportunity_id="OPP-TEST-0002",
            title="Invalid Tag Opportunity",
            description="Testing invalid domain tag rejection.",
            opportunity_type=OpportunityType.INTERNSHIP,
            organization="Tech Labs",
            domain_tags=["INVALID_TAG_NOT_IN_TAXONOMY"],
        )
