"""Load curated Achievement + Annotation records from YAML batch files.

Record files live under ``<dataset_root>/dataset/records/batch_<NN>.yaml``
and annotation-history files (optional) live under
``<dataset_root>/dataset/annotations/batch_<NN>.yaml``. Every entry is
validated by its Pydantic model (``extra="forbid"``); the loader itself
only enforces file-level invariants.

File-level problems raise :class:`DatasetError`. Per-entry problems
surface as :class:`pydantic.ValidationError` — same split as the Chunk
3 taxonomy loader and the Chunk 4 ingestion loaders, so the behaviour
is consistent across the codebase.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from nlp_semantic.schema import Achievement, Annotation


RECORDS_DIR = "records"
ANNOTATIONS_DIR = "annotations"
_BATCH_PATTERN = "batch_*.yaml"


class DatasetError(ValueError):
    """File-level issues in dataset YAML files.

    Covers: top-level YAML is not a list, an entry is not a mapping,
    duplicate ``achievement_id`` across record batches, duplicate
    ``annotation_id`` across annotation batches, dataset-root shape
    problems. Per-entry format problems surface as
    :class:`pydantic.ValidationError`.
    """


@dataclass(frozen=True)
class DatasetLoadReport:
    """Summary of a load pass.

    ``per_file_counts`` is keyed by the file's path relative to the
    dataset root (forward slashes) so the output is stable across
    operating systems.
    """

    records: list[Achievement]
    annotations: list[Annotation]
    record_files: list[str] = field(default_factory=list)
    annotation_files: list[str] = field(default_factory=list)
    per_file_counts: dict[str, int] = field(default_factory=dict)


# ---- single-file loaders -----------------------------------------------------


def _load_yaml_list(path: Path, *, label: str) -> list[dict]:
    """Shared shape check: file must exist, top level is a list of dicts."""
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return []
    if not isinstance(data, list):
        raise DatasetError(
            f"{path}: top-level YAML must be a list of {label} entries; "
            f"got {type(data).__name__}"
        )
    for i, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise DatasetError(
                f"{path}: entry at index {i} must be a mapping; got "
                f"{type(raw).__name__}"
            )
    return data


def _load_records_from_file(path: Path) -> list[Achievement]:
    raw_entries = _load_yaml_list(path, label="Achievement")
    return [Achievement(**raw) for raw in raw_entries]


def _load_annotations_from_file(path: Path) -> list[Annotation]:
    raw_entries = _load_yaml_list(path, label="Annotation")
    return [Annotation(**raw) for raw in raw_entries]


# ---- directory walkers -------------------------------------------------------


def _batch_files(dir_path: Path) -> list[Path]:
    """Return ``batch_*.yaml`` files inside ``dir_path`` in sorted name order.

    Returns an empty list if the directory does not exist (``FileNotFoundError``
    only comes from the top-level dataset-root check, not from an absent
    optional ``annotations/`` folder).
    """
    if not dir_path.is_dir():
        return []
    return sorted(dir_path.glob(_BATCH_PATTERN))


def _posix_rel(abs_path: Path, root: Path) -> str:
    """Format ``abs_path`` as a POSIX string relative to ``root`` when possible."""
    try:
        rel = abs_path.relative_to(root)
    except ValueError:
        return abs_path.name
    return str(rel).replace("\\", "/")


# ---- public API --------------------------------------------------------------


def load_records(dataset_root: str | Path) -> list[Achievement]:
    """Load every ``records/batch_*.yaml`` under ``<dataset_root>/dataset/``.

    Returns records in filename order, concatenated across batches.
    Raises :class:`DatasetError` on duplicate ``achievement_id``.
    """
    root = Path(dataset_root)
    records_dir = root / "dataset" / RECORDS_DIR
    records: list[Achievement] = []
    seen_ids: set[str] = set()
    for file_path in _batch_files(records_dir):
        for rec in _load_records_from_file(file_path):
            if rec.achievement_id in seen_ids:
                raise DatasetError(
                    f"duplicate achievement_id {rec.achievement_id!r} "
                    f"detected while loading {_posix_rel(file_path, root)}"
                )
            seen_ids.add(rec.achievement_id)
            records.append(rec)
    return records


def load_annotations(dataset_root: str | Path) -> list[Annotation]:
    """Load every ``annotations/batch_*.yaml`` under ``<dataset_root>/dataset/``.

    Returns annotations in filename order. Raises :class:`DatasetError`
    on duplicate ``annotation_id``. Absent ``annotations/`` directory
    is treated as an empty history (optional subfolder).
    """
    root = Path(dataset_root)
    anns_dir = root / "dataset" / ANNOTATIONS_DIR
    anns: list[Annotation] = []
    seen_ids: set[str] = set()
    for file_path in _batch_files(anns_dir):
        for ann in _load_annotations_from_file(file_path):
            if ann.annotation_id in seen_ids:
                raise DatasetError(
                    f"duplicate annotation_id {ann.annotation_id!r} "
                    f"detected while loading {_posix_rel(file_path, root)}"
                )
            seen_ids.add(ann.annotation_id)
            anns.append(ann)
    return anns


def load_dataset(dataset_root: str | Path) -> DatasetLoadReport:
    """Load records and annotations, returning a structured report.

    Fails fast on duplicate IDs or malformed files. Does **not** check
    foreign-key references, label-taxonomy membership, or ground-truth
    eligibility — those live in :mod:`nlp_semantic.dataset.validator`
    so the loader stays single-purpose.
    """
    root = Path(dataset_root)
    if not root.exists():
        raise FileNotFoundError(f"dataset_root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"dataset_root is not a directory: {root}")

    records_dir = root / "dataset" / RECORDS_DIR
    anns_dir = root / "dataset" / ANNOTATIONS_DIR

    record_files = _batch_files(records_dir)
    annotation_files = _batch_files(anns_dir)

    per_file_counts: dict[str, int] = {}
    records: list[Achievement] = []
    seen_rec_ids: set[str] = set()
    for file_path in record_files:
        file_records = _load_records_from_file(file_path)
        for rec in file_records:
            if rec.achievement_id in seen_rec_ids:
                raise DatasetError(
                    f"duplicate achievement_id {rec.achievement_id!r} "
                    f"detected while loading {_posix_rel(file_path, root)}"
                )
            seen_rec_ids.add(rec.achievement_id)
            records.append(rec)
        per_file_counts[_posix_rel(file_path, root)] = len(file_records)

    annotations: list[Annotation] = []
    seen_ann_ids: set[str] = set()
    for file_path in annotation_files:
        file_anns = _load_annotations_from_file(file_path)
        for ann in file_anns:
            if ann.annotation_id in seen_ann_ids:
                raise DatasetError(
                    f"duplicate annotation_id {ann.annotation_id!r} "
                    f"detected while loading {_posix_rel(file_path, root)}"
                )
            seen_ann_ids.add(ann.annotation_id)
            annotations.append(ann)
        per_file_counts[_posix_rel(file_path, root)] = len(file_anns)

    return DatasetLoadReport(
        records=records,
        annotations=annotations,
        record_files=[_posix_rel(p, root) for p in record_files],
        annotation_files=[_posix_rel(p, root) for p in annotation_files],
        per_file_counts=per_file_counts,
    )


def record_ids(records: Iterable[Achievement]) -> set[str]:
    """Return the set of ``achievement_id`` values in ``records``."""
    return {r.achievement_id for r in records}
