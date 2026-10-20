"""Tests for Annotation model."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from nlp_semantic.schema import (
    Annotation,
    AnnotationStatus,
    AnnotationTask,
    make_id,
)


def _minimal(**overrides) -> dict:
    base = {
        "annotation_id": make_id("ann"),
        "achievement_id": make_id("ach"),
        "task": AnnotationTask.PRIMARY_TYPE,
        "label_ids": ["lbl_hackathon"],
        "annotator": "m1_arayan",
        "is_synthetic": True,
    }
    base.update(overrides)
    return base


def test_primary_type_exact_one_label() -> None:
    a = Annotation(**_minimal())
    assert a.task == AnnotationTask.PRIMARY_TYPE
    assert a.review_status == AnnotationStatus.DRAFT


def test_primary_type_zero_labels_rejected() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(label_ids=[]))


def test_primary_type_two_labels_rejected() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(label_ids=["lbl_hackathon", "lbl_project"]))


def test_domain_tags_zero_allowed() -> None:
    a = Annotation(**_minimal(
        task=AnnotationTask.DOMAIN_TAGS,
        label_ids=[],
    ))
    assert a.label_ids == []


def test_domain_tags_many_allowed() -> None:
    a = Annotation(**_minimal(
        task=AnnotationTask.DOMAIN_TAGS,
        label_ids=["lbl_domain_ai", "lbl_domain_ml", "lbl_domain_nlp"],
    ))
    assert len(a.label_ids) == 3


def test_extraction_review_rejects_labels() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(
            task=AnnotationTask.EXTRACTION_REVIEW,
            label_ids=["lbl_hackathon"],
        ))


def test_extraction_review_empty_ok() -> None:
    a = Annotation(**_minimal(
        task=AnnotationTask.EXTRACTION_REVIEW,
        label_ids=[],
    ))
    assert a.task == AnnotationTask.EXTRACTION_REVIEW


@pytest.mark.parametrize(
    "bad_annotator",
    [
        "test.user@example.org",
        "user@example.org",
        "has space",
        "has@sign",
        "x",                       # too short
        "-starts_with_dash",       # first char must be [A-Za-z0-9_]
        "contains!bang",
    ],
)
def test_annotator_rejects_bad_values(bad_annotator: str) -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(annotator=bad_annotator))


@pytest.mark.parametrize(
    "good_annotator",
    ["m1_arayan", "anon_a1", "annotator_01", "team_handle-A", "_pseudo"],
)
def test_annotator_accepts_pseudonyms(good_annotator: str) -> None:
    a = Annotation(**_minimal(annotator=good_annotator))
    assert a.annotator == good_annotator


def test_review_status_not_started_rejected() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(review_status=AnnotationStatus.NOT_STARTED))


def test_review_status_conflicted_allowed() -> None:
    a = Annotation(**_minimal(review_status=AnnotationStatus.CONFLICTED))
    assert a.review_status == AnnotationStatus.CONFLICTED


@pytest.mark.parametrize(
    "status",
    [
        AnnotationStatus.DRAFT,
        AnnotationStatus.PENDING,
        AnnotationStatus.VERIFIED,
        AnnotationStatus.REJECTED,
        AnnotationStatus.CONFLICTED,
    ],
)
def test_all_non_not_started_statuses_allowed(status: AnnotationStatus) -> None:
    a = Annotation(**_minimal(review_status=status))
    assert a.review_status == status


def test_duplicate_label_ids_rejected() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(
            task=AnnotationTask.DOMAIN_TAGS,
            label_ids=["lbl_domain_ai", "lbl_domain_ai"],
        ))


def test_invalid_label_id_rejected() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(label_ids=["hackathon"]))


def test_annotation_id_prefix_checked() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(annotation_id=make_id("ach")))


def test_achievement_id_prefix_checked() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(achievement_id=make_id("ann")))


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(unexpected="x"))


def test_created_at_default_is_tz_aware() -> None:
    a = Annotation(**_minimal())
    assert a.created_at.tzinfo is not None
    assert a.created_at.utcoffset() is not None


def test_created_at_naive_datetime_rejected() -> None:
    with pytest.raises(ValidationError):
        Annotation(**_minimal(created_at=datetime(2024, 1, 1, 12, 0, 0)))


def test_created_at_utc_aware_allowed() -> None:
    ts = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
    a = Annotation(**_minimal(created_at=ts))
    assert a.created_at == ts
    assert a.created_at.utcoffset() == timedelta(0)


def test_created_at_non_utc_aware_allowed() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    ts = datetime(2024, 6, 15, 16, 0, 0, tzinfo=ist)
    a = Annotation(**_minimal(created_at=ts))
    assert a.created_at.utcoffset() == timedelta(hours=5, minutes=30)
