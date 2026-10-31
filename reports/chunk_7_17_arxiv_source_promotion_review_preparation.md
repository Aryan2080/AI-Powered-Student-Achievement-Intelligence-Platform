# Chunk 7.17 — arXiv Source Promotion Review Preparation (Read-Only)

**Report type:** source-review preparation packet for two independent human reviewers.
**Generated:** 2026-10-23 (session date).
**Final status:** `COMPLETED — ARXIV SOURCE PROMOTION REVIEW PACKET PREPARED. SOURCE REMAINS UNREVIEWED.`

> This packet does **not** promote the arXiv source. It assembles the material two independent human reviewers need to run the Chunk 6 / `SOURCE_REGISTRATION_GUIDE.md` sign-off. All reviewer-decision fields are deliberately blank.

---

## 1. Repository state

| Field | Value |
|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` |
| Branch | `feature/nlp-semantic` |
| HEAD before | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` |
| HEAD after | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` (unchanged — no commit) |
| Remote sync | `## feature/nlp-semantic...origin/feature/nlp-semantic` — in sync (not pushed) |
| Working tree before | ` M hybrid_dataset/metadata/sources.yaml` (Chunk 7.15 arXiv registration, uncommitted); `?? PROJECT_HANDOFF.md`; `?? reports/` (Chunk 7.16 report) |
| Working tree after | same, plus the single new file `reports/chunk_7_17_arxiv_source_promotion_review_preparation.md` (this file) |
| Teammate dirs (`src/ml`, `src/recommender`, `src/backend`) | Do not exist. Not touched. |

### 1.1 Protected hash verification

| File | Expected | Observed | Match |
|---|---|---|---|
| `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | ✓ |
| `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ✓ |

Verification performed at session start and preserved through the chunk (no file writes other than this report).

### 1.2 Source under review — current registry state

Captured directly from `hybrid_dataset/metadata/sources.yaml` via `load_and_validate_sources`:

| Field | Value |
|---|---|
| `source_id` | `src_08ee850ba4b54d1b81cdbd652809b613` |
| `source_name` | `arXiv` |
| `source_url` | `https://arxiv.org/` |
| `license` | `CC0-1.0` |
| `collection_date` | `2026-10-23` |
| `intended_use` | `primary_type_training_lbl_research_pub_metadata_only` |
| `review_status` | `unreviewed` |
| `is_synthetic` | `false` |
| `original_labels` | `[]` |
| Shows up in `unknown_license_ids`? | No (license is `CC0-1.0`, not `UNKNOWN`) |
| Shows up in `unverified_source_ids`? | Yes (`review_status: unreviewed`) |

---

## 2. Existing source-review workflow — findings

### 2.1 Authoritative documents (read in this chunk)

1. `hybrid_dataset/metadata/SOURCE_REGISTRATION_GUIDE.md` (read in Chunks 7.14 / 7.15 / 7.16; no change observed).
2. `hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md` (read in this chunk) — the parallel checklist for label promotion. Its reviewer-independence rules and sign-off template are the project's precedent and are explicitly referenced here where the source-registration guide is less specific.
3. `src/nlp_semantic/schema/source_registry.py` — the `SourceRegistry` Pydantic model and its field constraints.
4. `src/nlp_semantic/dataset/validator.py` — the `training_ready_subset` function, which gates training eligibility on `review_status == VERIFIED` **and** `license != UNKNOWN`.

### 2.2 What `review_status: verified` means to the code

A record is training-ready **only when all of**:
1. `annotation_status.<task> == VERIFIED` (per-task) — the Achievement's parent annotations are complete.
2. `primary_type` / `domain_tags` references labels with `status == APPROVED`.
3. `source.review_status == VERIFIED`.
4. `source.license.strip().upper() != "UNKNOWN"` (case-insensitive).

`review_status == VERIFIED` is a human-set flag. Code trusts the flag; it does **not** independently re-verify legal compliance.

### 2.3 Workflow as documented by `SOURCE_REGISTRATION_GUIDE.md`

The guide prescribes five steps:

