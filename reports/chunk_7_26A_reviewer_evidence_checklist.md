# Chunk 7.26A — Human Reviewer Evidence Checklist (Read-Only Audit)

**Report type:** read-only evidence audit for the Chunk 7.26A sign-off packet.
**Audience:** Ashok and Mohan (and anyone preparing follow-up reviewer materials).
**Generated:** 2026-10-24 (session date).
**Final status:** `AUDIT COMPLETE. SOURCE REMAINS "unreviewed". NO SIGN-OFF ENTERED. NO FILES MODIFIED EXCEPT THIS NEW REPORT.`

> This audit cross-walks the ten reviewer areas (D-A through D-J under the current thematic naming) against actual repository evidence. The ten themes in this report use the **current task's naming** (Source Eligibility & Licensing, Data Collection & Source Boundaries, …, Promotion & Remaining Risks). Where that naming overlaps the Chunk 7.26A §3 labels (which use different thematic groupings — mostly single-topic per label), each row below cites the Chunk 7.26A decision point(s) it includes. Nothing in this document is a sign-off, nor a reinterpretation of any prior reviewer decision.

---

## 1. Repository state (verified in this audit)

| Field | Value |
|---|---|
| Branch | `feature/nlp-semantic` |
| HEAD before + after | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` (unchanged — no commit in this audit) |
| Remote sync | in sync (not pushed) |
| Working tree | `M hybrid_dataset/metadata/sources.yaml` + `M pyproject.toml` + `M requirements.txt`; untracked policy / test / report files; `PROJECT_HANDOFF.md` untracked. This audit adds only this one new report. |
| Protected hash `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` ✓ |
| Protected hash `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` ✓ |
| Live source registry (via `load_and_validate_sources`) | `src_5a8a2998d6f44055a42dcfd8991e4d12`: `license='UNKNOWN'`, `status='unreviewed'`<br>`src_08ee850ba4b54d1b81cdbd652809b613`: `license='CC0-1.0'`, `status='unreviewed'` |
| Grep for populated `D-[A-J]_decision: (approve\|revise)` lines in `reports/` | **No matches.** No reviewer sign-off has been posted anywhere in the repository. |

Teammate dirs (`src/ml`, `src/recommender`, `src/backend`) do not exist and were not touched.

---

## 2. Files inspected (read-only)

- `hybrid_dataset/metadata/sources.yaml` (live load).
- `hybrid_dataset/metadata/arxiv_governance_decisions.md`.
- `hybrid_dataset/metadata/SOURCE_REGISTRATION_GUIDE.md`.
- `hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md`.
- `hybrid_dataset/labels/primary_taxonomy.yaml` (via grep for `lbl_research_pub`).
- `src/nlp_semantic/ingestion/arxiv_governance.py` (in prior-chunk context + fresh grep in this audit).
- `src/nlp_semantic/ingestion/rate_limit.py` (same).
- `src/nlp_semantic/ingestion/registry.py`, `manifest.py`, `inventory.py`.
- `src/nlp_semantic/schema/source_registry.py`, `achievement.py`, `annotation.py`, `label_taxonomy.py`, `enums.py`, `evidence.py`.
- `src/nlp_semantic/dataset/validator.py` (`training_ready_subset`).
- `tests/ingestion/test_arxiv_governance.py`, `test_rate_limit.py`, `test_redis_rate_limit.py`, `test_registry.py`, `test_manifest.py`, `test_inventory.py`.
- `reports/chunk_7_16` through `chunk_7_26A`.
- `pyproject.toml`, `requirements.txt`.

Nothing in `src/ml`, `src/recommender`, `src/backend` (do not exist).

---

## 3. D-A through D-J — evidence matrix (current thematic naming)

Legend for Status:
- **VERIFIED** — actual implementation code + passing tests + documentation agree. For URL-based items, "VERIFIED (static)" means the governance text records a prior human observation; reviewer must still re-observe at their own date.
- **PARTIALLY VERIFIED** — code exists and tests exist, but a specific guarantee is unverified (e.g. integration not run, external verification not performed).
- **NOT VERIFIED** — a required check has not been performed; evidence does not exist in the repo yet.
- **NOT APPLICABLE** — the item is procedural, external, or deliberately out-of-scope.

For every row:
1 Requirement · 2 Evidence location · 3 Implementation/test evidence · 4 Status · 5 Reviewer question · 6 Known limitation · 7 Blocker? · 8 Additional evidence needed?

### D-A — Source Eligibility & Licensing

(Chunk 7.26A §3 D-A + D-B + D-C: CC0 metadata wording, API ToU rate-limit wording, metadata-only scope.)

| # | Field | Value |
|---|---|---|
| 1 | Requirement | arXiv source is eligible as a `CC0-1.0`-metadata-licensed source whose current license wording still matches, and the project's intended use fits within CC0 1.0. |
| 2 | Evidence location | `hybrid_dataset/metadata/sources.yaml` arXiv entry's `usage_restrictions` block (CC0 verbatim quote; `https://info.arxiv.org/help/license/index.html` + `https://info.arxiv.org/help/api/tou.html` URLs); `arxiv_governance_decisions.md` §Revision 2. |
| 3 | Implementation/test | `src/nlp_semantic/schema/source_registry.py` enforces `license` as a required 1-200-char field; the registered value is `CC0-1.0`. `tests/ingestion/test_registry.py::test_shipped_sources_file_loads_registered_entries` asserts the entry present. |
| 4 | Status | **PARTIALLY VERIFIED** — the license identifier `CC0-1.0` is recorded and the verbatim quote lives in the entry, but the two external license-evidence URLs have NOT been re-observed within this chunk; they were human-verified at Chunk 7.14 observation date `2026-10-23` and have not been re-verified since. |
| 5 | Reviewer question | On your current observation date, does `https://info.arxiv.org/help/license/index.html` still read, verbatim, "A Creative Commons CC0 1.0 Universal Public Domain Dedication will apply to all metadata."? And does the project's `intended_use` ("primary_type_training_lbl_research_pub_metadata_only") fit within CC0 1.0 permissions? |
| 6 | Known limitation | arXiv page wording may change at any time. CC0 metadata ≠ full-text license. |
| 7 | Blocker? | **YES** — the Chunk 7.17 §5.5 sign-off template requires the reviewer to record their license-page observation date and wording status. |
| 8 | Additional evidence needed? | A current-dated reviewer re-observation of both URLs (the arXiv license page + the arXiv API ToU page). |

