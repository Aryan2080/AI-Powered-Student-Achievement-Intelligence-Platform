# Chunk 7.19 — Independent Audit of Chunk 7.18 (Read-Only)

**Report type:** independent read-only audit.
**Generated:** 2026-10-24 (session date).
**Audit scope:** verify whether the four mandatory arXiv governance revisions reported in Chunk 7.18 are genuinely satisfied, distinguishing *code exists / tested / integrated / requirement satisfied* for each.

---

## 1. Repository state

| Field | Value |
|---|---|
| Repository root | `C:\Users\Balaji\OneDrive\Desktop\SUPERVISED PROJECT\AI-Powered-Student-Achievement-Intelligence-Platform` |
| Branch | `feature/nlp-semantic` |
| HEAD | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` (unchanged — the Chunk 7.18 report accurately reported this) |
| Remote sync | `## feature/nlp-semantic...origin/feature/nlp-semantic` — in sync (not pushed) |
| Working tree | 1 modified file (`sources.yaml`) + 6 untracked artifacts (3 reports, 1 governance doc, 2 code modules, 2 test modules, and `PROJECT_HANDOFF.md`). See §11. |

**Baseline for Chunk 7.18 changes.** The Chunk 7.18 baseline is HEAD (`c8c1b80`). All Chunk 7.18 additions are either (a) a modification to the uncommitted ` M hybrid_dataset/metadata/sources.yaml` from Chunk 7.15, or (b) new untracked files. The baseline can be established cleanly.

### 1.1 Protected hash verification

| File | Expected | Observed | Match |
|---|---|---|---|
| `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | ✓ |
| `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ✓ |

### 1.2 Chunk 7.18 report existence

[`reports/chunk_7_18_arxiv_metadata_governance_revisions.md`](chunk_7_18_arxiv_metadata_governance_revisions.md) — present, 26,650 bytes.

---

## 2. Files inspected

Read-only inspection (file contents on disk, not Chunk 7.18 summary):

| Path | Size | Role |
|---|---|---|
| `src/nlp_semantic/ingestion/arxiv_governance.py` | 15,175 B | Policy module (Revisions 1-4) |
| `src/nlp_semantic/ingestion/rate_limit.py` | 3,726 B | Process-local rate limiter |
| `tests/ingestion/test_arxiv_governance.py` | 16,679 B | 76 policy-function tests |
| `tests/ingestion/test_rate_limit.py` | 6,351 B | 13 rate-limiter tests |
| `hybrid_dataset/metadata/arxiv_governance_decisions.md` | 10,396 B | Long-form governance doc |
| `hybrid_dataset/metadata/sources.yaml` (modified) | +101 lines vs HEAD | arXiv entry carrying Chunk 7.18 governance pointers |
| `src/nlp_semantic/ingestion/__init__.py` | unchanged | Does NOT export the new governance / rate_limit symbols |
| `src/nlp_semantic/ingestion/registry.py`, `manifest.py`, `inventory.py` | unchanged | Do not call governance / rate_limit |
| `src/nlp_semantic/dataset/*.py` | unchanged | Do not call governance / rate_limit |
| `src/nlp_semantic/schema/*.py` | unchanged | No new Achievement / Annotation fields |

**Integration grep (critical read-only inspection):**

```
$ grep -rn "arxiv_governance\|rate_limit\|ArxivRateLimiter\|validate_metadata_endpoint\|
    authorize_student_link\|is_withdrawn\|assess_peer_review_status\|
    redact_contact_emails\|OFFICIAL_METADATA_ENDPOINTS" src/
# (no results — nothing in src/ imports or calls these symbols
#  other than the two Chunk 7.18 modules themselves)
```

The grep returns **zero** callers outside the two modules themselves. The governance modules are **not** wired into any ingestion / collection / logging / record-creation code path in the repository today.

---

## 3. Implementation findings — overall

The Chunk 7.18 implementation produces **policy-surface modules** (functions, Pydantic models, exceptions, constants) that any future collector MUST route through. The repository has **no collector code today** — Chunk 7.16 was design-only — so none of the policy functions are *invoked* in a data-flow sense.

This is not a bug of Chunk 7.18, but it is the central honest finding of this audit: the four revisions require not only that policy surfaces *exist*, but that they *gate real behavior*. Chunk 7.18 satisfies (a) policy existence + (b) isolated test coverage; it does **not** satisfy (c) integration into live ingestion pathways, because those pathways do not exist yet.

Human reviewers must decide, per revision, whether (a)+(b) is sufficient at this project phase or whether (c) is a prerequisite for `verified` promotion.

Each phase below reports the four-level breakdown:

- **Code exists** — the function/class/constant is present on disk.
- **Code is tested** — a passing test asserts the behavior in isolation.
- **Code is integrated** — some existing non-test caller invokes the function.
- **Requirement satisfied** — the review requirement is enforced by actual data flow.

---

## 4. Phase 2 — Endpoint enforcement

