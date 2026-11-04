"""Unit tests for student profile aggregation."""
from datetime import date, timedelta
import pytest
from src.recommendation.domain.student_profile import AchievementLevel, AchievementSummary
from src.recommendation.profile_aggregator import StudentProfileAggregator


def test_time_decay_math():
    agg = StudentProfileAggregator(half_life_days=730.0)
    today = date.today()
    decay_now = agg.calculate_recency_decay(today, reference_date=today)
    assert decay_now == pytest.approx(1.0, rel=1e-3)

    decay_2yrs = agg.calculate_recency_decay(today - timedelta(days=730), reference_date=today)
    assert decay_2yrs == pytest.approx(0.5, rel=1e-2)


def test_profile_cold_start_handling():
    agg = StudentProfileAggregator()
    profile = agg.aggregate_profile(
        student_id="STU-COLD-01",
        department="Computer Science",
        program="B.Tech",
        year_of_study=1,
        gpa=8.0,
        declared_skills=["Python", "SQL"],
        declared_interests=["Machine Learning"],
        achievements=[],
    )
    assert profile.is_cold_start is True
    assert profile.profile_vector is not None
    assert len(profile.profile_vector) == 384
