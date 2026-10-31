# Chunk 7.16 — arXiv Metadata Collection Design (Read-Only)

**Report type:** design document; read-only investigation deliverable
**Generated:** 2026-10-23 (session date)
**Status:** COMPLETED — READ-ONLY METADATA COLLECTION DESIGN

> This file preserves the Chunk 7.16 findings verbatim from the chat delivery. It is a *proposed* design under internal review. Nothing in this document has been implemented, approved, or scheduled.

---

## A. Executive Summary

| Item | Value |
|---|---|
| Chunk number | 7.16 |
| Chunk type | Read-only technical design |
| Objective | Propose a workflow, field mapping, API strategy, rate-limit handling, deduplication, storage design, and human-review gates for collecting descriptive metadata from arXiv for the supervised-learning dataset |
| Scope | **Design only.** No collector implementation, no API calls, no metadata download, no record creation, no annotation, no source promotion, no taxonomy promotion |
| Final status | `COMPLETED — READ-ONLY METADATA COLLECTION DESIGN` |

### Key conclusions

1. The arXiv source is registered (`src_08ee850ba4b54d1b81cdbd652809b613`, `license: CC0-1.0`, `review_status: unreviewed`) from Chunk 7.15; the Chunk 7.14 human license re-verification cleared registration but did **not** promote the source.
2. Of ~12 arXiv metadata fields considered, only three land directly in existing `Achievement` schema fields (`arxiv_id` → `source_record_id`; optional `submitted` → `achievement_date`; optional reviewer-verified affiliation → `organization`). All other fields are **staging-only** and never persisted into Achievement rows.
3. The design preserves four strict identity levels: paper / version of a paper / person / achievement record. Multiple versions of a paper collapse to **one** Achievement row.
4. Rate pacing is single-process, single-thread, single-connection, ≥ 3 s between requests, collective across all operator machines. No concurrency, no retry storms.
5. arXiv categories (`cs.CL`, `cs.LG`, …) are **reviewer hints only**, never auto-applied as `domain_tags`.
6. No arXiv-derived record can reach `training_ready_subset` until all four gates close: source `review_status: verified`, `license != UNKNOWN`, `lbl_research_pub` promoted to `approved`, per-record `annotation_status.<task>: verified`.
7. Eleven unresolved questions (H1–H11) require decisions outside this chunk; of these, scope (H1), endpoint behavior (H2), and reviewer staffing (H11) are the biggest blockers to execution.

---

## B. Repository State

| Field | Value |
|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` |
| Working folder | `SUPERVISED PROJECT` |
| Branch | `feature/nlp-semantic` |
| HEAD | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` |
| Remote sync | `## feature/nlp-semantic...origin/feature/nlp-semantic` — in sync (not pushed) |
| Working tree before Chunk 7.16 | ` M hybrid_dataset/metadata/sources.yaml` (Chunk 7.15 arXiv registration, uncommitted); `?? PROJECT_HANDOFF.md` |
| Teammate dirs (`src/ml`, `src/recommender`, `src/backend`) | Do not exist. Not touched. |

### Protected file hash verification

| File | Expected (from prior chunks) | Observed in Chunk 7.16 | Match |
|---|---|---|---|
| `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | ✓ |
| `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ✓ |

---

## C. Existing Schema Inventory

Every field below was read directly from the source files during Chunk 7.16. No field is proposed or imagined. Where a datum has no destination in the existing schema, the mapping explicitly says so.

### C.1 `SourceRegistry` — 11 fields

Source: `src/nlp_semantic/schema/source_registry.py` lines 116-126.

| Field | Type / constraint |
|---|---|
| `source_id` | `src_<32 lowercase hex>` |
| `source_name` | `str`, 1–120 chars |
| `source_url` | `http`/`https` only; no embedded credentials |
| `license` | `str`, 1–200 chars (free text; `"UNKNOWN"` sentinel honored case-insensitively by `training_ready_subset`) |
| `usage_restrictions` | `str \| None`, ≤ 2000 chars |
| `collection_date` | `date`, must satisfy `<= today + 1 day` |
| `original_labels` | `list[str]` |
| `intended_use` | `str`, 1–200 chars |
| `mapping_notes` | `str \| None`, ≤ 2000 chars |
| `review_status` | `ReviewStatus` enum: `unreviewed \| in_review \| verified \| rejected` |
| `is_synthetic` | `bool`, default `false` |

### C.2 `Achievement` — 15 fields

Source: `src/nlp_semantic/schema/achievement.py` lines 33-69.

