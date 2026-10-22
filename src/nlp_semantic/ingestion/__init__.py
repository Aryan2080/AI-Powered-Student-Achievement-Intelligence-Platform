"""Ingestion package: source registry loader, manifest, and read-only inventory.

Public API is lazily re-exported from the three submodules so callers can
write ``from nlp_semantic.ingestion import load_sources`` without eagerly
importing every submodule. The laziness also avoids the ``runpy``
``RuntimeWarning`` that would otherwise fire when a user invokes the CLI
via ``python -m nlp_semantic.ingestion.inventory`` (the parent package's
__init__ would import ``inventory`` first, and runpy would then observe
the module already present in ``sys.modules``).

Chunk 4 scope: metadata-only; no file contents are ever read, no network
calls, no new runtime dependencies.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = [
    # Source registry
    "SourceLoadReport",
    "SourceRegistryError",
    "load_sources",
    "validate_sources",
    "load_and_validate_sources",
    "source_ids",
    # Manifest
    "ManifestEntry",
    "ManifestError",
    "load_manifest",
    "validate_manifest",
    "load_and_validate_manifest",
    # Inventory
    "InventoryEntry",
    "InventoryReport",
    "InventoryWarning",
    "build_inventory",
]

# name -> submodule it lives in
_LAZY: dict[str, str] = {
    "SourceLoadReport": "registry",
    "SourceRegistryError": "registry",
    "load_sources": "registry",
    "validate_sources": "registry",
    "load_and_validate_sources": "registry",
    "source_ids": "registry",
    "ManifestEntry": "manifest",
    "ManifestError": "manifest",
    "load_manifest": "manifest",
    "validate_manifest": "manifest",
    "load_and_validate_manifest": "manifest",
    "InventoryEntry": "inventory",
    "InventoryReport": "inventory",
    "InventoryWarning": "inventory",
    "build_inventory": "inventory",
}


def __getattr__(name: str) -> Any:
    submodule = _LAZY.get(name)
    if submodule is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )
    mod = import_module(f".{submodule}", __name__)
    value = getattr(mod, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()))


if TYPE_CHECKING:  # pragma: no cover - typing-only re-exports
    from .inventory import (
        InventoryEntry,
        InventoryReport,
        InventoryWarning,
        build_inventory,
    )
    from .manifest import (
        ManifestEntry,
        ManifestError,
        load_and_validate_manifest,
        load_manifest,
        validate_manifest,
    )
    from .registry import (
        SourceLoadReport,
        SourceRegistryError,
        load_and_validate_sources,
        load_sources,
        source_ids,
        validate_sources,
    )
