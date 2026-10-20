"""Identifier generation and format validation.

Record IDs are prefix + full UUID4 hex (32 lowercase chars):
``ach_<32-hex>``, ``evd_<32-hex>``, ``ann_<32-hex>``, ``src_<32-hex>``.

Taxonomy label IDs are human-readable snake-case:
``lbl_hackathon``, ``lbl_domain_ai`` (2-60 chars after the ``lbl_`` prefix).

Pydantic models validate the string shape only. Cross-record existence
(e.g. that a referenced ``source_id`` actually appears in the
``SourceRegistry``) is a dataset-level concern enforced later, not here.
"""
from __future__ import annotations

import re
import uuid

ID_HEX_LENGTH = 32
ID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")

_RECORD_PREFIXES: dict[str, str] = {
    "ach": "Achievement",
    "evd": "Evidence",
    "ann": "Annotation",
    "src": "SourceRegistry",
}

# label_id: starts with lbl_, then 2-60 chars from [a-z0-9_], first of which
# must be [a-z0-9] (so e.g. lbl__foo is rejected).
LABEL_ID_RE = re.compile(r"^lbl_[a-z0-9][a-z0-9_]{1,59}$")


def make_id(prefix: str) -> str:
    """Generate a new record ID of the form ``<prefix>_<uuid4_hex>``."""
    if prefix not in _RECORD_PREFIXES:
        raise ValueError(
            f"Unknown ID prefix {prefix!r}. Known prefixes: "
            f"{sorted(_RECORD_PREFIXES)}"
        )
    return f"{prefix}_{uuid.uuid4().hex}"


def validate_prefixed_id(value: str, prefix: str) -> str:
    """Validate a record ID. Returns ``value`` unchanged on success."""
    if prefix not in _RECORD_PREFIXES:
        raise ValueError(f"Unknown ID prefix {prefix!r}")
    expected_prefix = f"{prefix}_"
    if not isinstance(value, str) or not value.startswith(expected_prefix):
        raise ValueError(
            f"ID must start with {expected_prefix!r}; got {value!r}"
        )
    hex_part = value[len(expected_prefix):]
    if not ID_HEX_RE.fullmatch(hex_part):
        raise ValueError(
            f"ID hex suffix must be exactly {ID_HEX_LENGTH} lowercase hex "
            f"chars; got {hex_part!r}"
        )
    return value


def validate_label_id(value: str) -> str:
    """Validate a taxonomy label ID. Returns ``value`` unchanged on success."""
    if not isinstance(value, str) or not LABEL_ID_RE.fullmatch(value):
        raise ValueError(
            "label_id must match pattern 'lbl_<snake_case>' with 2-60 chars "
            f"after the prefix; got {value!r}"
        )
    return value
