"""Annotation model — one annotation decision per (achievement, task) pair."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import AnnotationStatus, AnnotationTask
from .identifiers import validate_label_id, validate_prefixed_id

# ``[^\s@]+@[^\s@]+\.[^\s@]+`` catches well-formed email-like strings.
_EMAIL_LIKE_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
# Pseudonym: starts with alphanumeric or underscore, length 2-64,
# interior chars from [A-Za-z0-9_-]. No '@', no spaces.
_ANNOTATOR_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$")


class Annotation(BaseModel):
    """One annotation decision for one (achievement, task) pair.

    This is a history record. The current summary status per task lives on
    ``Achievement.annotation_status``. An unverified ``Annotation`` must
    not silently replace a verified one; mismatch detection is a
    dataset-level concern, not enforced here.

    Privacy note: ``annotator`` must be a pseudonym or team handle, never
    an email, real name, or contact detail. The mapping from pseudonym to
    identity must not be stored in this repository.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    annotation_id: str
    achievement_id: str
    task: AnnotationTask
    label_ids: list[str] = Field(default_factory=list)
    annotator: str
    review_status: AnnotationStatus = AnnotationStatus.DRAFT
    notes: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_synthetic: bool = False

    @field_validator("annotation_id")
    @classmethod
    def _validate_annotation_id(cls, v: str) -> str:
        return validate_prefixed_id(v, "ann")

    @field_validator("achievement_id")
    @classmethod
    def _validate_achievement_id(cls, v: str) -> str:
        return validate_prefixed_id(v, "ach")

    @field_validator("label_ids")
    @classmethod
    def _validate_label_ids(cls, v: list[str]) -> list[str]:
        for lid in v:
            validate_label_id(lid)
        if len(set(v)) != len(v):
            raise ValueError("label_ids must not contain duplicates")
        return v

    @field_validator("annotator")
    @classmethod
    def _validate_annotator(cls, v: str) -> str:
        if _EMAIL_LIKE_RE.match(v):
            raise ValueError(
                "annotator must be a pseudonym or team handle, not an email "
                "address"
            )
        if not _ANNOTATOR_RE.match(v):
            raise ValueError(
                "annotator must be 2-64 chars, start with alphanumeric or "
                "underscore, and contain only letters, digits, '_' or '-'"
            )
        return v

    @field_validator("review_status")
    @classmethod
    def _validate_review_status(cls, v: AnnotationStatus) -> AnnotationStatus:
        if v == AnnotationStatus.NOT_STARTED:
            raise ValueError(
                "Annotation.review_status must not be 'not_started'; the "
                "absence of annotation is represented by having no "
                "Annotation row and the parent Achievement's "
                "annotation_status marking it 'not_started'."
            )
        return v

    @field_validator("created_at")
    @classmethod
    def _validate_created_at_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError(
                "created_at must be a timezone-aware datetime; naive "
                "datetimes are not accepted. Use datetime.now(timezone.utc) "
                "or attach an explicit tzinfo."
            )
        return v

    @model_validator(mode="after")
    def _check_task_arity(self) -> "Annotation":
        if self.task == AnnotationTask.PRIMARY_TYPE:
            if len(self.label_ids) != 1:
                raise ValueError(
                    "annotation task 'primary_type' requires exactly one "
                    "label_id"
                )
        elif self.task == AnnotationTask.EXTRACTION_REVIEW:
            if self.label_ids:
                raise ValueError(
                    "annotation task 'extraction_review' must have empty "
                    "label_ids; it is a review task, not a classification "
                    "task"
                )
        # DOMAIN_TAGS: 0..N allowed; status disambiguates "none applicable"
        # vs "not started" via Achievement.annotation_status.
        return self
