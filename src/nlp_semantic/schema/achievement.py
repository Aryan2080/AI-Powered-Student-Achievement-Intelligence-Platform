"""Achievement model and per-task annotation status map."""
from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import AnnotationStatus
from .identifiers import validate_label_id, validate_prefixed_id


class AnnotationStatusMap(BaseModel):
    """Current task-level annotation status summary for one Achievement.

    One status per task. ``NOT_STARTED`` means *no annotation performed yet*
    for that task and is distinct from an annotation that was performed and
    produced an empty result (``VERIFIED`` with empty ``domain_tags``, for
    example). Downstream code must not infer negative labels from
    ``NOT_STARTED`` and must not treat ``DRAFT``/``PENDING``/``CONFLICTED``
    annotations as verified ground truth.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    primary_type: AnnotationStatus = AnnotationStatus.NOT_STARTED
    domain_tags: AnnotationStatus = AnnotationStatus.NOT_STARTED


class Achievement(BaseModel):
    """One claimed achievement.

    ``primary_type`` and ``domain_tags`` may carry values at ``DRAFT`` or
    ``PENDING`` status. Only records whose matching
    ``annotation_status.<task>`` is ``VERIFIED`` are eligible as ground
    truth; that eligibility rule is enforced by downstream dataset
    validation, not by this model.

    Extraction fields (``level``, ``outcome``, ``event_name``,
    ``organization``, ``achievement_date``, ``rank``, ``skills``) are
    information-extraction outputs and are intentionally NOT classification
    labels.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    achievement_id: str
    source_id: str
    source_record_id: str = Field(min_length=1, max_length=200)
    achievement_text: str = Field(min_length=1, max_length=4000)
    primary_type: str | None = None
    domain_tags: list[str] = Field(default_factory=list)
    level: str | None = Field(default=None, max_length=120)
    outcome: str | None = Field(default=None, max_length=120)
    event_name: str | None = Field(default=None, max_length=250)
    organization: str | None = Field(default=None, max_length=250)
    achievement_date: date | None = None
    rank: int | None = None
    skills: list[str] = Field(default_factory=list)
    evidence_id: str | None = None
    annotation_status: AnnotationStatusMap = Field(default_factory=AnnotationStatusMap)
    is_synthetic: bool = False

    @field_validator("achievement_id")
    @classmethod
    def _validate_achievement_id(cls, v: str) -> str:
        return validate_prefixed_id(v, "ach")

    @field_validator("source_id")
    @classmethod
    def _validate_source_id(cls, v: str) -> str:
        return validate_prefixed_id(v, "src")

    @field_validator("evidence_id")
    @classmethod
    def _validate_evidence_id(cls, v: str | None) -> str | None:
        return v if v is None else validate_prefixed_id(v, "evd")

    @field_validator("primary_type")
    @classmethod
    def _validate_primary_type(cls, v: str | None) -> str | None:
        return v if v is None else validate_label_id(v)

    @field_validator("domain_tags")
    @classmethod
    def _validate_domain_tags(cls, v: list[str]) -> list[str]:
        for tag in v:
            validate_label_id(tag)
        if len(set(v)) != len(v):
            raise ValueError("domain_tags must not contain duplicates")
        return v

    @field_validator("skills")
    @classmethod
    def _validate_skills(cls, v: list[str]) -> list[str]:
        for s in v:
            if not isinstance(s, str) or not s.strip():
                raise ValueError("skills entries must be non-empty strings")
            if len(s) > 120:
                raise ValueError("skill strings must be at most 120 chars")
        if len(set(v)) != len(v):
            raise ValueError("skills must not contain duplicates")
        return v

    @field_validator("achievement_date")
    @classmethod
    def _validate_date(cls, v: date | None) -> date | None:
        if v is None:
            return v
        max_allowed = date.today() + timedelta(days=1)
        if v > max_allowed:
            raise ValueError(
                f"achievement_date must be <= {max_allowed.isoformat()} "
                f"(today + 1 day clock-skew tolerance); got {v.isoformat()}"
            )
        return v

    @field_validator("rank")
    @classmethod
    def _validate_rank(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v < 1:
            raise ValueError("rank must be >= 1 when set")
        return v

    @model_validator(mode="after")
    def _check_annotation_consistency(self) -> "Achievement":
        if (
            self.annotation_status.primary_type == AnnotationStatus.NOT_STARTED
            and self.primary_type is not None
        ):
            raise ValueError(
                "primary_type is set but annotation_status.primary_type is "
                "'not_started'; move the status to 'draft' or higher before "
                "populating primary_type."
            )
        if (
            self.annotation_status.domain_tags == AnnotationStatus.NOT_STARTED
            and self.domain_tags
        ):
            raise ValueError(
                "domain_tags is non-empty but annotation_status.domain_tags "
                "is 'not_started'; move the status to 'draft' or higher "
                "before populating domain_tags."
            )
        return self
