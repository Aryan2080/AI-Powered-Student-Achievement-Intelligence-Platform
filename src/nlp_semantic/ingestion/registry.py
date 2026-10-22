"""Load and validate ``hybrid_dataset/metadata/sources.yaml``.

Each YAML entry is routed through :meth:`SourceRegistry.from_untrusted`
so a credential-bearing ``source_url`` raises :class:`CredentialInUrlError`
before Pydantic sees the raw value. The loader does not wrap or re-raise
exceptions with additional context, so no raw URL can land in a
loader-generated error message.

Advisory warnings — ``license == "UNKNOWN"`` and non-``VERIFIED``
``review_status`` — accumulate in :class:`SourceLoadReport` and never
raise. Registration is not approval; downstream training must gate on
``review_status == VERIFIED`` plus a human-approved license decision.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from nlp_semantic.schema import (
    ReviewStatus,
    SourceRegistry,
    UNKNOWN_LICENSE,
)


class SourceRegistryError(ValueError):
    """File-level issues in ``sources.yaml``.

    Covers: top-level YAML is not a list, an entry is not a mapping,
    duplicate ``source_id`` within the file. Per-entry format problems
    surface as :class:`pydantic.ValidationError`; credential-bearing URLs
    surface as :class:`nlp_semantic.schema.CredentialInUrlError`.
    """


@dataclass(frozen=True)
class SourceLoadReport:
    """Result of validating a loaded source registry.

    ``entries`` is the loaded set. ``unknown_license_ids`` and
    ``unverified_source_ids`` are advisory — they do not block the load.
    Downstream code decides what to do with them.
    """

    entries: list[SourceRegistry]
    unknown_license_ids: list[str] = field(default_factory=list)
    unverified_source_ids: list[str] = field(default_factory=list)


def load_sources(path: str | Path) -> list[SourceRegistry]:
    """Load a YAML list into a list of :class:`SourceRegistry` records.

    Each entry dict is passed to :meth:`SourceRegistry.from_untrusted`
    (never :class:`SourceRegistry` directly). An empty YAML (or ``null``)
    is treated as an empty list.

    Raises:
        FileNotFoundError: path does not exist.
        SourceRegistryError: top-level YAML is not a list, or a list
            element is not a mapping.
        pydantic.ValidationError: an entry fails Pydantic validation.
        nlp_semantic.schema.CredentialInUrlError: an entry's
            ``source_url`` contains embedded credentials.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return []
    if not isinstance(data, list):
        raise SourceRegistryError(
            f"{p}: top-level YAML must be a list; got "
            f"{type(data).__name__}"
        )
    entries: list[SourceRegistry] = []
    for i, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise SourceRegistryError(
                f"{p}: entry at index {i} must be a mapping; got "
                f"{type(raw).__name__}"
            )
        entries.append(SourceRegistry.from_untrusted(raw))
    return entries


def validate_sources(entries: Iterable[SourceRegistry]) -> SourceLoadReport:
    """Enforce file-local invariants and collect advisory warnings.

    Fatal:
        - duplicate ``source_id`` within the set.

    Advisory (surface in the report, do not raise):
        - ``license == "UNKNOWN"`` on any entry.
        - ``review_status != VERIFIED`` on any entry.

    Raises:
        SourceRegistryError: on any fatal invariant.
    """
    entries_list = list(entries)

    seen: set[str] = set()
    unknown_license_ids: list[str] = []
    unverified_source_ids: list[str] = []

    for e in entries_list:
        if e.source_id in seen:
            raise SourceRegistryError(
                f"duplicate source_id {e.source_id!r} in sources"
            )
        seen.add(e.source_id)
        if e.license == UNKNOWN_LICENSE:
            unknown_license_ids.append(e.source_id)
        if e.review_status != ReviewStatus.VERIFIED:
            unverified_source_ids.append(e.source_id)

    return SourceLoadReport(
        entries=entries_list,
        unknown_license_ids=unknown_license_ids,
        unverified_source_ids=unverified_source_ids,
    )


def load_and_validate_sources(path: str | Path) -> SourceLoadReport:
    """Convenience: ``validate_sources(load_sources(path))``."""
    return validate_sources(load_sources(path))


def source_ids(entries: Iterable[SourceRegistry]) -> set[str]:
    """Return the set of ``source_id`` values present in ``entries``.

    Helper for a future dataset-level validator that needs to confirm
    that every ``Achievement.source_id`` references a known
    ``SourceRegistry`` row. Chunk 4 does not perform that cross-record
    check itself.
    """
    return {e.source_id for e in entries}
