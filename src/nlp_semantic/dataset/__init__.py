"""Dataset preparation package (Chunk 5).

Public API is lazily re-exported from the submodules — same pattern as
:mod:`nlp_semantic.ingestion` — so running
``python -m nlp_semantic.dataset.cli`` does not trigger a runpy
double-import warning.

Chunk 5 scope: metadata-only loading, cross-record validation,
deterministic duplicate detection, class-distribution reports,
reproducible splits, and a thin CLI. No OCR, no embeddings, no
transformer code, no new runtime dependencies.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = [
    # Loader
    "DatasetError",
    "DatasetLoadReport",
    "load_annotations",
    "load_dataset",
    "load_records",
    # Validator
    "DatasetValidationReport",
    "eligible_ground_truth",
    "training_ready_subset",
    "validate_dataset",
    # Duplicates
    "DuplicateGroup",
    "DuplicateReport",
    "find_duplicates",
    # Stats
    "DatasetStatsReport",
    "compute_stats",
    # Splits
    "SplitFeasibilityError",
    "SplitManifest",
    "SplitResult",
    "generate_splits",
    "write_splits",
    # Agreement (Chunk 6)
    "AgreementReport",
    "Disagreement",
    "compute_agreement",
    "find_disagreements",
]

_LAZY: dict[str, str] = {
    "DatasetError": "loader",
    "DatasetLoadReport": "loader",
    "load_annotations": "loader",
    "load_dataset": "loader",
    "load_records": "loader",
    "DatasetValidationReport": "validator",
    "eligible_ground_truth": "validator",
    "training_ready_subset": "validator",
    "validate_dataset": "validator",
    "DuplicateGroup": "duplicates",
    "DuplicateReport": "duplicates",
    "find_duplicates": "duplicates",
    "DatasetStatsReport": "stats",
    "compute_stats": "stats",
    "SplitFeasibilityError": "splits",
    "SplitManifest": "splits",
    "SplitResult": "splits",
    "generate_splits": "splits",
    "write_splits": "splits",
    "AgreementReport": "agreement",
    "Disagreement": "agreement",
    "compute_agreement": "agreement",
    "find_disagreements": "agreement",
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
    from .agreement import (
        AgreementReport,
        Disagreement,
        compute_agreement,
        find_disagreements,
    )
    from .duplicates import DuplicateGroup, DuplicateReport, find_duplicates
    from .loader import (
        DatasetError,
        DatasetLoadReport,
        load_annotations,
        load_dataset,
        load_records,
    )
    from .splits import (
        SplitFeasibilityError,
        SplitManifest,
        SplitResult,
        generate_splits,
        write_splits,
    )
    from .stats import DatasetStatsReport, compute_stats
    from .validator import (
        DatasetValidationReport,
        eligible_ground_truth,
        training_ready_subset,
        validate_dataset,
    )
