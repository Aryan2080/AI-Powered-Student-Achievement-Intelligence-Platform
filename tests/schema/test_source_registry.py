"""Tests for SourceRegistry model and its safe ingestion boundary."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from nlp_semantic.schema import (
    CredentialInUrlError,
    ReviewStatus,
    SourceRegistry,
    UNKNOWN_LICENSE,
    make_id,
)

# Unique synthetic tokens — chosen so they would NOT appear in generic
# error text or any URL other than the one we construct in the test.
# Never printed by tests on either success or failure.
_SAFE_USER = "k2z9m1q_user"
_SAFE_PASS = "x7v4b8n_token"


def _minimal(**overrides) -> dict:
    base = {
        "source_id": make_id("src"),
        "source_name": "Example Public Dataset",
        "source_url": "https://example.org/dataset",
        "license": "CC-BY-4.0",
        "collection_date": date.today(),
        "intended_use": "primary_type_training",
        "is_synthetic": True,
    }
    base.update(overrides)
    return base


def test_minimal_valid() -> None:
    s = SourceRegistry(**_minimal())
    assert s.review_status == ReviewStatus.UNREVIEWED
    assert s.original_labels == []


@pytest.mark.parametrize(
    "bad_url",
    [
        "ftp://example.org/x",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "example.org/no-scheme",
    ],
)
def test_url_scheme_rejected(bad_url: str) -> None:
    with pytest.raises(ValidationError):
        SourceRegistry(**_minimal(source_url=bad_url))


def test_url_no_host_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceRegistry(**_minimal(source_url="https:///path"))


def test_url_none_allowed() -> None:
    s = SourceRegistry(**_minimal(source_url=None))
    assert s.source_url is None


def test_http_url_allowed() -> None:
    s = SourceRegistry(**_minimal(source_url="http://data.example.gov/x"))
    assert s.source_url == "http://data.example.gov/x"


def test_unknown_license_allowed_but_not_permission() -> None:
    """UNKNOWN passes the schema; it does NOT auto-approve usage."""
    s = SourceRegistry(**_minimal(license=UNKNOWN_LICENSE))
    assert s.license == UNKNOWN_LICENSE
    # review_status defaults to UNREVIEWED — eligibility is a dataset-level
    # decision; this record alone is not permission to train or publish.
    assert s.review_status == ReviewStatus.UNREVIEWED


def test_unknown_license_requires_explicit_verification_to_be_marked_verified() -> None:
    """A reviewer must explicitly set review_status=VERIFIED; UNKNOWN
    license does not block the schema, but the model does not auto-grant
    verified state."""
    s = SourceRegistry(**_minimal(license=UNKNOWN_LICENSE))
    # Verify the default did not silently become VERIFIED
    assert s.review_status != ReviewStatus.VERIFIED


def test_empty_license_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceRegistry(**_minimal(license=""))


def test_whitespace_license_rejected() -> None:
    # str_strip_whitespace strips before min_length check
    with pytest.raises(ValidationError):
        SourceRegistry(**_minimal(license="   "))


def test_future_collection_date_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceRegistry(**_minimal(
            collection_date=date.today() + timedelta(days=30)
        ))


def test_today_collection_date_allowed() -> None:
    s = SourceRegistry(**_minimal(collection_date=date.today()))
    assert s.collection_date == date.today()


def test_missing_source_name_rejected() -> None:
    data = _minimal()
    data.pop("source_name")
    with pytest.raises(ValidationError):
        SourceRegistry(**data)


def test_missing_license_rejected() -> None:
    data = _minimal()
    data.pop("license")
    with pytest.raises(ValidationError):
        SourceRegistry(**data)


def test_missing_intended_use_rejected() -> None:
    data = _minimal()
    data.pop("intended_use")
    with pytest.raises(ValidationError):
        SourceRegistry(**data)


def test_source_id_prefix_checked() -> None:
    with pytest.raises(ValidationError):
        SourceRegistry(**_minimal(source_id=make_id("ach")))


def test_original_labels_preserved_verbatim() -> None:
    raw = ["Winner", "1st Prize", "Hackathon-X"]
    s = SourceRegistry(**_minimal(original_labels=raw))
    assert s.original_labels == raw


def test_empty_original_label_entry_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceRegistry(**_minimal(original_labels=["ok", ""]))


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceRegistry(**_minimal(mystery="x"))


# --- Direct constructor (trusted-input path) ---------------------------------
# The field validator still rejects credential URLs on this path, but Pydantic
# captures the raw input in ValidationError.errors()[*]["input"] regardless of
# hide_input_in_errors. Documented limitation: untrusted callers must use
# SourceRegistry.from_untrusted().


@pytest.mark.parametrize(
    "shape",
    ["user_pass", "user_only", "pass_only", "http_variant"],
)
def test_direct_constructor_rejects_credential_url(shape: str) -> None:
    """Direct construction raises ValidationError for credential URLs.

    This test does NOT print the URL on failure; it uses boolean guards so
    assertion messages do not echo credential tokens.
    """
    if shape == "user_pass":
        url = "https://" + _SAFE_USER + ":" + _SAFE_PASS + "@example.org/data"
    elif shape == "user_only":
        url = "https://" + _SAFE_USER + "@example.org/data"
    elif shape == "pass_only":
        url = "https://:" + _SAFE_PASS + "@example.org/data"
    else:
        url = "http://" + _SAFE_USER + ":" + _SAFE_PASS + "@data.example.gov/x"

    with pytest.raises(ValidationError) as exc_info:
        SourceRegistry(**_minimal(source_url=url))

    # hide_input_in_errors=True covers str() and repr(). This still must hold.
    for representation in (str(exc_info.value), repr(exc_info.value)):
        if _SAFE_USER in representation or _SAFE_PASS in representation:
            raise AssertionError("credential token leaked in str/repr of ValidationError")
        if url in representation:
            raise AssertionError("full URL leaked in str/repr of ValidationError")


def test_direct_constructor_leak_in_structured_errors_is_documented_limitation() -> None:
    """Documented limitation: ValidationError.errors()[*]['input'] still carries
    the raw URL on the direct-construction path. Future-proofs the docs: if
    Pydantic changes behaviour or the schema fully closes this gap, this
    assertion will fail and alert the maintainer to update schema/README.md
    rather than silently losing the warning.
    """
    url = "https://" + _SAFE_USER + ":" + _SAFE_PASS + "@example.org/data"
    with pytest.raises(ValidationError) as exc_info:
        SourceRegistry(**_minimal(source_url=url))
    inputs = [e.get("input") for e in exc_info.value.errors()]
    leak_present = any(
        isinstance(x, str) and (_SAFE_USER in x or _SAFE_PASS in x)
        for x in inputs
    )
    # If this ever becomes False, the direct-construction path is now safe
    # against structured error leaks and schema/README.md should be updated.
    assert leak_present, (
        "direct-construction leak no longer present — update "
        "schema/README.md to retire the warning about Pydantic's "
        "ValidationError.errors()[*]['input']"
    )


def test_valid_credential_free_https_url_accepted_on_direct_constructor() -> None:
    s = SourceRegistry(**_minimal(source_url="https://data.example.org/dataset.csv"))
    assert s.source_url == "https://data.example.org/dataset.csv"


# --- Safe ingestion boundary: SourceRegistry.from_untrusted ------------------


@pytest.mark.parametrize(
    "shape",
    ["user_pass", "user_only", "pass_only", "http_variant"],
)
def test_from_untrusted_rejects_credential_url_without_leak(shape: str) -> None:
    """Safe boundary raises CredentialInUrlError; no credentials leak.

    Checks str(exc), repr(exc), exc.args, and exc.field across every form a
    logger might reach. Uses boolean guards so a failing assertion message
    never echoes the credential tokens.
    """
    if shape == "user_pass":
        url = "https://" + _SAFE_USER + ":" + _SAFE_PASS + "@example.org/data"
    elif shape == "user_only":
        url = "https://" + _SAFE_USER + "@example.org/data"
    elif shape == "pass_only":
        url = "https://:" + _SAFE_PASS + "@example.org/data"
    else:
        url = "http://" + _SAFE_USER + ":" + _SAFE_PASS + "@data.example.gov/x"

    data = _minimal(source_url=url)
    try:
        SourceRegistry.from_untrusted(data)
    except CredentialInUrlError as exc:
        representations: dict[str, str] = {
            "str(exc)": str(exc),
            "repr(exc)": repr(exc),
            "exc.args": str(exc.args),
        }
        for rep_name, rep in representations.items():
            for token_name, token in (
                ("username", _SAFE_USER),
                ("password", _SAFE_PASS),
                ("full_url", url),
            ):
                if token in rep:
                    raise AssertionError(
                        f"{token_name} leaked into {rep_name} of CredentialInUrlError"
                    )
        if exc.field != "source_url":
            raise AssertionError("CredentialInUrlError.field is not 'source_url'")
        # Not a Pydantic ValidationError — no structured ``errors()`` payload.
        if hasattr(exc, "errors"):
            # Only acceptable if it is NOT the Pydantic-style callable payload
            # (e.g. the standard Exception has no 'errors' attribute at all).
            raise AssertionError(
                "CredentialInUrlError unexpectedly carries an 'errors' attribute"
            )
        return
    raise AssertionError(
        f"CredentialInUrlError not raised by from_untrusted for shape={shape!r}"
    )


def test_from_untrusted_credential_error_type_is_valueerror() -> None:
    """CredentialInUrlError must subclass ValueError so generic error handlers
    that catch ValueError still see it, without widening the catch to
    Exception."""
    assert issubclass(CredentialInUrlError, ValueError)


def test_from_untrusted_accepts_clean_https_url() -> None:
    data = _minimal(source_url="https://data.example.org/dataset.csv")
    s = SourceRegistry.from_untrusted(data)
    assert s.source_url == "https://data.example.org/dataset.csv"


def test_from_untrusted_accepts_clean_http_url() -> None:
    data = _minimal(source_url="http://data.example.gov/x")
    s = SourceRegistry.from_untrusted(data)
    assert s.source_url == "http://data.example.gov/x"


def test_from_untrusted_accepts_none_url() -> None:
    data = _minimal(source_url=None)
    s = SourceRegistry.from_untrusted(data)
    assert s.source_url is None


def test_from_untrusted_passes_through_other_validation_errors() -> None:
    """A non-credential problem (bad license) still raises ValidationError,
    NOT CredentialInUrlError. The safe boundary only intercepts credential
    URLs; it does not swallow other errors."""
    data = _minimal(source_url="https://example.org/data", license="")
    with pytest.raises(ValidationError):
        SourceRegistry.from_untrusted(data)


def test_from_untrusted_non_string_url_defers_to_pydantic() -> None:
    """A non-string source_url is Pydantic's problem; the safe boundary must
    not raise CredentialInUrlError for the wrong reason."""
    data = _minimal()
    data["source_url"] = 123  # type: ignore[assignment]
    with pytest.raises(ValidationError):
        SourceRegistry.from_untrusted(data)
    # And NOT CredentialInUrlError
    data2 = _minimal()
    data2["source_url"] = 123  # type: ignore[assignment]
    try:
        SourceRegistry.from_untrusted(data2)
    except CredentialInUrlError:
        raise AssertionError(
            "CredentialInUrlError raised for non-string input"
        )
    except ValidationError:
        pass
