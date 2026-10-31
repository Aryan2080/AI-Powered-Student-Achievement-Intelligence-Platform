# arXiv Source Governance Decisions

**Source id:** `src_08ee850ba4b54d1b81cdbd652809b613`
**Source name:** `arXiv`
**Current review status:** `unreviewed` (pending a new human review of these revisions).
**Governance origin:** Chunk 7.17 human source review — Ashok (approve, metadata-only CC0 1.0); Mohan (revise — approval conditional on the revisions implemented below).
**Implementation chunk:** 7.18.

This document captures the detailed governance decisions for the arXiv metadata source. The source registry entry in `hybrid_dataset/metadata/sources.yaml` carries a brief pointer to this document; the long-form text lives here so the registry entry stays within its 2000-character field cap.

Implementation does NOT equal approval. The source remains `unreviewed` until a new human review decides whether the implementation satisfies Mohan's revision requirements.

---

## Revision 1 — Official API endpoints and rate limiting

**Approved metadata endpoints (the only two that may be used):**

| Name | URL |
|---|---|
| Query API | `https://export.arxiv.org/api/query` |
| OAI-PMH | `https://oaipmh.arxiv.org/oai` |

**Prohibited:** HTML scraping of `/abs/`, `/pdf/`, `/src/`, `/html/`, `/format/` paths on any arXiv host. These are not metadata endpoints.

Enforcement module: [`src/nlp_semantic/ingestion/arxiv_governance.py`](../../src/nlp_semantic/ingestion/arxiv_governance.py)
  - Constant: `OFFICIAL_METADATA_ENDPOINTS`
  - Validator: `validate_metadata_endpoint(url)` — rejects non-whitelist URLs; rejects `/abs/` / `/pdf/` / etc. on any host.
  - Exceptions: `EndpointNotAllowedError`, `AbsScrapingProhibitedError`.

**Rate limiting:**
- At most one active connection at a time.
- At least 3.0 seconds between successive requests.
- arXiv's ToU specifies collective rate limits across all machines under the user's control.

Enforcement module: [`src/nlp_semantic/ingestion/rate_limit.py`](../../src/nlp_semantic/ingestion/rate_limit.py)
  - Class: `ArxivRateLimiter` with an `acquire()` context manager.
  - Constant: `MIN_REQUEST_SPACING_SECONDS = 3.0`.

**Architectural evolution (Chunk 7.22 — Redis coordinator available):**

- The default-constructed `ArxivRateLimiter()` is still backed by the process-local `_DEFAULT_COORDINATOR`. This is unchanged.
- A **Redis-backed coordinator** has been implemented (`RedisCoordinator` in `rate_limit.py`) that provides cross-process + cross-machine guarantees via an atomic Lua script using Redis server time.
- Selection is environment-driven via `ARXIV_RATE_COORDINATOR_URL`:
  - unset / empty / `in_process:` → process-local (status quo).
  - `redis://…` or `rediss://…` → `RedisCoordinator` constructed by `make_coordinator_from_env()`.
- **Fail-closed:** when a Redis URL is explicitly configured but the server is unavailable, `make_coordinator_from_env()` raises `RateLimitCoordinatorUnavailableError`. It does NOT silently fall back to the process-local coordinator.
- **Deployment status:** no production Redis endpoint is configured in this repository. The code is **implementation + unit-tested** against `fakeredis[lua]`; cross-machine behavior with a real Redis server remains **NOT VERIFIED** in this chunk (no infrastructure available). The global cross-machine blocker is not resolved until a real deployment is stood up and verified.

**Compensating operator discipline (unchanged default posture):**
- Exactly ONE collector process runs at any time.
- Exactly ONE operator machine runs the collector at any time.
- If a second machine ever runs collection, operators coordinate so that collective rate stays ≤ 1 request / 3 s.
- If and when a shared Redis endpoint is configured, operator discipline relaxes to "any machine that holds the right `ARXIV_RATE_COORDINATOR_URL` can run a collector."

---

## Revision 2 — Metadata license and content restrictions

