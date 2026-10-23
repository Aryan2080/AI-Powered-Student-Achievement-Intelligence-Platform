"""Tests for ManifestEntry and the manifest loader / validator."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from nlp_semantic.schema import (
    DocumentFileType,
    SourceRegistry,
    make_id,
)
from nlp_semantic.ingestion.manifest import (
    ManifestEntry,
    ManifestError,
    load_and_validate_manifest,
    load_manifest,
    validate_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SHIPPED_MANIFEST = REPO_ROOT / "hybrid_dataset" / "metadata" / "manifest.yaml"
SHIPPED_SOURCES = REPO_ROOT / "hybrid_dataset" / "metadata" / "sources.yaml"

# Registered via the Chunk 7.3-A.5 conservative source-registration PR.
SIH_2024_SOURCE_ID = "src_5a8a2998d6f44055a42dcfd8991e4d12"


def _manifest_entry_dict(**overrides) -> dict:
    base = {
        "source_id": make_id("src"),
        "raw_subdir": "hybrid_dataset/raw/public_datasets/example",
        "expected_file_types": ["pdf"],
        "expected_count": 10,
        "sampling_notes": "synthetic",
        "is_synthetic": True,
    }
    base.update(overrides)
    return base


def _source_entry(**overrides) -> SourceRegistry:
    data = {
        "source_id": make_id("src"),
        "source_name": "Synthetic",
        "source_url": "https://example.org/x",
        "license": "CC-BY-4.0",
        "collection_date": date.today(),
        "intended_use": "primary_type_training",
        "review_status": "verified",
        "is_synthetic": True,
    }
    data.update(overrides)
    return SourceRegistry(**data)


def _write(tmp_path: Path, text: str, name: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _dump(entries: list[dict]) -> str:
    return yaml.safe_dump(entries, sort_keys=False)


# ---- shipped file ------------------------------------------------------------


def test_shipped_manifest_loads_empty() -> None:
    assert load_manifest(SHIPPED_MANIFEST) == []


def test_shipped_manifest_and_sources_cross_validate() -> None:
    """Shipped manifest remains empty; shipped sources now carries at
    least the Chunk 7.3-A.5 SIH entry. Cross-validation must succeed:
    an empty manifest trivially has no unknown-source references
    against a non-empty source registry.
    """
    entries, report = load_and_validate_manifest(SHIPPED_MANIFEST, SHIPPED_SOURCES)
    assert entries == []
    source_registry_ids = {s.source_id for s in report.entries}
    assert SIH_2024_SOURCE_ID in source_registry_ids


# ---- loader shape failures ---------------------------------------------------


def test_empty_yaml_returns_empty(tmp_path: Path) -> None:
    f = _write(tmp_path, "", "manifest.yaml")
    assert load_manifest(f) == []


def test_top_level_not_list_rejected(tmp_path: Path) -> None:
    f = _write(tmp_path, "source_id: src_abc\n", "manifest.yaml")
    with pytest.raises(ManifestError, match="top-level YAML must be a list"):
        load_manifest(f)


def test_entry_not_mapping_rejected(tmp_path: Path) -> None:
    f = _write(tmp_path, "- just_a_string\n", "manifest.yaml")
    with pytest.raises(ManifestError, match="must be a mapping"):
        load_manifest(f)


# ---- per-entry Pydantic failures ---------------------------------------------


def test_missing_required_field_rejected(tmp_path: Path) -> None:
    e = _manifest_entry_dict()
    e.pop("source_id")
    f = _write(tmp_path, _dump([e]), "manifest.yaml")
    with pytest.raises(ValidationError):
        load_manifest(f)


def test_extra_field_rejected(tmp_path: Path) -> None:
    e = _manifest_entry_dict(mystery="x")
    f = _write(tmp_path, _dump([e]), "manifest.yaml")
    with pytest.raises(ValidationError):
        load_manifest(f)


@pytest.mark.parametrize(
    "bad_subdir",
    [
        "/absolute/path",
        "C:/windows/path",
        "hybrid_dataset/raw/foo/../escape",
        "hybrid_dataset\\raw\\backslash",
        "hybrid_dataset/raw//double_slash",
        "something_else/raw/foo",
        "hybrid_dataset/processed/foo",
    ],
)
def test_bad_raw_subdir_rejected(tmp_path: Path, bad_subdir: str) -> None:
    e = _manifest_entry_dict(raw_subdir=bad_subdir)
    f = _write(tmp_path, _dump([e]), "manifest.yaml")
    with pytest.raises(ValidationError):
        load_manifest(f)


def test_bad_expected_file_type_rejected(tmp_path: Path) -> None:
    e = _manifest_entry_dict(expected_file_types=["not_an_enum_value"])
    f = _write(tmp_path, _dump([e]), "manifest.yaml")
    with pytest.raises(ValidationError):
        load_manifest(f)


def test_negative_expected_count_rejected(tmp_path: Path) -> None:
    e = _manifest_entry_dict(expected_count=-1)
    f = _write(tmp_path, _dump([e]), "manifest.yaml")
    with pytest.raises(ValidationError):
        load_manifest(f)


def test_bad_source_id_rejected(tmp_path: Path) -> None:
    e = _manifest_entry_dict(source_id="ach_" + "a" * 32)
    f = _write(tmp_path, _dump([e]), "manifest.yaml")
    with pytest.raises(ValidationError):
        load_manifest(f)


# ---- cross-validation --------------------------------------------------------


def test_valid_manifest_with_matching_source_ok() -> None:
    src = _source_entry()
    entry = ManifestEntry(**_manifest_entry_dict(source_id=src.source_id))
    validate_manifest([entry], [src])


def test_manifest_source_id_not_in_registry_rejected() -> None:
    src = _source_entry()
    other_sid = make_id("src")
    entry = ManifestEntry(**_manifest_entry_dict(source_id=other_sid))
    with pytest.raises(ManifestError, match="unknown source_id"):
        validate_manifest([entry], [src])


def test_duplicate_source_id_in_manifest_rejected() -> None:
    src = _source_entry()
    e1 = ManifestEntry(**_manifest_entry_dict(
        source_id=src.source_id,
        raw_subdir="hybrid_dataset/raw/a",
    ))
    e2 = ManifestEntry(**_manifest_entry_dict(
        source_id=src.source_id,
        raw_subdir="hybrid_dataset/raw/b",
    ))
    with pytest.raises(ManifestError, match="duplicate source_id"):
        validate_manifest([e1, e2], [src])


def test_duplicate_raw_subdir_in_manifest_rejected() -> None:
    src1 = _source_entry()
    src2 = _source_entry()
    shared = "hybrid_dataset/raw/shared"
    e1 = ManifestEntry(**_manifest_entry_dict(source_id=src1.source_id, raw_subdir=shared))
    e2 = ManifestEntry(**_manifest_entry_dict(source_id=src2.source_id, raw_subdir=shared))
    with pytest.raises(ManifestError, match="duplicate raw_subdir"):
        validate_manifest([e1, e2], [src1, src2])
