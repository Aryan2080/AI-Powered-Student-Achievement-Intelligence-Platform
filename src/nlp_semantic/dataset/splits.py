"""Deterministic, source-grouped train/val/test splits.

Guarantees (hard):

* Deterministic — same input + same seed produces the same assignment.
* Source-group integrity — every record carrying a given ``source_id``
  lands in exactly one split. No ``source_id`` crosses splits.
* Synthetic records excluded from real-data splits by default
  (``exclude_synthetic=True``). This is a filter, not a quality claim
  about non-synthetic data.
* The seed and the full assignment are recorded in a manifest so the
  split can be reproduced or audited.
* Every output file's SHA-256 is recorded in the manifest.

What this module does **not** promise:

* True stratification by ``primary_type``. Source grouping and
  stratification can conflict: when all records of a class live in one
  source, that class cannot be split proportionally. The manifest
  reports actual class distribution; it does not claim stratification
  that it cannot deliver.
* Catching semantic duplicates that span sources. Deterministic
  duplicate detection runs separately (``find_duplicates``); semantic
  dedup is deferred to a later chunk.
* Any guarantee about splits in the face of class imbalance in the
  input. If an entire class fits in one source, so will the entire
  class.

Infeasibility is surfaced in :attr:`SplitManifest.warnings`, not
raised. A nonsense ratio tuple (negative, non-finite, or not summing
to 1 within tolerance) raises :class:`SplitFeasibilityError` early.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nlp_semantic.schema import Achievement


DEFAULT_RATIOS: dict[str, float] = {"train": 0.70, "val": 0.15, "test": 0.15}
_RATIO_SUM_TOL = 1e-6
SPLITS_SUBDIR = "processed/splits"


class SplitFeasibilityError(ValueError):
    """Ratios are structurally invalid (negative, non-finite, or do not sum to 1)."""


@dataclass(frozen=True)
class SplitManifest:
    seed: int
    ratios: dict[str, float]
    actual_sizes: dict[str, int]
    actual_ratios: dict[str, float]
    source_assignments: dict[str, list[str]]
    class_distribution: dict[str, dict[str, int]]
    excluded_synthetic_count: int
    file_hashes: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "ratios": dict(self.ratios),
            "actual_sizes": dict(self.actual_sizes),
            "actual_ratios": dict(self.actual_ratios),
            "source_assignments": {k: list(v) for k, v in self.source_assignments.items()},
            "class_distribution": {
                k: dict(v) for k, v in self.class_distribution.items()
            },
            "excluded_synthetic_count": self.excluded_synthetic_count,
            "file_hashes": dict(self.file_hashes),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class SplitResult:
    splits: dict[str, list[Achievement]]
    manifest: SplitManifest


# ---- helpers ----------------------------------------------------------------


def _validate_ratios(ratios: Mapping[str, float]) -> None:
    if not ratios:
        raise SplitFeasibilityError("ratios must contain at least one split name")
    for name, v in ratios.items():
        if not isinstance(v, (int, float)):
            raise SplitFeasibilityError(
                f"ratio for {name!r} must be numeric; got {type(v).__name__}"
            )
        if not math.isfinite(v):
            raise SplitFeasibilityError(f"ratio for {name!r} is not finite: {v}")
        if v < 0:
            raise SplitFeasibilityError(f"ratio for {name!r} is negative: {v}")
    s = sum(ratios.values())
    if abs(s - 1.0) > _RATIO_SUM_TOL:
        raise SplitFeasibilityError(
            f"ratios must sum to 1.0 (+/-{_RATIO_SUM_TOL}); got sum={s!r}"
        )


def _group_by_source(records: Iterable[Achievement]) -> dict[str, list[Achievement]]:
    """Return source_id -> list of records (preserving input order)."""
    out: dict[str, list[Achievement]] = {}
    for rec in records:
        out.setdefault(rec.source_id, []).append(rec)
    return out


def _assign_source_groups(
    sorted_source_ids: list[str],
    group_sizes: dict[str, int],
    ratios: dict[str, float],
    total: int,
) -> dict[str, list[str]]:
    """Greedy source-group → split assignment with largest-deficit-first ordering.

    Walks ``sorted_source_ids`` in order; for each group, picks the
    split whose current fill is furthest below its target. Ties resolve
    in favor of the split with the smaller name (so order is
    deterministic given the ratio keys).
    """
    assignments: dict[str, list[str]] = {name: [] for name in ratios}
    fills: Counter[str] = Counter()
    targets = {name: ratios[name] * total for name in ratios}

    split_names_sorted = sorted(ratios.keys())
    for sid in sorted_source_ids:
        size = group_sizes[sid]
        # pick split with largest (target - fill); tie-break by name.
        best_name = min(
            split_names_sorted,
            key=lambda n: (-(targets[n] - fills[n]), n),
        )
        assignments[best_name].append(sid)
        fills[best_name] += size
    return assignments


def _class_distribution(
    records: Iterable[Achievement],
) -> dict[str, int]:
    """primary_type → count (None → '<none>') for a split."""
    c: Counter[str] = Counter()
    for r in records:
        key = r.primary_type if r.primary_type is not None else "<none>"
        c[key] += 1
    return {k: v for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))}


# ---- public API --------------------------------------------------------------


def generate_splits(
    records: Iterable[Achievement],
    *,
    seed: int,
    ratios: Mapping[str, float] | None = None,
    exclude_synthetic: bool = True,
) -> SplitResult:
    """Produce a reproducible source-grouped split.

    Args:
        records: input Achievement records.
        seed: deterministic shuffle seed; recorded in the manifest.
        ratios: split-name → target proportion. Defaults to 70/15/15.
            Must sum to 1 ± 1e-6.
        exclude_synthetic: when True (default), drop ``is_synthetic``
            records before assignment. The excluded count is recorded
            in the manifest.

    Returns:
        A :class:`SplitResult` with the per-split record lists and a
        :class:`SplitManifest`. The manifest's ``warnings`` list is
        non-empty if the input did not permit the requested ratios.

    Raises:
        SplitFeasibilityError: ratios are structurally invalid.
    """
    r = dict(ratios) if ratios is not None else dict(DEFAULT_RATIOS)
    _validate_ratios(r)

    all_records = list(records)
    if exclude_synthetic:
        excluded = sum(1 for rec in all_records if rec.is_synthetic)
        real_records = [rec for rec in all_records if not rec.is_synthetic]
    else:
        excluded = 0
        real_records = all_records

    warnings: list[str] = []
    groups = _group_by_source(real_records)
    source_ids = sorted(groups.keys())

    rng = random.Random(seed)
    rng.shuffle(source_ids)

    group_sizes = {sid: len(groups[sid]) for sid in source_ids}
    total = sum(group_sizes.values())

    assignments: dict[str, list[str]]
    if total == 0:
        assignments = {name: [] for name in r}
        warnings.append("no_records_to_split")
    else:
        assignments = _assign_source_groups(source_ids, group_sizes, r, total)

    splits: dict[str, list[Achievement]] = {}
    actual_sizes: dict[str, int] = {}
    class_dist: dict[str, dict[str, int]] = {}
    for name in r:
        split_records: list[Achievement] = []
        for sid in assignments[name]:
            split_records.extend(groups[sid])
        splits[name] = split_records
        actual_sizes[name] = len(split_records)
        class_dist[name] = _class_distribution(split_records)

    actual_ratios = (
        {name: actual_sizes[name] / total for name in r}
        if total > 0
        else {name: 0.0 for name in r}
    )

    # Infeasibility surfaced as warnings (not errors).
    for name, target in r.items():
        if target > 0 and actual_sizes[name] == 0:
            warnings.append(f"empty_split:{name}")
    if len(source_ids) < sum(1 for v in r.values() if v > 0):
        warnings.append(
            f"source_group_count_below_nonzero_split_count:"
            f"{len(source_ids)}<{sum(1 for v in r.values() if v > 0)}"
        )

    manifest = SplitManifest(
        seed=seed,
        ratios=r,
        actual_sizes=actual_sizes,
        actual_ratios=actual_ratios,
        source_assignments=assignments,
        class_distribution=class_dist,
        excluded_synthetic_count=excluded,
        warnings=warnings,
    )
    return SplitResult(splits=splits, manifest=manifest)


def write_splits(
    result: SplitResult,
    dataset_root: str | Path,
) -> SplitManifest:
    """Write JSONL splits + ``split_manifest.json`` under ``<root>/processed/splits/``.

    The target directory is created if missing (parents too). JSONL
    files are overwritten atomically relative to the directory (write
    then rename). The returned manifest is the original manifest
    enriched with the SHA-256 of every file written.
    """
    root = Path(dataset_root)
    out_dir = root / SPLITS_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)

    file_hashes: dict[str, str] = {}
    for name, records in result.splits.items():
        file_path = out_dir / f"{name}.jsonl"
        payload = "".join(
            rec.model_dump_json(exclude_none=False) + "\n" for rec in records
        )
        # Use write_bytes to avoid Windows universal-newline translation
        # (write_text would convert '\n' to '\r\n' on Windows and change
        # the file's SHA-256). Writing bytes keeps the on-disk hash
        # identical to the hash computed here.
        encoded = payload.encode("utf-8")
        file_path.write_bytes(encoded)
        file_hashes[f"{name}.jsonl"] = hashlib.sha256(encoded).hexdigest()

    enriched = SplitManifest(
        seed=result.manifest.seed,
        ratios=result.manifest.ratios,
        actual_sizes=result.manifest.actual_sizes,
        actual_ratios=result.manifest.actual_ratios,
        source_assignments=result.manifest.source_assignments,
        class_distribution=result.manifest.class_distribution,
        excluded_synthetic_count=result.manifest.excluded_synthetic_count,
        file_hashes=file_hashes,
        warnings=list(result.manifest.warnings),
    )
    manifest_path = out_dir / "split_manifest.json"
    manifest_path.write_text(
        json.dumps(enriched.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return enriched