### D-B — Data Collection & Source Boundaries

(Chunk 7.26A §3 D-B indirectly; also covers metadata-only scope boundary + endpoint whitelist + `/abs/` scraping prohibition.)

| # | Field | Value |
|---|---|---|
| 1 | Requirement | Any future collector MUST (a) hit only `https://export.arxiv.org/api/query` or `https://oaipmh.arxiv.org/oai`, (b) NOT scrape `/abs/`, `/pdf/`, `/src/`, `/html/`, `/format/` on any arXiv host, (c) honor the 1-request / 3-second + single-connection rate limit, and (d) never download / store PDF / TeX / source archives / figures. |
| 2 | Evidence location | `arxiv_governance_decisions.md` §Revision 1 + §Revision 2 "NOT in scope" block; `sources.yaml` arXiv entry's ENDPOINTS + RATE LIMIT + NOT AUTHORIZED blocks; `src/nlp_semantic/ingestion/arxiv_governance.py` constants + validators; `src/nlp_semantic/ingestion/rate_limit.py`. |
| 3 | Implementation/test | `arxiv_governance.OFFICIAL_METADATA_ENDPOINTS = {"query_api":…, "oai_pmh":…}`; `validate_metadata_endpoint()` function with URL-whitelist + scraping-path rejection; `reject_forbidden_content_type()` for PDF/TeX/archives/images. Tests: `tests/ingestion/test_arxiv_governance.py::TestEndpointValidation` (15 tests, incl. `test_abs_path_rejected_on_arxiv_host`, `test_abs_path_rejected_on_export_arxiv_host`, `test_scrape_rejection_takes_precedence_over_host_whitelist`); `TestForbiddenContentType` (14 parametrized tests). |
| 4 | Status | **PARTIALLY VERIFIED (code) + NOT INTEGRATED (end-to-end)** — the policy surface works in isolation; no collector exists that invokes it. The isolated code enforces (a)+(b)+(d). (c) is covered by the rate-limit code — see D-H. |
| 5 | Reviewer question | Are the two official endpoints the correct metadata endpoints on your observation date? Is the metadata-only scope (title/abstract/authors/identifiers/categories/DOI/journal_ref/comment/dates) the correct permanent arXiv ingestion boundary? |
| 6 | Known limitation | Policy helpers aren't invoked by any production ingestion today (no collector exists). End-to-end enforcement is a future-chunk concern. |
| 7 | Blocker? | **PARTIAL** — enforceable as a policy surface. The reviewer must decide if "policy surface + unit tests + no end-to-end integration yet" is sufficient at the `verified` promotion gate. |
| 8 | Additional evidence needed? | None at the policy-surface level. End-to-end evidence requires a future collector chunk. |

### D-C — Record Eligibility & Student Linkage

(Chunk 7.26A §3 D-E — student-verification gate; plus preprint classification from D-F indirectly; plus Chunk 7.11 five-stage review workflow context.)

| # | Field | Value |
|---|---|---|
| 1 | Requirement | Linking an arXiv paper to a student profile requires at least one of (verified ORCID, verified institutional email, advisor verification). Name similarity, affiliation strings, and author position are NEVER sufficient. Preprint-vs-peer-reviewed is caller-supplied via explicit flags; no inference from arXiv id / date / title / authors / abstract. |
| 2 | Evidence location | `arxiv_governance_decisions.md` §Revision 3; `src/nlp_semantic/ingestion/arxiv_governance.py` `StudentVerificationEvidence`, `authorize_student_link()`, `MissingStudentVerificationError`, `PeerReviewStatus`, `assess_peer_review_status()`. Chunk 7.11 §C-D student-identification workflow (described in prior-chunk reports). |
| 3 | Implementation/test | `TestStudentAttribution` (7 tests incl. `test_no_name_similarity_shortcut_exists`); `TestPeerReviewStatus` (6 tests covering "DOI present but unverified still preprint" / "verified flag without field still preprint" paths). |
| 4 | Status | **PARTIALLY VERIFIED (gate)** — gate function behaves correctly on caller-supplied booleans. **NOT INTEGRATED** — no record-creation path calls the gate. **UPSTREAM** — the module does NOT itself verify ORCIDs, institutional emails, or advisor sign-offs; those are caller responsibilities. |
| 5 | Reviewer question | Are (verified ORCID, verified institutional email, advisor verification) the correct three accepted student-verification paths? Is "upstream verification is the caller's responsibility" an acceptable architectural split? Is the default-preprint classification correct? |
| 6 | Known limitation | Caller-supplied booleans; module takes callers at their word. No ingestion path invokes the gate today. |
| 7 | Blocker? | **PARTIAL** — gate exists and is unit-tested. Reviewer must accept the upstream-caller split. |
| 8 | Additional evidence needed? | None at the policy-surface level. End-to-end evidence requires a future collector + per-paper review chunk. |