Inspected: `src/nlp_semantic/ingestion/arxiv_governance.py`.

### 4.1 Observed implementation

```python
OFFICIAL_METADATA_ENDPOINTS: Final[dict[str, str]] = {
    "query_api": "https://export.arxiv.org/api/query",
    "oai_pmh":   "https://oaipmh.arxiv.org/oai",
}

def validate_metadata_endpoint(url: str) -> str:
    # ...
    for scrape_prefix in ("/abs", "/pdf", "/src", "/html", "/format"):
        if lower_path.startswith(scrape_prefix):
            raise AbsScrapingProhibitedError(...)
    # whitelist on exact (scheme, hostname, path.rstrip("/")) tuple
    # http: raises EndpointNotAllowedError
```

### 4.2 Findings

| Finding | Code exists | Tested | Integrated | Requirement satisfied | Verdict |
|---|---|---|---|---|---|
| Query API and OAI-PMH endpoints registered as constants | ✓ | ✓ (`test_official_endpoints_whitelist_has_exact_two`) | n/a (constant) | ✓ | **PASS** |
| `/abs/` scraping prohibited | ✓ | ✓ (`test_abs_path_rejected_on_arxiv_host`, `test_abs_path_rejected_on_export_arxiv_host`) | ✗ — no caller | ✗ — no ingestion path to prohibit | **PARTIAL** |
| `/pdf/`, `/src/`, `/html/`, `/format/` prohibited | ✓ | ✓ (one test per prefix) | ✗ | ✗ | **PARTIAL** |
| Non-whitelist endpoints rejected | ✓ | ✓ (`test_non_whitelist_arxiv_host_rejected`, `test_non_arxiv_host_rejected`) | ✗ | ✗ | **PARTIAL** |
| `http://` scheme rejected | ✓ | ✓ (`test_http_scheme_rejected`) | ✗ | ✗ | **PARTIAL** |
| Validation invoked by actual ingestion entry point | ✗ — no caller exists in `src/` | n/a | ✗ | ✗ | **FAIL (integration)** |
| Tests cover bypass attempts | ✓ (`test_scrape_rejection_takes_precedence_over_host_whitelist` covers mixing `/abs/` with non-whitelist host) | ✓ | n/a | n/a | **PASS** |

### 4.3 Phase-2 summary

Endpoint validation works correctly as an **isolated gate** (code + tests). It is **not integrated** anywhere in the repository today. "Arbitrary endpoints can bypass validation" is vacuously true because there is no ingestion code path to bypass; nothing in `src/` currently makes HTTP requests to arXiv. The validator is ready to be wired into any future collector.

---

## 5. Phase 3 — Rate limiter audit

Inspected: `src/nlp_semantic/ingestion/rate_limit.py`.

### 5.1 Observed implementation

```python
MIN_REQUEST_SPACING_SECONDS: Final[float] = 3.0

class ArxivRateLimiter:
    def __init__(self, min_spacing_seconds=3.0, *, clock=time.monotonic,
                 sleeper=time.sleep):
        # rejects min_spacing_seconds < 3.0
        self._lock = threading.Lock()
        self._last_acquire_time = None

    @contextmanager
    def acquire(self):
        self._lock.acquire()
        try:
            # compute deficit; sleep if < 3 s elapsed
            # update self._last_acquire_time
            yield
        finally:
            self._lock.release()
```

### 5.2 Findings

| Finding | Code exists | Tested | Integrated | Requirement satisfied | Verdict |
|---|---|---|---|---|---|
| ≥ 3 seconds between requests within a process | ✓ | ✓ (`test_second_acquire_within_gap_sleeps_remainder`, `test_three_rapid_acquires_each_waits_three_seconds`) | ✗ — no caller | ✗ (process-only; no collector) | **PARTIAL** |
| Single-connection within a process (threads cannot overlap) | ✓ | ✓ (`test_single_connection_lock_serializes_threads`: 4 threads, observed concurrency = 1) | ✗ | ✗ | **PARTIAL** |
| Lock released on exception (safe) | ✓ (try/finally structure confirmed on disk) | ✗ — no test asserts "an exception inside `with lim.acquire()` releases the lock and the next acquire can proceed" | ✗ | ✗ | **PARTIAL — test gap** |
| Correct behavior across multiple instances within one process | ✗ — the limiter stores `_last_acquire_time` on `self`; two separate `ArxivRateLimiter()` instances each have their own clock. Two instances in the same process would run at double the aggregate rate. | ✗ | ✗ | ✗ | **FAIL — single-instance assumption not enforced** |
| Correct behavior across multiple processes | ✗ — `threading.Lock` + `self._last_acquire_time` are per-process. The module docstring explicitly documents this limitation. | ✗ | ✗ | ✗ | **FAIL (per Chunk 7.19 §Phase 3: classify as NOT SATISFIED)** |
| Rate limiter invoked by actual arXiv client | ✗ — no caller in `src/` | n/a | ✗ | ✗ | **FAIL (integration)** |
| Operator-discipline documentation present | ✓ (module docstring + governance doc + `sources.yaml`) | ✓ (`test_module_documents_process_local_limitation`) | n/a | n/a (compensating control, not a code enforcement) | **PASS (as documentation)** |

