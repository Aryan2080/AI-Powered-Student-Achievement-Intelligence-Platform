"""Tests for LabelTaxonomy model."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from nlp_semantic.schema import (
    LabelTaxonomy,
    TaxonomyStatus,
    TaxonomyTask,
)


def _minimal(**overrides) -> dict:
    base = {
        "label_id": "lbl_hackathon",
        "task_name": TaxonomyTask.PRIMARY_TYPE,
        "display_name": "Hackathon",
        "definition": (
            "Participation or placement in a time-boxed competitive team "
            "event."
        ),
    }
    base.update(overrides)
    return base


def test_minimal_valid() -> None:
    t = LabelTaxonomy(**_minimal())
    assert t.status == TaxonomyStatus.DRAFT
    assert t.inclusion_rules == []
    assert t.supersedes is None


def test_bad_label_id_rejected() -> None:
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(label_id="Hackathon"))


def test_label_id_uppercase_rejected() -> None:
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(label_id="lbl_Hackathon"))


def test_label_id_missing_prefix_rejected() -> None:
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(label_id="hackathon"))


def test_supersedes_format_checked() -> None:
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(supersedes="hack"))


def test_supersedes_valid() -> None:
    t = LabelTaxonomy(**_minimal(supersedes="lbl_old_hackathon"))
    assert t.supersedes == "lbl_old_hackathon"


def test_task_name_restricted_to_taxonomy_tasks() -> None:
    """extraction_review is NOT a TaxonomyTask value."""
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(task_name="extraction_review"))


def test_task_name_primary_type_allowed() -> None:
    t = LabelTaxonomy(**_minimal(task_name=TaxonomyTask.PRIMARY_TYPE))
    assert t.task_name == TaxonomyTask.PRIMARY_TYPE


def test_task_name_domain_tags_allowed() -> None:
    t = LabelTaxonomy(**_minimal(
        label_id="lbl_domain_ai",
        task_name=TaxonomyTask.DOMAIN_TAGS,
        display_name="AI Domain",
    ))
    assert t.task_name == TaxonomyTask.DOMAIN_TAGS


def test_definition_required() -> None:
    data = _minimal()
    data.pop("definition")
    with pytest.raises(ValidationError):
        LabelTaxonomy(**data)


def test_definition_empty_rejected() -> None:
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(definition=""))


def test_empty_rule_entries_rejected() -> None:
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(inclusion_rules=["ok", "  "]))


def test_status_enum_strict() -> None:
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(status="FINAL"))


@pytest.mark.parametrize(
    "status",
    [
        TaxonomyStatus.DRAFT,
        TaxonomyStatus.UNDER_REVIEW,
        TaxonomyStatus.APPROVED,
        TaxonomyStatus.DEPRECATED,
    ],
)
def test_all_taxonomy_statuses_allowed(status: TaxonomyStatus) -> None:
    t = LabelTaxonomy(**_minimal(status=status))
    assert t.status == status


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(category="misc"))


def test_round_trip_json() -> None:
    t = LabelTaxonomy(**_minimal(
        inclusion_rules=["Team-based entry"],
        exclusion_rules=["Solo project submissions"],
        examples=["Won HackMIT 2024"],
        status=TaxonomyStatus.APPROVED,
    ))
    assert LabelTaxonomy.model_validate_json(t.model_dump_json()) == t


def test_self_supersede_rejected() -> None:
    with pytest.raises(ValidationError):
        LabelTaxonomy(**_minimal(
            label_id="lbl_hackathon",
            supersedes="lbl_hackathon",
        ))


def test_supersedes_none_still_valid() -> None:
    t = LabelTaxonomy(**_minimal(supersedes=None))
    assert t.supersedes is None


def test_distinct_supersede_still_valid() -> None:
    t = LabelTaxonomy(**_minimal(
        label_id="lbl_hackathon_v2",
        supersedes="lbl_hackathon",
    ))
    assert t.supersedes == "lbl_hackathon"
    assert t.label_id == "lbl_hackathon_v2"
