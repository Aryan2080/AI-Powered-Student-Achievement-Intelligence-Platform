"""Tests for taxonomy YAML loader and file-local validator."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from nlp_semantic.schema import (
    LabelTaxonomy,
    TaxonomyError,
    TaxonomyStatus,
    TaxonomyTask,
    load_and_validate_taxonomy,
    load_taxonomy,
    validate_taxonomy,
)


# Shipped taxonomy files, resolved relative to the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
PRIMARY_YAML = REPO_ROOT / "hybrid_dataset" / "labels" / "primary_taxonomy.yaml"
DOMAIN_YAML = REPO_ROOT / "hybrid_dataset" / "labels" / "domain_tags.yaml"


# ---------- shipped files load and validate ----------------------------------


def test_primary_taxonomy_loads() -> None:
    entries = load_taxonomy(PRIMARY_YAML)
    assert len(entries) == 14


def test_primary_taxonomy_all_draft_and_task() -> None:
    entries = load_taxonomy(PRIMARY_YAML)
    for e in entries:
        assert e.status == TaxonomyStatus.DRAFT
        assert e.task_name == TaxonomyTask.PRIMARY_TYPE


def test_primary_taxonomy_passes_validate() -> None:
    entries = load_taxonomy(PRIMARY_YAML)
    validate_taxonomy(entries)  # must not raise


def test_primary_taxonomy_round_trip() -> None:
    entries = load_and_validate_taxonomy(PRIMARY_YAML)
    assert len(entries) == 14
    assert len({e.label_id for e in entries}) == 14


def test_domain_tags_loads() -> None:
    entries = load_taxonomy(DOMAIN_YAML)
    assert len(entries) == 10


def test_domain_tags_all_draft_and_task() -> None:
    entries = load_taxonomy(DOMAIN_YAML)
    for e in entries:
        assert e.status == TaxonomyStatus.DRAFT
        assert e.task_name == TaxonomyTask.DOMAIN_TAGS


def test_domain_tags_passes_validate() -> None:
    entries = load_taxonomy(DOMAIN_YAML)
    validate_taxonomy(entries)


# ---------- loader failure modes -----------------------------------------------


def _write_yaml(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_empty_yaml_returns_empty_list(tmp_path: Path) -> None:
    f = _write_yaml(tmp_path / "empty.yaml", "")
    assert load_taxonomy(f) == []


def test_null_yaml_returns_empty_list(tmp_path: Path) -> None:
    f = _write_yaml(tmp_path / "null.yaml", "null\n")
    assert load_taxonomy(f) == []


def test_top_level_not_list_rejected(tmp_path: Path) -> None:
    f = _write_yaml(tmp_path / "mapping.yaml", "label_id: lbl_x\n")
    with pytest.raises(TaxonomyError):
        load_taxonomy(f)


def test_entry_not_mapping_rejected(tmp_path: Path) -> None:
    f = _write_yaml(tmp_path / "scalar_entry.yaml", "- just_a_string\n")
    with pytest.raises(TaxonomyError):
        load_taxonomy(f)


def test_unknown_field_rejected(tmp_path: Path) -> None:
    f = _write_yaml(
        tmp_path / "unknown.yaml",
        "- label_id: lbl_ab\n"
        "  task_name: primary_type\n"
        "  display_name: AB\n"
        "  definition: d\n"
        "  mystery_field: oops\n",
    )
    with pytest.raises(ValidationError):
        load_taxonomy(f)


def test_bad_label_id_rejected(tmp_path: Path) -> None:
    f = _write_yaml(
        tmp_path / "bad_id.yaml",
        "- label_id: lbl_Hackathon\n"
        "  task_name: primary_type\n"
        "  display_name: X\n"
        "  definition: d\n",
    )
    with pytest.raises(ValidationError):
        load_taxonomy(f)


# ---------- validate_taxonomy failure modes -----------------------------------


def _entry(label_id: str, task: TaxonomyTask = TaxonomyTask.PRIMARY_TYPE,
           **kw) -> LabelTaxonomy:
    base = dict(
        label_id=label_id,
        task_name=task,
        display_name=label_id.replace("lbl_", "").replace("_", " ").title(),
        definition="synthetic test entry",
    )
    base.update(kw)
    return LabelTaxonomy(**base)


def test_validate_empty_set_ok() -> None:
    validate_taxonomy([])  # no raise


def test_duplicate_label_id_rejected() -> None:
    e1 = _entry("lbl_ab")
    e2 = _entry("lbl_ab", display_name="AB2")
    with pytest.raises(TaxonomyError, match="duplicate label_id"):
        validate_taxonomy([e1, e2])


def test_mixed_task_name_rejected() -> None:
    e1 = _entry("lbl_ab", task=TaxonomyTask.PRIMARY_TYPE)
    e2 = _entry("lbl_cd", task=TaxonomyTask.DOMAIN_TAGS)
    with pytest.raises(TaxonomyError, match="mixes multiple task_name"):
        validate_taxonomy([e1, e2])


def test_missing_supersedes_reference_rejected() -> None:
    e = _entry("lbl_ab", supersedes="lbl_nope")
    with pytest.raises(TaxonomyError, match="not present"):
        validate_taxonomy([e])


def test_two_entry_cycle_rejected() -> None:
    # a -> b, b -> a   (a cycle of length 2)
    e_a = _entry("lbl_aa", supersedes="lbl_bb")
    e_b = _entry("lbl_bb", supersedes="lbl_aa")
    with pytest.raises(TaxonomyError, match="cycle"):
        validate_taxonomy([e_a, e_b])


def test_three_entry_cycle_rejected() -> None:
    # a -> b -> c -> a
    e_a = _entry("lbl_aa", supersedes="lbl_bb")
    e_b = _entry("lbl_bb", supersedes="lbl_cc")
    e_c = _entry("lbl_cc", supersedes="lbl_aa")
    with pytest.raises(TaxonomyError, match="cycle"):
        validate_taxonomy([e_a, e_b, e_c])


def test_valid_linear_supersede_chain_allowed() -> None:
    # chain c -> b -> a with no cycle
    e_a = _entry("lbl_aa")
    e_b = _entry("lbl_bb", supersedes="lbl_aa")
    e_c = _entry("lbl_cc", supersedes="lbl_bb")
    validate_taxonomy([e_a, e_b, e_c])


def test_load_and_validate_convenience() -> None:
    entries = load_and_validate_taxonomy(PRIMARY_YAML)
    assert len(entries) == 14
