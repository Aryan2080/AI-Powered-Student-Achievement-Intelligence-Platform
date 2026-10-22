"""Manifest schema and cross-reference validation.

A manifest describes **expectations** about raw dataset content on disk:
one entry per registered source, naming its subdirectory under
``hybrid_dataset/raw/``, the file types that are expected there, and an
advisory expected count. The manifest does not record what is actually
present — that is the inventory's job (see :mod:`inventory`).
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from nlp_semantic.schema import (
    DocumentFileType,
    RAW_HYBRID_PREFIX,
    SourceRegistry,
    reject_unsafe_relative_path,
    validate_prefixed_id,
)

from .registry import SourceLoadReport, load_and_validate_sources


class ManifestError(ValueError):
    """File-level issues: top-level YAML not a list, entry not a mapping,
    duplicate ``source_id`` or ``raw_subdir`` across entries, or a
    manifest ``source_id`` not present in the loaded source registry.
    Per-entry format problems surface as
    :class:`pydantic.ValidationError`.
    """


class ManifestEntry(BaseModel):
    """One manifest row: where a source's raw files are expected to live.

    Fields:
        source_id: references a :class:`SourceRegistry` row by its
            ``src_<32hex>`` ID. Existence is checked by
            :func:`validate_manifest`, not by Pydantic.
        raw_subdir: path under ``hybrid_dataset/raw/`` (forward slashes,
            no absolute paths, no ``..``, no backslashes, no empty
            segments). This describes where files are expected on disk;
            the inventory reports what is actually there.
        expected_file_types: advisory list of ``DocumentFileType`` values
            the manifest expects to find in this subdir.
        expected_count: advisory, non-negative. ``None`` means unknown.
        sampling_notes: free-text notes about sampling or ingestion
            caveats; ≤ 2000 characters.
        is_synthetic: ``True`` for test or placeholder entries.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    source_id: str
    raw_subdir: str
    expected_file_types: list[DocumentFileType] = Field(default_factory=list)
    expected_count: int | None = None
    sampling_notes: str | None = Field(default=None, max_length=2000)
    is_synthetic: bool = False

    @field_validator("source_id")
    @classmethod
    def _validate_source_id(cls, v: str) -> str:
        return validate_prefixed_id(v, "src")

    @field_validator("raw_subdir")
    @classmethod
    def _validate_raw_subdir(cls, v: str) -> str:
        return reject_unsafe_relative_path(v, must_start_with=RAW_HYBRID_PREFIX)

    @field_validator("expected_count")
    @classmethod
    def _validate_expected_count(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v < 0:
            raise ValueError("expected_count must be >= 0 when set")
        return v


def load_manifest(path: str | Path) -> list[ManifestEntry]:
    """Load a manifest YAML file into a list of ManifestEntry records.

    Each entry is strictly validated by Pydantic (``extra="forbid"``);
    an empty YAML (or ``null``) is treated as an empty list.

    Raises:
        FileNotFoundError: path does not exist.
        ManifestError: top-level YAML is not a list, or an entry is not
            a mapping.
        pydantic.ValidationError: an entry fails ManifestEntry
            validation.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ManifestError(
            f"{p}: top-level YAML must be a list; got {type(data).__name__}"
        )
    entries: list[ManifestEntry] = []
    for i, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise ManifestError(
                f"{p}: entry at index {i} must be a mapping; got "
                f"{type(raw).__name__}"
            )
        entries.append(ManifestEntry(**raw))
    return entries


def validate_manifest(
    entries: Iterable[ManifestEntry],
    sources: Iterable[SourceRegistry],
) -> None:
    """Enforce file-local and cross-reference invariants.

    Fatal:
        - Duplicate ``source_id`` across manifest entries.
        - Duplicate ``raw_subdir`` across manifest entries.
        - Any manifest ``source_id`` not present among ``sources``.

    This function does NOT check that ``raw_subdir`` exists on the
    filesystem — the inventory reports actual presence separately.

    Raises:
        ManifestError: on any fatal invariant.
    """
    entries_list = list(entries)
    known_source_ids = {s.source_id for s in sources}

    seen_source: set[str] = set()
    seen_subdir: set[str] = set()
    for e in entries_list:
        if e.source_id in seen_source:
            raise ManifestError(
                f"duplicate source_id {e.source_id!r} in manifest"
            )
        seen_source.add(e.source_id)

        if e.raw_subdir in seen_subdir:
            raise ManifestError(
                f"duplicate raw_subdir {e.raw_subdir!r} in manifest"
            )
        seen_subdir.add(e.raw_subdir)

        if e.source_id not in known_source_ids:
            raise ManifestError(
                f"manifest references unknown source_id {e.source_id!r} "
                "(not present in sources.yaml)"
            )


def load_and_validate_manifest(
    manifest_path: str | Path,
    sources_path: str | Path,
) -> tuple[list[ManifestEntry], SourceLoadReport]:
    """Convenience: load the manifest and sources, cross-validate, return both."""
    source_report = load_and_validate_sources(sources_path)
    entries = load_manifest(manifest_path)
    validate_manifest(entries, source_report.entries)
    return entries, source_report