1. **Draft entry.** PR adds one new source with `review_status: unreviewed`, `is_synthetic: false`, and the pre-registration checklist filled on the PR description. Source ID is generated via `make_id("src")`.
2. **First reviewer.** A different team member walks through the pre-registration checklist against the source itself.
3. **Second reviewer.** A second team member re-verifies the license and provenance claims. **Two sign-offs required.**
4. **Promote.** The author updates `review_status: verified` in a follow-up commit on the same PR, referencing both reviewers' sign-offs.
5. **Merge.** Only after both sign-offs and the Chunk 4 ingestion loader validates the entry (`python -m nlp_semantic.ingestion.inventory`).

### 2.4 Pre-registration checklist as prescribed by the guide

The guide groups the checklist into four categories:

**Provenance**
- Stable canonical URL (not session-scoped or rate-limited).
- URL resolves without authentication for anyone with public access.
- Content described in `source_name` is actually present at the URL.
- `collection_date` reflects the date the content was observed.

**License and reuse terms**
- A written license, ToS, or usage statement is visible at the source.
- The license text has been read in full; its canonical identifier noted.
- The license permits the intended uses described in `intended_use`.
- Attribution requirements captured in `usage_restrictions`.
- Share-alike / derivative restrictions captured in `usage_restrictions`.
- If license is unknown or ambiguous: use `UNKNOWN` + `unreviewed`.

**Privacy and PII**
- Content does not include student personal data that cannot be rephrased or removed.
- If names appear only as public bylines, downstream policy decided and noted in `mapping_notes`.
- No credentials embedded in `source_url` (Chunk 4 boundary rejects these).

**Original labels**
- Source's own labels captured verbatim in `original_labels`; no silent remapping.

### 2.5 Observed gap — no source-specific sign-off template

The `TAXONOMY_APPROVAL_CHECKLIST.md` prescribes a strict per-reviewer PR-comment template with required fields (`label_id`, `reviewer`, `date`, `decision`, `rationale`), and names a four-state disagreement workflow. The `SOURCE_REGISTRATION_GUIDE.md` does **not** carry an equivalent template.

**Finding (gap, not a blocker):** source promotions have been operating against the taxonomy template as precedent. Chunk 7.17 does **not** author a new template (that would be an unapproved workflow change per §12 of the Chunk 7.17 prompt and §10 of the Chunk 7.16 prompt). Instead, this packet proposes — for reviewer use only, not as a committed artifact — a sign-off block that mirrors the taxonomy template adapted to sources. See §5.5.

### 2.6 Reviewer independence (precedent from TAXONOMY_APPROVAL_CHECKLIST.md §Reviewer independence)

1. Each reviewer independently reads the source entry, the Chunk 7.14 / 7.15 human-verified license evidence, and the Chunk 7.16 collection design.
2. Each reviewer posts their own `approve` or `revise` decision with a rationale **before** discussing the decision with the proposer or with the other reviewer.
3. Discussion follows once both initial decisions are posted.
4. Procedural, not technically enforced.
5. The proposer cannot count as either reviewer.

**Not fabricated here.** Chunk 7.17 does **not** supply reviewer identities, timestamps, decisions, or rationales. All reviewer fields in this packet are blank.

### 2.7 Disagreement workflow (precedent)

- Both current decisions `approve` + every checklist box ticked → proposer prepares the status-changing commit.
- Either current decision `revise` → source **must not** be promoted; revise and re-review.
- Never edit or delete a previous sign-off comment to hide a change of position.
- Persistent disagreement after two cycles → third independent reviewer; majority of three resolves.
- Automated tests passing is not a sign-off.

---

## 3. Evidence checklist (prepared for human reviewers)

Every item is a reviewer action. Nothing below is pre-decided.

### A. Source identity