### 5.3 Phase-3 summary

The rate limiter satisfies the **within-one-process** requirement (3-second gap + single-connection serialization) and releases the lock on exception.

The **global** requirement — "at most one active connection" and "limits apply collectively across all machines" — is **NOT SATISFIED by code**, per the explicit Chunk 7.19 §Phase 3 rule ("If the limiter is process-local, classify the global requirement as NOT SATISFIED unless another existing mechanism guarantees global enforcement"). The repository has no other mechanism (no Redis mutex, no file lock, no DB-backed semaphore). The compensating control is documented operator discipline (single collector, single machine), captured in the module docstring, the governance doc, and `sources.yaml`.

Two additional findings surface from inspection that the Chunk 7.18 report did not explicitly flag:

1. **Multi-instance within one process.** Nothing enforces that only one `ArxivRateLimiter` exists per process. If two `ArxivRateLimiter()` are constructed in the same process (e.g. by two parallel coroutines each creating their own), they will not share the single-connection or 3-sec-gap state. A singleton accessor (e.g. `ArxivRateLimiter.shared()`) is a natural fix; it was contemplated in the module docstring sketch but is NOT implemented.
2. **Exception-safety test gap.** The try/finally structure in `acquire` releases the lock on exception, but no test asserts "an exception raised inside `with lim.acquire(): raise X` leaves the lock free so the next thread can acquire." The behavior is correct by code inspection; no test covers it.

Both are PARTIAL/FAIL findings in the table above.

---

## 6. Phase 4 — Metadata and license enforcement

Inspected: `arxiv_governance.ArxivMetadataRecord`, `reject_forbidden_content_type`.

### 6.1 Findings

| Finding | Code exists | Tested | Integrated | Requirement satisfied | Verdict |
|---|---|---|---|---|---|
| Metadata-only descriptive fields (title, abstract, authors, identifiers, categories, DOI/journal_ref/comment, dates) | ✓ (`ArxivMetadataRecord`) | ✓ | ✗ — no caller constructs these | ✗ — model is staging-only | **PARTIAL** |
| `extra="forbid"` prevents accidental `pdf_url` / `body` / `content` fields | ✓ | ✓ (`test_extra_fields_rejected`) | ✗ | ✗ | **PARTIAL** |
| `per_paper_license_uri: str \| None` tracks per-record license | ✓ | ✓ (`test_per_paper_license_uri_none_is_unknown`, `test_per_paper_license_uri_may_be_set`) | ✗ | ✗ | **PARTIAL** |
| Unknown license cannot silently become approved | ✓ (`None` is explicit UNKNOWN; function docstring + governance doc disclaim CC0 inference) | ✓ | ✗ | ✗ | **PARTIAL** |
| PDF / TeX / source archive / image rejected via `reject_forbidden_content_type` | ✓ (12 content-type prefixes) | ✓ (14 parametrized tests) | ✗ — no caller | ✗ | **PARTIAL** |
| Case-insensitive content-type match (`APPLICATION/PDF`) rejected | ✓ | ✓ (`test_case_insensitive`) | ✗ | ✗ | **PARTIAL** |
| Existing ingestion pathways cannot bypass content-type checks | ✗ — vacuously true (no ingestion exists) | n/a | ✗ | ✗ | **NOT VERIFIED (no code path to test)** |
| No prohibited content via another field or raw payload | ✓ (`ArxivMetadataRecord` has no body/content/url field) | ✓ (`test_extra_fields_rejected`) | ✗ | ✗ | **PARTIAL** |

### 6.2 Phase-4 summary

The staging model and content-type gate are correct in isolation. They are **not connected to actual production ingestion** because no production ingestion exists. The "no accidental full-text download" guarantee today is structural: there is no download path to accidentally include a `pdf_url` field in — because there is no download path.

---

## 7. Phase 5 — Peer review and withdrawal

Inspected: `PeerReviewStatus`, `assess_peer_review_status`, `is_withdrawn`, `_WITHDRAWN_PATTERNS`.

### 7.1 Findings — peer review