| Field | Type / constraint |
|---|---|
| `achievement_id` | `ach_<32 hex>` |
| `source_id` | `src_<32 hex>` |
| `source_record_id` | `str`, 1–200 chars |
| `achievement_text` | `str`, 1–4000 chars |
| `primary_type` | `str \| None` (label_id pattern `lbl_<snake>`, 2-60 chars) |
| `domain_tags` | `list[str]` (label_id pattern), no duplicates |
| `level` | `str \| None`, ≤ 120 chars |
| `outcome` | `str \| None`, ≤ 120 chars |
| `event_name` | `str \| None`, ≤ 250 chars |
| `organization` | `str \| None`, ≤ 250 chars |
| `achievement_date` | `date \| None`, must satisfy `<= today + 1 day` |
| `rank` | `int \| None`, `>= 1` when set |
| `skills` | `list[str]`, each ≤ 120 chars, no duplicates |
| `evidence_id` | `evd_<32 hex> \| None` |
| `annotation_status` | `AnnotationStatusMap { primary_type, domain_tags }` with per-task `AnnotationStatus` enum |
| `is_synthetic` | `bool`, default `false` |

**Cross-field invariant:** `primary_type` cannot be set while `annotation_status.primary_type == NOT_STARTED`; same for `domain_tags` vs `annotation_status.domain_tags`. Validator-enforced.

### C.3 `Annotation` — 8 persistent fields + `is_synthetic`

Source: `src/nlp_semantic/schema/annotation.py` lines 19-46.

| Field | Type / constraint |
|---|---|
| `annotation_id` | `ann_<32 hex>` |
| `achievement_id` | `ach_<32 hex>` |
| `task` | `AnnotationTask` enum: `primary_type \| domain_tags \| extraction_review` |
| `label_ids` | `list[str]` (arity by task: `primary_type` requires exactly 1; `extraction_review` must be empty; `domain_tags` is 0..N) |
| `annotator` | pseudonym (`labeler_<NNN>` convention); email-like rejected; must be 2-64 chars from `[A-Za-z0-9_-]` starting with alphanum/underscore |
| `review_status` | `AnnotationStatus` (any value **except** `NOT_STARTED` — that's reserved for the parent Achievement's status summary) |
| `notes` | `str \| None`, ≤ 2000 chars |
| `created_at` | tz-aware `datetime` (naive datetimes rejected) |
| `is_synthetic` | `bool` |

### C.4 `ManifestEntry` — 6 fields

Source: `src/nlp_semantic/ingestion/manifest.py` lines 37-67.

| Field | Type / constraint |
|---|---|
| `source_id` | FK to `SourceRegistry.source_id` |
| `raw_subdir` | path under `hybrid_dataset/raw/`; no `..`, no backslashes, no empty segments, no absolute paths |
| `expected_file_types` | `list[DocumentFileType]` (enum: `pdf \| image_jpg \| image_png \| image_tiff \| text \| other`) |
| `expected_count` | `int \| None`, `>= 0` |
| `sampling_notes` | `str \| None`, ≤ 2000 chars |
| `is_synthetic` | `bool` |

### C.5 `LabelTaxonomy` — 8 fields

Source: `src/nlp_semantic/schema/label_taxonomy.py`.

| Field | Type / constraint |
|---|---|
| `label_id` | `lbl_<snake>` (2-60 chars after prefix) |
| `task_name` | `TaxonomyTask` enum: `primary_type \| domain_tags` |
| `display_name` | `str`, 1–120 chars |
| `definition` | `str`, 1–2000 chars |
| `inclusion_rules` | `list[str]` |
| `exclusion_rules` | `list[str]` |
| `examples` | `list[str]` |
| `status` | `TaxonomyStatus` enum: `draft \| under_review \| approved \| deprecated` |
| `supersedes` | `label_id \| None`, must differ from own `label_id` |

### C.6 Domain-tag labels (current state)

Observed in `hybrid_dataset/labels/domain_tags.yaml`: 10 labels, all `status: draft` — `lbl_domain_ai`, `_ml`, `_nlp`, `_cv`, `_security`, `_systems`, `_web`, `_data`, `_hardware`, `_other`. (These label definitions were not re-read in Chunk 7.16; status is derived from prior-chunk context.)

### C.7 Evidence

Source: `src/nlp_semantic/schema/evidence.py`. Represents an evidence artifact (PDF/image/text) under `hybrid_dataset/raw/evidence_documents/`. `Evidence.relative_path` must start with `hybrid_dataset/raw/evidence_documents/`; it is **not** suitable for arXiv metadata, which is a structured record rather than a file artifact.

### C.8 Governance gates for `training_ready_subset`

Source: `src/nlp_semantic/dataset/validator.py` lines 321-371.

A record is training-ready **only when all of**:
1. `annotation_status.<task> == VERIFIED` (per-task),
2. `primary_type` / `domain_tags` references labels with `status == APPROVED` (not `draft`),
3. `source.review_status == VERIFIED`,
4. `source.license.strip().upper() != "UNKNOWN"` (case-insensitive).

