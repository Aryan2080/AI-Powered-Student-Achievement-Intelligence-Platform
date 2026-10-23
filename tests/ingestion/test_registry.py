"""Tests for the source registry loader."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from nlp_semantic.schema import (
    CredentialInUrlError,
    ReviewStatus,
    SourceRegistry,
    UNKNOWN_LICENSE,
    make_id,
)
from nlp_semantic.ingestion.registry import (
    SourceLoadReport,
    SourceRegistryError,
    load_and_validate_sources,
    load_sources,
    source_ids,
    validate_sources,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SHIPPED_SOURCES = REPO_ROOT / "hybrid_dataset" / "metadata" / "sources.yaml"

# Registered via the Chunk 7.3-A.5 conservative source-registration PR.
# License is intentionally UNKNOWN and review_status is unreviewed until
# the Chunk 7.2 two-independent-reviewer sign-off process completes.
SIH_2024_SOURCE_ID = "src_5a8a2998d6f44055a42dcfd8991e4d12"


# Sentinel tokens for credential-leak test. These must never appear in any
# exception's str/repr/args. Chosen so they wouldn't appear in generic
# error text or any URL other than the one we construct.
_SAFE_USER = "k2z9m1q_regtest_user"
_SAFE_PASS = "x7v4b8n_regtest_token"


def _entry(**overrides) -> dict:
    base = {
        "source_id": make_id("src"),
        "source_name": "Synthetic Public Dataset",
        "source_url": "https://example.org/dataset",
        "license": "CC-BY-4.0",
        "collection_date": date.today().isoformat(),
        "intended_use": "primary_type_training",
        "review_status": "verified",
        "is_synthetic": True,
    }
    base.update(overrides)
    return base


def _write(tmp_path: Path, text: str, name: str = "sources.yaml") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _dump(entries: list[dict]) -> str:
    """Serialize a list of entry dicts to YAML without pulling in yaml here."""
    import yaml
    return yaml.safe_dump(entries, sort_keys=False)


# ---- shipped file ------------------------------------------------------------


def test_shipped_sources_file_loads_registered_entries() -> None:
    """The shipped sources.yaml carries at least the Chunk 7.3-A.5 SIH entry.

    The entry is intentionally registered with ``license = UNKNOWN`` and
    ``review_status = unreviewed``; promotion to ``verified`` is a human
    sign-off step tracked separately.
    """
    entries = load_sources(SHIPPED_SOURCES)
    ids = source_ids(entries)
    assert SIH_2024_SOURCE_ID in ids
    sih = next(e for e in entries if e.source_id == SIH_2024_SOURCE_ID)
    assert sih.license == UNKNOWN_LICENSE
    assert sih.review_status == ReviewStatus.UNREVIEWED
    assert sih.is_synthetic is False


def test_shipped_sources_file_validates_with_expected_conservative_advisories() -> None:
    """Chunk 7.3-A.5's conservative registration intentionally triggers
    the ``unknown_license_ids`` and ``unverified_source_ids`` advisory
    lists. These are not failures; they are the expected signal that
    the Chunk 7.2 two-independent-reviewer sign-off is still pending.
    """
    report = load_and_validate_sources(SHIPPED_SOURCES)
    assert isinstance(report, SourceLoadReport)
    assert SIH_2024_SOURCE_ID in source_ids(report.entries)
    assert SIH_2024_SOURCE_ID in report.unknown_license_ids
    assert SIH_2024_SOURCE_ID in report.unverified_source_ids


# ---- loader shape failures ---------------------------------------------------


def test_empty_yaml_returns_empty_list(tmp_path: Path) -> None:
    f = _write(tmp_path, "")
    assert load_sources(f) == []


def test_top_level_scalar_rejected(tmp_path: Path) -> None:
    f = _write(tmp_path, "just a scalar\n")
    with pytest.raises(SourceRegistryError, match="top-level YAML must be a list"):
        load_sources(f)


def test_top_level_mapping_rejected(tmp_path: Path) -> None:
    f = _write(tmp_path, "source_id: src_abc\n")
    with pytest.raises(SourceRegistryError, match="top-level YAML must be a list"):
        load_sources(f)


def test_entry_not_mapping_rejected(tmp_path: Path) -> None:
    f = _write(tmp_path, "- just_a_string\n")
    with pytest.raises(SourceRegistryError, match="must be a mapping"):
        load_sources(f)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_sources(tmp_path / "does_not_exist.yaml")


# ---- per-entry Pydantic failures ---------------------------------------------


def test_missing_required_field_rejected(tmp_path: Path) -> None:
    e = _entry()
    e.pop("source_name")
    f = _write(tmp_path, _dump([e]))
    with pytest.raises(ValidationError):
        load_sources(f)


def test_extra_field_rejected(tmp_path: Path) -> None:
    e = _entry(mystery_field="oops")
    f = _write(tmp_path, _dump([e]))
    with pytest.raises(ValidationError):
        load_sources(f)


def test_bad_source_id_prefix_rejected(tmp_path: Path) -> None:
    e = _entry(source_id="ach_" + "a" * 32)
    f = _write(tmp_path, _dump([e]))
    with pytest.raises(ValidationError):
        load_sources(f)


# ---- credential URL protection ------------------------------------------------


def test_credential_url_in_yaml_raises_credential_error_no_leak(tmp_path: Path) -> None:
    bad_url = f"https://{_SAFE_USER}:{_SAFE_PASS}@example.org/x"
    e = _entry(source_url=bad_url)
    f = _write(tmp_path, _dump([e]))

    with pytest.raises(CredentialInUrlError) as exc_info:
        load_sources(f)

    exc = exc_info.value
    leaky = (
        str(exc),
        repr(exc),
        *(str(a) for a in exc.args),
    )
    for s in leaky:
        assert _SAFE_USER not in s, "credential leaked in exception representation"
        assert _SAFE_PASS not in s, "credential leaked in exception representation"
        assert "example.org" not in s, "raw host leaked in exception representation"


# ---- validate_sources --------------------------------------------------------


def test_valid_single_entry_loads_and_validates(tmp_path: Path) -> None:
    e = _entry()
    f = _write(tmp_path, _dump([e]))
    report = load_and_validate_sources(f)
    assert len(report.entries) == 1
    assert report.unknown_license_ids == []
    assert report.unverified_source_ids == []


def test_duplicate_source_id_rejected(tmp_path: Path) -> None:
    sid = make_id("src")
    e1 = _entry(source_id=sid, source_name="A")
    e2 = _entry(source_id=sid, source_name="B")
    f = _write(tmp_path, _dump([e1, e2]))
    with pytest.raises(SourceRegistryError, match="duplicate source_id"):
        load_and_validate_sources(f)


def test_unknown_license_is_advisory(tmp_path: Path) -> None:
    e = _entry(license=UNKNOWN_LICENSE)
    f = _write(tmp_path, _dump([e]))
    report = load_and_validate_sources(f)
    assert report.unknown_license_ids == [e["source_id"]]
    assert report.unverified_source_ids == []
    assert len(report.entries) == 1


def test_unverified_review_status_is_advisory(tmp_path: Path) -> None:
    e = _entry(review_status="unreviewed")
    f = _write(tmp_path, _dump([e]))
    report = load_and_validate_sources(f)
    assert report.unverified_source_ids == [e["source_id"]]
    assert report.unknown_license_ids == []


# ---- from_untrusted is on the hot path ----------------------------------------


def test_loader_uses_from_untrusted_not_direct_constructor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    e = _entry()
    f = _write(tmp_path, _dump([e]))

    call_count = {"n": 0}
    real_from_untrusted = SourceRegistry.from_untrusted

    def spy(data):
        call_count["n"] += 1
        return real_from_untrusted(data)

    monkeypatch.setattr(SourceRegistry, "from_untrusted", classmethod(lambda cls, data: spy(data)))

    load_sources(f)
    assert call_count["n"] == 1, "loader must route every entry through from_untrusted"


# ---- source_ids helper -------------------------------------------------------


def test_source_ids_helper_returns_expected_set() -> None:
    e1 = SourceRegistry(**{k: v for k, v in _entry().items()})
    e2_dict = _entry()
    e2 = SourceRegistry(**e2_dict)
    assert source_ids([e1, e2]) == {e1.source_id, e2.source_id}


def test_source_ids_helper_on_empty_iterable() -> None:
    assert source_ids([]) == set()