| Finding | Code exists | Tested | Integrated | Requirement satisfied | Verdict |
|---|---|---|---|---|---|
| Missing DOI/journal_ref → `UNREFEREED_PREPRINT` | ✓ | ✓ (`test_default_is_unrefereed_preprint`) | ✗ — no caller | ✗ (no record creation to classify) | **PARTIAL** |
| DOI present but unverified → `UNREFEREED_PREPRINT` | ✓ | ✓ (`test_doi_present_but_unverified_still_preprint`) | ✗ | ✗ | **PARTIAL** |
| External verification required to promote to `PEER_REVIEWED` | ✓ (keyword-only `doi_externally_verified` / `journal_ref_externally_verified` flags) | ✓ (`test_doi_verified_promotes_to_peer_reviewed`, `test_journal_ref_verified_promotes_to_peer_reviewed`) | ✗ | ✗ | **PARTIAL — meaning:** the function accepts a boolean flag; it does **not** verify that the DOI is a real DOI or that a journal reference is a real peer-reviewed journal. The caller supplies the verification. The function's "enforceability" is the caller's responsibility. | 
| Verified flag without the corresponding field is still preprint | ✓ | ✓ (`test_verified_flag_without_field_still_preprint`) | ✗ | ✗ | **PARTIAL** |
| Never infers peer review from title / authors / abstract / date | ✓ (function reads only `doi` and `journal_ref` plus explicit flags) | ✓ | ✗ | ✗ | **PARTIAL** |
| Classification invoked by actual record creator | ✗ | n/a | ✗ | ✗ | **FAIL (integration)** |

### 7.2 Findings — withdrawals

| Finding | Code exists | Tested | Integrated | Requirement satisfied | Verdict |
|---|---|---|---|---|---|
| Patterns: `\bwithdrawn\b`, `\bthis paper has been withdrawn\b`, `\bauthors? withdrew\b`, `\bretract(?:ed\|ion)\b` | ✓ | ✓ (9 tests covering positives, negatives, case variants, None) | ✗ — no caller | ✗ (no ingestion to exclude from) | **PARTIAL** |
| Case-insensitive | ✓ | ✓ (`test_case_insensitive`) | ✗ | ✗ | **PARTIAL** |
| Empty / None comment → not withdrawn | ✓ | ✓ | ✗ | ✗ | **PARTIAL** |
| Withdrawn record cannot proceed into eligible linking | ✗ — enforcement is caller-responsibility; no caller | ✗ | ✗ | ✗ | **FAIL (integration)** |

### 7.3 Phase-5 summary — false-positive / false-negative risks