The newly registered arXiv source today has `review_status: unreviewed`; `lbl_research_pub` is still `draft`. Any arXiv-derived Achievement would be excluded on both of those grounds today.

---

## D. Metadata Field Mapping

Legend:
- **Dest. field** = where the datum could land in the existing schema, if anywhere.
- **Review req.** = reviewer must act on this before it is persisted.
- **Prohibited inference** = what MUST NOT be derived automatically.

| arXiv metadata | Meaning | Proposed use | Dest. field (existing) | Transformation | Review req. | Prohibited inference |
|---|---|---|---|---|---|---|
| `arxiv_id` (base, e.g. `2403.12345`) | Canonical paper identifier | Dedup key for `source_record_id` | `Achievement.source_record_id` (string, 1-200 chars) | Namespaced: `"arxiv-" + base_id` | — | NOT a student identifier; NOT an achievement outcome |
| `arxiv_id` version (e.g. `v2`) | Version within paper history | Metadata only; reviewer-visible comment | **None** (no schema field) | Record in staging-only sidecar (not in Achievement) | — | Multiple versions ≠ multiple achievements |
| `title` | Paper title | Reviewer evidence; may be referenced in `achievement_text` | **Partial.** No dedicated `title` field | Used verbatim in `achievement_text` prose at reviewer discretion | Reviewer chooses whether to include | Title ≠ `event_name`; title ≠ achievement outcome |
| `abstract` | Short description | Reviewer evidence only (NOT stored in Achievement) | **None** | Keep in staging; not propagated | Reviewer reads for Stage D | Abstract ≠ `achievement_text`; must not be copy-pasted as record text |
| `authors` | Author bylines | Candidate list for Chunk 7.11 Stage A/C review | **None** at the record level; public byline captured in per-record reviewer comment, not a schema field | — | Mandatory | Author list ≠ student roster; name match ≠ identity match |
| `authors[*].affiliation` (when present) | Author's institution | Reviewer hint for Stage B (student status) | `Achievement.organization` — **only** if reviewer verifies enrollment at that institution on `submitted` date | Reviewer-set after Stage B | Mandatory | Affiliation ≠ student enrollment; corresponding-author affiliation ≠ all authors' affiliations |
| `submitted` / `created` date | First-version submission date | Candidate for `achievement_date` | `Achievement.achievement_date` (`date \| None`, `<= today + 1 day`) | ISO datetime → `date`; must pass the Chunk 7.4-A.2 "unambiguous event date" test | Reviewer may set | Submission ≠ acceptance ≠ publication; arXiv submission does not establish prior journal acceptance |
| `updated` date | Latest version date | Reviewer sanity check only | **None** | Keep in staging | — | Later `updated` ≠ different achievement |
| `primary_category` (e.g. `cs.CL`) | arXiv-assigned primary classification | Reviewer **hint** for `domain_tags` | **Must NOT auto-populate `domain_tags`.** Reviewer manually sets per the Chunk 7.13 reviewer-hint table | Discard from staging once reviewer uses it | Mandatory | Category ≠ `domain_tag`; `cs.CL` ≠ `lbl_domain_nlp` without reviewer confirmation |
| `all_categories` | Additional arXiv categories | Reviewer **hint** | same as above | same | same | same |
| `doi` (when present) | External identifier for published version | Reviewer sanity check; influences `primary_type` decision (preprint vs peer-reviewed is open — see H3) | **None** at the record level | Keep in staging | — | DOI ≠ achievement outcome; peer-review status cannot be inferred from DOI presence alone |
| `journal_ref` (when present) | Author-supplied publication reference | Reviewer sanity check | **None** at the record level | Keep in staging | — | Author-asserted on arXiv; NOT verified; cannot be treated as peer-review proof |
| `comment` (when present) | Author's free-text comment | Reviewer sanity check (sometimes "to appear in …") | **None** at the record level | Keep in staging | — | Author claim ≠ verification |
| `license` (per-paper, when present) | Per-paper reuse license | Flags whether full-text would be reusable (out of scope); useful as reviewer context | **None** (metadata-only scope); NOT USED to permit full-text ingestion | Keep in staging as a notation only | Mandatory IF full-text question is opened (separate SourceRegistry entry required) | Per-paper license ≠ CC0 permission for full text; most arXiv papers default to the arXiv non-exclusive license, which does NOT grant redistribution |

### D.1 Field-mapping summary

Of ~12 arXiv metadata fields considered, only three land in Achievement schema fields: `arxiv_id` (into `source_record_id`), optional `submitted` date (into `achievement_date` if reviewer confirms unambiguous), and optional reviewer-verified affiliation (into `organization`). All other fields are **staging-only**. This is deliberate: the project's model input is `achievement_text` alone, and persisting more metadata into Achievement rows would expand the training surface without a corresponding annotation task.