### D-D — Privacy & Personal Information

(Chunk 7.26A §3 D-G — email redaction + no-logger posture; also PII policy from the SIH precedent.)

| # | Field | Value |
|---|---|---|
| 1 | Requirement | Submitter contact emails MUST be redacted from any log output. Only public byline + arXiv paper ID stored; no email, phone, student ID, personal website, or other PII. |
| 2 | Evidence location | `arxiv_governance_decisions.md` §Revision 4 Contact privacy; `src/nlp_semantic/ingestion/arxiv_governance.py` `redact_contact_emails()`, `_EMAIL_RE`; `sources.yaml` PRIVACY block. |
| 3 | Implementation/test | `redact_contact_emails(text)` returns text with email-like substrings replaced by `[REDACTED_EMAIL]`. `TestEmailRedaction` (6 tests covering single, multiple, no-email, empty, exception-message scenario, debug-payload scenario). |
| 4 | Status | **PARTIALLY VERIFIED (redaction function) + NOT INTEGRATED (no logger)** — function exists and is unit-tested; the repo has no logger in `src/` (`grep -rln "logger\." src/` returns no production hits). Chunk 7.19 §9.1 flags obfuscated-email patterns (`foo [at] bar`) as a documented regex gap. |
| 5 | Reviewer question | Is "no logger exists today; redaction is a policy surface awaiting a logging pathway" acceptable at the current promotion gate? Does the regex gap matter? |
| 6 | Known limitation | Obfuscated-email detection out of scope. The regex won't catch `foo (at) example (dot) com`-style text. |
| 7 | Blocker? | **PARTIAL** — reviewer must accept the no-logger posture or require integration before promotion. |
| 8 | Additional evidence needed? | None at policy-surface level. End-to-end evidence requires a future logger + collector chunk. |

### D-E — Annotation & Label Governance

(Separate from the Chunk 7.26A §3 reviewer-only decisions; covers `lbl_research_pub` taxonomy status, Chunk 6 dual annotation workflow, Chunk 7.1 taxonomy guidelines, and the `training_ready_subset` label gate.)

| # | Field | Value |
|---|---|---|
| 1 | Requirement | Any arXiv-derived Achievement record intended for training must reference a `primary_type` label whose `TaxonomyStatus == APPROVED`. `annotation_status.<task> == VERIFIED` is required per task before `training_ready_subset` returns the record. Taxonomy promotion follows `TAXONOMY_APPROVAL_CHECKLIST.md` (two independent sign-offs, same template as source promotion). |
| 2 | Evidence location | `src/nlp_semantic/dataset/validator.py` `training_ready_subset()` function (lines 321-371); `src/nlp_semantic/schema/enums.py` `TaxonomyStatus`, `AnnotationStatus`; `hybrid_dataset/labels/primary_taxonomy.yaml` (status fields); `hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md`. |
| 3 | Implementation/test | `training_ready_subset` filters on label status `APPROVED` + source `VERIFIED` + license ≠ `UNKNOWN` + per-task `annotation_status: VERIFIED`. `tests/dataset/test_validator.py` exercises this (34 passing). |
| 4 | Status | **VERIFIED (code) + UNRESOLVED (data state)** — the gate code works; the DATA does not yet satisfy the gate. **`lbl_research_pub` is still `status: draft`.** No arXiv-derived Achievement records exist. |
| 5 | Reviewer question | Note that source promotion alone does NOT unlock training. Any downstream expectation that arXiv records flow into training must additionally wait for (a) `lbl_research_pub` to be promoted to `approved` via a separate `TAXONOMY_APPROVAL_CHECKLIST.md` workflow, (b) a collector to exist, (c) per-record annotations to reach `VERIFIED`. Are you comfortable approving the source knowing the training-eligibility chain still has these open gates? |
| 6 | Known limitation | `lbl_research_pub` promotion is a separate chunk; not Chunk 7.26A's scope. |
| 7 | Blocker? | **NO (for source promotion specifically)** — the Chunk 7.17 §5.8 gate does not require `lbl_research_pub` to be `approved` before source `verified`. BUT it is a blocker for dataset readiness. |
| 8 | Additional evidence needed? | None for source promotion. For training eligibility: separate `lbl_research_pub` promotion chunk + collector + annotations. |

### D-F — Dataset Readiness & Training Eligibility