- **False positives.** The pattern `\bwithdrawn\b` would match a sentence like `"This paper responds to a withdrawn claim in Smith et al."` — comment text about *someone else's* withdrawal. Risk: medium. Mitigation: downstream reviewer rechecks a flagged withdrawal; `is_withdrawn` is a *signal* not a decision.
- **False negatives.** The patterns do NOT match:
  - obfuscated phrasings (`"w/d by authors"`, `"paper rescinded"`, `"no longer available"`),
  - withdrawals signaled by metadata flags OUTSIDE the `comment` field (e.g. the arXiv API's "withdrawn" status flag on the paper itself, which is a different data point),
  - withdrawals in non-English comments.
  Risk: medium. Mitigation: downstream reviewer rechecks; the governance doc explicitly says `is_withdrawn` is a positive signal, not a proof.

The function is honest about its scope. The patterns are useful but not exhaustive; the governance doc and docstring both make this explicit. Both risks are PARTIAL findings.

---

## 8. Phase 6 — Student attribution

Inspected: `StudentVerificationEvidence`, `authorize_student_link`.

### 8.1 Findings

| Finding | Code exists | Tested | Integrated | Requirement satisfied | Verdict |
|---|---|---|---|---|---|
| At least one of (`orcid_verified`, `institutional_email_verified`, `advisor_verified`) required | ✓ (`authorize_student_link` raises `MissingStudentVerificationError` when `evidence.any_accepted` is False) | ✓ (`test_all_three_false_rejects`, plus one test per True path) | ✗ — no caller | ✗ | **PARTIAL** |
| ORCID evidence actually verified | ✗ — the function accepts `orcid_verified: bool` from the caller; it does NOT itself verify the ORCID against ORCID.org, check revocation, or confirm the ORCID resolves to a real identity | ✗ (not tested because the module does not perform this verification) | ✗ | **The requirement "ORCID evidence is actually verified" is caller-responsibility; the governance module takes the caller's word. This is honest in the docstring.** | **PARTIAL — upstream responsibility** |
| Institutional email actually verified | ✗ — same pattern: caller supplies a boolean | ✗ | ✗ | **PARTIAL — upstream responsibility** |
| Advisor verification traceable | ✗ — `advisor_verified: bool` has no traceability field (no advisor name, no sign-off date). The function does not force the caller to record provenance. | ✗ | ✗ | **PARTIAL — traceability lives OUTSIDE the governance module (e.g. in the reviewer PR comments per the Chunk 7.17 §5.5 sign-off block)** |
| Populated-but-unverified field cannot authorize | ✓ (only `True` on at least one of the three flags passes; a `False` or default is rejected) | ✓ (`test_all_three_false_rejects` exercises the default/False state) | ✗ | ✗ | **PARTIAL** |
| Name similarity cannot bypass | ✓ (no name-similarity path exists in the module; the test `test_no_name_similarity_shortcut_exists` asserts the module has no `auto_attribute` / `attribute_by_name` / `name_match_attribute` / `guess_student` / `match_student` public symbols) | ✓ | ✗ (vacuously — no attribution code exists at all) | ✗ (no caller to bypass with) | **PASS — structurally safe** |
| Author identity vs. student status vs. achievement eligibility kept separate | ✓ (module docstring + governance doc explicitly separate the three) | ✓ (the three flags are each a boolean on `StudentVerificationEvidence`; there is no joint "student_and_author_verified" shortcut) | ✗ | ✗ | **PARTIAL** |
| Enforcement path tested | The test exercises the gate function in isolation. There is no *end-to-end* enforcement test ("constructor builds an achievement from an arXiv record and refuses when evidence is missing") because the end-to-end path does not exist. | ✓ (isolated) / ✗ (end-to-end) | ✗ | ✗ | **PARTIAL** |

### 8.2 Phase-6 summary

The gate is correct and structurally safe (no name-similarity bypass path exists). The honest limitation: the module **takes the caller's word** that the three verification flags are actually true. External verification pipelines (ORCID validation, SMTP institutional-email challenge, advisor sign-off record) are upstream project responsibilities; the module is the enforcement **gate**, not the **verifier**. The Chunk 7.18 module docstrings and the governance doc are explicit about this.

---

## 9. Phase 7 — Privacy and presentation

Inspected: `ARXIV_ACKNOWLEDGMENT`, `canonical_abs_link`, `redact_contact_emails`, `_EMAIL_RE`.

### 9.1 Findings

| Finding | Code exists | Tested | Integrated | Requirement satisfied | Verdict |
|---|---|---|---|---|---|
| Required acknowledgment text exact | ✓ (`ARXIV_ACKNOWLEDGMENT = "Thank you to arXiv for use of its open access interoperability"`) | ✓ (`test_acknowledgment_text_matches_review`) | ✗ — no caller displays it anywhere | ✗ — no UI / README / log emits this | **PARTIAL** |
| Does not claim arXiv endorsement | ✓ | ✓ (`test_acknowledgment_does_not_claim_endorsement`) | n/a | n/a | **PASS** |
| Canonical abstract links constructed safely | ✓ (`canonical_abs_link` validates the ID against `_BASE_ARXIV_ID_RE` and returns `https://arxiv.org/abs/<id>`) | ✓ (new-style and old-style IDs; malformed rejected) | ✗ — no caller renders links | ✗ | **PARTIAL** |
| Canonical link is display-only, not a metadata endpoint | ✓ (passing a canonical link to `validate_metadata_endpoint` raises `AbsScrapingProhibitedError`) | ✓ (`test_canonical_link_is_display_only_not_metadata_endpoint`) | ✗ | ✗ | **PARTIAL** |
| Submitter contact emails stripped from logs | ✓ (`redact_contact_emails` substitutes `[REDACTED_EMAIL]`) | ✓ (6 tests covering single/multiple emails, empty, non-email, exception messages, debug payload dumps) | ✗ — **no logger exists in `src/`.** `grep -rln "logger\.\|logging\.getLogger"` on `src/` returns nothing. There is no logging pathway to integrate `redact_contact_emails` into. | ✗ | **FAIL — integration (no logger exists), PARTIAL otherwise** |
| Exceptions / debug output do not expose raw emails | ✓ (tested on representative strings) | ✓ | ✗ — same reason | ✗ | **FAIL — integration** |
| Obfuscated emails (`foo [at] example [dot] com`) redacted | ✗ — the regex is `[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}`; obfuscations are not matched | ✗ (not tested) | ✗ | ✗ | **PARTIAL — documented limitation; see Chunk 7.18 report §8 L7** |

### 9.2 Phase-7 summary

The three primitives are correct in isolation. **None are wired into any emission pathway because no emission pathway exists in `src/` today.** The repository has no logger. The acknowledgment is a constant that no UI or report currently prints. The canonical-link helper has no caller. These are policy surfaces awaiting a future user of them.

---

## 10. Phase 8 — Registry and governance consistency

Inspected: `hybrid_dataset/metadata/sources.yaml`, `hybrid_dataset/metadata/arxiv_governance_decisions.md`.

### 10.1 Findings

| Finding | Status | Evidence |
|---|---|---|
| arXiv source remains `unreviewed` | ✓ Confirmed | Live `load_and_validate_sources` returns `review_status='unreviewed'`; `src_08ee850ba4b54d1b81cdbd652809b613` appears in `unverified_source_ids`. |
| No fabricated approval or promotion | ✓ Confirmed | Review-status field is literally `unreviewed`; no reviewer pseudonym, date, or signature appears in the registry entry. |
| `usage_restrictions` accurately describes implemented protections | **PARTIAL** | The text says `"Enforcement (process-local; operator discipline required for cross-process): src/nlp_semantic/ingestion/rate_limit.py."` — honest about process-local scope. The text also says `"HTML scraping of /abs, /pdf, /src, /html, /format on any arXiv host is PROHIBITED (Chunk 7.18 Rev 1)"` — the validator exists but there is no ingestion pathway today to actually prohibit. The language says "PROHIBITED" (declarative), which could be read as "enforced by the system" when in fact the enforcement is a policy surface waiting for a caller. **A sharper phrasing would be "WILL BE PROHIBITED by any future ingestion that routes through `validate_metadata_endpoint`"** — but the governance doc clarifies this at length. Borderline. |
| Registry text does not claim enforcement that the code does not provide | **PARTIAL** | Mostly accurate (rate limit is honestly labeled process-local). The `/abs/` "PROHIBITED" wording and the `redact_contact_emails` reference could be read as end-to-end enforcement rather than policy-surface-only. The governance doc softens this but a strict reader could call this out. |
| SIH entry untouched | ✓ Confirmed | SIH entry (`src_5a8a2998d6f44055a42dcfd8991e4d12`) unchanged: `license=UNKNOWN`, `review_status=unreviewed`, `usage_restrictions`-length 985, `mapping_notes`-length 1786 — identical to the pre-Chunk-7.18 state. |
| Governance decisions document preserves Ashok APPROVE + Mohan REVISE outcomes | ✓ Confirmed | `arxiv_governance_decisions.md` §Governance origin: `"Chunk 7.17 human source review — Ashok (approve, metadata-only CC0 1.0); Mohan (revise — approval conditional on the revisions implemented below)."` Verbatim match for Ashok's "approve" and Mohan's "revise". |
| Governance doc preserves "implementation ≠ approval" | ✓ Confirmed | Opening paragraph: `"Implementation does NOT equal approval. The source remains unreviewed until a new human review decides..."` |

### 10.2 Phase-8 summary

Governance text is accurate on the governance-decision-recording axis (Ashok/Mohan preserved; no promotion fabricated; source stays `unreviewed`). It is **borderline** on the enforcement-claim axis: the `sources.yaml` wording uses "PROHIBITED" and declarative references to module functions in a way that a strict reader could interpret as end-to-end enforcement. The governance doc softens this with a long "policy surface" framing, and the Chunk 7.18 report §8 explicitly flags "L1 — rate limiter is process-local." A follow-up revision could sharpen the `sources.yaml` wording to say "ENFORCED BY policy module when invoked" rather than bare "PROHIBITED"; this is a cosmetic correctness improvement, not a safety-critical gap.

---

## 11. Phase 9 — Test verification

Tests re-executed in this chunk (read-only — no files created or modified; pytest produces no persistent artifacts beyond `__pycache__/`, which already exists).

### 11.1 Commands and results

| Command | Passed | Failed | Skipped | Collection errors | Completed |
|---|---|---|---|---|---|
| `python -m pytest tests/ingestion/test_arxiv_governance.py tests/ingestion/test_rate_limit.py --tb=short` | **89** | 0 | 0 | 0 | **Yes** |
| `python -m pytest tests/ingestion/ --tb=short` | **164** | 0 | 4 | 0 | **Yes** |
| `python -m pytest tests/schema/ tests/ingestion/ tests/test_smoke.py --tb=short` | **398** | 0 | 4 | 0 | **Yes** |
| `python -m pytest tests/dataset/ --tb=line` | 0 | 0 | 0 | **3** | **No — collection interrupted** |

All numbers **match the Chunk 7.18 report exactly**: 89 new tests, 164 ingestion, 398 schema+ingestion+smoke. The dataset collection error remains and **has not been resolved** (and this chunk did not touch it, per the read-only mandate).

### 11.2 Coverage breadth assessment

The 89 new tests exercise the policy functions in isolation thoroughly. **They do not exercise end-to-end integration** (i.e. "an ingestion collector routes through `validate_metadata_endpoint` + `ArxivRateLimiter` + `reject_forbidden_content_type` + `authorize_student_link` + `redact_contact_emails` and refuses a forbidden path end-to-end"). An integration test would require the collector to exist, which it does not.

### 11.3 Specific test gaps identified

1. **Rate-limiter exception-safety test gap** (§5.2 finding). No test asserts that an exception inside `with lim.acquire(): raise X` releases the lock. The code is correct by inspection (`try/finally`); the test is missing.
2. **Multi-instance rate-limiter test gap.** No test confirms the limiter's single-instance assumption, i.e. that two `ArxivRateLimiter()` instances in the same process would double the aggregate rate. The behavior exists but is not explicitly covered.
3. **End-to-end integration tests** — not applicable today (nothing to integrate with). Would become required when a collector lands.

---

## 12. Findings categorized

### 12.1 PASS (correctly implemented AND no integration requirement implicated)

- Protected file hashes unchanged.
- Chunk 7.18 report accurately records what was built and what remains limited.
- Ashok APPROVE and Mohan REVISE outcomes preserved verbatim in the governance doc.
- Source review status is `unreviewed`; no promotion was fabricated.
- `ARXIV_ACKNOWLEDGMENT` text matches the review-approved string.
- No name-similarity automatic-attribution path exists in the governance module (`test_no_name_similarity_shortcut_exists`).
- All 89 new tests pass; 164 ingestion tests pass; 398 schema+ingestion+smoke pass. Verified independently.

### 12.2 PARTIAL (correctly implemented in isolation; integration pending)

- Endpoint validation (works; no caller).
- `/abs/`, `/pdf/`, `/src/`, `/html/`, `/format/` prohibition (works; no caller).
- Rate limiter 3-second gap AND single-connection WITHIN A PROCESS (works; no caller).
- `ArxivMetadataRecord` + `extra="forbid"` + `per_paper_license_uri` None-as-UNKNOWN (works; no caller).
- Forbidden content-type rejection — PDF / TeX / archives / images (works; no caller).
- Peer-review classification default-preprint-unless-externally-verified (works; no caller; external verification is caller-supplied boolean).
- Withdrawal regex (works; no caller; false-positive and false-negative risks documented).
- `authorize_student_link` gate (works; no caller; the three evidence flags are caller-supplied booleans — module does NOT verify the flags themselves).
- `canonical_abs_link` (works; no caller displays).
- `redact_contact_emails` (works; no logger exists to integrate it into).
- `sources.yaml` governance pointer text: accurate on the governance-decision axis; borderline on the enforcement-claim axis.

### 12.3 FAIL (per the Chunk 7.19 §Phase 3 explicit rule)

- **Global (cross-process / cross-machine) rate-limit guarantee.** The limiter is process-local by design. No shared coordinator exists in the repository. The compensating control is documented operator discipline. Per the Chunk 7.19 instruction ("If the limiter is process-local, classify the global requirement as NOT SATISFIED unless another existing mechanism guarantees global enforcement") this is a FAIL on the global-scope requirement.
- **Integration of all policy surfaces into ingestion / collection / logging pathways.** Zero callers exist in `src/` outside the two Chunk 7.18 modules themselves. This is a FAIL on the "integrated" column for every revision — but it is a FAIL because the collector does not exist, not because the policy module is wrong.
- **Multi-instance safety within one process.** Not technically enforced; a naive caller instantiating two `ArxivRateLimiter()` would halve the per-connection gap.

### 12.4 NOT VERIFIED

- Any claim that arXiv's current (today's) API responses, endpoint URLs, pagination, and error semantics match the hard-coded whitelist and the module's assumptions. This chunk performed no network requests. The whitelist is derived from the Chunk 7.14 human verification; it has not been re-verified in Chunk 7.19.

