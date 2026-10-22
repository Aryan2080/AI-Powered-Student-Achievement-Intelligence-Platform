"""Chunk 7.1 — structural checks on the refined primary-taxonomy entries.

These tests pin down the operational distinctions added in Chunk 7.1
WITHOUT asserting exact prose. The checks are intentionally loose
(presence of key operational terms + structural invariants) so small
future rewording does not break the suite, while still catching
regressions that drop the intended distinctions.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from nlp_semantic.schema import (
    LabelTaxonomy,
    TaxonomyStatus,
    TaxonomyTask,
    load_and_validate_taxonomy,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PRIMARY_YAML = REPO_ROOT / "hybrid_dataset" / "labels" / "primary_taxonomy.yaml"


@pytest.fixture(scope="module")
def primary_entries() -> list[LabelTaxonomy]:
    return load_and_validate_taxonomy(PRIMARY_YAML)


@pytest.fixture(scope="module")
def by_label_id(primary_entries: list[LabelTaxonomy]) -> dict[str, LabelTaxonomy]:
    return {e.label_id: e for e in primary_entries}


# ---- structural invariants (what Chunk 7.1 must NOT break) ------------------


def test_14_primary_entries_still_present(primary_entries: list[LabelTaxonomy]) -> None:
    assert len(primary_entries) == 14


def test_all_entries_remain_draft(primary_entries: list[LabelTaxonomy]) -> None:
    """Chunk 7.1 is a definition refinement — not a promotion."""
    for e in primary_entries:
        assert e.status == TaxonomyStatus.DRAFT, (
            f"{e.label_id} must remain draft; got {e.status.value}"
        )


def test_three_target_label_ids_unchanged(by_label_id: dict[str, LabelTaxonomy]) -> None:
    for label_id in ("lbl_hackathon", "lbl_competition", "lbl_project"):
        assert label_id in by_label_id, f"{label_id} must still exist"


def test_three_target_labels_are_primary_type(by_label_id: dict[str, LabelTaxonomy]) -> None:
    for label_id in ("lbl_hackathon", "lbl_competition", "lbl_project"):
        assert by_label_id[label_id].task_name == TaxonomyTask.PRIMARY_TYPE


def test_target_labels_have_populated_rules(by_label_id: dict[str, LabelTaxonomy]) -> None:
    """Each refined label still has at least one inclusion rule, one exclusion
    rule, and at least three examples."""
    for label_id in ("lbl_hackathon", "lbl_competition", "lbl_project"):
        e = by_label_id[label_id]
        assert e.inclusion_rules, f"{label_id} must retain inclusion_rules"
        assert e.exclusion_rules, f"{label_id} must retain exclusion_rules"
        assert len(e.examples) >= 3, f"{label_id} must retain >= 3 examples"


# ---- operational distinctions added by Chunk 7.1 ---------------------------


def _joined(label: LabelTaxonomy) -> str:
    return "\n".join(
        [label.definition]
        + list(label.inclusion_rules)
        + list(label.exclusion_rules)
    ).lower()


def test_hackathon_carries_seven_day_bound(by_label_id: dict[str, LabelTaxonomy]) -> None:
    """lbl_hackathon must state the seven-calendar-day build-window bound."""
    text = _joined(by_label_id["lbl_hackathon"])
    assert "seven calendar days" in text, (
        "lbl_hackathon definition/rules must state the seven-calendar-day bound"
    )


def test_hackathon_requires_demonstrable_prototype(
    by_label_id: dict[str, LabelTaxonomy],
) -> None:
    """lbl_hackathon must require a demonstrable prototype / MVP deliverable."""
    text = _joined(by_label_id["lbl_hackathon"])
    assert "prototype" in text
    assert ("mvp" in text) or ("minimum viable product" in text) or (
        "implementation" in text
    )


def test_hackathon_rejects_async_multiweek(by_label_id: dict[str, LabelTaxonomy]) -> None:
    text = _joined(by_label_id["lbl_hackathon"])
    assert "asynchronous" in text, (
        "lbl_hackathon exclusions must address multi-week asynchronous programs"
    )


def test_competition_defined_positively(by_label_id: dict[str, LabelTaxonomy]) -> None:
    """lbl_competition's definition must mention judged / scored / ranked —
    not rely primarily on 'not a hackathon'.
    """
    definition = by_label_id["lbl_competition"].definition.lower()
    assert ("judged" in definition) or ("scored" in definition) or ("ranked" in definition)


def test_competition_allows_participation_without_placement(
    by_label_id: dict[str, LabelTaxonomy],
) -> None:
    text = _joined(by_label_id["lbl_competition"])
    assert "judged participation" in text or "participation" in text


def test_project_is_artifact_centric(by_label_id: dict[str, LabelTaxonomy]) -> None:
    definition = by_label_id["lbl_project"].definition.lower()
    assert "artifact" in definition
    assert ("substantive" in definition) or ("substantial" in definition) or (
        "meaningful" in definition
    )


def test_project_rejects_universal_numeric_thresholds(
    by_label_id: dict[str, LabelTaxonomy],
) -> None:
    """Chunk 7.1 explicitly forbids baking numeric thresholds into PROJECT."""
    text = _joined(by_label_id["lbl_project"])
    assert ("not defined by universal numeric thresholds" in text) or (
        "not defined through arbitrary" in text
    ), "lbl_project must call out that substantiality is not a numeric threshold"


def test_project_accepts_single_meaningful_merged_pr(
    by_label_id: dict[str, LabelTaxonomy],
) -> None:
    """Open-source contributions evaluated by substance — a single
    meaningful merged pull request may qualify."""
    text = _joined(by_label_id["lbl_project"])
    assert "merged pull request" in text, (
        "lbl_project must allow a single meaningful merged pull request"
    )


def test_project_follow_on_rule_present(by_label_id: dict[str, LabelTaxonomy]) -> None:
    """The 'materially distinct follow-on may be recorded separately' rule
    must appear on both HACKATHON and PROJECT (duplicate-claim guard)."""
    for label_id in ("lbl_hackathon", "lbl_project"):
        text = _joined(by_label_id[label_id])
        assert "materially distinct" in text, (
            f"{label_id} must state the materially-distinct follow-on rule"
        )


def test_duplicate_record_guard_present(by_label_id: dict[str, LabelTaxonomy]) -> None:
    """All three labels must warn against duplicating the same claim."""
    for label_id in ("lbl_hackathon", "lbl_competition", "lbl_project"):
        text = _joined(by_label_id[label_id])
        assert "duplicate" in text or "do not duplicate" in text, (
            f"{label_id} must state a duplicate-record guard"
        )


# ---- annotation guidelines coverage ----------------------------------------


def test_annotation_guidelines_has_boundary_matrix() -> None:
    """The decision procedure + boundary matrix added by Chunk 7.1 must
    be present in ANNOTATION_GUIDELINES.md.
    """
    text = (
        REPO_ROOT / "hybrid_dataset" / "dataset" / "ANNOTATION_GUIDELINES.md"
    ).read_text("utf-8").lower()
    assert "hackathon" in text and "competition" in text and "project" in text
    assert "boundary matrix" in text
    assert "event-centric" in text and "artifact-centric" in text
    assert "seven calendar days" in text
    assert "merged pull request" in text