| # | Field | Value |
|---|---|---|
| 1 | Requirement | Clear separation between "source promoted to `verified`" and "dataset is training-ready." Source promotion unlocks ONE of multiple preconditions; it does NOT make records training-ready. |
| 2 | Evidence location | `arxiv_governance_decisions.md` §Not changed by this chunk; `reports/chunk_7_17_...md` §3.F separate-decisions table (rows 4 vs 5-9); `reports/chunk_7_25_...md` §7 dataset-readiness-limitations table. |
| 3 | Implementation/test | `training_ready_subset()` currently returns an empty subset for the arXiv source (source not `verified`; label `draft`). After hypothetical promotion, it still returns zero records (no records exist; no collector). |
| 4 | Status | **DOCUMENTED (procedural); UNRESOLVED (end-to-end) across multiple independent gates.** |
| 5 | Reviewer question | Do you acknowledge that an `approve` on this source does NOT make the dataset training-ready, and specifically does NOT (a) create any arXiv-derived Achievement record, (b) promote `lbl_research_pub` to `approved`, (c) generate any new training-ready records? |
| 6 | Known limitation | Dataset-readiness blockers persist regardless of source-promotion outcome: K4 (no collector), K11 (chained preconditions), and Chunk 7.25 §7. |
| 7 | Blocker? | **NO** for source promotion. **YES** for dataset readiness, independently. |
| 8 | Additional evidence needed? | None. Each downstream gate has its own chunk. |

### D-G — Governance Enforcement & Implementation

(Chunk 7.26A §3 D-C + D-F — scope + withdrawal handling; also combines the acknowledgment/canonical-link policy.)

| # | Field | Value |
|---|---|---|
| 1 | Requirement | Governance policies (metadata-only scope, forbidden content types, preprint classification, withdrawal detection, student-link gate, acknowledgment, canonical links, email redaction) are implemented as code modules + Pydantic models + unit tests. End-to-end integration is a future-chunk concern. |
| 2 | Evidence location | `src/nlp_semantic/ingestion/arxiv_governance.py` (entire module); `tests/ingestion/test_arxiv_governance.py` (76 tests across 7 test classes). |
| 3 | Implementation/test | The policy module exposes `OFFICIAL_METADATA_ENDPOINTS`, `ARXIV_ACKNOWLEDGMENT`, `CC0_LICENSE_URI`, `validate_metadata_endpoint`, `reject_forbidden_content_type`, `ArxivMetadataRecord`, `PeerReviewStatus`, `assess_peer_review_status`, `is_withdrawn`, `StudentVerificationEvidence`, `authorize_student_link`, `canonical_abs_link`, `redact_contact_emails`, + 4 custom exceptions. All 76 test classes pass. |
| 4 | Status | **VERIFIED (code + unit tests) + NOT INTEGRATED (no production caller)** — Chunk 7.19 audit confirmed this; the gap is architectural and expected. |
| 5 | Reviewer question | Is the policy-surface-only enforcement scope acceptable at the current promotion gate? (The Chunk 7.19 audit §4-§9 characterization explicitly identifies which specific policies are "implemented + tested" vs "not integrated into collector/logger.") |
| 6 | Known limitation | Chunk 7.19 B2 — "no ingestion / collection / logger pathway exists." Expected until a future collector chunk. |
| 7 | Blocker? | **PARTIAL** — depends on reviewer tolerance for policy-surface-only enforcement at the source-promotion stage. |
| 8 | Additional evidence needed? | None at policy-surface level. |

### D-H — Infrastructure & Redis Readiness