---

## E. API Collection Design

### E.1 Verified facts (human-verified in Chunk 7.14 / 7.15)

1. The arXiv **metadata** is CC0 1.0 ("A Creative Commons CC0 1.0 Universal Public Domain Dedication will apply to all metadata.").
2. Legacy APIs (OAI-PMH, RSS, arXiv API) must not exceed **one request every three seconds**.
3. Use must be limited to **one connection at a time**.
4. Limits apply **collectively across all machines** under the user's control.
5. Full-text / PDF / source-file redistribution is **not** granted by CC0 metadata permissions.
6. API terms may change; must re-check at every future collection date.

### E.2 Newly researched API documentation

**Not investigated in Chunk 7.16.** This design deliberately did not re-fetch arXiv's API reference pages. The implementer must verify endpoint URLs, parameter grammar, and response schemas against the official documentation at implementation time; do not treat anything in §E.3 below as verified unless this document says so explicitly.

### E.3 Candidate endpoints — assumptions and open questions

**Channel A — arXiv Query API (legacy)**
- *Assumption:* endpoint lives under the `export.arxiv.org/api/` path and returns Atom XML. Not verified in this chunk.
- *Open question A1:* exact endpoint URL and parameter grammar.
- *Open question A2:* response-field names in the Atom feed (likely `title`, `summary` = abstract, `author`/`name`, `arxiv:primary_category`, `published`, `updated`, `arxiv:doi`, `arxiv:journal_ref`, `arxiv:comment` — all unverified).
- *Open question A3:* exact pagination parameters and total-count behavior.
- *Open question A4:* error-response format and status codes under rate-limit or quota breach.

**Channel B — OAI-PMH (bulk)**
- *Verified fact:* arXiv's own API ToU designates OAI-PMH as the bulk-metadata interoperability channel subject to the same rate limits.
- *Open question B1:* exact OAI-PMH endpoint URL.
- *Open question B2:* which `metadataPrefix` to use (`arXiv` vs `arXivRaw` vs `oai_dc`).
- *Open question B3:* `set` grammar for subsetting (e.g. by arXiv category) and whether `resumptionToken` handling matches standard OAI-PMH.
- *Open question B4:* `from`/`until` date semantics (submitted vs updated).

**Recommendation:** use OAI-PMH for the first batch, falling back to the Query API for individual-paper confirmation during Chunk 7.11 Stage A review. Rationale: fewer requests under the 1-per-3-second budget; `resumptionToken` is the standard way to iterate large sets without state on the client; arXiv's own ToU names OAI-PMH as the preferred bulk channel.

### E.4 Query strategy

The design does **not** propose a scope query. Scope decisions are a project-team concern:
- *Which arXiv categories?* (D4-a) — unresolved; CS-only vs multi-archive.
- *What date range?* (D4-b) — unresolved; depends on dataset scope.
- *What volume cap?* (D4-c) — unresolved; needs rate-budget estimate.