### 12.5 Exact file paths and symbols

| Finding | Path | Symbol(s) |
|---|---|---|
| Endpoints | `src/nlp_semantic/ingestion/arxiv_governance.py` | `OFFICIAL_METADATA_ENDPOINTS`, `validate_metadata_endpoint`, `AbsScrapingProhibitedError`, `EndpointNotAllowedError` |
| Rate limiter | `src/nlp_semantic/ingestion/rate_limit.py` | `MIN_REQUEST_SPACING_SECONDS`, `ArxivRateLimiter`, `acquire` |
| Metadata record | `src/nlp_semantic/ingestion/arxiv_governance.py` | `ArxivMetadataRecord`, `_BASE_ARXIV_ID_RE`, `ARXIV_SOURCE_ID` |
| Content-type gate | `src/nlp_semantic/ingestion/arxiv_governance.py` | `reject_forbidden_content_type`, `ForbiddenContentTypeError`, `_FORBIDDEN_CONTENT_PREFIXES` |
| Peer review | `src/nlp_semantic/ingestion/arxiv_governance.py` | `PeerReviewStatus`, `assess_peer_review_status` |
| Withdrawals | `src/nlp_semantic/ingestion/arxiv_governance.py` | `is_withdrawn`, `_WITHDRAWN_PATTERNS` |
| Student link | `src/nlp_semantic/ingestion/arxiv_governance.py` | `StudentVerificationEvidence`, `authorize_student_link`, `MissingStudentVerificationError` |
| Acknowledgment / canonical / redaction | `src/nlp_semantic/ingestion/arxiv_governance.py` | `ARXIV_ACKNOWLEDGMENT`, `canonical_abs_link`, `redact_contact_emails`, `_EMAIL_RE` |
| Governance registry | `hybrid_dataset/metadata/sources.yaml` | arXiv source entry (lines 96-end) |
| Governance doc | `hybrid_dataset/metadata/arxiv_governance_decisions.md` | all |

