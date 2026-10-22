"""Tests for the reproducible split generator."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from nlp_semantic.schema import Achievement, make_id
from nlp_semantic.dataset.splits import (
    DEFAULT_RATIOS,
    SplitFeasibilityError,
    SplitManifest,
    SplitResult,
    generate_splits,
    write_splits,
)


# ---- fixtures ---------------------------------------------------------------


def _rec(source_id: str, **overrides: Any) -> Achievement:
    base: dict[str, Any] = dict(
        achievement_id=make_id("ach"),
        source_id=source_id,
        source_record_id="src-ext-" + make_id("ach")[-6:],
        achievement_text="A record.",
        is_synthetic=False,
    )
    base.update(overrides)
    return Achievement(**base)


def _records_from_many_sources(n_sources: int, per_source: int) -> list[Achievement]:
    """Build ``n_sources`` groups of ``per_source`` records each."""
    out = []
    for _ in range(n_sources):
        sid = make_id("src")
        for _ in range(per_source):
            out.append(_rec(sid))
    return out


# ---- ratio validation -------------------------------------------------------


def test_default_ratios_sum_to_one() -> None:
    assert abs(sum(DEFAULT_RATIOS.values()) - 1.0) < 1e-9


def test_negative_ratio_raises_feasibility_error() -> None:
    with pytest.raises(SplitFeasibilityError, match="negative"):
        generate_splits([], seed=0, ratios={"train": -0.1, "val": 0.5, "test": 0.6})


def test_ratios_not_summing_to_one_raise() -> None:
    with pytest.raises(SplitFeasibilityError, match="sum"):
        generate_splits([], seed=0, ratios={"train": 0.5, "val": 0.3, "test": 0.1})


def test_empty_ratios_raise() -> None:
    with pytest.raises(SplitFeasibilityError, match="at least one"):
        generate_splits([], seed=0, ratios={})


def test_non_finite_ratio_raises() -> None:
    with pytest.raises(SplitFeasibilityError, match="finite"):
        generate_splits([], seed=0, ratios={"train": float("inf"), "val": 0.0, "test": 0.0})


# ---- determinism ------------------------------------------------------------


def test_same_seed_same_input_produces_identical_result() -> None:
    recs = _records_from_many_sources(n_sources=12, per_source=3)
    a = generate_splits(recs, seed=42)
    b = generate_splits(recs, seed=42)
    assert a.manifest.source_assignments == b.manifest.source_assignments
    assert a.manifest.actual_sizes == b.manifest.actual_sizes
    assert [r.achievement_id for r in a.splits["train"]] == [
        r.achievement_id for r in b.splits["train"]
    ]


def test_different_seeds_can_produce_different_assignments() -> None:
    recs = _records_from_many_sources(n_sources=12, per_source=3)
    a = generate_splits(recs, seed=0)
    b = generate_splits(recs, seed=99999)
    # It is possible but unlikely that two different seeds produce the
    # exact same assignment for 12 groups; assert at least one split
    # differs so the test fails if the seed is being ignored.
    assert a.manifest.source_assignments != b.manifest.source_assignments


# ---- source-group leakage (property) ----------------------------------------


def test_no_source_id_crosses_splits_small() -> None:
    recs = _records_from_many_sources(n_sources=12, per_source=3)
    result = generate_splits(recs, seed=7)
    seen: dict[str, str] = {}
    for name, rs in result.splits.items():
        for r in rs:
            if r.source_id in seen and seen[r.source_id] != name:
                raise AssertionError(
                    f"source_id {r.source_id} appears in both "
                    f"{seen[r.source_id]!r} and {name!r}"
                )
            seen[r.source_id] = name


@pytest.mark.parametrize("seed", list(range(10)))
def test_no_source_id_crosses_splits_property(seed: int) -> None:
    """Property: for ten seeds, no source_id ever crosses splits."""
    recs = _records_from_many_sources(n_sources=20, per_source=5)
    result = generate_splits(recs, seed=seed)
    seen: dict[str, str] = {}
    for name, rs in result.splits.items():
        for r in rs:
            if r.source_id in seen:
                assert seen[r.source_id] == name
            seen[r.source_id] = name


# ---- synthetic exclusion ----------------------------------------------------


def test_synthetic_records_excluded_by_default() -> None:
    sid1 = make_id("src")
    sid2 = make_id("src")
    recs = [_rec(sid1) for _ in range(2)] + [_rec(sid2, is_synthetic=True) for _ in range(3)]
    result = generate_splits(recs, seed=1)
    total_in_splits = sum(len(rs) for rs in result.splits.values())
    assert total_in_splits == 2  # synthetic ones dropped
    assert result.manifest.excluded_synthetic_count == 3


def test_synthetic_included_when_flag_disabled() -> None:
    sid = make_id("src")
    recs = [_rec(sid), _rec(sid, is_synthetic=True)]
    result = generate_splits(recs, seed=1, exclude_synthetic=False)
    assert result.manifest.excluded_synthetic_count == 0
    total = sum(len(rs) for rs in result.splits.values())
    assert total == 2


# ---- infeasibility handling (warnings, not errors) --------------------------


def test_no_records_at_all_produces_empty_splits_with_warning() -> None:
    result = generate_splits([], seed=0)
    assert all(len(rs) == 0 for rs in result.splits.values())
    assert "no_records_to_split" in result.manifest.warnings


def test_too_few_source_groups_warns() -> None:
    """Fewer source groups than non-zero splits should surface as a warning."""
    sid1 = make_id("src")
    sid2 = make_id("src")
    recs = [_rec(sid1) for _ in range(3)] + [_rec(sid2) for _ in range(3)]
    result = generate_splits(recs, seed=0)
    assert any(w.startswith("source_group_count_below_nonzero_split_count") for w in result.manifest.warnings)


# ---- actual ratios reporting ------------------------------------------------


def test_actual_ratios_reported_close_to_targets_on_balanced_input() -> None:
    recs = _records_from_many_sources(n_sources=20, per_source=5)  # 100 records, 20 groups
    result = generate_splits(recs, seed=0)
    total = sum(result.manifest.actual_sizes.values())
    assert total == 100
    # Each actual ratio within 10% absolute of target on this scale.
    for name, target in DEFAULT_RATIOS.items():
        assert abs(result.manifest.actual_ratios[name] - target) < 0.10


def test_class_distribution_populated_per_split() -> None:
    sid1, sid2, sid3 = make_id("src"), make_id("src"), make_id("src")
    recs = (
        [_rec(sid1, primary_type=None) for _ in range(4)]
        + [_rec(sid2, primary_type=None) for _ in range(4)]
        + [_rec(sid3, primary_type=None) for _ in range(4)]
    )
    result = generate_splits(recs, seed=0)
    for name, dist in result.manifest.class_distribution.items():
        total = sum(dist.values())
        assert total == result.manifest.actual_sizes[name]


# ---- write_splits -----------------------------------------------------------


def test_write_splits_produces_jsonl_and_manifest(tmp_path: Path) -> None:
    recs = _records_from_many_sources(n_sources=6, per_source=2)
    result = generate_splits(recs, seed=0)
    manifest = write_splits(result, tmp_path)

    splits_dir = tmp_path / "processed" / "splits"
    assert (splits_dir / "train.jsonl").exists()
    assert (splits_dir / "val.jsonl").exists()
    assert (splits_dir / "test.jsonl").exists()
    assert (splits_dir / "split_manifest.json").exists()

    # Manifest should carry file hashes.
    assert set(manifest.file_hashes) == {"train.jsonl", "val.jsonl", "test.jsonl"}

    # Each line of each jsonl is a valid Achievement JSON.
    for name in ("train", "val", "test"):
        lines = (splits_dir / f"{name}.jsonl").read_text("utf-8").splitlines()
        assert len(lines) == manifest.actual_sizes[name]
        for line in lines:
            payload = json.loads(line)
            assert "achievement_id" in payload


def test_write_splits_is_reproducible(tmp_path: Path) -> None:
    recs = _records_from_many_sources(n_sources=6, per_source=2)
    r1 = generate_splits(recs, seed=0)
    r2 = generate_splits(recs, seed=0)
    m1 = write_splits(r1, tmp_path / "a")
    m2 = write_splits(r2, tmp_path / "b")
    assert m1.file_hashes == m2.file_hashes


def test_manifest_json_is_well_formed(tmp_path: Path) -> None:
    recs = _records_from_many_sources(n_sources=6, per_source=2)
    result = generate_splits(recs, seed=0)
    write_splits(result, tmp_path)
    data = json.loads((tmp_path / "processed" / "splits" / "split_manifest.json").read_text("utf-8"))
    assert data["seed"] == 0
    assert "file_hashes" in data
    assert "actual_sizes" in data
    assert "class_distribution" in data


def test_manifest_file_hashes_match_file_contents(tmp_path: Path) -> None:
    recs = _records_from_many_sources(n_sources=4, per_source=2)
    result = generate_splits(recs, seed=1)
    manifest = write_splits(result, tmp_path)
    for name, expected_hash in manifest.file_hashes.items():
        actual = hashlib.sha256(
            (tmp_path / "processed" / "splits" / name).read_bytes()
        ).hexdigest()
        assert actual == expected_hash


# ---- defensive: inputs are not mutated --------------------------------------


def test_generate_splits_never_mutates_input() -> None:
    sid = make_id("src")
    recs = [_rec(sid) for _ in range(5)]
    ids_before = [r.achievement_id for r in recs]
    generate_splits(recs, seed=0)
    ids_after = [r.achievement_id for r in recs]
    assert ids_before == ids_after