**Scope.** CC0 1.0 ([https://creativecommons.org/publicdomain/zero/1.0/](https://creativecommons.org/publicdomain/zero/1.0/)) applies to arXiv descriptive metadata only, defined for the purposes of this governance decision as:

- `title`
- `abstract`
- `authors` (public byline; see Revision 4 for contact-email redaction)
- `base_arxiv_id` and version suffix
- `primary_category` and `all_categories`
- `doi` (when present on the arXiv record)
- `journal_ref` (when present)
- `comment` (when present, used by Revision 3 withdrawal detection)
- `submitted_date`, `updated_date`

**NOT in scope** (explicitly rejected by this registration):
- Full-text PDFs.
- TeX / source archives.
- Figures / images.
- Hosting or serving arXiv e-prints.
- Redistribution of arXiv articles.

Per-paper license tracking: a per-paper license URI may appear on individual arXiv records. The `ArxivMetadataRecord.per_paper_license_uri` field tracks it. **`None` means unknown or unverified; it is NOT a license to redistribute full text.** The source-level CC0 declaration does NOT constitute per-record license verification.

Enforcement:
  - Model: `ArxivMetadataRecord` (metadata-only Pydantic model; distinct from `Achievement`).
  - Validator: `reject_forbidden_content_type(content_type)` raises `ForbiddenContentTypeError` for `application/pdf`, `application/x-tex`, `application/postscript`, tar/gzip/zip archives, and `image/*`.

**No accidental full-text download.** The repository ships no collector yet; this policy is enforced by (a) the content-type rejection function, (b) the model's `extra="forbid"`, (c) the explicit absence of any "download body to disk" code path. Any future collector that attempts to persist a non-metadata content type will trip the validator.

---

## Revision 3 — Preprint status, withdrawals, student attribution

### Preprint classification

Mohan's rule: a record without a VERIFIED DOI or journal reference MUST be classified `unrefereed_preprint`. Presence of a DOI / journal_ref string on the arXiv record is author-asserted and does NOT constitute verification.

Enforcement:
  - Enum: `PeerReviewStatus` with `UNREFEREED_PREPRINT`, `PEER_REVIEWED`, `UNKNOWN`.
  - Function: `assess_peer_review_status(record, *, doi_externally_verified, journal_ref_externally_verified)` — defaults both flags to `False`, so the default classification is `UNREFEREED_PREPRINT`. Promotion to `PEER_REVIEWED` requires the caller to pass `True` for one of the flags AND the record to carry the corresponding field.
  - The function NEVER infers peer-review from arXiv identifier, publication date, title, author list, or abstract.

### Withdrawals

Enforcement:
  - Function: `is_withdrawn(record)` returns `True` when `record.comment` matches a withdrawal pattern (`\bwithdrawn\b`, `\bthis paper has been withdrawn\b`, `\bauthors? withdrew\b`, `\bretract(ed|ion)\b`), case-insensitive.
  - Callers (future collectors / record creators) MUST exclude withdrawn records from eligible ingestion and from linking to student profiles.

### Student attribution gates

Linking an arXiv paper to a student profile requires AT LEAST ONE of:
1. Verified ORCID
2. Verified institutional email
3. Advisor verification

Enforcement:
  - Model: `StudentVerificationEvidence { orcid_verified, institutional_email_verified, advisor_verified }`.
  - Property: `any_accepted` returns `True` iff at least one flag is `True`.
  - Function: `authorize_student_link(record, evidence)` raises `MissingStudentVerificationError` when `any_accepted` is `False`.

**Separation of concerns:**
- Author-identity disambiguation (name → person) is a separate step that runs BEFORE `authorize_student_link`, not within it.
- Student status verification is distinct from authorship verification (Chunk 7.11 Stages B vs C).
- Achievement eligibility is distinct from identity / authorship / student-status checks.
- Name similarity, affiliation strings, and author position are NEVER sufficient on their own to attribute a paper to a student. There is no auto-attribution path in the governance module.

**Evidence provenance:** per-record review status and evidence provenance remain the caller's responsibility (future per-record review workflow). The governance module does not persist or audit evidence; it only enforces the gate.

---

## Revision 4 — Acknowledgment, canonical links, contact privacy

### Acknowledgment

Required display text (constant: `ARXIV_ACKNOWLEDGMENT`):

> Thank you to arXiv for use of its open access interoperability

CC0 1.0 does not legally require attribution. This is a project convention honoring arXiv's own request. The project does NOT claim arXiv endorsement.

### Canonical links

Canonical arXiv abstract-page link helper: `canonical_abs_link(base_arxiv_id)` returns `https://arxiv.org/abs/<id>`.

- The canonical link is for human-facing display only.
- The canonical link MUST NOT be scraped for metadata ingestion. The endpoint-validation function `validate_metadata_endpoint` rejects any `/abs/` URL.

### Contact privacy — email redaction

Enforcement:
  - Function: `redact_contact_emails(text)` returns `text` with email-like substrings replaced by `[REDACTED_EMAIL]`.
  - Callers MUST route log messages, raw payload dumps, exception messages, debug output, and serialized records through `redact_contact_emails` before emission or persistence.
  - Submitter contact emails must not reach the log stream, the error stream, or the staging store.

Useful operational diagnostics (host, HTTP status, record ID, retry counter, rate-limit state) remain emittable; only email-like substrings are redacted.

---

## Not changed by this chunk

- Source `review_status` remains `unreviewed`.
- `license: CC0-1.0` on the source entry is unchanged.
- `collection_date: 2026-10-23` on the source entry is unchanged.
- `lbl_research_pub` taxonomy label remains `draft`.
- `training_ready_subset` behavior unchanged.
- No ingestion / collection code runs.
- No API request is initiated.
- No metadata is downloaded.
- No PDF / TeX / source archive is stored.
- No record is created in `hybrid_dataset/dataset/records/`.
- No annotation is created.
- No student profile is linked.

A new human review is required to decide whether the implementation of Revisions 1-4 satisfies Mohan's revision conditions and whether the source may be promoted.

---

## Related files

| Path | Purpose |
|---|---|
| [`hybrid_dataset/metadata/sources.yaml`](sources.yaml) | Source registry entry (brief pointer to this doc). |
| [`src/nlp_semantic/ingestion/arxiv_governance.py`](../../src/nlp_semantic/ingestion/arxiv_governance.py) | Policy module enforcing Revisions 1-4. |
| [`src/nlp_semantic/ingestion/rate_limit.py`](../../src/nlp_semantic/ingestion/rate_limit.py) | Process-local arXiv rate limiter. |
| [`tests/ingestion/test_arxiv_governance.py`](../../tests/ingestion/test_arxiv_governance.py) | Tests for the policy module. |
| [`tests/ingestion/test_rate_limit.py`](../../tests/ingestion/test_rate_limit.py) | Tests for the rate limiter. |
| [`hybrid_dataset/metadata/SOURCE_REGISTRATION_GUIDE.md`](SOURCE_REGISTRATION_GUIDE.md) | Project-wide source-registration workflow. |
| [`reports/chunk_7_17_arxiv_source_promotion_review_preparation.md`](../../reports/chunk_7_17_arxiv_source_promotion_review_preparation.md) | The source-review packet that preceded this chunk. |
| [`reports/chunk_7_18_arxiv_metadata_governance_revisions.md`](../../reports/chunk_7_18_arxiv_metadata_governance_revisions.md) | Chunk 7.18 implementation report. |
