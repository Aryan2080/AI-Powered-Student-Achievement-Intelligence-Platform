"""Shared helpers for the dataset tests."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from nlp_semantic.schema import make_id


REPO_ROOT = Path(__file__).resolve().parents[2]


def record_dict(**overrides: Any) -> dict:
    """Minimal valid Achievement payload, ready for YAML serialization."""
    base: dict[str, Any] = {
        "achievement_id": make_id("ach"),
        "source_id": make_id("src"),
        "source_record_id": "src-ext-001",
        "achievement_text": "A synthetic achievement for tests.",
        "is_synthetic": True,
    }
    base.update(overrides)
    return base


def annotation_dict(**overrides: Any) -> dict:
    """Minimal valid Annotation payload (primary_type task by default)."""
    base: dict[str, Any] = {
        "annotation_id": make_id("ann"),
        "achievement_id": make_id("ach"),
        "task": "primary_type",
        "label_ids": ["lbl_hackathon"],
        "annotator": "labeler_001",
        "review_status": "draft",
        "created_at": datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc).isoformat(),
        "is_synthetic": True,
    }
    base.update(overrides)
    return base


def source_dict(**overrides: Any) -> dict:
    base: dict[str, Any] = {
        "source_id": make_id("src"),
        "source_name": "Synthetic Source",
        "source_url": "https://example.org/x",
        "license": "CC-BY-4.0",
        "collection_date": date.today().isoformat(),
        "intended_use": "primary_type_training",
        "review_status": "verified",
        "is_synthetic": True,
    }
    base.update(overrides)
    return base


def write_yaml(path: Path, entries: list[dict] | None, *, raw: str | None = None) -> Path:
    """Write a YAML list (or raw text) to ``path``, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(entries, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture
def dataset_root(tmp_path: Path) -> Path:
    """A clean dataset root with the expected subdirectories pre-created."""
    root = tmp_path / "ds"
    (root / "dataset" / "records").mkdir(parents=True)
    (root / "dataset" / "annotations").mkdir(parents=True)
    (root / "metadata").mkdir(parents=True)
    (root / "labels").mkdir(parents=True)
    return root
