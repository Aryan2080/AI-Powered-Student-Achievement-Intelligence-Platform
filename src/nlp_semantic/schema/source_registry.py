"""SourceRegistry model and safe ingestion boundary."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import ReviewStatus
from .identifiers import validate_prefixed_id

UNKNOWN_LICENSE = "UNKNOWN"


class CredentialInUrlError(ValueError):
    """Raised when a source URL carries embedded credentials.

    The exception's message, ``args`` tuple, and every string
    representation are deliberately fixed and do NOT include the
    supplied URL, username, or password. Callers may match on this
    specific type to distinguish credential-prohibited input from other
    validation failures.

    This exception is produced only by the safe ingestion boundary
    :meth:`SourceRegistry.from_untrusted`. Direct Pydantic construction
    raises :class:`pydantic.ValidationError` and is a separate (less
    safe) path — see the ``SourceRegistry`` class docstring.
    """

    def __init__(self, field: str = "source_url") -> None:
        self.field = field
        super().__init__(
            f"{field}: URL must not contain embedded credentials. "
            "The offending value is not echoed by this validation "
            "path; strip credentials before registering the source."
        )


def _reject_credential_bearing_source_url(data: Mapping[str, Any]) -> None:
    """Pre-Pydantic scan for embedded credentials in ``source_url``.

    If ``data["source_url"]`` is a string whose authority carries a
    ``user:password@``, ``user@``, or ``:password@`` component, raise
    :class:`CredentialInUrlError` **without** including the URL,
    username, or password in the exception.

    Does nothing when ``source_url`` is absent, ``None``, or not a
    string — those cases are Pydantic's problem to validate downstream.
    """
    url = data.get("source_url")
    if not isinstance(url, str):
        return
    parsed = urlparse(url)
    has_creds = parsed.username is not None or parsed.password is not None
    # Drop references to the raw URL and parsed object before raising,
    # so that neither remains in the local frame captured by any
    # traceback-walking logger.
    del url, parsed
    if has_creds:
        # ``from None`` suppresses implicit chaining of any inner
        # exception that might otherwise carry URL fragments in its
        # context (currently none, but defensive).
        raise CredentialInUrlError("source_url") from None


class SourceRegistry(BaseModel):
    """One registered dataset or data origin.

    ``license == "UNKNOWN"`` is permitted at the schema level but
    conveys NO permission to train on, redistribute, or publish from
    this source. Eligibility is decided by a later dataset validator
    that reads this row plus the ``review_status``. ``original_labels``
    are preserved verbatim and must not be silently remapped to our
    schema's taxonomy.

    **Safe ingestion.** For any input whose ``source_url`` originated
    outside this repository (parsed YAML/JSON, user form input,
    downloaded manifest, …), construct the record via the safe boundary
    :meth:`from_untrusted`. The field validator on this class also
    rejects credential-bearing URLs on the direct constructor path, but
    Pydantic captures the raw input in ``ValidationError.errors()`` and
    ``ValidationError.json()`` regardless of
    ``hide_input_in_errors=True`` (that flag only hides input from
    ``str()``/``repr()``). ``from_untrusted`` intercepts the URL
    **before** Pydantic sees it, so no error representation can contain
    the supplied credentials.
    """

    # hide_input_in_errors=True only hides input from str(exc) / repr(exc).
    # It does NOT redact ValidationError.errors()[*]["input"] or .json().
    # For untrusted URL input, callers MUST use SourceRegistry.from_untrusted;
    # see the class docstring and schema/README.md.
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        hide_input_in_errors=True,
    )

    source_id: str
    source_name: str = Field(min_length=1, max_length=120)
    source_url: str | None = None
    license: str = Field(min_length=1, max_length=200)
    usage_restrictions: str | None = Field(default=None, max_length=2000)
    collection_date: date
    original_labels: list[str] = Field(default_factory=list)
    intended_use: str = Field(min_length=1, max_length=200)
    mapping_notes: str | None = Field(default=None, max_length=2000)
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    is_synthetic: bool = False

    @classmethod
    def from_untrusted(cls, data: Mapping[str, Any]) -> "SourceRegistry":
        """Safe constructor for untrusted source-registry data.

        Use this instead of ``SourceRegistry(**data)`` whenever any
        field (particularly ``source_url``) originated outside this
        repository.

        If ``data["source_url"]`` contains embedded credentials, raises
        :class:`CredentialInUrlError` before Pydantic sees the input.
        The resulting exception's message, ``args``, ``str()``,
        ``repr()``, and traceback do not contain the URL, username, or
        password.

        For every other validation failure (bad license, future date,
        malformed ID, missing field, …) a normal
        :class:`pydantic.ValidationError` is raised unchanged.
        """
        _reject_credential_bearing_source_url(data)
        return cls(**data)

    @field_validator("source_id")
    @classmethod
    def _validate_source_id(cls, v: str) -> str:
        return validate_prefixed_id(v, "src")

    @field_validator("source_url")
    @classmethod
    def _validate_source_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v:
            raise ValueError("source_url must be a non-empty URL when set")
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                "source_url must use scheme 'http' or 'https'; got "
                f"{parsed.scheme!r}"
            )
        # Second line of defence on the direct-construction path.
        # NOTE: on this path Pydantic will still capture the raw URL in
        # ValidationError.errors()[*]["input"]; untrusted callers must
        # use SourceRegistry.from_untrusted() to avoid that exposure.
        if parsed.username is not None or parsed.password is not None:
            raise ValueError(
                "source_url must not contain embedded credentials "
                "('user:password@' in the authority); strip them before "
                "registering the source."
            )
        if not parsed.hostname:
            raise ValueError("source_url must include a hostname")
        return v

    @field_validator("collection_date")
    @classmethod
    def _validate_collection_date(cls, v: date) -> date:
        max_allowed = date.today() + timedelta(days=1)
        if v > max_allowed:
            raise ValueError(
                f"collection_date must be <= {max_allowed.isoformat()}; got "
                f"{v.isoformat()}"
            )
        return v

    @field_validator("original_labels")
    @classmethod
    def _validate_original_labels(cls, v: list[str]) -> list[str]:
        for lbl in v:
            if not isinstance(lbl, str) or not lbl.strip():
                raise ValueError(
                    "original_labels entries must be non-empty strings"
                )
        return v