- [ ] Confirm the `source_id` under review is `src_08ee850ba4b54d1b81cdbd652809b613`.
- [ ] Confirm the registry entry currently reads: `source_name: "arXiv"`, `source_url: "https://arxiv.org/"`, `license: "CC0-1.0"`, `intended_use: "primary_type_training_lbl_research_pub_metadata_only"`.
- [ ] Confirm `is_synthetic: false`.
- [ ] Confirm `original_labels: []` (empty is correct: arXiv's own classification system is not persisted into Achievement labels — see §C and the Chunk 7.16 §D field mapping).
- [ ] Note any source-identity ambiguity, including whether `source_name: "arXiv"` is specific enough or whether the entry would benefit from clarifying the metadata-only scope in the name itself. (Reviewer judgment.)
- [ ] Confirm this is the only arXiv entry in `sources.yaml` (no duplicate).

**Evidence already in the repo:**
- `hybrid_dataset/metadata/sources.yaml` entry lines (post-Chunk 7.15 edit).
- Chunk 7.15 registration report (session transcript).
- Chunk 7.16 collection design (`reports/chunk_7_16_arxiv_metadata_collection_design.md`).

**Evidence still needed from the reviewer:**
- Reviewer re-opens `https://arxiv.org/` and confirms the site at that URL is still arXiv.

### B. Metadata license evidence

- [ ] Re-open `https://info.arxiv.org/help/license/index.html` and confirm the current page still contains, verbatim, `"A Creative Commons CC0 1.0 Universal Public Domain Dedication will apply to all metadata."` Record any wording change.
- [ ] Re-open `https://info.arxiv.org/help/api/tou.html` and confirm the current page still contains the one-request-per-three-seconds and single-connection constraints. Record any wording change.
- [ ] Confirm the registered `license: "CC0-1.0"` matches the metadata license on the arXiv page.
- [ ] Confirm that the registry entry's `usage_restrictions` is consistent with the page content on the reviewer's observation date.
- [ ] Confirm the project's `intended_use` ("research dataset metadata-only training signal for `lbl_research_pub`") falls within the CC0 1.0 permissions.

**Explicit scope boundary (not a reviewer decision — a reviewer compliance check):**
- CC0 1.0 applies to **descriptive metadata only** — title, abstract, authors, identifiers, categories.
- **CC0 does NOT grant** rights to redistribute full-text PDFs, source files, or figures. These are governed by per-paper arXiv licenses (default: arXiv perpetual non-exclusive license, which does NOT grant third-party redistribution — per the arXiv Bulk Data page: `"We are thus unable to grant others the right to distribute arXiv articles."`).
- The reviewer confirms this scope is preserved in `usage_restrictions` and `mapping_notes`.

**Evidence still needed from the reviewer:**
- The reviewer's **own observation date** of the two evidence URLs, written in ISO form in their sign-off block.
- The reviewer's confirmation that the wording still matches, or an explicit note of any change.

### C. API usage and operational compliance

Previously supplied official terms (Chunk 7.14/7.15; not re-verified in this chunk):
- At most one request every three seconds.
- One connection at a time.
- Limits apply collectively across all machines under the user's control.
- No rate-limit circumvention.

- [ ] Confirm the registered `usage_restrictions` captures the three-second interval, single-connection, and aggregate-rate rules.
- [ ] Confirm that **no code implementing API collection yet exists** in the repository. (The Chunk 7.16 design is proposed but not implemented.)
- [ ] Confirm the registration does **not** by itself authorize metadata collection — collection is a separate future chunk.
- [ ] Note that any future collector must enforce the three-second gate at the single-process, single-thread level, with single-connection HTTP, and must not auto-parallelize across machines.

**Implementation evidence that WOULD be required before any metadata collection is authorized** (not required for *source* promotion, but noted here so reviewers see the gating structure):
- Collector module with unit tests covering the sleep gate.
- Pre-run script that reads the arXiv license and ToU pages, hashes them, and halts the run if the hashes differ from the reviewer-verified hashes recorded in the sign-off.
- Per-run manifest format (see Chunk 7.16 §G).

### D. Source integrity and provenance

- [ ] Confirm records derived from this source will set `Achievement.source_id = "src_08ee850ba4b54d1b81cdbd652809b613"`.
- [ ] Confirm the proposed deduplication key is the base arXiv ID (`"arxiv-" + base_arxiv_id`), **not** the versioned form (`...v2`).
- [ ] Confirm multiple versions of a paper collapse to **one** `Achievement` row (version tracked in a YAML comment, not a schema field — see Chunk 7.16 §F.7 for the unresolved schema limitation).
- [ ] Confirm that per-paper metadata provenance fields the collector will retain (title, abstract, authors, submitted date, primary_category, DOI/journal_ref/comment if present) are **staging-only** and not persisted into Achievement rows beyond the three Chunk 7.16 §D.1 destinations.
- [ ] Note the unresolved deduplication risk: paper versions and DOI collisions must not merge records; see Chunk 7.16 §F.5 for the DOI-collision rule.
- [ ] Note that `Achievement` has no `arxiv_version` field; this is deliberate per Chunk 7.16 §F.7 and is NOT a blocker for source promotion but is a note for future record creation.

### E. Human review requirements (two independent reviewers)

**Reviewer 1 fields (BLANK, for a human to fill):**

```
reviewer_1_pseudonym:   labeler_<NNN>
reviewer_1_date:        YYYY-MM-DD
reviewer_1_decision:    <approve | revise>
reviewer_1_license_page_observation: YYYY-MM-DD; wording_match: <yes | note change>
reviewer_1_tou_page_observation:     YYYY-MM-DD; wording_match: <yes | note change>
reviewer_1_rationale:   >
  Two or three sentences identifying the evidence weighed (metadata-only
  scope, CC0 verbatim quote, API-terms rate limits, full-text exclusion,
  arXiv endorsement restriction, student-identification caveat) and any
  remaining issue. If the decision is `revise`, state what must change
  before approval.
```

**Reviewer 2 fields (BLANK, for a different human to fill):**

```
reviewer_2_pseudonym:   labeler_<NNN>
reviewer_2_date:        YYYY-MM-DD
reviewer_2_decision:    <approve | revise>
reviewer_2_license_page_observation: YYYY-MM-DD; wording_match: <yes | note change>
reviewer_2_tou_page_observation:     YYYY-MM-DD; wording_match: <yes | note change>
reviewer_2_rationale:   >
  Two or three sentences; independent of Reviewer 1; posted BEFORE
  reading Reviewer 1's rationale.
```

**Independence rules:**
- Reviewer 1 posts their decision **before** Reviewer 2 reads it.
- Reviewer 2 posts their decision **before** discussing with Reviewer 1 or the proposer.
- The proposer (whoever authored the Chunk 7.15 registration commit) is **not** eligible as a reviewer.
- Neither Reviewer 1 nor Reviewer 2 may delegate to an AI assistant, team Slack vote, or batch review.
- An AI assistant's output is **not** a reviewer sign-off.

**No reviewer identities are supplied by this packet.** The two blocks above are templates; they are intentionally empty.

### F. Separate decisions preserved

The source promotion decision does **not** establish any of the following; each is an independent governance check:

| # | Decision | Established by |
|---|---|---|
| 1 | Source identity verification | The current chunk's §A reviewer actions |
| 2 | Metadata license verification | The current chunk's §B reviewer actions |
| 3 | API terms and operational compliance | The current chunk's §C reviewer actions |
| 4 | Source approval / promotion | A follow-up PR, **only** after both reviewers mark decision: `approve` and all pre-registration checklist boxes are ticked |
| 5 | Individual achievement eligibility | Chunk 7.11 Stage D, per-record |
| 6 | Student status verification | Chunk 7.11 Stage B, per-record |
| 7 | Authorship verification | Chunk 7.11 Stage C, per-record |
| 8 | Achievement date verification | Reviewer judgment per `Achievement.achievement_date` schema rule (<= today+1); submission date is NOT automatically achievement date (Chunk 7.4-A.2 precedent) |
| 9 | Annotation and label review | Chunk 6 dual-sign-off per task; `lbl_research_pub` promotion must land separately via `TAXONOMY_APPROVAL_CHECKLIST.md` |

Source promotion unlocks only decisions 1-4. Decisions 5-9 remain per-record and are not touched by this packet.

---

## 4. Metadata collection design risks (Chunk 7.16-derived)

Each row is classified per the Chunk 7.17 prompt's five categories.

| Topic | Finding | Classification |
|---|---|---|
| Endpoint URL and parameter grammar for the arXiv Query API | Not re-verified in Chunk 7.16; implementer must verify at implementation time | **Unverified** |
| Response field names in the Atom feed | Inferred from prior-chunk knowledge; not verified in Chunk 7.16 | **Unverified** |
| Pagination parameters (`start`, `max_results`) and total-count behavior | Not verified | **Unverified** |
| Error-response format and status codes under rate-limit breach | Not verified | **Unverified** |
| OAI-PMH endpoint URL | Not verified in Chunk 7.16 | **Unverified** |
| OAI-PMH `metadataPrefix` choice (`arXiv` vs `arXivRaw` vs `oai_dc`) | Not verified | **Unverified** |
| OAI-PMH `resumptionToken` handling | Standard OAI-PMH behavior assumed; not verified against arXiv | **Unverified** |
| `from`/`until` date semantics (submitted vs updated) | Not verified | **Unverified** |
| Rate-limit *enforcement*: is it in the implementation or merely in the design? | **Design only.** No implementation exists in the repository today. | **Verified from repository evidence** |
| Base vs versioned arXiv ID handling | Dedup key is base ID; version in YAML comment; one Achievement per base ID | **Supported by previously supplied official terms + Chunk 7.16 §F** |
| Audit of metadata changes across versions | YAML-comment convention proposed; schema has no version field | **Requires human decision** (Chunk 7.16 §F.7) |
| Duplicate detection without losing provenance | Collector-run manifest + base-ID dedup; across-run dedup against prior staging manifest | **Requires a future implementation chunk** (Chunk 7.16 §G) |
| Submission dates misread as achievement dates | Chunk 7.16 §D explicitly says submission is a candidate but reviewer must apply the Chunk 7.4-A.2 "unambiguous event date" test | **Supported by previously supplied official terms** (arXiv submitted date exists); **requires human decision** per record |
| arXiv endpoint behavior re API terms (unchanged over time?) | Reviewer must re-verify the ToU URL on their collection date; API terms may change | **Requires human decision** |
| Reliability of running `tests/dataset/` suite | Pre-existing collection error (`ModuleNotFoundError: No module named 'tests.dataset'`) in the user's Python environment; see §6 | **Verified from repository evidence** |

**No external term or API behavior was independently re-verified in this chunk.**

---

## 5. Review decision packet (reviewer fields are blank)

### 5.1 Source identity and current registry status

- `source_id`: `src_08ee850ba4b54d1b81cdbd652809b613`
- `source_name`: `arXiv`
- `source_url`: `https://arxiv.org/`
- `license`: `CC0-1.0`
- `collection_date`: `2026-10-23`
- `intended_use`: `primary_type_training_lbl_research_pub_metadata_only`
- `review_status`: **`unreviewed`** (not changed by this chunk)
- `is_synthetic`: `false`
- `original_labels`: `[]`
- Registered via Chunk 7.15 after Chunk 7.14 human license re-verification.

### 5.2 Evidence already available

- Verbatim arXiv metadata CC0 1.0 clause (Chunks 7.14/7.15; human-supplied).
- Verbatim arXiv Bulk Data redistribution clause.
- Verbatim arXiv API rate limit (one request per three seconds; one connection).
- Chunk 7.15 registration diff and validation output (ingestion test suite: 75 passed, 4 skipped; still passes in this chunk).
- Chunk 7.16 collection design (`reports/chunk_7_16_arxiv_metadata_collection_design.md`).
- Chunk 7.16 scope statement: metadata-only; no full-text ingestion.

### 5.3 Evidence still missing

- Reviewer 1's own fresh observation of the two evidence URLs with reviewer-stated date.
- Reviewer 2's own fresh observation of the two evidence URLs with reviewer-stated date (independent of Reviewer 1).
- Two reviewer sign-off blocks matching §3-E, posted independently.
- A project-team decision on the preprint-vs-peer-reviewed question (Chunk 7.16 §J H3) — not a blocker for *source* promotion, but noted.
- A project-team decision on the multi-author rowing policy (Chunk 7.16 §J H4) — not a blocker for source promotion.

### 5.4 License scope and limitations

- **In scope** (CC0 1.0): descriptive metadata — title, abstract, authors (public byline), arXiv identifiers, classification terms. Permitted: retrieve, store, transform, share.
- **Out of scope** (NOT granted by this registration):
  - Full-text PDF ingestion.
  - TeX / source-file ingestion.
  - Figure ingestion.
  - Hosting or serving arXiv e-prints.
  - Redistribution of arXiv articles.
- Attribution: CC0 removes legal attribution requirement; arXiv **requests** the acknowledgment line as a courtesy — the project honors this as convention.

### 5.5 Proposed sign-off block (for reviewer use only; NOT committed in this chunk)

Mirroring the `TAXONOMY_APPROVAL_CHECKLIST.md` template, adapted for a source. **This block is a suggestion to the reviewers; it is not an authored project artifact.** Each of the two reviewers posts their own, independently, on the eventual promotion PR:

```
source_id: src_08ee850ba4b54d1b81cdbd652809b613
reviewer:  labeler_<NNN>
date:      YYYY-MM-DD
license_page_observed_on:  YYYY-MM-DD   # the reviewer's own ISO date
license_page_wording:      match | note change (quote the change)
tou_page_observed_on:      YYYY-MM-DD
tou_page_wording:          match | note change (quote the change)
decision:  approve | revise
rationale: >
  Two or three sentences on the evidence weighed:
  - Metadata-only scope preserved (title/abstract/authors/identifiers/categories).
  - CC0 verbatim quote still matches on observation date (or quoted change).
  - API ToU rate limit and single-connection restriction still match.
  - Full-text redistribution exclusion preserved in usage_restrictions.
  - Student-identification caveat routed to Chunk 7.11 workflow.
  - Trademark / endorsement rule preserved.
  Any remaining issue; if decision is `revise`, state what must change
  before approval.
```

### 5.6 Independent-review decision fields

See §3-E. Both reviewer blocks are **blank** by design.

### 5.7 Disagreement resolution requirements (precedent from TAXONOMY_APPROVAL_CHECKLIST.md §Reviewer-disagreement workflow)

- Both current decisions `approve` + §A, §B, §C, §D all ticked → proposer prepares a follow-up commit changing `review_status: verified`.
- Either current decision `revise` → the arXiv entry **must not** be promoted; proposer revises the entry text per the reviewer's rationale; both reviewers post a fresh decision block after revision.
- Never edit or delete a prior sign-off comment; append new ones.
- Two full cycles without convergence → request an independent third reviewer; majority of three resolves.

### 5.8 Promotion prerequisites — binary gate

The source may be promoted to `review_status: verified` **only when all** of the following are true:

1. Both reviewer blocks posted independently, both reading `decision: approve`.
2. Checklist §A (identity), §B (license), §C (API/operational), §D (provenance) all boxes ticked by at least one of the two reviewers.
3. No `revise` decision outstanding.
4. No wording-change note on either evidence page without an accompanying reviewer approval that the change does not materially alter the CC0 1.0 metadata license or the aggregate rate-limit rule.
5. The proposer has prepared the single-field YAML change (`review_status: unreviewed` → `review_status: verified`) in a follow-up commit on the same branch, with no other change bundled.

### 5.9 Outstanding risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Reviewer independence is procedural, not technically enforced | PR template reminds reviewers; proposer is excluded from reviewing. |
| R2 | License page wording may change between the Chunk 7.14 reviewer observation (2026-10-23) and a reviewer's §B observation | §B requires the reviewer to record the observation date and note any wording change. If a change is material, the entry's `usage_restrictions` must be updated **before** promotion. |
| R3 | Multiple competing "arXiv" sources could be created over time (e.g. a future full-text entry) | A future full-text source would be a separate `SourceRegistry` entry. Reviewers should confirm no duplicate currently exists. |
| R4 | `lbl_research_pub` is still `draft` and cannot be used in training | This is **not** a source-promotion blocker; it is a separate taxonomy promotion via `TAXONOMY_APPROVAL_CHECKLIST.md`. Reviewers should note it so expectations about training readiness remain accurate. |
| R5 | Pre-existing `tests/dataset/` collection error (see §6) | Not fixed in this chunk; documented. Ingestion-level tests remain green. |

### 5.10 Explicit no-promotion conclusion

**This packet does not approve, promote, or activate the arXiv source.**
`review_status: unreviewed` is unchanged after this chunk.
No reviewer identity, date, decision, rationale, or sign-off block is populated.

---

## 6. Human review and promotion gate

- The source remains `unreviewed` (confirmed §1.2 and §5.1).
- The supplied license evidence (Chunk 7.14 reviewer-supplied) has **not** been independently re-verified in this chunk; no fresh observation was performed.
- No independent human reviewer identities or approvals were supplied.
- AI-generated review is **not** a substitute for independent human sign-off.
- No source promotion is authorized by this task.
- Source promotion must remain blocked until the §5.8 binary gate is satisfied by actual human reviewers.

The repository's existing workflow (`SOURCE_REGISTRATION_GUIDE.md` + the taxonomy template as precedent for sign-off structure) is **sufficient** for the review. The §2.5 gap (no source-specific sign-off template committed to the repo) is a documentation improvement opportunity for a future chunk and does **not** block the review. The §5.5 proposed block is suggested for reviewer use only; it is not a committed artifact.

---

## 7. Test and audit

### 7.1 Ingestion suite

Command:
```
python -m pytest tests/ingestion/ --tb=short
```

Result: **75 passed, 4 skipped.** No regression from Chunk 7.15 state.

Includes:
- `test_shipped_sources_file_loads_registered_entries` — passes.
- `test_shipped_sources_file_validates_with_expected_conservative_advisories` — passes (SIH still in `unknown_license_ids` + `unverified_source_ids`; arXiv in `unverified_source_ids` only, since license is `CC0-1.0`).
- `test_shipped_manifest_and_sources_cross_validate` — passes.

### 7.2 Registry live-state inspection

Command:
```
python -c "from nlp_semantic.ingestion.registry import load_and_validate_sources; …"
```

Result:
- 2 entries loaded.
- arXiv entry (`src_08ee850ba4b54d1b81cdbd652809b613`) present; `review_status: unreviewed`.
- SIH entry (`src_5a8a2998d6f44055a42dcfd8991e4d12`) present; `review_status: unreviewed`; `license: UNKNOWN`.
- `unknown_license_ids`: `['src_5a8a2998d6f44055a42dcfd8991e4d12']` (SIH only — expected).
- `unverified_source_ids`: both entries (expected — neither has been promoted).

### 7.3 Pre-existing `tests/dataset/` collection error

Command:
```
python -m pytest tests/dataset/ --tb=line
```

Result (unchanged from Chunk 7.15/7.16):
```
ERROR tests/dataset/test_cli.py
ERROR tests/dataset/test_loader.py
ERROR tests/dataset/test_validator.py
Interrupted: 3 errors during collection
3 errors in 0.16s
```

**This is a collection error, not a test failure.** Root cause (established in Chunk 7.15): installed `tests` package at `C:\Users\Balaji\AppData\Roaming\Python\Python313\site-packages\tests\__init__.py` shadows the local `tests/` directory in `import tests` resolution; `pyproject.toml` sets `pythonpath = ["src"]` only; no `tests/__init__.py` exists.

Not fixed in this chunk per the Chunk 7.17 prompt §7 and the Chunk 7.16 prompt §10. Not changed. Not investigated further in this chunk.

### 7.4 Protected hash re-verification

Re-run at the end of the chunk:

| File | SHA-256 | Match |
|---|---|---|
| `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | ✓ |
| `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ✓ |

### 7.5 Dataset-state invariants

Confirmed via `git status`:
- `sources.yaml` carries only the Chunk 7.15 modification; Chunk 7.17 did not touch it.
- No new file under `hybrid_dataset/dataset/records/`.
- No new file under `hybrid_dataset/dataset/annotations/`.
- No file written under `hybrid_dataset/processed/splits/`.
- No file written under `hybrid_dataset/labels/`.
- No change to `hybrid_dataset/metadata/manifest.yaml`.
- No change to `hybrid_dataset/raw/.gitkeep`.

---

## 8. Exact files created or modified

| Path | Action | Rationale |
|---|---|---|
| `reports/chunk_7_17_arxiv_source_promotion_review_preparation.md` | **CREATED** (this file) | The sole chunk deliverable. |

No other file created, modified, deleted, or renamed by this chunk.

The `?? reports/` entry in `git status` was first created by Chunk 7.16; this chunk adds a sibling file inside it. The directory itself remains untracked.

---

## 9. Explicit statement that source promotion did not occur

- **No source was approved.**
- **No source was promoted.**
- **No source's `review_status` field was changed.**
- **No reviewer identity was fabricated, invented, simulated, or recorded.**
- **No reviewer approval was fabricated, invented, simulated, or recorded.**
- **No API request was initiated.**
- **No metadata was collected.**
- **No download occurred.**
- **No commit, no push, no staging, no branch switch.**

The arXiv source `src_08ee850ba4b54d1b81cdbd652809b613` remains `review_status: unreviewed` in `hybrid_dataset/metadata/sources.yaml`.

The two-independent-reviewer sign-off process defined by `SOURCE_REGISTRATION_GUIDE.md` (and the §5.5 sign-off block adapted from `TAXONOMY_APPROVAL_CHECKLIST.md`) is now **ready for two actual humans to execute**. This packet is the preparation; the review itself is a separate action, outside this chunk.
