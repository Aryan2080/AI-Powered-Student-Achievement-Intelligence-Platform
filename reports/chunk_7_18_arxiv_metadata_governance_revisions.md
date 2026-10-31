# Chunk 7.18 — arXiv Metadata Governance Revisions (Implementation)

**Report type:** implementation report. Mohan's four mandatory governance revisions.
**Generated:** 2026-10-24 (session date; the arXiv source entry's `collection_date` remains `2026-10-23`).
**Final governance status:** `UNREVIEWED — IMPLEMENTATION COMPLETE, PENDING NEW HUMAN REVIEW.`

> Implementation does NOT equal approval. Ashok approved metadata-only use under CC0 1.0; Mohan returned `revise`. These revisions implement Mohan's conditions. A new human review must inspect this implementation and explicitly decide whether the source may be promoted to `verified`.

---

## 1. Repository state

### 1.1 Starting state (verified at chunk start)

| Field | Value |
|---|---|
| Branch | `feature/nlp-semantic` |
| HEAD | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` |
| Working tree before | ` M hybrid_dataset/metadata/sources.yaml` (Chunk 7.15 arXiv registration, uncommitted); `?? PROJECT_HANDOFF.md`; `?? reports/` (Chunks 7.16, 7.17 reports) |

### 1.2 Final state

| Field | Value |
|---|---|
| Branch | `feature/nlp-semantic` (unchanged) |
| HEAD | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` (unchanged — no commit) |
| Working tree after | ` M hybrid_dataset/metadata/sources.yaml` (updated with Chunk 7.18 governance pointers); `?? PROJECT_HANDOFF.md`; `?? hybrid_dataset/metadata/arxiv_governance_decisions.md`; `?? reports/`; `?? src/nlp_semantic/ingestion/arxiv_governance.py`; `?? src/nlp_semantic/ingestion/rate_limit.py`; `?? tests/ingestion/test_arxiv_governance.py`; `?? tests/ingestion/test_rate_limit.py` |
| Remote sync | in sync (no push) |

---

## 2. Files inspected

Read-only inspection during Phase 1 (and prior chunks' already-loaded context):

- `hybrid_dataset/metadata/sources.yaml` (post-Chunk 7.15 state).
- `hybrid_dataset/metadata/SOURCE_REGISTRATION_GUIDE.md`.
- `hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md`.
- `src/nlp_semantic/schema/source_registry.py` (field constraints, 2000-char caps).
- `src/nlp_semantic/schema/achievement.py` (confirmed no new fields added here).
- `src/nlp_semantic/schema/annotation.py`.
- `src/nlp_semantic/schema/enums.py`.
- `src/nlp_semantic/schema/label_taxonomy.py`.
- `src/nlp_semantic/schema/evidence.py` (confirmed Evidence is for raw/evidence_documents only).
- `src/nlp_semantic/schema/path_safety.py`.
- `src/nlp_semantic/ingestion/__init__.py` (lazy `__getattr__` pattern).
- `src/nlp_semantic/ingestion/registry.py`.
- `src/nlp_semantic/ingestion/manifest.py`.
- `src/nlp_semantic/ingestion/inventory.py`.
- `src/nlp_semantic/dataset/validator.py` (`training_ready_subset` gate).
- `src/nlp_semantic/dataset/loader.py`, `splits.py`.
- `tests/ingestion/__init__.py`, `tests/ingestion/test_registry.py`, `test_manifest.py`.
- `reports/chunk_7_17_arxiv_source_promotion_review_preparation.md`.
- `reports/chunk_7_16_arxiv_metadata_collection_design.md`.
- The human-review PDF (`arXiv_Source_Governance_Review_Ashok_Mohan.pdf`) was named in the prompt but is **not present on disk** anywhere under `SUPERVISED PROJECT/`. Implementation proceeded against the review outcomes as summarized in the chunk prompt (Ashok approve / Mohan revise + four mandatory revisions). This is noted as a provenance limitation; a new human reviewer should still be able to confirm the implementation matches the PDF they hold.

---

## 3. Files changed and why

| Path | Action | Reason |
|---|---|---|
| [`src/nlp_semantic/ingestion/arxiv_governance.py`](../src/nlp_semantic/ingestion/arxiv_governance.py) | **CREATED** | Policy module implementing Revisions 1-4 as reusable functions, exceptions, and Pydantic models. Pure policy — no I/O, no network. |
| [`src/nlp_semantic/ingestion/rate_limit.py`](../src/nlp_semantic/ingestion/rate_limit.py) | **CREATED** | `ArxivRateLimiter` enforcing 1 request / 3 s + single-connection semantics for one Python process. Process-local; operator discipline required for cross-process. |
| [`hybrid_dataset/metadata/arxiv_governance_decisions.md`](../hybrid_dataset/metadata/arxiv_governance_decisions.md) | **CREATED** | Long-form governance document that `sources.yaml` cannot carry (2000-char field cap). Documents every revision and the enforcement module location. |
| [`hybrid_dataset/metadata/sources.yaml`](../hybrid_dataset/metadata/sources.yaml) | **MODIFIED** | arXiv entry's `usage_restrictions` and `mapping_notes` compressed and extended with Chunk 7.18 governance pointers (endpoints, scraping prohibition, acknowledgment, student-link gate, preprint rule, withdrawals, per-paper license handling). Within 2000-char cap. |
| [`tests/ingestion/test_arxiv_governance.py`](../tests/ingestion/test_arxiv_governance.py) | **CREATED** | 76 tests covering Revisions 1-4 policy functions. |
| [`tests/ingestion/test_rate_limit.py`](../tests/ingestion/test_rate_limit.py) | **CREATED** | 13 tests covering construction, pacing, and concurrency serialization. |

**NOT changed** (deliberately):
- `src/ml`, `src/recommender`, `src/backend` — do not exist; not created.
- `PROJECT_HANDOFF.md` — untracked and byte-for-byte preserved.
- `hybrid_dataset/raw/.gitkeep` — byte-for-byte preserved.
- All existing Pydantic models (`Achievement`, `Annotation`, `SourceRegistry`, `LabelTaxonomy`, `Evidence`, `ManifestEntry`) — not modified. The new `ArxivMetadataRecord` lives in the governance module as a staging-only Pydantic model that is distinct from `Achievement`.
- Taxonomy YAMLs (`primary_taxonomy.yaml`, `domain_tags.yaml`) — not modified.
- `pyproject.toml`, `tests/__init__.py`, installed Python packages — not modified (Phase 3 would have required this to resolve the pre-existing `tests/dataset/` collection error; out of scope).
- `src/nlp_semantic/ingestion/__init__.py` — not modified. New modules are importable directly as `nlp_semantic.ingestion.arxiv_governance` and `nlp_semantic.ingestion.rate_limit`; adding them to the lazy `__getattr__` registry would be a cosmetic addition that this chunk's scope does not justify.
- No records, annotations, splits, taxonomy promotions, source promotions, or review-status changes.

---

## 4. Review requirements — implementation status

### 4.1 Revision 1 — Official API endpoints and rate limiting

| Requirement | Status | Evidence |
|---|---|---|
| Register `https://export.arxiv.org/api/query` | ✓ Implemented | `arxiv_governance.OFFICIAL_METADATA_ENDPOINTS["query_api"]`; also captured in `sources.yaml` `usage_restrictions` block. |
| Register `https://oaipmh.arxiv.org/oai` | ✓ Implemented | `arxiv_governance.OFFICIAL_METADATA_ENDPOINTS["oai_pmh"]`; `sources.yaml`. |
| Use the existing source registry and conventions | ✓ Done | `sources.yaml` modified in place; no schema change required. |
| Prohibit `/abs/` HTML scraping for metadata ingestion | ✓ Implemented | `validate_metadata_endpoint` raises `AbsScrapingProhibitedError` for `/abs/`, `/pdf/`, `/src/`, `/html/`, `/format/` on any host. |
| At most one active connection | ✓ Implemented (process-local) | `ArxivRateLimiter` uses `threading.Lock`; `acquire()` is strictly serializing within one process. Verified by `TestRateLimiterConcurrency::test_single_connection_lock_serializes_threads` (max concurrent holders = 1 observed over 4 threads). |
| At least 3 seconds between requests | ✓ Implemented | `MIN_REQUEST_SPACING_SECONDS = 3.0`; `ArxivRateLimiter.acquire` sleeps for the deficit. Verified by `test_second_acquire_within_gap_sleeps_remainder` and `test_three_rapid_acquires_each_waits_three_seconds`. |
| Limits shared across workers/processes where supported | **DOCUMENTED LIMITATION** | The repository has no shared coordinator (Redis / DB / file-lock service). The limiter is PROCESS-LOCAL by design, with the limitation documented in the module docstring and in `arxiv_governance_decisions.md` §Revision 1. **Compensating control:** operator discipline — exactly one collector process on one machine at a time. Verified by `test_module_documents_process_local_limitation`. |
| Do not assume process-local satisfies global | ✓ Explicit | The module docstring, `arxiv_governance_decisions.md`, and `sources.yaml` all state the limiter is process-local and that cross-process compliance is operator discipline. |
| Tests for endpoint registration, prohibited scraping, concurrency, request spacing | ✓ Implemented | 15 endpoint-validation tests + 13 rate-limit tests. |
| No live API requests during this task | ✓ Satisfied | Zero network calls made in this chunk. |

### 4.2 Revision 2 — Metadata license and content restrictions

| Requirement | Status | Evidence |
|---|---|---|
| Identify permitted descriptive metadata fields | ✓ Done | `arxiv_governance_decisions.md` §Revision 2 lists them; `ArxivMetadataRecord` captures them as model fields. |
| Track applicable license URI at the individual-record level | ✓ Implemented | `ArxivMetadataRecord.per_paper_license_uri: str | None`. Verified by `test_per_paper_license_uri_none_is_unknown` and `test_per_paper_license_uri_may_be_set`. |
| Prohibit PDF / TeX / full-text storage | ✓ Implemented | `reject_forbidden_content_type` raises `ForbiddenContentTypeError` for `application/pdf`, `application/x-tex`, `application/x-latex`, `application/postscript`, tar/gzip/bzip2/zip archives, and `image/*`. Verified by 12 parametrized tests. |
| Source-level CC0 ≠ per-record license verification | ✓ Explicit | `per_paper_license_uri = None` is the explicit UNKNOWN state; module docstring and `arxiv_governance_decisions.md` state that `None` does NOT infer CC0 for the full-text. |
| Preserve explicit unknown state when license absent | ✓ Implemented | `None` is the UNKNOWN sentinel; never auto-filled. |
| Tests for allowed fields, record-level license, missing license, PDF/TeX/full-text rejection, no accidental full-text download | ✓ Implemented | `TestArxivMetadataRecord` (8 tests) + `TestForbiddenContentType` (14 tests). The "no accidental full-text download" guarantee is structural: the repository has no download path, and the only recognized metadata record model (`ArxivMetadataRecord`) is `extra="forbid"` with no `pdf_url`/`body`/`content` field — tested by `test_extra_fields_rejected`. |

### 4.3 Revision 3 — Preprint status, withdrawals, student attribution

| Requirement | Status | Evidence |
|---|---|---|
| Records without verified DOI/journal_ref → `unrefereed_preprint` | ✓ Implemented | `assess_peer_review_status` defaults both verification flags to `False`; the default classification is `UNREFEREED_PREPRINT`. Verified by `test_default_is_unrefereed_preprint`, `test_doi_present_but_unverified_still_preprint`, `test_journal_ref_present_but_unverified_still_preprint`. |
| Parse comments for withdrawals | ✓ Implemented | `is_withdrawn(record)` matches `\bwithdrawn\b`, `\bthis paper has been withdrawn\b`, `\bauthors? withdrew\b`, `\bretract(ed|ion)\b` (case-insensitive). Verified by 9 tests covering positives, negatives, case variants, and None. |
| Exclude withdrawn papers from eligible ingestion/linking | ✓ Policy; **not implementation-enforced here** | `is_withdrawn` is the signal function; any future collector must gate on it before promoting a record. Documented in `arxiv_governance_decisions.md`. No ingestion code exists today, so there is nothing additional to wire. |
| Never infer peer review from arXiv id, date, title, authors, abstract | ✓ Enforced | `assess_peer_review_status` only reads `doi` and `journal_ref` on the record plus externally supplied verification flags. Verified by `test_verified_flag_without_field_still_preprint`. |
| Require at least one of (ORCID, institutional email, advisor) before linking to student | ✓ Implemented | `authorize_student_link(record, evidence)` raises `MissingStudentVerificationError` unless `evidence.any_accepted`. Verified by 6 tests covering all-false and each individual True path. |
| Keep author-identity disambiguation separate from student status / achievement eligibility | ✓ Explicit | Module docstring and `arxiv_governance_decisions.md` §Revision 3 both state: disambiguation runs BEFORE `authorize_student_link`, not within it. |
| Do not auto-assign student profiles based on name similarity | ✓ Enforced structurally | No auto-attribution function exists. Verified by `test_no_name_similarity_shortcut_exists`, which asserts the module has no public symbol containing `auto_attribute`, `attribute_by_name`, `name_match_attribute`, `guess_student`, or `match_student`. |
| Preserve review status and evidence provenance | ✓ Preserved | Source `review_status: unreviewed` unchanged. Per-record review workflow (Chunk 7.11 five-stage) is referenced by `arxiv_governance_decisions.md` and preserved. |
| Tests for all required scenarios | ✓ Implemented | 17 tests across `TestPeerReviewStatus`, `TestWithdrawals`, `TestStudentAttribution`. |

### 4.4 Revision 4 — Acknowledgment, canonical links, contact privacy

| Requirement | Status | Evidence |
|---|---|---|
| Display acknowledgment `"Thank you to arXiv for use of its open access interoperability"` | ✓ Implemented | `ARXIV_ACKNOWLEDGMENT` constant; `sources.yaml` records the convention. Verified by `test_acknowledgment_text_matches_review`. |
| Do not claim arXiv endorsement | ✓ Enforced | `test_acknowledgment_does_not_claim_endorsement` asserts the constant contains no "endorse"/"sponsor"/"affiliat"/"approved by arxiv" tokens. `sources.yaml` and `arxiv_governance_decisions.md` repeat the trademark rule. |
| Use canonical abstract links for arXiv records | ✓ Implemented | `canonical_abs_link(base_arxiv_id)` returns `https://arxiv.org/abs/<id>`. Verified for new-style and old-style IDs; malformed IDs rejected. |
| Canonical link is display-only, not a metadata endpoint | ✓ Enforced | `test_canonical_link_is_display_only_not_metadata_endpoint` passes the canonical link through `validate_metadata_endpoint` and asserts `AbsScrapingProhibitedError`. |
| Strip submitter contact emails from ingestion logs | ✓ Implemented | `redact_contact_emails(text)` regex-substitutes email-like substrings with `[REDACTED_EMAIL]`. |
| Ensure logs do not retain emails via exception messages, raw payloads, debug output, serialized records | ✓ Enforced | `test_redaction_in_exception_messages` and `test_redaction_in_debug_payload_dump` cover both representative paths. Policy applies to any caller emitting log output; the function is the single sanctioned emission gate per `arxiv_governance_decisions.md`. |
| Preserve useful operational diagnostics | ✓ Explicit | `test_redaction_in_exception_messages` verifies that `"line 42"` and `"ValueError"` survive redaction; only email-like substrings are stripped. |
| Tests for acknowledgment, canonical links, email redaction | ✓ Implemented | 11 tests across `TestAcknowledgment`, `TestCanonicalLink`, `TestEmailRedaction`. |

---

## 5. Schema changes

**No existing Pydantic model was modified in this chunk.** `Achievement`, `Annotation`, `SourceRegistry`, `LabelTaxonomy`, `Evidence`, `ManifestEntry` are byte-identical to their HEAD versions.

**One new Pydantic model added**, in a new module:

| New model | File | Purpose |
|---|---|---|
| `ArxivMetadataRecord` | `src/nlp_semantic/ingestion/arxiv_governance.py` | Staging-only metadata record. NOT the `Achievement` schema. Represents the fields a future collector would stage per paper. `extra="forbid"`; `per_paper_license_uri: str | None` tracks per-record license with `None` as explicit UNKNOWN. |
| `StudentVerificationEvidence` | same file | Three-flag evidence record used only by `authorize_student_link`. `extra="forbid"`. |
| `PeerReviewStatus` enum | same file | `UNREFEREED_PREPRINT | PEER_REVIEWED | UNKNOWN`. |

**Rationale.** The Chunk 7.17 §F "separate decisions" table and the Chunk 7.16 §C.1 field mapping both decided that arXiv metadata fields do not persist into `Achievement` beyond `source_record_id`, (optional) `achievement_date`, and (optional) reviewer-verified `organization`. Capturing the full metadata set would therefore require either (a) expanding `Achievement` or (b) a staging-only model. (a) would be an unapproved schema change; (b) is the minimum compatible choice and is what this chunk adopts. The schema gap (Chunk 7.16 §F.7, no `arxiv_version` field on `Achievement`) is **documented and NOT closed by this chunk**; version remains in per-record YAML comments.

---

## 6. Tests executed

### 6.1 New-module tests (full detail)

Command:
```
python -m pytest tests/ingestion/test_arxiv_governance.py tests/ingestion/test_rate_limit.py --tb=short -v
```

Result:

| Metric | Count |
|---|---|
| Passed | **89** |
| Failed | 0 |
| Skipped | 0 |
| Collection errors | 0 |
| Completed successfully | **Yes** |

Breakdown:
- `test_arxiv_governance.py` — 76 passed (endpoint validation, forbidden content types, record model, peer-review classification, withdrawals, student attribution, acknowledgment, canonical links, email redaction).
- `test_rate_limit.py` — 13 passed (construction, pacing, concurrency serialization, operator-discipline documentation).

### 6.2 Full ingestion suite (regression check)

Command:
```
python -m pytest tests/ingestion/ --tb=short
```

Result:

| Metric | Count |
|---|---|
| Passed | **164** |
| Failed | 0 |
| Skipped | 4 |
| Collection errors | 0 |
| Completed successfully | **Yes** |

Includes 75 pre-existing ingestion tests (all pass) + 89 new tests.

### 6.3 Schema + ingestion + smoke

Command:
```
python -m pytest tests/schema/ tests/ingestion/ tests/test_smoke.py --tb=short
```

Result:

| Metric | Count |
|---|---|
| Passed | **398** |
| Failed | 0 |
| Skipped | 4 |
| Collection errors | 0 |
| Completed successfully | **Yes** |

Pre-Chunk-7.18 baseline was 309 passed; the +89 delta accounts for every new test module.

### 6.4 Registry live-state inspection

Command:
```
python -c "from nlp_semantic.ingestion.registry import load_and_validate_sources; ..."
```

Result:
- 2 entries loaded.
- arXiv entry (`src_08ee850ba4b54d1b81cdbd652809b613`): `license=CC0-1.0`, `review_status=unreviewed`. Both `usage_restrictions` (1936 chars) and `mapping_notes` (1986 chars) under the 2000-char Pydantic cap.
- SIH entry (`src_5a8a2998d6f44055a42dcfd8991e4d12`): `license=UNKNOWN`, `review_status=unreviewed`. Unchanged by this chunk.

### 6.5 Dataset test collection — pre-existing failure

Command:
```
python -m pytest tests/dataset/ --tb=line
```

Result:

| Metric | Count |
|---|---|
| Passed | 0 |
| Failed | 0 |
| Skipped | 0 |
| Collection errors | **3** |
| Completed successfully | **No** (collection interrupted) |

Error (unchanged from Chunk 7.15 § G onward):
```
ERROR tests/dataset/test_cli.py
ERROR tests/dataset/test_loader.py
ERROR tests/dataset/test_validator.py
ModuleNotFoundError: No module named 'tests.dataset'
Interrupted: 3 errors during collection
```

**Unresolved.** Root cause (established in Chunk 7.15, re-confirmed in Chunks 7.16, 7.17, 7.18): the user's Python 3.13 site-packages contains an unrelated `tests` package at `C:\Users\Balaji\AppData\Roaming\Python\Python313\site-packages\tests\__init__.py` that shadows the local repo's `tests/` directory in any `import tests` resolution; `pyproject.toml` sets `pythonpath = ["src"]` only; no `tests/__init__.py` exists. **Not fixed here** per the Chunk 7.18 prompt §Phase 3 ("Investigate only insofar as it blocks relevant verification"). Did not block Chunk 7.18 verification because no Chunk 7.18 test lives under `tests/dataset/`.

---

## 7. Dataset test collection issue — unchanged

- **Status:** UNRESOLVED (pre-existing from Chunk 7.15).
- **Scope impact on this chunk:** none — all Chunk 7.18 tests live under `tests/ingestion/` and collect successfully.
- **Not silently reported as passing.** The exact collection error is captured in §6.5 above.
- **Not fixed.** No `pyproject.toml` edit, no new `tests/__init__.py`, no installed-package change.

---

## 8. Incomplete requirements / documented limitations

| # | Limitation | Documented at |
|---|---|---|
| L1 | Rate limiter is process-local; cross-process rate guarantee requires operator discipline (single collector, single machine). | `src/nlp_semantic/ingestion/rate_limit.py` module docstring; `hybrid_dataset/metadata/arxiv_governance_decisions.md` §Revision 1; `sources.yaml` `usage_restrictions`. |
| L2 | Arxiv version is not a schema field on `Achievement`. Version lives in per-record YAML comment convention. | Chunk 7.16 §F.7; `arxiv_governance_decisions.md`; `sources.yaml` `mapping_notes`. Not closed by this chunk. |
| L3 | Dataset test collection error unresolved (pre-existing environment-level issue). | §6.5 and §7 of this report. |
| L4 | The human-review PDF `arXiv_Source_Governance_Review_Ashok_Mohan.pdf` was referenced in the chunk prompt but is not present on disk under `SUPERVISED PROJECT/`. The implementation proceeded against the review outcomes as summarized in the prompt itself. A new human reviewer should still be able to confirm the implementation matches the PDF they hold. | §2 of this report. |
| L5 | `is_withdrawn` is a text-pattern heuristic over the author-supplied comment; it is a POSITIVE signal that must trigger exclusion, but a False does NOT prove the paper is not withdrawn. | `arxiv_governance.is_withdrawn` docstring; `arxiv_governance_decisions.md` §Revision 3. |
| L6 | External verification flags (DOI, journal_ref, ORCID, institutional email, advisor) are inputs to the governance module; the module does NOT verify them itself. External verification pipelines are a separate project responsibility. | Module docstrings; `arxiv_governance_decisions.md`. |
| L7 | Email redaction regex covers typical patterns; obfuscated addresses (e.g. `foo [at] example [dot] com`) are not detected. The function is a sanitizer, not a classifier. | `redact_contact_emails` docstring. |

None of L1-L7 are a Mohan-revision shortfall. They are the architecturally honest statements of what the policy module does and does not promise.

---

## 9. Final source governance status

| Field | Value |
|---|---|
| `source_id` | `src_08ee850ba4b54d1b81cdbd652809b613` |
| `source_name` | `arXiv` |
| `source_url` | `https://arxiv.org/` |
| `license` | `CC0-1.0` |
| `collection_date` | `2026-10-23` (reviewer-observed in Chunk 7.14; unchanged) |
| `intended_use` | `primary_type_training_lbl_research_pub_metadata_only` |
| `review_status` | **`unreviewed`** (unchanged) |
| `is_synthetic` | `false` |
| Governance implementation | Chunk 7.18 revisions 1-4 complete |
| Promotion status | **BLOCKED pending a new human review of this implementation** |

A new human review must:
1. Inspect [`src/nlp_semantic/ingestion/arxiv_governance.py`](../src/nlp_semantic/ingestion/arxiv_governance.py).
2. Inspect [`src/nlp_semantic/ingestion/rate_limit.py`](../src/nlp_semantic/ingestion/rate_limit.py).
3. Inspect [`hybrid_dataset/metadata/arxiv_governance_decisions.md`](../hybrid_dataset/metadata/arxiv_governance_decisions.md).
4. Inspect the updated [`sources.yaml`](../hybrid_dataset/metadata/sources.yaml) arXiv entry.
5. Decide whether these revisions satisfy Mohan's conditions.
6. If approve: post two independent sign-off comments per the Chunk 7.17 §5.5 template.
7. Then (and only then) edit `review_status: unreviewed → verified` in a follow-up commit.

---

## 10. Protected file hash verification

Verified at session start and at session end — both match the expected values:

| File | Expected | Observed (end) | Match |
|---|---|---|---|
| `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | ✓ |
| `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ✓ |

---

## 11. Final `git status`

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

`git diff --stat`:
```
hybrid_dataset/metadata/sources.yaml | 101 +++++++++++++++++++++++++++++++++++
1 file changed, 101 insertions(+)
```

- The 101 insertions represent the Chunk 7.15 arXiv entry (as compressed and extended by Chunk 7.18) relative to HEAD (`c8c1b80`, pre-Chunk-7.15). No lines removed; strictly additive at the file level, with the arXiv entry content refreshed by this chunk's edits to the uncommitted working-tree text.

---

## 12. Confirmation — no API, no collection, no commits

- No API request initiated ✓
- No metadata collected ✓
- No download performed (no PDF, no TeX, no source archive, no full text) ✓
- No achievement record created ✓
- No annotation created ✓
- No dataset split generated ✓
- No taxonomy promoted ✓
- No source promoted (`review_status: unreviewed` unchanged) ✓
- No reviewer identity invented ✓
- No fake reviewer approval recorded ✓
- No staging performed ✓
- No commits performed ✓
- No pushes performed ✓
- No branch switched, created, or deleted ✓
- No teammate directory touched (none exist) ✓
- `pyproject.toml` not modified ✓
- `tests/__init__.py` not created ✓
- Installed Python packages not modified ✓
- Protected file hashes unchanged ✓
- Chunk 7.4-D reviewer-independence stop preserved ✓
- Mohan's `revise` decision NOT represented as `approve` ✓
- Ashok's `approve` decision NOT represented as unanimous approval ✓

---

## 13. Summary

- **Four mandatory governance revisions implemented** as policy modules + staging model + updated source entry + extensive tests.
- **No existing Pydantic schema modified.** Minimal compatible change: new modules + new staging-only models; no change to `Achievement` / `Annotation` / `SourceRegistry` / `LabelTaxonomy` / `Evidence` / `ManifestEntry`.
- **89 new tests, all passing.** Full ingestion suite 164 pass, 4 skipped; broader schema + ingestion + smoke 398 pass, 4 skipped.
- **Documented limitations preserved honestly.** Rate limiter is process-local; dataset test collection error is unresolved; arXiv version is not a schema field; no automatic external verification.
- **Source stays `unreviewed`.** Implementation is not promotion.
- **Awaiting a new human review** of this implementation to decide whether the source may be promoted.
