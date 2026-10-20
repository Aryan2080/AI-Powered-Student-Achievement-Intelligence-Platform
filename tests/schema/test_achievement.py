"""Tests for Achievement and AnnotationStatusMap."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from nlp_semantic.schema import (
    Achievement,
    AnnotationStatus,
    AnnotationStatusMap,
    make_id,
)


def _minimal(**overrides) -> dict:
    base = {
        "achievement_id": make_id("ach"),
        "source_id": make_id("src"),
        "source_record_id": "src_rec_001",
        "achievement_text": "Won first prize at Hackathon XYZ, 2024.",
        "is_synthetic": True,
    }
    base.update(overrides)
    return base


def test_minimal_achievement_valid() -> None:
    a = Achievement(**_minimal())
    assert a.primary_type is None
    assert a.domain_tags == []
    assert a.annotation_status.primary_type == AnnotationStatus.NOT_STARTED
    assert a.annotation_status.domain_tags == AnnotationStatus.NOT_STARTED
    assert a.is_synthetic is True


def test_bad_achievement_id() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(achievement_id="ach_tooShort"))


def test_bad_source_id_prefix() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(source_id=make_id("ach")))


def test_empty_text_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(achievement_text=""))


def test_whitespace_only_text_rejected() -> None:
    # str_strip_whitespace strips before min_length check
    with pytest.raises(ValidationError):
        Achievement(**_minimal(achievement_text="   "))


def test_invalid_primary_label_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(
            primary_type="lbl_Hackathon",  # uppercase, invalid
            annotation_status=AnnotationStatusMap(
                primary_type=AnnotationStatus.DRAFT
            ),
        ))


def test_draft_primary_type_allowed() -> None:
    a = Achievement(**_minimal(
        primary_type="lbl_hackathon",
        annotation_status=AnnotationStatusMap(
            primary_type=AnnotationStatus.DRAFT
        ),
    ))
    assert a.primary_type == "lbl_hackathon"
    assert a.annotation_status.primary_type == AnnotationStatus.DRAFT


def test_pending_primary_type_allowed() -> None:
    a = Achievement(**_minimal(
        primary_type="lbl_hackathon",
        annotation_status=AnnotationStatusMap(
            primary_type=AnnotationStatus.PENDING
        ),
    ))
    assert a.annotation_status.primary_type == AnnotationStatus.PENDING


def test_verified_primary_type_allowed() -> None:
    a = Achievement(**_minimal(
        primary_type="lbl_hackathon",
        annotation_status=AnnotationStatusMap(
            primary_type=AnnotationStatus.VERIFIED
        ),
    ))
    assert a.annotation_status.primary_type == AnnotationStatus.VERIFIED


def test_not_started_with_primary_type_rejected() -> None:
    # primary_type set but status still NOT_STARTED → consistency rule fires
    with pytest.raises(ValidationError):
        Achievement(**_minimal(primary_type="lbl_hackathon"))


def test_not_started_with_domain_tags_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(domain_tags=["lbl_domain_ai"]))


def test_verified_empty_domain_tags_allowed() -> None:
    """Verified-empty is distinguishable from not-started-empty."""
    a = Achievement(**_minimal(
        domain_tags=[],
        annotation_status=AnnotationStatusMap(
            domain_tags=AnnotationStatus.VERIFIED
        ),
    ))
    assert a.domain_tags == []
    assert a.annotation_status.domain_tags == AnnotationStatus.VERIFIED


def test_pending_candidate_domain_tag_allowed() -> None:
    a = Achievement(**_minimal(
        domain_tags=["lbl_domain_ai"],
        annotation_status=AnnotationStatusMap(
            domain_tags=AnnotationStatus.PENDING
        ),
    ))
    assert a.domain_tags == ["lbl_domain_ai"]


def test_duplicate_domain_tags_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(
            domain_tags=["lbl_domain_ai", "lbl_domain_ai"],
            annotation_status=AnnotationStatusMap(
                domain_tags=AnnotationStatus.DRAFT
            ),
        ))


def test_invalid_domain_tag_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(
            domain_tags=["domain-ai"],  # missing prefix
            annotation_status=AnnotationStatusMap(
                domain_tags=AnnotationStatus.DRAFT
            ),
        ))


def test_future_date_rejected() -> None:
    far_future = date.today() + timedelta(days=30)
    with pytest.raises(ValidationError):
        Achievement(**_minimal(achievement_date=far_future))


def test_today_date_allowed() -> None:
    a = Achievement(**_minimal(achievement_date=date.today()))
    assert a.achievement_date == date.today()


def test_rank_zero_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(rank=0))


def test_rank_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(rank=-1))


def test_rank_positive_allowed() -> None:
    a = Achievement(**_minimal(rank=1))
    assert a.rank == 1


def test_evidence_id_prefix_checked() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(evidence_id="ach_" + "a" * 32))


def test_evidence_id_valid_allowed() -> None:
    eid = make_id("evd")
    a = Achievement(**_minimal(evidence_id=eid))
    assert a.evidence_id == eid


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(junk_field="x"))


def test_skills_duplicate_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(skills=["python", "python"]))


def test_skills_empty_entry_rejected() -> None:
    with pytest.raises(ValidationError):
        Achievement(**_minimal(skills=["python", "  "]))


def test_round_trip_json() -> None:
    a = Achievement(**_minimal(
        primary_type="lbl_hackathon",
        domain_tags=["lbl_domain_ai"],
        annotation_status=AnnotationStatusMap(
            primary_type=AnnotationStatus.VERIFIED,
            domain_tags=AnnotationStatus.PENDING,
        ),
    ))
    assert Achievement.model_validate_json(a.model_dump_json()) == a
