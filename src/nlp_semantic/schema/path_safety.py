"""Shared path-safety validator for hybrid_dataset-relative paths.

Extracted from :mod:`evidence` so that both the Evidence model and the
Chunk 4 ingestion manifest can share one implementation. The validator's
behavior and every error-message string are preserved byte-identical to
the original private helper, so Evidence tests continue to pass unchanged.
"""
from __future__ import annotations

RAW_HYBRID_PREFIX = "hybrid_dataset/raw/"
APPROVED_EVIDENCE_PREFIX = "hybrid_dataset/raw/evidence_documents/"
PROCESSED_TEXT_PREFIX = "hybrid_dataset/processed/"


def reject_unsafe_relative_path(v: str, *, must_start_with: str) -> str:
    """Validate a hybrid_dataset-relative path.

    Rules (order and messages preserved from the former private helper):

    - Must be a non-empty string.
    - Must not contain backslashes.
    - Must not be an absolute POSIX path (``/...``).
    - Must not be an absolute Windows path (``X:...``).
    - Must not contain any ``..`` segment.
    - Must not contain any empty segment (no doubled slashes).
    - Must start with ``must_start_with``.

    Returns ``v`` unchanged on success. Raises :class:`ValueError` with
    the original error wording on failure.
    """
    if not v:
        raise ValueError("path must be a non-empty string")
    if "\\" in v:
        raise ValueError("path must use forward slashes, not backslashes")
    if v.startswith("/"):
        raise ValueError("path must not be an absolute POSIX path")
    if len(v) >= 2 and v[1] == ":":
        raise ValueError("path must not be an absolute Windows path")
    parts = v.split("/")
    if any(p == ".." for p in parts):
        raise ValueError("path must not contain '..' segments")
    if any(p == "" for p in parts):
        raise ValueError("path must not contain empty segments")
    if not v.startswith(must_start_with):
        raise ValueError(f"path must start with {must_start_with!r}")
    return v