---

## 13. Remaining blockers

Blockers to the human reviewers' promotion decision (ordered by impact):

| # | Blocker | Severity | Required action |
|---|---|---|---|
| B1 | Rate limiter is process-local; global rate guarantee rests on operator discipline alone. The Chunk 7.19 instruction classifies this as NOT SATISFIED. | **HIGH if reviewers require code-level global enforcement.** Can be satisfied by (a) committing to single-process / single-machine operation as policy, OR (b) adding a shared coordinator (file lock, Redis mutex) in a future chunk. | Reviewer decision + possible future implementation chunk. |
| B2 | No ingestion / collection / logger pathway exists in the repository. All policy surfaces are uncalled today. | **HIGH if reviewers require end-to-end enforcement.** LOW if reviewers accept "policy surfaces ready for a future collector." | Reviewer decision; the Chunk 7.16 design describes the future collector but it is not implemented. |
| B3 | `ArxivRateLimiter` does not enforce single-instance per process. Two instances in the same process would not share state. | **MEDIUM.** | Future minor refactor (add `.shared()` singleton + factory enforcement). |
| B4 | Rate limiter exception-safety behavior is correct by code inspection but not covered by an explicit test. | **LOW.** | Future one-line test addition. |
| B5 | Withdrawal regex is heuristic; false negatives possible on obfuscated / non-English phrasings; no coverage for arXiv's own "withdrawn" status flag outside `comment`. | **LOW-MEDIUM depending on tolerance.** | Future refinement; the governance doc already labels this as a positive-signal-only function. |
| B6 | `authorize_student_link` takes caller-supplied booleans and does not itself verify ORCID / institutional email / advisor sign-off. | **LOW.** The honest division of responsibility is correct; external verification is explicitly out-of-scope for the gate function. | None required — this is architecturally correct separation. Reviewers must confirm they accept the "the module gates; the caller verifies" split. |
| B7 | `sources.yaml` wording uses "PROHIBITED" declaratively, which could be read as end-to-end enforcement despite the governance doc's softer "policy surface" framing. | **LOW (cosmetic).** | Future small text revision in `usage_restrictions`. |
| B8 | Pre-existing `tests/dataset/` collection error. Unresolved. Not Chunk-7.18-caused. | **LOW** (does not affect Chunk 7.18 verification). | Separate narrow chunk (e.g. add `tests/__init__.py` or update `pyproject.toml` pythonpath). |

