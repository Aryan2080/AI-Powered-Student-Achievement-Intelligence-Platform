"""arXiv metadata governance (Chunk 7.18 — Mohan-revision implementation).

Policy module. Enforces the four governance revisions mandated by the
Chunk 7.17 human source review (Ashok: approve metadata-only use;
Mohan: revise — required schema and endpoint updates).

1. Official metadata endpoints; prohibit ``/abs/`` HTML scraping.
2. Metadata-only handling under CC0-1.0; per-record license tracking;
   reject full-text / PDF / TeX / source-archive storage.
3. Preprint classification; withdrawal detection; student-attribution
   gates requiring at least one verified evidence path.
4. Acknowledgment constant; canonical abstract-link helper; log
   contact-email redaction.

This module is pure policy. It never performs API requests, downloads,
or filesystem writes. Any future collector MUST route endpoint
selection, record validation, student attribution, and log emission
through this module.

Related:
    - Governance context: ``hybrid_dataset/metadata/arxiv_governance_decisions.md``
    - Source registry entry: ``src_08ee850ba4b54d1b81cdbd652809b613`` in
      ``hybrid_dataset/metadata/sources.yaml``
    - Rate-limit enforcement: :mod:`nlp_semantic.ingestion.rate_limit`

Governance status after this chunk: the source remains
``review_status: unreviewed``. Implementation of these revisions does
NOT constitute promotion; a subsequent human review must inspect the
implementation and explicitly authorize promotion.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Final
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- constants ---------------------------------------------------------------

#: Chunk 7.15 arXiv source id (registered in sources.yaml).
ARXIV_SOURCE_ID: Final[str] = "src_08ee850ba4b54d1b81cdbd652809b613"

#: Chunk 7.18 Revision 1 — the two official arXiv metadata endpoints.
#: Any metadata collection must target one of these exactly.
OFFICIAL_METADATA_ENDPOINTS: Final[dict[str, str]] = {
    "query_api": "https://export.arxiv.org/api/query",
    "oai_pmh":   "https://oaipmh.arxiv.org/oai",
}

#: Chunk 7.18 Revision 4 — acknowledgment line requested by arXiv.
#: CC0 does not legally require attribution; this is a project convention
#: that honors arXiv's own request.
ARXIV_ACKNOWLEDGMENT: Final[str] = (
    "Thank you to arXiv for use of its open access interoperability"
)

#: Canonical CC0 1.0 Public Domain Dedication URI. Applies to arXiv
#: *descriptive metadata only*. Does NOT grant any permission over arXiv
#: full-text (PDF, TeX, source files, figures).
CC0_LICENSE_URI: Final[str] = (
    "https://creativecommons.org/publicdomain/zero/1.0/"
)

# Content-type prefixes that must NEVER be stored or downloaded.
# Chunk 7.18 Revision 2.
_FORBIDDEN_CONTENT_PREFIXES: Final[tuple[str, ...]] = (
    "application/pdf",
    "application/x-tex",
    "application/x-latex",
    "application/postscript",
    "application/x-tar",
    "application/gzip",
    "application/x-gzip",
    "application/x-bzip2",
    "application/zip",
    "image/",  # figures are full-text artifacts
)

# Allowed content-type prefixes for metadata responses.
_ALLOWED_METADATA_CONTENT_PREFIXES: Final[tuple[str, ...]] = (
    "application/xml",
    "application/atom+xml",
    "application/rss+xml",
    "application/json",
    "text/xml",
)

# Email regex used ONLY for log redaction. Not an address validator.
# Captures typical RFC-ish tokens well enough to prevent accidental leakage.
_EMAIL_RE: Final[re.Pattern[str]] = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)

# arXiv base identifier regex. Covers the two format eras:
#   old-style   math-ph/0411035   or   cs.LG/0601001
#   new-style   2403.12345
_BASE_ARXIV_ID_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:(?P<new>\d{4}\.\d{4,5})|"
    r"(?P<old>[a-z\-]+(?:\.[A-Z]{2})?/\d{7}))$"
)

# Author-supplied comment patterns that signal a withdrawal.
_WITHDRAWN_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bwithdrawn\b", re.IGNORECASE),
    re.compile(r"\bthis paper has been withdrawn\b", re.IGNORECASE),
    re.compile(r"\bauthors? withdrew\b", re.IGNORECASE),
    re.compile(r"\bretract(?:ed|ion)\b", re.IGNORECASE),
)


# ---- exceptions --------------------------------------------------------------


class AbsScrapingProhibitedError(ValueError):
    """Attempt to use an arXiv HTML page (``/abs/``, ``/pdf/``, ``/src/``,
    ``/html/``, ``/format/``) as a metadata source. Chunk 7.18 Revision 1
    forbids HTML scraping for metadata ingestion."""


class EndpointNotAllowedError(ValueError):
    """URL does not match any :data:`OFFICIAL_METADATA_ENDPOINTS` entry."""


class ForbiddenContentTypeError(ValueError):
    """Content-type is a disallowed artifact (PDF, TeX, source archive,
    full-text, figure). Chunk 7.18 Revision 2 forbids storing or
    downloading such content."""


class MissingStudentVerificationError(ValueError):
    """Student link requested without any accepted verification evidence.
    Chunk 7.18 Revision 3 requires at least one of (verified ORCID,
    verified institutional email, advisor verification)."""


# ---- Revision 1 — endpoint validation ---------------------------------------


def validate_metadata_endpoint(url: str) -> str:
    """Validate that ``url`` is one of the two official arXiv metadata
    endpoints. Returns the stripped URL on success.

    Rejects:
      - ``/abs/``, ``/pdf/``, ``/src/``, ``/html/``, ``/format/`` paths
        on ANY host (:class:`AbsScrapingProhibitedError`).
      - Any URL not matching the whitelist exactly on (scheme, host,
        path) (:class:`EndpointNotAllowedError`).
      - Non-``https`` schemes (:class:`EndpointNotAllowedError`).
    """
    stripped = url.strip()
    parsed = urlparse(stripped)
    if parsed.scheme != "https":
        raise EndpointNotAllowedError(
            f"metadata endpoint must use https; got scheme "
            f"{parsed.scheme!r}"
        )

    # Prohibit scraping-oriented paths across ANY host.
    lower_path = (parsed.path or "").lower()
    for scrape_prefix in ("/abs", "/pdf", "/src", "/html", "/format"):
        if lower_path.startswith(scrape_prefix):
            raise AbsScrapingProhibitedError(
                f"arXiv HTML/full-text paths (/abs, /pdf, /src, /html, "
                "/format) are not metadata endpoints and must not be "
                "scraped for metadata ingestion. Use the official "
                f"endpoints: {sorted(OFFICIAL_METADATA_ENDPOINTS.values())}."
            )

    # Whitelist on exact (scheme, hostname, path-no-trailing-slash) tuple.
    for endpoint_url in OFFICIAL_METADATA_ENDPOINTS.values():
        allowed = urlparse(endpoint_url)
        allowed_key = (allowed.scheme, allowed.hostname,
                       (allowed.path or "").rstrip("/"))
        actual_key = (parsed.scheme, parsed.hostname,
                      (parsed.path or "").rstrip("/"))
        if actual_key == allowed_key:
            return stripped

    raise EndpointNotAllowedError(
        f"endpoint {stripped!r} is not in OFFICIAL_METADATA_ENDPOINTS; "
        f"allowed: {sorted(OFFICIAL_METADATA_ENDPOINTS.values())}"
    )


# ---- Revision 2 — metadata record and content-type rejection -----------------


def reject_forbidden_content_type(content_type: str | None) -> None:
    """Raise :class:`ForbiddenContentTypeError` for a disallowed artifact.

    ``None`` is treated as 'unknown but not demonstrably forbidden' and
    is allowed to pass. An unknown content-type does NOT license storing
    full text; callers must still only persist descriptive metadata.
    """
    if content_type is None:
        return
    ct = content_type.strip().lower().split(";", 1)[0]
    for forbidden in _FORBIDDEN_CONTENT_PREFIXES:
        if ct.startswith(forbidden):
            raise ForbiddenContentTypeError(
                f"content-type {ct!r} is a prohibited artifact under the "
                "metadata-only governance scope (Chunk 7.18 Revision 2). "
                "The project may not store or download PDF, TeX, source "
                "archives, figures, or full-text papers."
            )


class ArxivMetadataRecord(BaseModel):
    """One staged arXiv metadata record. Metadata-only.

    Not the ``Achievement`` schema. This is a staging-only Pydantic
    model holding the fields the Chunk 7.16 §C.1 mapping identifies.
    Downstream promotion to an ``Achievement`` row requires the Chunk
    7.11 five-stage review workflow.

    ``per_paper_license_uri`` is ``None`` whenever the per-record
    license is absent or unverified. ``None`` is the explicit UNKNOWN
    state; callers MUST NOT infer CC0 (CC0 applies to the metadata
    corpus, not to a paper's full text) or any other per-paper license
    from ``None``.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    base_arxiv_id: str
    version_at_collection: str | None = None  # e.g. "v2"
    title: str = Field(min_length=1, max_length=1000)
    abstract: str = Field(default="", max_length=10000)
    authors: list[str] = Field(default_factory=list)
    submitted_date: str  # ISO date; validated as string here
    updated_date: str | None = None
    primary_category: str = Field(min_length=1, max_length=40)
    all_categories: list[str] = Field(default_factory=list)
    doi: str | None = None
    journal_ref: str | None = None
    comment: str | None = None
    per_paper_license_uri: str | None = None  # None = unknown/unverified
    source_id: str = ARXIV_SOURCE_ID

    @field_validator("base_arxiv_id")
    @classmethod
    def _check_base_id(cls, v: str) -> str:
        if not _BASE_ARXIV_ID_RE.match(v):
            raise ValueError(
                f"base_arxiv_id {v!r} does not match arXiv ID patterns "
                "(expected '<yymm>.<nnnnn>' or '<archive>/<nnnnnnn>')"
            )
        return v

    @field_validator("source_id")
    @classmethod
    def _check_source(cls, v: str) -> str:
        if v != ARXIV_SOURCE_ID:
            raise ValueError(
                f"ArxivMetadataRecord.source_id must be {ARXIV_SOURCE_ID!r}; "
                f"got {v!r}"
            )
        return v


# ---- Revision 3 — preprint status, withdrawals, student attribution ---------


class PeerReviewStatus(str, Enum):
    """Peer-review classification used by downstream governance.

    ``UNREFEREED_PREPRINT`` is the default when no externally verified
    DOI or journal reference is available. ``PEER_REVIEWED`` requires
    independent external verification (not merely the presence of a DOI
    or journal_ref string on the arXiv record).
    """

    UNREFEREED_PREPRINT = "unrefereed_preprint"
    PEER_REVIEWED = "peer_reviewed"
    UNKNOWN = "unknown"


def assess_peer_review_status(
    record: ArxivMetadataRecord,
    *,
    doi_externally_verified: bool = False,
    journal_ref_externally_verified: bool = False,
) -> PeerReviewStatus:
    """Classify ``record``'s peer-review status conservatively.

    Mohan's rule: a record without a VERIFIED DOI or journal reference
    MUST be classified :attr:`PeerReviewStatus.UNREFEREED_PREPRINT`.
    Mere presence of a DOI or journal_ref string on the arXiv record is
    author-asserted and does NOT constitute verification. The caller
    passes explicit external-verification flags.

    The function never infers peer-review from the arXiv identifier,
    publication date, title, author list, or abstract.
    """
    if doi_externally_verified and record.doi is not None:
        return PeerReviewStatus.PEER_REVIEWED
    if journal_ref_externally_verified and record.journal_ref is not None:
        return PeerReviewStatus.PEER_REVIEWED
    return PeerReviewStatus.UNREFEREED_PREPRINT


def is_withdrawn(record: ArxivMetadataRecord) -> bool:
    """Return ``True`` if ``record.comment`` matches a withdrawal pattern.

    Text-pattern heuristic over the author-supplied comment. A ``False``
    does NOT prove the paper is not withdrawn; a ``True`` is a signal
    that must trigger exclusion from eligible ingestion / linking.
    """
    if not record.comment:
        return False
    return any(p.search(record.comment) for p in _WITHDRAWN_PATTERNS)


class StudentVerificationEvidence(BaseModel):
    """Verification evidence accepted by Chunk 7.18 Revision 3.

    Linking a paper to a student profile requires at least one of
    the three flags to be ``True``.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    orcid_verified: bool = False
    institutional_email_verified: bool = False
    advisor_verified: bool = False

    @property
    def any_accepted(self) -> bool:
        return (
            self.orcid_verified
            or self.institutional_email_verified
            or self.advisor_verified
        )


def authorize_student_link(
    record: ArxivMetadataRecord,
    evidence: StudentVerificationEvidence,
) -> None:
    """Raise :class:`MissingStudentVerificationError` unless at least one
    of (ORCID verified, institutional email verified, advisor verified)
    on ``evidence`` is ``True``.

    This function is the ONLY sanctioned entry point for linking an
    arXiv paper to a student profile. Any future record-creation path
    must call this; name similarity, affiliation strings, and author
    position are NEVER sufficient on their own.

    Author-identity disambiguation (e.g. ORCID lookup, name-to-identity
    reconciliation) is a SEPARATE step that must run before this
    function is called, not within it.
    """
    if not evidence.any_accepted:
        raise MissingStudentVerificationError(
            f"cannot link arXiv record {record.base_arxiv_id!r} to a "
            "student profile: no accepted verification evidence present. "
            "Required: at least one of (orcid_verified, "
            "institutional_email_verified, advisor_verified)."
        )


# ---- Revision 4 — acknowledgment, canonical links, email redaction ----------


def canonical_abs_link(base_arxiv_id: str) -> str:
    """Return the canonical arXiv abstract-page link for display.

    The canonical URL is the host-rooted ``/abs/`` page. The project
    DISPLAYS this link as a human-facing reference but NEVER scrapes it
    for metadata (see :func:`validate_metadata_endpoint`).
    """
    if not _BASE_ARXIV_ID_RE.match(base_arxiv_id):
        raise ValueError(
            f"base_arxiv_id {base_arxiv_id!r} does not match arXiv ID "
            "patterns"
        )
    return f"https://arxiv.org/abs/{base_arxiv_id}"


def redact_contact_emails(text: str) -> str:
    """Return ``text`` with email-like substrings replaced by
    ``[REDACTED_EMAIL]``.

    Prevents accidental submitter-email leakage in log messages, raw
    payload dumps, exception messages, debug output, and serialized
    records (Chunk 7.18 Revision 4). Does not modify ``text`` when it
    is empty or ``None``-equivalent.
    """
    if not text:
        return text
    return _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
