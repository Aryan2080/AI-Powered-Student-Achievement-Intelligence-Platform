"""LabelTaxonomy model — one label definition per (task, label_id) pair."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import TaxonomyStatus, TaxonomyTask
from .identifiers import validate_label_id


class LabelTaxonomy(BaseModel):
    """One label definition for one taxonomy task.

    ``task_name`` is constrained to ``TaxonomyTask`` (``primary_type`` or
    ``domain_tags``). ``extraction_review`` is intentionally NOT a taxonomy
    task; it has no labels, it is a review workflow.

    Renamed or replaced labels are expressed via ``supersedes``: the new
    label row references the old label's ``label_id``, and the old row's
    ``status`` is moved to ``deprecated``. Both rows are kept so historical
    annotations remain interpretable.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    label_id: str
    task_name: TaxonomyTask
    display_name: str = Field(min_length=1, max_length=120)
    definition: str = Field(min_length=1, max_length=2000)
    inclusion_rules: list[str] = Field(default_factory=list)
    exclusion_rules: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    status: TaxonomyStatus = TaxonomyStatus.DRAFT
    supersedes: str | None = None

    @field_validator("label_id")
    @classmethod
    def _validate_label_id(cls, v: str) -> str:
        return validate_label_id(v)

    @field_validator("supersedes")
    @classmethod
    def _validate_supersedes(cls, v: str | None) -> str | None:
        return v if v is None else validate_label_id(v)

    @field_validator("inclusion_rules", "exclusion_rules", "examples")
    @classmethod
    def _validate_string_list(cls, v: list[str]) -> list[str]:
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("list entries must be non-empty strings")
        return v

    @model_validator(mode="after")
    def _check_no_self_supersede(self) -> "LabelTaxonomy":
        if self.supersedes is not None and self.supersedes == self.label_id:
            raise ValueError(
                "supersedes must reference a different label_id; a label "
                "cannot supersede itself"
            )
        return self