Whatever scope is chosen must be **expressible as a reproducible query string** stored alongside the staged metadata (not just in a reviewer's head).

### E.5 Request pacing design

| Rule | Implementation requirement |
|---|---|
| ≥ 3.0 s between requests | Single-process, single-thread client with a sleep gate. No worker pool, no asyncio concurrency, no distributed queue. |
| 1 connection at a time | Reuse a single HTTP connection (one `requests.Session` or equivalent); no connection pool with `maxsize > 1`. |
| Collective rate limit across machines | A single operator machine runs the collector at any time. If a second machine ever runs it, operators MUST coordinate so collective rate ≤ 1 req / 3 s. The implementation MUST NOT auto-spawn parallel workers. |
| No retry storm | Any 4xx or 5xx response triggers at most one exponential-backoff retry with floor `6 s`, and a hard limit of 3 total retries per request. On exhaustion, the request fails and is logged; the collector does not continue silently. |
| No unbounded retry loop | A session-level retry counter must be enforced (e.g. ≤ 50 total retries per session) to prevent slow degradation from a persistent arXiv-side issue consuming a 3-second slot indefinitely. |

### E.6 Pagination / continuation

- OAI-PMH: honor `resumptionToken` exactly; each page is a separate request subject to the 3-second gate.
- Query API (if used): if the official documentation defines `start` + `max_results`, use the smallest `max_results` that produces complete pages (likely 100-200; **unverified**).

### E.7 Error handling

| Observed status | Design response |
|---|---|
| 2xx | Parse XML; validate presence of required fields (`arxiv_id`, `title`, `authors`, `submitted`, `primary_category`); log and skip if required field absent |
| 3xx | Follow redirects **only** to arXiv hostnames; otherwise error |
| 4xx (except 429) | Fail that request; do NOT retry |
| 429 | Honor any `Retry-After` header; otherwise backoff with floor 6 s |
| 5xx | Backoff per §E.5 "no retry storm" |
| Timeout | Treat as 5xx-equivalent; backoff per §E.5 |

### E.8 Incremental updates

- First collection run captures `(from=<project-start-date>, until=<today>)`.
- Each subsequent run passes `from=<previous_run.until>` to pick up only new submissions.
- A per-run manifest records `(from, until, resumptionToken_count, total_records, api_terms_url_hash, license_url_hash, run_timestamp)` so the run is reproducible.

### E.9 Reproducibility

Every collection run must emit a manifest capturing:
- Exact query grammar used.
- Pagination state at the end of the run.
- SHA-256 hashes of the arXiv license page and ToU page as the collector observed them. If observed hashes differ from the Chunk 7.15 reviewer-verified hashes, the run is treated as untrusted and the diff is surfaced to a human reviewer **before** records are persisted.
- Collector version.
- Rate-limit budget used.

---

## F. Deduplication

### F.1 Canonical arXiv identifier

The canonical identifier is the **base ID** (e.g. `2403.12345`), **not** the versioned form (`2403.12345v2`). Matches the Chunk 7.15 `mapping_notes` convention.

### F.2 Mapping to `Achievement.source_record_id`

`Achievement.source_record_id` = `"arxiv-" + base_arxiv_id`. Namespacing avoids collision with any future source that happens to use the same raw numeric ID.

### F.3 Version handling

- Multiple versions of the same paper → **ONE** Achievement row.
- The reviewer-chosen "canonical" version (typically the latest at review time, or the version with a DOI if present) is captured in a per-record YAML comment next to the Achievement row.
- If the paper is revised after the Achievement row is created, the reviewer records that in the YAML comment and MUST decide whether the revision affects the Chunk 7.11 Stage D (achievement eligibility) decision. The record itself is **not** duplicated.

### F.4 Duplicate API responses

- Collector emits a `(base_arxiv_id, submitted_date)` tuple for every record it ingests.
- If the collector re-encounters an existing base_arxiv_id within a run, it logs and skips.
- Across runs, the collector consults the previous staging manifest and skips any base_arxiv_id already staged.

### F.5 DOI / alternate-identifier conflicts

If two arXiv records carry the same DOI (rare; happens when a paper has an updated DOI assignment), the deduplication key is still the base arXiv ID — DOI collision does not merge records. The collision is surfaced to the reviewer as a sanity-check flag.

### F.6 Preserved distinctions

| Level | Example |
|---|---|
| 1. Paper | arXiv base ID `2403.12345` |
| 2. Version of a paper | `2403.12345v2` (NOT a separate record) |
| 3. Person | A human author (established through Chunk 7.11 Stage A, outside this design) |
| 4. Achievement record | One `Achievement` row referencing (paper, person) with primary_type and annotation_status, after Stages A-E all VERIFIED |

The design never collapses levels (e.g. does not promote "paper has multiple authors" → "multiple Achievement records" until Stage A has succeeded for each author).

### F.7 Unresolved schema limitation

The current `Achievement` schema has **no field for arXiv version**. This is a deliberate design choice preserved by this document: version lives in the YAML sidecar comment, not in a schema field. If the project team later decides version-level tracking is required (e.g. "we trained on v1; v2 has different results"), that is a **separate schema-approval chunk** and not part of this registration.

---

## G. Metadata Storage Design

**All structures below are proposals, not implemented schemas.** No staging directory was created; no code was written.

### G.1 Proposed staging format

- Location: a staging directory outside `hybrid_dataset/raw/` (e.g. `staging/arxiv_runs/<run_id>/`). The staging directory is **not** committed to the repository. Rationale: `hybrid_dataset/raw/` is reserved for evidence documents (per `path_safety.py` `APPROVED_EVIDENCE_PREFIX`), and arXiv metadata is not a documentary evidence artifact.
- Format: JSONL (one normalized metadata record per line) + a per-run YAML manifest. Why JSONL: streamable, easily append-only, easy to re-process. Why YAML for the manifest: consistent with the project's existing `metadata/sources.yaml` and `metadata/manifest.yaml` conventions.
- The staging format is **not** a Pydantic model today; it is a sidecar.

### G.2 Required per-record fields in staging (proposed)

| Staging field | Source |
|---|---|
| `base_arxiv_id` | arXiv `arxiv_id` without version |
| `version_at_collection` | arXiv `arxiv_id` version suffix (`v1`, `v2`, …) |
| `title` | arXiv `title` |
| `abstract` | arXiv `summary` |
| `authors[]` with `name`, `affiliation?` | arXiv `author.name` / `author.affiliation` |
| `submitted_date` | arXiv `published` |
| `updated_date` | arXiv `updated` |
| `primary_category` | arXiv `arxiv:primary_category` |
| `all_categories[]` | arXiv `arxiv:category` entries |
| `doi` | arXiv `arxiv:doi` when present |
| `journal_ref` | arXiv `arxiv:journal_ref` when present |
| `comment` | arXiv `arxiv:comment` when present |
| `per_paper_license` | arXiv `arxiv:license` when present (recorded but NOT used to permit full-text) |
| `collection_timestamp_utc` | collector clock (tz-aware UTC) |
| `source_id` | `src_08ee850ba4b54d1b81cdbd652809b613` (the Chunk 7.15 arXiv entry) |
| `collector_version` | semver string of the collector module |
| `request_endpoint` | which endpoint produced this record |
| `request_params` | the query parameters that returned this record |
| `review_status` | always `candidate` at staging time; **not** a `ReviewStatus` enum value — explicitly a staging-only sentinel to prevent accidental promotion |

### G.3 Per-run manifest (proposed)

```
run_id, collection_date, query_grammar, from_date, until_date,
total_requests_made, total_records_ingested, total_records_skipped,
base_arxiv_ids: [...],
license_evidence_sha256: {
  license_page_url: "...", observed_sha256: "..."
  tou_page_url: "...", observed_sha256: "..."
},
collector_version
```

### G.4 Validation

- Every staging record must have `base_arxiv_id`, `title`, at least one author, `submitted_date`, and `primary_category`. Missing any → log and skip.
- `submitted_date` must parse to a valid ISO date and respect `<= today + 1 day` (same rule as the Achievement schema).
- `base_arxiv_id` must match the arXiv regex (unverified; implementer confirms the correct pattern).
- Staging validation does **not** rely on the project's Pydantic models (staging is not a schema-managed state).

### G.5 Error handling at ingest

- A record that fails validation is logged with its `base_arxiv_id` (if known) and skipped; the run continues.
- A whole-page parse failure is logged and the page is retried once per §E.5; on second failure the run halts.
- Rate-limit violations (429) halt the run until the retry-after window elapses.

### G.6 Review status handling

- Staging records never carry a `review_status` value from the `ReviewStatus` enum. They carry a staging-only sentinel such as `"candidate"` to prevent any accidental coercion into a `SourceRegistry` or `Evidence` review-state transition.
- Promotion from staging to Achievement is a per-record human action and happens only after Chunk 7.11 Stages A-E are all VERIFIED.

### G.7 Reproducibility

- The staging run is reproducible from `(query_grammar, from_date, until_date, seed_if_any)` plus the arXiv API's own responses at that time. The collector does not need to be re-run to reconstruct an older run's state; the manifest + staged records are sufficient.

### G.8 Not written in this chunk

- No staging directory created.
- No collector module scaffolded.
- No downloaded metadata persisted.
- No sidecar manifest file written.

---

## H. Human Review Workflow

Each row is an **independent** governance check. None are automatically established by arXiv metadata.

| # | Check | What arXiv metadata DOES provide | What is **required** separately |
|---|---|---|---|
| 1 | **Paper identification** | `base_arxiv_id`, `title`, `authors`, `submitted` date | Confirmation that the paper exists at the arXiv ID and matches the title + abstract the collector staged |
| 2 | **Student identity** (Chunk 7.11 Stage A) | Public author byline | External evidence that a named author is a specific individual (ETD, department roster, workshop student-program page, or university-hosted CV). Byline alone does NOT establish identity |
| 3 | **Student status** (Chunk 7.11 Stage B) | Affiliation when present | Evidence that the enrollment range includes `submitted_date`. If `graduated < submitted_date`, or enrollment range unverifiable, status is NOT verified |
| 4 | **Authorship** (Chunk 7.11 Stage C) | Author list, position (first / middle / last) | Confirmation that the person is a named author (not merely acknowledged), with position + equal-contribution notes captured |
| 5 | **Achievement eligibility** (Chunk 7.11 Stage D) | `primary_category`, `doi`, `journal_ref`, `comment` — all author-asserted | Reviewer judgment that the paper fits `lbl_research_pub` per the Chunk 7.1 definition; AND `lbl_research_pub` has been promoted to `status: approved` via Chunk 7.2 |
| 6 | **Annotation eligibility** (Chunk 7.11 Stage E) | Nothing | Two independent annotators per task per the Chunk 6 workflow; Cohen's κ / Jaccard on the agreement run; `annotation_status.<task>: verified` only after dual sign-off |

### H.1 Statements the design explicitly rejects

- arXiv categories cannot auto-populate `domain_tags`.
- Author name match cannot auto-establish student identity.
- Affiliation string cannot auto-establish student status.
- First-author position cannot auto-establish student status.
- `journal_ref` cannot auto-establish peer review.
- `doi` presence cannot auto-establish peer review.
- Paper existence cannot auto-establish personal achievement eligibility.

---

## I. Training and Leakage Prevention

### I.1 Achievement-text-only model input

The project's model input is `Achievement.achievement_text` **alone**. This decision was established in prior chunks (Chunks 7.5–7.6) and is preserved by this design. The collector must never write arXiv metadata into `achievement_text` beyond what a human reviewer wrote. Copy-pasting the abstract into `achievement_text` is explicitly forbidden.

### I.2 Paper-version leakage prevention

§F.3 — only one Achievement row per base arXiv ID; version-level duplication cannot leak because it does not exist in the record set.

### I.3 Duplicate-paper split prevention

- `Achievement.source_id` groups all arXiv records into the same source. The Chunk 5 `splits.py` module keeps all records with a given `source_id` in exactly one split — this guarantees NO cross-split leakage of records sharing the arXiv source.
- Finer-grained leakage prevention (e.g. per-author across splits) is **out of scope** for this design; a separate chunk could add it if needed.

### I.4 Real-vs-synthetic separation

- arXiv-sourced records set `is_synthetic: false`.
- The Chunk 5 `splits.py` `exclude_synthetic=True` default correctly excludes any accidental synthetic sibling records from real splits.

### I.5 Prohibition on automatic domain tagging

- arXiv categories (`primary_category`, `all_categories`) are reviewer **hints** only.
- The collector must never populate `Achievement.domain_tags`.
- Reviewers populate `domain_tags` per the Chunk 7.13 confidence table during Chunk 6 annotation; dual sign-off applies.

### I.6 Training-readiness requirements

A record becomes training-ready **only** when all four gates close:
1. Source `review_status: verified` (Chunk 7.2 two-sign-off workflow; separate from this design).
2. Source `license != "UNKNOWN"` (already satisfied: `CC0-1.0`).
3. Primary-type label `status: approved` — `lbl_research_pub` is `draft` today; needs Chunk 7.2 taxonomy promotion.
4. Per-record `annotation_status.<task>: verified` (Chunk 6 workflow; two annotators, dual sign-off).

The collector cannot shortcut any of these.

### I.7 Explicitly preserved decisions

- No dataset splits are created in this chunk.
- The achievement-text-only input decision is **not** changed.
- Metadata collection does **not** make a record training-ready.

---

## J. Risks and Unresolved Questions

Each row is a decision outside the scope of this chunk.

| # | Risk / question | Decision owner | Blocks what? |
|---|---|---|---|
| H1 | Scope of first collection run (which categories, which date range, what volume) | Project team | §F Step 0 (scope decision) |
| H2 | Exact API endpoint behavior, response fields, pagination, error semantics (A1-A4, B1-B4 in §E.3) | Implementer, verified against official arXiv documentation at implementation time | §F Step 3 (collector implementation) |
| H3 | Preprint vs peer-reviewed: should `primary_type` have a sub-label for "preprint only"? | Project team taxonomy decision | Could promote `lbl_research_pub` without resolving; future refinement |
| H4 | Multi-author papers: one row per author, or one row per paper with all student authors in `achievement_text`? | Project team | §F Step 5 reviewer workflow |
| H5 | arXiv version is NOT in the Achievement schema (§F.7). Decide whether the YAML-comment-only convention is sufficient | Project team | None today; future question |
| H6 | arXiv does not identify authors as students — the Chunk 7.11 workflow needs an in-repo document (`STUDENT_IDENTIFICATION_CHECKLIST.md`) | Project team | Could land before or in parallel with §F Step 5 |
| H7 | Student PII policy for arXiv-sourced records (byline + affiliation stored, nothing else; evidence URLs in YAML comments only) | Already documented in Chunk 7.15 `mapping_notes`; no new decision needed | — |
| H8 | What if the arXiv License page wording changes mid-run? | Operational policy: re-verify at every run start; if the collector observed hash differs from the Chunk 7.15 reviewer-verified hash, suspend the run and surface to a human reviewer | §F Step 4 operational discipline |
| H9 | Rate-limit collective-across-machines policy: only one operator machine runs the collector at any time | Operational policy; no code enforcement available | — |
| H10 | Pre-existing `tests/dataset/` collection error (Chunk 7.15 §G) — see §K | Separate chunk; out of scope here | Nothing today — registry- and schema-level tests still pass |
| H11 | Reviewer-independence requirement for §F Step 5 (two independent reviewers per record) can block scaling | Project team: possibly staffing or acceptance of a smaller initial dataset | §F Step 5 throughput |

**No question in this table was silently resolved.**

---

## K. Dataset Test Issue

### K.1 The reported error

Chunk 7.15 reported, during full-suite validation:

```
tests/dataset/test_cli.py        ModuleNotFoundError: No module named 'tests.dataset'
tests/dataset/test_loader.py     ModuleNotFoundError: No module named 'tests.dataset'
tests/dataset/test_validator.py  ModuleNotFoundError: No module named 'tests.dataset'
```

### K.2 Root cause (established in Chunk 7.15)

- `pyproject.toml` sets `pythonpath = ["src"]` only (unchanged since initial scaffold commit `1fbd8ad`, which predates every chunk).
- There is no `tests/__init__.py`.
- The user's Python 3.13 has an **unrelated package named `tests`** installed at `C:\Users\Balaji\AppData\Roaming\Python\Python313\site-packages\tests\__init__.py` that shadows the local `tests/` directory in any `import tests` resolution.
- Collection fails before any test function runs.

### K.3 Investigated in Chunk 7.16?

No. Chunk 7.16 §10 explicitly instructs **"Do not fix this issue in Chunk 7.16"** and **"Document it as an unresolved testing limitation."**

### K.4 Current status

**UNRESOLVED.** Not fixed; not scheduled; not touched in this chunk. Resolution requires one of:
- Add `tests/__init__.py` (schema change to the test layout).
- Add `"."` to `pyproject.toml` `pythonpath`.
- Uninstall the site-packages `tests` package in the user's environment.

All three are out of scope here.

### K.5 Impact on this chunk

None. Chunk 7.16 is design-only; no tests were required to run. The Chunk 7.15 registry-level ingestion and schema tests passed (309 passed, 4 skipped) and continue to be the authoritative check for the arXiv source entry.

---

## L. Safety Audit

Explicit per-item confirmations for Chunk 7.16:

| Item | Confirmation |
|---|---|
| API requests initiated | **No** — zero network calls to arXiv during this chunk |
| Metadata downloaded | **No** |
| Repository files modified | **No** — Chunk 7.16 wrote no file (this report file is a Chunk 7.16-postscript deliverable, generated under the Chunk 7.16 report-generation prompt; see §M) |
| Source registry changed | **No** — `sources.yaml` is unchanged from the Chunk 7.15 state |
| Achievement records created | **No** — `hybrid_dataset/dataset/records/` is unchanged |
| Annotations created | **No** — `hybrid_dataset/dataset/annotations/` is unchanged |
| Dataset splits created | **No** — `hybrid_dataset/processed/splits/` is untouched |
| Taxonomy changed | **No** — all 24 labels remain at prior `draft` state |
| Model, training, or evaluation code changed | **No** — `src/` is untouched |
| Protected files changed | **No** — SHA256s match prior captures (see §B) |
| Staging performed | **No** — no `git add` in Chunk 7.16 |
| Commits performed | **No** — HEAD still at `c8c1b80` |
| Pushes performed | **No** — no `git push` |
| Branch switched, created, or deleted | **No** — still on `feature/nlp-semantic` |
| `pyproject.toml` touched | **No** |
| `tests/__init__.py` created | **No** |
| Installed Python package modified | **No** |
| Teammate directories touched | **No** — `src/ml`, `src/recommender`, `src/backend` do not exist and were not created |
| arXiv source promoted to `verified` | **No** — remains `unreviewed` |
| `lbl_research_pub` promoted to `approved` | **No** — remains `draft` |
| Reviewer identities invented | **No** |
| Chunk 7.4-D reviewer-independence stop | **Preserved** |

---

## M. Final Status

**COMPLETED — READ-ONLY METADATA COLLECTION DESIGN**

### M.1 Scope reminder

This is the design-chunk status. The accompanying report-generation request (which produced this file) wrote a single new file at `reports/chunk_7_16_arxiv_metadata_collection_design.md`. No other repository state was changed by either the Chunk 7.16 design pass or by this report generation.

### M.2 What this chunk does NOT authorize

- Collector implementation.
- Live arXiv API calls.
- Source promotion.
- `lbl_research_pub` promotion.
- Achievement-record creation from arXiv metadata.
- Annotation creation.
- Dataset-split regeneration.
- Any modification to teammate directories.

### M.3 Next actions requiring project-owner decisions

1. Resolve §J H1 (scope of first collection run).
2. Begin Chunk 7.2 source-promotion workflow for the arXiv source (two independent human sign-offs).
3. Begin Chunk 7.2 taxonomy promotion of `lbl_research_pub`.
4. Decide §J H3 (preprint vs peer-reviewed).
5. Decide §J H4 (multi-author rowing policy).

Each is a separate chunk; this design does not pre-empt them.