---

## 14. Recommended next action

**Implementation appears ready for human review**, with the following clarifications the reviewers must weigh:

1. **Policy-surface vs. end-to-end interpretation.** The reviewers must decide whether Mohan's four revisions require (a) policy surfaces (functions, constants, exceptions, Pydantic models) ready to be used by any future collector, OR (b) end-to-end enforcement in a working collector. Chunk 7.18 delivers (a) rigorously; (b) is not possible without a collector, and no collector is in scope for the Chunk 7.17 / 7.18 arc.
2. **Rate-limit global requirement.** If the reviewers require code-level global rate enforcement (across processes / machines), Chunk 7.18 does **not** satisfy that; a shared coordinator in a future chunk would be required. If the reviewers accept operator discipline (one process, one machine) as the compensating control, Chunk 7.18 satisfies Revision 1 at the policy-surface level.
3. **Multi-instance limiter + exception-safety test** are small follow-up items (B3, B4) that could land before promotion or be deferred as low-severity follow-ups.
4. **Cosmetic text correction** on `sources.yaml` enforcement-claim phrasing (B7) is deferrable.

The source MUST remain `unreviewed` until two independent human reviewers decide, using the Chunk 7.17 §5.5 sign-off template, whether these revisions satisfy Mohan's `revise` conditions.

---

## 15. Final governance decision (NOT made in this chunk)

**Audit conclusion:** `Implementation appears ready for human review.`

The source **remains `unreviewed`**. This chunk does **not** promote the source, does **not** approve the source, and does **not** make a promotion decision on the human reviewers' behalf. Ashok's `approve` and Mohan's `revise` are preserved; no new reviewer identities, dates, or decisions were created.

---

## 16. Final `git status`

```
## feature/nlp-semantic...origin/feature/nlp-semantic
 M hybrid_dataset/metadata/sources.yaml
?? PROJECT_HANDOFF.md
?? hybrid_dataset/metadata/arxiv_governance_decisions.md
?? reports/
?? src/nlp_semantic/ingestion/arxiv_governance.py
?? src/nlp_semantic/ingestion/rate_limit.py
?? tests/ingestion/test_arxiv_governance.py
?? tests/ingestion/test_rate_limit.py
```

Chunk 7.19 added ONE new file to the working tree: this audit report at `reports/chunk_7_19_arxiv_governance_implementation_audit.md`. No other file was created, modified, deleted, or renamed.

---

## 17. Safety confirmation

- No file modified ✓
- No file created (except this audit report, which Chunk 7.19 §Phase 10 instructed) ✓
- No file deleted or renamed ✓
- No stage, no commit, no push, no branch switch ✓
- No network / API request ✓
- No metadata collected or downloaded ✓
- Source `review_status` unchanged (`unreviewed`) ✓
- No fabricated reviewer identity, date, decision, or approval ✓
- Teammate directories (`src/ml`, `src/recommender`, `src/backend`) not touched (none exist) ✓
- Protected file hashes unchanged ✓
- Existing user changes (` M hybrid_dataset/metadata/sources.yaml` from Chunks 7.15 + 7.18) preserved ✓
- Pre-existing `tests/dataset/` collection error not silently fixed; status reported honestly ✓
- Chunk 7.4-D reviewer-independence stop preserved ✓