(Chunk 7.26A §3 D-D — Mohan's primary residual; combines rate-limit code + Redis coordinator + real-Redis integration + cross-machine operational verification.)

| # | Field | Value |
|---|---|---|
| 1 | Requirement | Rate-limit code must enforce ≥ 3 s between requests + single connection, collectively across machines. If a shared coordinator is required, it must be implemented with atomic operations, fail-closed semantics, no silent fallback, and must be verified against real infrastructure. |
| 2 | Evidence location | `src/nlp_semantic/ingestion/rate_limit.py` entire file (Protocol + `_ArxivCoordinator` + `_DEFAULT_COORDINATOR` + `RedisCoordinator` + factory + errors); `arxiv_governance_decisions.md` §Revision 1 (Architectural evolution; Compensating operator discipline). Reports: Chunk 7.19 §Phase 3, Chunk 7.20 §5-§7, Chunk 7.21 §Final status, Chunk 7.22 §4-§10, Chunk 7.23 §9. |
| 3 | Implementation/test | `tests/ingestion/test_rate_limit.py` (24 tests covering shared default coordinator + exception safety); `tests/ingestion/test_redis_rate_limit.py` (31 passing fakeredis unit tests + 1 integration test correctly skipped on missing `ARXIV_TEST_REDIS_URL`). |
| 4 | Status | **PARTIALLY VERIFIED** — code shipped + fakeredis unit tests pass + fail-closed semantics unit-tested. **NOT VERIFIED (real Redis integration)** — `TestRedisIntegration` skipped on missing env var; no local test Redis available (Chunk 7.23 §3 confirmed no `redis-server` on `$PATH`, no running Redis process, no `ARXIV_RATE_COORDINATOR_URL` set). **NOT VERIFIED (cross-machine operational)** — requires ≥ 2 machines sharing one Redis endpoint. **UNRESOLVED (deployment)** — no production Redis endpoint is configured anywhere. |
| 5 | Reviewer question | **Mohan's primary residual.** Do you accept the current implementation + documented operator discipline (one process, one machine) as sufficient for `review_status: verified`? OR must real-Redis cross-machine operational verification complete first? |
| 6 | Known limitation | Chunk 7.19 §Phase 3 explicitly classifies the global cross-machine requirement as "NOT SATISFIED by code." Operator-discipline is procedural, not code-enforced. |
| 7 | Blocker? | **YES for cross-machine operational guarantee. OPEN for policy-surface + operator-discipline posture.** Reviewer decision. |
| 8 | Additional evidence needed? | Reviewer-dependent. If reviewer requires real-Redis verification: a future Chunk 7.26 (local-Redis test execution) and then a staged two-machine test. If reviewer accepts operator discipline: no additional evidence. |

### D-I — Test Evidence & Regression Safety

(Chunk 7.26A §3 D-H — Chunk 7.24 test infrastructure fix.)

| # | Field | Value |
|---|---|---|
| 1 | Requirement | The test suite must collect without errors and give reproducible pass counts the reviewers can trust. The Chunk 7.15 → 7.23 `tests/dataset/` collection error must be resolved so the 152 dataset tests actually run. |
| 2 | Evidence location | `tests/__init__.py` + `tests/schema/__init__.py` (Chunk 7.24 additions) + `pyproject.toml` `pythonpath = ["src", "."]` extension; `reports/chunk_7_24_...md` §4. |
| 3 | Implementation/test | Chunk 7.24 report records: `tests/dataset/` 152 passed, 0 failed, 0 collection errors; `tests/ingestion/` 206 passed, 5 skipped; `tests/schema/` 231 passed; full combined 592 passed, 5 skipped, 0 failed, 0 collection errors. Chunk 7.24 re-verification run confirmed identical counts. This audit did NOT re-execute tests (the test numbers it quotes are from Chunk 7.24's reproduced run; re-executing would waste cycles without producing new evidence). |
| 4 | Status | **VERIFIED (via the Chunk 7.24 re-execution).** |
| 5 | Reviewer question | Is the three-file Chunk 7.24 fix (`tests/__init__.py`, `tests/schema/__init__.py`, `pyproject.toml` pythonpath) acceptable as a non-production-affecting hygiene change that lets you trust the 592-pass count? |
| 6 | Known limitation | 4 of the 5 skips are pre-existing inventory platform skips. 1 is the Redis integration skip (ties to D-H). Full-suite tests cover the policy modules + schema + ingestion; they do NOT test end-to-end collection (no collector exists). |
| 7 | Blocker? | **NO** (the fix clears the pre-existing error; test counts are now trustworthy). |
| 8 | Additional evidence needed? | None. |

### D-J — Promotion, Approval & Remaining Risks

| # | Field | Value |
|---|---|---|
| 1 | Requirement | Source promotion to `review_status: verified` requires the Chunk 7.17 §5.8 five-point gate + the Chunk 7.26A §6 eight-point promotion checklist to both be satisfied, including TWO INDEPENDENT HUMAN SIGN-OFF BLOCKS with `overall_decision: approve`. |
| 2 | Evidence location | Chunk 7.17 §5.8 (5-point gate); Chunk 7.26A §6 (8-point checklist); `arxiv_governance_decisions.md` opening paragraph ("Implementation does NOT equal approval"). |
| 3 | Implementation/test | None applicable — this is a procedural/policy area. Chunk 7.26A §7 and §8 contain the blank reviewer sign-off templates. |
| 4 | Status | **NOT VERIFIED (sign-offs absent).** No populated reviewer sign-off blocks exist anywhere in the repo (confirmed by `grep -rnE "^D-[A-J]_decision:\s*(approve\|revise)\b" reports/` returning zero matches). |
| 5 | Reviewer question | Based on your independent evaluation of D-A through D-I above, do you set your `overall_decision` to `approve` or `revise`? If `revise`, which specific decision point(s) must change first? |
| 6 | Known limitation | Ashok's prior APPROVE pre-dates the Chunk 7.18/7.20/7.22 revisions. Mohan's prior REVISE is not an approval. Neither prior decision is binding for the current scope. |
| 7 | Blocker? | **YES — this is THE source-promotion gate.** No promotion is possible without two independent approve sign-offs. |
| 8 | Additional evidence needed? | Two populated independent sign-off blocks (one from Ashok, one from Mohan) in a tracked location (PR comment, dedicated review file, etc.). The Chunk 7.26A §7 and §8 templates specify the required field set. |

---

## 4. K1-K11 known-limitation matrix

Status column: **ACCEPTED (reviewer must decide)** / **DOCUMENTED (procedural)** / **OPEN (requires future chunk)**.

| K # | Limitation | Current status | Blocker for source promotion? | Reviewer must weigh |
|---|---|---|---|---|
| K1 | **Real-Redis integration test NOT executed.** `TestRedisIntegration` skipped on missing `ARXIV_TEST_REDIS_URL`; no local test Redis. | OPEN (requires authorized local Redis; Chunk 7.23 §5 setup instructions) | **PARTIAL — depends on D-H decision.** HIGH if reviewer requires code-tested cross-machine; LOW if reviewer accepts operator discipline. | Yes (D-H) |
| K2 | **Cross-machine operational verification NOT performed.** | OPEN (requires ≥ 2 machines + staged deployment) | Same as K1 — depends on D-H. | Yes (D-H) |
| K3 | **No Redis infrastructure provisioned.** `ARXIV_RATE_COORDINATOR_URL` unset; in-process coordinator remains the operational default. | OPEN (requires Aryan's authorization + deployment) | Same as K1 — depends on D-H. | Yes (D-H) |
| K4 | **No collector exists.** All governance helpers are policy surfaces with no production callers. | OPEN (requires a future collector chunk) | **PARTIAL** — reviewer must decide if policy-surface + unit-test coverage is sufficient at the source-promotion stage. | Yes (D-G, D-F) |
| K5 | **Single-Redis-endpoint design** (no Redlock multi-master). A partition could, in principle, admit two slots. | DOCUMENTED (non-guarantee stated in `rate_limit.py` docstring + Chunk 7.22 §4.2) | LOW at project scale. | Only if reviewer requires Redlock. |
| K6 | **Withdrawal regex heuristic.** False-positive + false-negative risks documented. | DOCUMENTED (Chunk 7.19 §7.3 risk analysis). | LOW-MEDIUM — `is_withdrawn()` is a positive-signal-only function; reviewer must accept the characterization. | Yes (addressed in D-G) |
| K7 | **Email redaction regex** doesn't match obfuscated `foo [at] bar` patterns. | DOCUMENTED (Chunk 7.19 §9.1). | LOW. | Only if reviewer requires obfuscated-pattern handling. |
| K8 | **External verification pipelines upstream.** `authorize_student_link` takes caller-supplied booleans; doesn't itself verify ORCID / institutional email / advisor sign-off. | DOCUMENTED (Chunk 7.19 §8.2). | Reviewer must accept the architectural split. | Yes (D-C) |
| K9 | **Orphan site-packages `tests` package** still exists in the user's Python environment; worked around by the Chunk 7.24 fix. | DOCUMENTED + WORKED-AROUND (Chunk 7.24 §3). | LOW. | Yes (D-I) — reviewer confirms the fix is acceptable. |
| K10 | **`ArxivRateLimiter` facade** doesn't yet expose a `coordinator=` kwarg (reaches Redis only via `make_coordinator_from_env()`). | DOCUMENTED (Chunk 7.22 §10 L4). | LOW (no caller exists). | Only if reviewer requires the facade extension. |
| K11 | **Dataset readiness blocked** even after a successful source promotion: `lbl_research_pub` is `draft`; no collector; no arXiv-derived records; `training_ready_subset` returns none. | OPEN (chain of separate chunks). | NO for source promotion. YES for dataset readiness, independently. | Yes (D-E, D-F) |

---

## 5. Eight promotion-condition status matrix (from Chunk 7.26A §6)

| # | Promotion condition | Current status | Blocker? |
|---|---|---|---|
| 1 | Reviewer 1 (Ashok) sign-off block present with `decision: approve` | **NOT MET** — no populated Reviewer-1 block exists | **YES** |
| 2 | Reviewer 2 (Mohan) sign-off block present with `decision: approve` | **NOT MET** — no populated Reviewer-2 block exists | **YES** |
| 3 | Both sign-off blocks posted independently (independence rules per Chunk 7.17 §2.6) | **NOT APPLICABLE YET** — can only be verified once blocks exist | Blocker-adjacent to #1 and #2 |
| 4 | Neither reviewer is the proposer (Aryan) | **NOT APPLICABLE YET** — depends on who posts #1 and #2 | — |
| 5 | Neither sign-off is AI-generated | **NOT APPLICABLE YET** — depends on #1 and #2 provenance | — |
| 6 | No reviewer decision is `revise` | **NOT APPLICABLE YET** — depends on #1 and #2 content | — |
| 7 | Both `license_page_wording` and `tou_page_wording` are `match` (or both explicitly approved change) | **NOT APPLICABLE YET** — depends on reviewer re-observation | — |
| 8 | The Chunk 7.17 §5.8 five-point gate is satisfied | **NOT MET** — subsumes #1 and #2 | **YES** |

**Conclusion:** 0 of 8 conditions are currently met. Primary blockers are #1 and #2 (and transitively #8). The remaining five conditions are gated on #1/#2.

---

## 6. Test evidence (from Chunk 7.24 verification; what the tests do and do NOT prove)

### 6.1 What the tests DO prove

- Governance policy functions behave correctly in isolation (76 arxiv_governance tests).
- Rate limiter behaves correctly within one Python process, including multi-instance sharing + exception safety (24 rate_limit tests).
- Redis coordinator behaves correctly against `fakeredis[lua]` (31 Redis tests), including fail-closed semantics, Lua-script atomicity, factory parsing, URL-not-leaked-in-errors.
- `training_ready_subset` correctly excludes records that don't meet all four gates (34 validator tests).
- Source registry schema + loader + manifest cross-validation work (75 ingestion tests).
- The orphan `tests` shadow is worked around; dataset tests collect (152 dataset tests, previously 3 collection errors).

### 6.2 What the tests do NOT prove

- They do NOT prove the governance policies are invoked by any production code (no collector exists).
- They do NOT prove the Redis coordinator works against a real Redis server (integration test skipped).
- They do NOT prove cross-machine rate-limit coordination (operational test, not CI).
- They do NOT prove the acknowledgment is actually displayed to users (no UI surface).
- They do NOT prove the email redaction is actually applied before any log emission (no logger exists).
- They do NOT prove the student-verification pipelines (ORCID, email, advisor) work (external, upstream).
- They do NOT prove the arXiv license page content on the reviewer's observation date.
- They do NOT prove `lbl_research_pub` is approved (it is still `draft`).
- They do NOT prove any arXiv-derived Achievement record is or ever will be training-ready.

### 6.3 Test counts (unchanged since Chunk 7.24)

| Suite | Passed | Skipped | Failed | Collection errors |
|---|---|---|---|---|
| `tests/dataset/` | 152 | 0 | 0 | 0 |
| `tests/ingestion/` | 206 | 5 | 0 | 0 |
| `tests/schema/` | 231 | 0 | 0 | 0 |
| `tests/test_smoke.py` | 3 | 0 | 0 | 0 |
| **Full combined** | **592** | **5** | **0** | **0** |

Expected skips: 4 inventory platform skips + 1 `TestRedisIntegration` skip (missing `ARXIV_TEST_REDIS_URL`).

---

## 7. Current source and promotion status

| Field | Current value |
|---|---|
| Source id | `src_08ee850ba4b54d1b81cdbd652809b613` |
| License | `CC0-1.0` |
| `review_status` | **`unreviewed`** |
| Promotion status | **BLOCKED** — zero of eight Chunk 7.26A §6 conditions met |
| Reviewer 1 sign-off (Ashok) | **NOT PRESENT in the repository** |
| Reviewer 2 sign-off (Mohan) | **NOT PRESENT in the repository** |
| Previous Ashok APPROVE | preserved as historical record (pre-revision scope); does NOT cover the current implementation |
| Previous Mohan REVISE | preserved as historical record; is NOT an approval |
| Chunk 7.26A packet exists? | ✓ `reports/chunk_7_26A_independent_reviewer_sign_off_packet.md` (27,486 bytes) |

---

## 8. Missing reviewer evidence (summary)

The following must be posted to a tracked location (e.g. PR comments on a dedicated promotion PR, or a committed `reviews/` directory) before source promotion is possible:

1. **Ashok's current-scope sign-off block** (Chunk 7.26A §7 template, with every `<…>` placeholder replaced by a real value).
2. **Mohan's current-scope sign-off block** (Chunk 7.26A §8 template, with every `<…>` placeholder replaced by a real value).
3. Both blocks must be posted **independently** per the Chunk 7.17 §2.6 reviewer-independence rules.
4. Both must specifically answer D-A through D-I (per this audit's labels) AND the Chunk 7.26A §3 D-A through D-I decisions. The two label sets are different thematic groupings of overlapping evidence; a reviewer sign-off following the Chunk 7.26A §7/§8 template will satisfy both.
5. The `overall_decision` field must be a literal `approve` or `revise` (NOT a pipe-template string).
6. The `license_page_observed_on` and `tou_page_observed_on` fields must be real ISO dates reflecting the reviewer's own re-observation.
7. The `rationale` field must contain real sentences (not placeholder text).

**No AI output qualifies as a reviewer sign-off.** No prior decision qualifies as a current-scope sign-off.

---

## 9. Reviewer-decision placeholders (BLANK — audit explicitly does not populate)

### 9.1 Reviewer 1 (Ashok) — placeholder, blank

```
Reviewer 1 (Ashok) decisions on this audit (DO NOT fill in here; post the
Chunk 7.26A §7 sign-off block to a tracked location instead):

D-A Source Eligibility & Licensing          : <not yet decided by Ashok>
D-B Data Collection & Source Boundaries     : <not yet decided by Ashok>
D-C Record Eligibility & Student Linkage    : <not yet decided by Ashok>
D-D Privacy & Personal Information          : <not yet decided by Ashok>
D-E Annotation & Label Governance           : <not yet decided by Ashok>
D-F Dataset Readiness & Training Eligibility: <not yet decided by Ashok>
D-G Governance Enforcement & Implementation : <not yet decided by Ashok>
D-H Infrastructure & Redis Readiness        : <not yet decided by Ashok>
D-I Test Evidence & Regression Safety       : <not yet decided by Ashok>
D-J Promotion, Approval & Remaining Risks   : <not yet decided by Ashok>

overall_decision: <not yet decided by Ashok>
```

### 9.2 Reviewer 2 (Mohan) — placeholder, blank

```
Reviewer 2 (Mohan) decisions on this audit (DO NOT fill in here; post the
Chunk 7.26A §8 sign-off block to a tracked location instead):

D-A Source Eligibility & Licensing          : <not yet decided by Mohan>
D-B Data Collection & Source Boundaries     : <not yet decided by Mohan>
D-C Record Eligibility & Student Linkage    : <not yet decided by Mohan>
D-D Privacy & Personal Information          : <not yet decided by Mohan>
D-E Annotation & Label Governance           : <not yet decided by Mohan>
D-F Dataset Readiness & Training Eligibility: <not yet decided by Mohan>
D-G Governance Enforcement & Implementation : <not yet decided by Mohan>
D-H Infrastructure & Redis Readiness        : <not yet decided by Mohan>
D-I Test Evidence & Regression Safety       : <not yet decided by Mohan>
D-J Promotion, Approval & Remaining Risks   : <not yet decided by Mohan>

overall_decision: <not yet decided by Mohan>
```

**Explicit statement, per the Chunk 7.26A §Reviewer Decision Handling instruction:** **Current-scope independent decisions have NOT been established.** No actual signed reviewer evidence exists in the repository as of this audit. Ashok's and Mohan's prior decisions (APPROVE for a pre-revision scope; REVISE pending revisions) are preserved as historical facts and are NOT treated as current-scope approvals.

---

## 10. Is the packet ready to send to human reviewers?

### 10.1 Yes — the packet (Chunk 7.26A) and this evidence checklist are ready to send to Ashok and Mohan.

The two documents together give the reviewers:
- A complete evidence trail (this audit's D-A through D-J matrix + K1-K11 matrix + 8-condition matrix).
- Pointers to every relevant source file, test, and prior report.
- Honest status labels (VERIFIED / PARTIALLY VERIFIED / NOT VERIFIED / NOT APPLICABLE).
- Explicitly named gaps (K1-K11) that each reviewer must weigh.
- Blank sign-off templates (Chunk 7.26A §7 for Ashok, §8 for Mohan) with angle-bracketed placeholders making it unambiguous that nothing has been filled in on their behalf.
- A clear 8-point promotion gate and the current state (0 of 8 met; blocker is the absence of two independent approve sign-offs).
- A preserved record of prior reviewer decisions (Ashok APPROVE pre-revision, Mohan REVISE) that is explicitly NOT reinterpreted.

### 10.2 Reviewer workflow

1. Each reviewer independently reads this audit + the Chunk 7.26A packet.
2. Each reviewer re-opens the two arXiv evidence URLs on their own observation date.
3. Each reviewer makes an independent decision on D-A through D-J.
4. Each reviewer posts their Chunk 7.26A §7 (Ashok) or §8 (Mohan) sign-off block to a tracked location (PR comment, review file).
5. The eight promotion conditions are rechecked by whoever runs the next chunk.
6. Only if ALL 8 conditions are met does a FUTURE chunk perform the single-field YAML edit `review_status: unreviewed → verified`.

### 10.3 What "ready to send" does NOT mean

- Does NOT mean the source will be promoted.
- Does NOT mean reviewers will approve.
- Does NOT mean the dataset is training-ready even after a successful promotion (K11, D-F).
- Does NOT mean cross-machine Redis coordination has been operationally verified (K1, K2, D-H).
- Does NOT mean a collector exists (K4, D-G).

---

## 11. Confirmation — no modification beyond this new audit report

- No API request initiated ✓
- No metadata collected ✓
- No download performed (no PDF, no TeX, no source archive, no full text) ✓
- No achievement record created ✓
- No annotation created ✓
- No dataset split generated ✓
- No taxonomy promoted ✓
- No source promoted ✓
- `src_08ee850ba4b54d1b81cdbd652809b613` remains `review_status: unreviewed` ✓
- Ashok APPROVE and Mohan REVISE outcomes preserved as historical facts, NOT reinterpreted ✓
- No reviewer identity, date, decision, rationale, or sign-off entered ✓
- No tracker/placeholder was converted into a sign-off ✓
- No stage, no commit, no push, no branch switch ✓
- No teammate directory touched (none exist) ✓
- `src/*` not modified ✓
- `tests/*` not modified in this audit ✓
- `pyproject.toml`, `requirements.txt` not modified ✓
- `hybrid_dataset/metadata/sources.yaml` not modified ✓
- `hybrid_dataset/metadata/arxiv_governance_decisions.md` not modified ✓
- `PROJECT_HANDOFF.md` not modified ✓
- No Redis endpoint contacted (known or unknown) ✓
- No arXiv endpoint contacted ✓
- No infrastructure provisioned ✓
- Protected hashes unchanged ✓
- Chunk 7.4-D reviewer-independence stop preserved ✓
- No source code or configuration changed; the only on-disk effect is the creation of this one new report file ✓

---

## 12. Final status

**AUDIT COMPLETE. SOURCE REMAINS `unreviewed`. PACKET READY TO SEND TO ASHOK AND MOHAN. NO CURRENT-SCOPE REVIEWER DECISIONS EXIST. PROMOTION IS BLOCKED PENDING TWO INDEPENDENT SIGN-OFF BLOCKS.**

Next step (external to this chunk; not Claude-executed): Ashok and Mohan independently work through this audit + the Chunk 7.26A packet, re-observe the two external evidence URLs, and post their individual sign-off blocks per the Chunk 7.26A §7 / §8 templates to a tracked location. A FUTURE narrowly scoped chunk re-checks the 8 promotion conditions and, only if all are met, performs the single-field YAML edit.
