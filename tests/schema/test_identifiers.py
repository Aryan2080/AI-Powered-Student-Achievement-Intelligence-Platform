"""Tests for identifier generation and format validation."""
from __future__ import annotations

import pytest

from nlp_semantic.schema.identifiers import (
    ID_HEX_RE,
    make_id,
    validate_label_id,
    validate_prefixed_id,
)


@pytest.mark.parametrize("prefix", ["ach", "evd", "ann", "src"])
def test_make_id_shape(prefix: str) -> None:
    value = make_id(prefix)
    assert value.startswith(f"{prefix}_")
    assert ID_HEX_RE.fullmatch(value[len(prefix) + 1 :])


def test_make_id_rejects_unknown_prefix() -> None:
    with pytest.raises(ValueError):
        make_id("xyz")


@pytest.mark.parametrize("prefix", ["ach", "evd", "ann", "src"])
def test_round_trip_valid_prefixes(prefix: str) -> None:
    value = make_id(prefix)
    assert validate_prefixed_id(value, prefix) == value


def test_validate_rejects_wrong_prefix() -> None:
    value = make_id("ach")
    with pytest.raises(ValueError):
        validate_prefixed_id(value, "evd")


@pytest.mark.parametrize(
    "bad",
    [
        "ach_short",
        "ach_" + "f" * 31,
        "ach_" + "F" * 32,       # uppercase hex rejected
        "ach_" + "g" * 32,       # non-hex char
        "ach-" + "a" * 32,       # wrong separator
        "ACH_" + "a" * 32,       # uppercase prefix rejected
        "ach_" + "a" * 33,       # too long
        "achach_" + "a" * 32,    # malformed prefix
    ],
)
def test_validate_rejects_malformed(bad: str) -> None:
    with pytest.raises(ValueError):
        validate_prefixed_id(bad, "ach")


@pytest.mark.parametrize(
    "good",
    ["lbl_hackathon", "lbl_domain_ai", "lbl_a1", "lbl_research_pub", "lbl_0a"],
)
def test_label_id_valid(good: str) -> None:
    assert validate_label_id(good) == good


@pytest.mark.parametrize(
    "bad",
    [
        "lbl_",                # too short after prefix
        "lbl_A",                # uppercase
        "hackathon",            # missing prefix
        "lbl_hack-athon",       # hyphen not allowed inside
        "lbl_ hackathon",       # space
        "lbl__hack",            # leading underscore after prefix (first char must be [a-z0-9])
        "lbl_" + "a" * 61,     # over 60 chars
    ],
)
def test_label_id_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        validate_label_id(bad)
