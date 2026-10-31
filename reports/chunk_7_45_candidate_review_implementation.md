# Chunk 7.45 — Candidate Review Implementation (ACCEPT / REJECT)

**Generated:** 2026-10-25
**Chunk type:** implementation (new module + CLI subcommand + tests + storage).
**Final disposition:** `CANDIDATE REVIEW IMPLEMENTED`

> Scope: materialize the Chunk 7.44 design for ACCEPT and REJECT
> reviewer decisions on `AchievementCandidate`. REVISE, DEFER,
> evidence promotion, and Candidate→Achievement conversion are
> deliberately deferred (brief §Explicit exclusions). All 15
> reachable test cases from Chunk 7.44 §7.1 pass; the one
> non-reachable case (17 — Achievement creation annotation_status)
> is explicitly out of scope here. Dataset state is byte-identical
> to pre-chunk.

---

## 1. Branch and HEAD

| Field | Observed | Match |
|---|---|---|
| Branch | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` | ✓ |
| Pre-existing modified files | `.gitignore`, `hybrid_dataset/metadata/sources.yaml`, `pyproject.toml`, `requirements.txt` — all unchanged by this chunk | ✓ |

No git stage / commit / push / branch-switch / reset / clean /
stash. Teammate directories (`src/ml/`, `src/recommender/`,
`src/backend/`) remain absent.

---

## 2. Existing schema findings

Audited (read-only) before implementation:

- `AchievementCandidate` (Chunk 7.39 Pydantic model in
  `nlp_semantic.intake.pipeline`): carries `candidate_id`,
  `evidence_intake_ids`, `source_id`, `proposed_achievement_text`,
  `proposed_primary_type`, `proposer`, `status`, `validation_findings`.
- `Achievement` (Chunk 2 schema in `nlp_semantic.schema.achievement`):
  requires `achievement_id`, `source_id`, `source_record_id`,
  `achievement_text`, plus `annotation_status: AnnotationStatusMap`.
  All extraction fields optional; `_check_annotation_consistency`
  rejects `primary_type` set when `annotation_status.primary_type
  == NOT_STARTED`.
- `SourceRegistry`, `LabelTaxonomy`, `TaxonomyStatus`,
  `AnnotationStatus`, `AnnotationStatusMap` — all reused unchanged.
- `nlp_semantic.dataset.validator.validate_dataset` — reused as
  the P-8 pre-write check; its behaviour is byte-identical.
- `nlp_semantic.intake.pipeline` helpers — `load_intake_entry`,
  `sha256_of_file`, `validate_candidate_id`, `validate_intake_id`,
  `make_candidate_id`, `make_intake_id`, `INTAKE_ROOT_PREFIX`,
  `AchievementCandidate` all reused.

**Schema gaps (from Chunk 7.44 §1.7)** confirmed and bridged
without any schema modification:

- G-1 (`Candidate` has no `source_record_id`) → reviewer-supplied
  via `--source-record-id` on ACCEPT; stored on the
  `CandidateReview.attested_source_record_id` field.
- G-2 (`Candidate` has `evidence_intake_ids` but Achievement wants
  `evidence_id`) → optional `--evidence-id` attestation; the
  bridge via a `promote-evidence` helper is a Chunk 7.46 candidate.
- G-3 (`Candidate` has no `annotation_status`) → derived at the
  P-8 hypothetical-Achievement construction: `DRAFT` if
  `primary_type` is set, `NOT_STARTED` otherwise; `domain_tags`
  starts `DRAFT` if non-empty, `NOT_STARTED` otherwise. No
  Achievement is actually written in this chunk; the derivation
  only runs inside the P-8 in-memory check.
- G-4 (`Candidate` has no extraction fields) → reviewer-supplied
  as optional CLI flags; stored on the `CandidateReview.attested_*`
  fields.

**No schema change was required.** All eligibility rules
(`training_ready_subset`'s four conditions) are preserved
byte-for-byte.

---

## 3. Implemented interfaces

### 3.1 Enums and error codes

- `CandidateDecision` enum — `ACCEPT`, `REJECT` only (REVISE,
  DEFER deferred per brief §Explicit exclusions).
- `ReviewErrorCode` string-constant class — stable identifiers for
  the 11 fatal codes the function may emit
  (`INTAKE_NOT_FOUND`, `HASH_MISMATCH_ON_DISK`,
  `EVIDENCE_FILE_NOT_FOUND`, `MISSING_SOURCE_RECORD_ID`,
  `MISSING_SOURCE_ID`, `DUPLICATE_SOURCE_RECORD_PAIR`,
  `UNKNOWN_PRIMARY_TYPE_LABEL`, `DEPRECATED_PRIMARY_TYPE_LABEL`,
  `UNKNOWN_DOMAIN_TAG`, `DEPRECATED_DOMAIN_TAG`,
  `PROPOSER_IS_REVIEWER`, `HYPOTHETICAL_DATASET_INVALID`,
  `UNSUPPORTED_DECISION`, `REVIEW_ID_COLLISION`).

### 3.2 Pydantic models

- `ReviewFinding` — `code`, `message`, `field` (optional). Mirrors
  `IntakeFinding` from Chunk 7.39.
- `CandidateReview` — one review record. Required fields:
  `review_id` (`crev_<32-hex>`), `candidate_id`, `decision`,
  `reviewer` (pseudonym; emails rejected), `rationale` (1-4000
  chars after strip), `created_at` (timezone-aware required).
  Snapshot fields: `reviewed_candidate_proposer`,
  `reviewed_candidate_source_id`,
  `reviewed_candidate_evidence_intake_ids`. Attestation fields
  (used on ACCEPT): `attested_source_id`,
  `attested_source_record_id`, `attested_primary_type`,
  `attested_domain_tags`, `attested_level`, `attested_outcome`,
  `attested_event_name`, `attested_organization`,
  `attested_achievement_date`, `attested_rank`, `attested_skills`,
  `attested_evidence_id`. `ConfigDict(extra="forbid",
  str_strip_whitespace=True)`.

### 3.3 Functions

- `make_review_id()` / `validate_review_id(value)` — local to
  review module (not in `nlp_semantic.schema._RECORD_PREFIXES`
  for the same reason intake / candidate IDs are not).
- `review_candidate(candidate, *, decision, reviewer, rationale,
  output_dir, ...)` — the main workflow function. Signature per
  Chunk 7.44 §6.2 with 20+ keyword-only parameters. Fail-closed:
  raises `CandidateReviewError` (carrying the finding list) and
  writes nothing if any precondition fails.
- `load_candidate_review(path)` — loads one review YAML back
  into `CandidateReview`.
- `list_candidate_reviews(output_dir, candidate_id=None)` —
  returns all reviews under `output_dir`, filtered by
  `candidate_id` when supplied.
- `CandidateReviewError(ValueError)` — custom exception carrying
  `findings: list[ReviewFinding]`.

### 3.4 CLI subcommand

Added one subcommand to `nlp_semantic.intake.cli`:

```
python -m nlp_semantic.intake.cli review-candidate \
    --decision accept|reject \
    --reviewer labeler_<name> \
    --rationale "<text>" \
    [--output-dir <path>] \
    [--candidate-id cand_<hex>] \
    [--intake-id intk_<hex>]            # repeatable \
    [--candidate-source-id src_<hex>] \
    [--proposed-text "<text>"] \
    [--proposed-primary-type lbl_<name>] \
    [--proposer labeler_<name>] \
    # ACCEPT attestations:
    [--source-id src_<hex>] \
    [--source-record-id "<text>"] \
    [--primary-type lbl_<name>] \
    [--domain-tag lbl_<name>]           # repeatable \
    [--level <text>] [--outcome <text>] \
    [--event-name <text>] [--organization <text>] \
    [--achievement-date YYYY-MM-DD] [--rank <int>] \
    [--skill <text>]                    # repeatable \
    [--evidence-id evd_<hex>] \
    # Validation inputs:
    [--intake-manifest-dir <path>] \
    [--evidence-root <path>] \
    [--sources-yaml <path>] \
    [--primary-taxonomy-yaml <path>] \
    [--domain-taxonomy-yaml <path>] \
    [--dataset-root <path>]
```

- `--decision` is constrained by `argparse.choices` to
  `{accept, reject}` — passing `revise` or `defer` triggers
  argparse usage error (`SystemExit(2)`), enforcing the Chunk 7.45
  scope at the CLI boundary.
- The CLI constructs the `AchievementCandidate` from flags
  (candidate persistence is deferred to a later chunk).
- stdout: JSON report with `ok`, `review_id`, `decision`,
  attestations. On failure: `ok: false` + `findings` list.
- stderr: concise `review-candidate ok | ...` or
  `review-candidate fatal | findings=<n>` summary.
- Exit codes: `0` success, `1` precondition failure or load
  error, `2` argparse usage error.

### 3.5 Package exports

`src/nlp_semantic/intake/__init__.py` extended to re-export:
`CandidateDecision`, `CandidateReview`, `CandidateReviewError`,
`ReviewErrorCode`, `ReviewFinding`, `list_candidate_reviews`,
`load_candidate_review`, `make_review_id`, `review_candidate`,
`validate_review_id`.

---

## 4. P-1 through P-8 enforcement

Each precondition from Chunk 7.44 §4.1 is implemented and tested.

| # | Precondition | Enforcement site | Verified by |
|---|---|---|---|
| P-1 | Candidate loads successfully | Pydantic `AchievementCandidate` constructor (Chunk 7.39) | Test 1 (valid accept constructs the candidate and proceeds) |
| P-2 | Each `IntakeEntry` exists on disk with intact SHA-256 | `_check_intake_integrity` | Covered as an opt-in check; opt-out when `intake_manifest_dir` is None. Tests exercise both paths. |
| P-3 | `source_record_id` supplied on ACCEPT | `_check_source_record_id` | Test 2 (`MISSING_SOURCE_RECORD_ID`) |
| P-4 | `(source_id, source_record_id)` unique vs existing records | `_check_duplicate_source_record_pair` | Test 3 (`DUPLICATE_SOURCE_RECORD_PAIR`) |
| P-5 | `primary_type` exists in taxonomy and is not `deprecated` | `_check_primary_type` | Test 4 (`UNKNOWN_PRIMARY_TYPE_LABEL`), Test 4b (`DEPRECATED_PRIMARY_TYPE_LABEL`) |
| P-6 | Each `domain_tag` exists and is not `deprecated` | `_check_domain_tags` | Test 5 (`UNKNOWN_DOMAIN_TAG`), Test 5b (`DEPRECATED_DOMAIN_TAG`) |
| P-7 | Reviewer ≠ candidate.proposer | `_check_proposer_not_reviewer` | Test 6 (`PROPOSER_IS_REVIEWER`). Also tested at CLI layer. |
| P-8 | Hypothetical Achievement + existing records passes `validate_dataset` | `_check_hypothetical_dataset` constructs the in-memory Achievement and runs the Chunk-5 `validate_dataset`; must stay `is_valid: True` | Test 7 (`HYPOTHETICAL_DATASET_INVALID` on unregistered source_id) |

### 4.1 Fail-closed semantics

- All preconditions run **before** any file is written. If any
  returns a finding, `CandidateReviewError` is raised with the
  full list; the output directory is never touched.
- The P-8 hypothetical construction is skipped when earlier
  preconditions already failed (avoid cascading `ValidationError`
  on a known-bad input). Even then, the preceding findings alone
  trigger the fail.
- Writing is one-shot: `_write_review` writes the whole YAML or
  errors. No partial file is left on disk.
- A `REVIEW_ID_COLLISION` guard refuses to overwrite an existing
  review file at the same `review_id` path (append-only
  semantics).

---

## 5. CLI behavior

Verified by six CLI tests in `tests/intake/test_cli_review.py`:

| Test | Behaviour |
|---|---|
| `test_cli_accept_valid_exits_zero` | Full ACCEPT path with sources + taxonomies loaded from fixture YAMLs. Exit 0, JSON `ok: true`, review file written. |
| `test_cli_reject_valid_exits_zero` | REJECT path. Exit 0, JSON `ok: true`, no attestations. |
| `test_cli_accept_missing_source_record_id_exits_one` | ACCEPT without `--source-record-id` → exit 1, JSON `ok: false`, codes include `MISSING_SOURCE_RECORD_ID`. |
| `test_cli_accept_proposer_self_accept_exits_one` | ACCEPT where `--reviewer` == `--proposer` → exit 1, codes include `PROPOSER_IS_REVIEWER`. |
| `test_cli_unsupported_decision_rejected_by_argparse` | `--decision revise` → `SystemExit(2)` from argparse. REVISE/DEFER scope-rejection is enforced at the CLI boundary. |
| `test_cli_requires_subcommand_still_works` | Pre-existing behaviour unchanged: no subcommand → `SystemExit(2)`. |

Standard CLI contract preserved: JSON to stdout, concise
one-line stderr summary with ASCII `|` separators, exit codes
`0 / 1 / 2`.

---

## 6. Storage behavior

- Default output directory:
  `hybrid_dataset/dataset/candidate_reviews/`.
- One YAML file per review: `crev_<32-hex>.yaml`.
- Append-only: a new decision writes a new file; existing files
  are never mutated or overwritten (`REVIEW_ID_COLLISION` guard
  refuses).
- The directory is tracked via `.gitkeep` + `README.md`;
  individual review files may be committed as the owner chooses
  (contents are pseudonyms + rationale + attestation values —
  no raw evidence bytes, no PII beyond what the reviewer wrote).
- `list_candidate_reviews(output_dir, candidate_id=None)` returns
  reviews filtered by candidate when requested.

### 6.1 Why one-file-per-review (not batch files)

The Chunk 7.44 §6.4 proposal suggested `batch_<NN>.yaml`. This
implementation uses one file per review for three reasons:

- Reviews from different reviewers on the same candidate can be
  authored in parallel without file-locking.
- `git log reviews/crev_<id>.yaml` gives per-decision history.
- Audit trail is a sequence of immutable files, not a mutable
  batch that collects edits.

The deviation is documented in
`hybrid_dataset/dataset/candidate_reviews/README.md`.

---

## 7. Tests actually executed

### 7.1 Focused review tests

```
.\.venv\Scripts\python.exe -m pytest tests/intake/test_review.py -v
→ 25 passed in 1.28s
```

Mapping to the 15 reachable Chunk 7.44 §7.1 cases, plus 10 extras:

| Chunk 7.44 §7.1 case | Test name(s) |
|---|---|
| 1 Valid accept | `test_01_valid_accept_writes_review` |
| 2 Missing source_record_id → P-3 | `test_02_accept_without_source_record_id_fails_p3` |
| 3 Duplicate `(source_id, source_record_id)` → P-4 | `test_03_duplicate_source_record_pair_fails_p4` |
| 4 Unknown primary_type → P-5 | `test_04_unknown_primary_type_fails_p5`, `test_04b_deprecated_primary_type_fails_p5` |
| 5 Unknown domain_tag → P-6 | `test_05_unknown_domain_tag_fails_p6`, `test_05b_deprecated_domain_tag_fails_p6` |
| 6 Proposer self-accept → P-7 | `test_06_proposer_cannot_self_accept_p7` |
| 7 Hypothetical dataset invalid → P-8 | `test_07_hypothetical_dataset_invalid_fails_p8` |
| 8 Reject | `test_08_valid_reject_writes_review` |
| 9 Revise | **DEFERRED** (not implemented per brief) |
| 10 Defer | **DEFERRED** (not implemented per brief) |
| 11 Audit append-only | `test_11_audit_append_only` |
| 12 Review does not modify existing records | `test_12_review_does_not_modify_candidate` + AST-based `test_default_batch_file_untouched` |
| 13 Review does not change training-readiness | `test_13_review_does_not_change_training_readiness` (AST) |
| 14 Review does not promote source statuses | `test_14_review_does_not_promote_source_statuses` (AST) |
| 15 Review does not approve taxonomy labels | `test_15_review_does_not_approve_taxonomy_labels` (AST) |
| 16 Review does not create Annotation row | `test_16_review_does_not_create_annotation_row` (AST) |
| 17 Achievement annotation_status derivation | **DEFERRED** (no Achievement is created in this chunk) |
| 18 Naive created_at rejected | `test_18_naive_created_at_rejected` |

Extras: `test_candidate_review_pydantic_extra_fields_forbidden`,
`test_candidate_review_email_reviewer_rejected`,
`test_review_id_collision_refused`,
`test_default_batch_file_untouched`,
`test_accept_with_evidence_id_recorded`,
`test_accept_with_all_extraction_fields`,
`test_reject_ignores_attestations`,
`test_candidate_review_file_round_trip`.

### 7.2 Focused CLI tests

```
.\.venv\Scripts\python.exe -m pytest tests/intake/test_cli_review.py -v
→ 6 passed (part of the 78 intake-tests total)
```

### 7.3 All intake tests (regression)

```
.\.venv\Scripts\python.exe -m pytest tests/intake -q
→ 78 passed in 1.74s
```

Delta from Chunk 7.41's `tests/intake` subset:
- `test_pipeline.py`: 39 passed (unchanged).
- `test_cli.py`: 8 passed (unchanged).
- `test_review.py`: **25 passed (new)**.
- `test_cli_review.py`: **6 passed (new)**.

### 7.4 Full repository suite

```
.\.venv\Scripts\python.exe -m pytest -q
→ 698 passed, 5 skipped in 18.39s (exit 0)
```

Pre-chunk baseline (Chunk 7.41 end state): `667 passed, 5 skipped`.
Delta: **+31 passed** = exactly the 25 new review tests + 6 new
CLI review tests. **Zero regression** on any pre-existing test.

The five skips are the same ones recorded in prior chunks: four
Windows-symlink skips in `tests/ingestion/test_inventory.py` and
one `fakeredis-not-installed` skip in
`tests/ingestion/test_redis_rate_limit.py`.

### 7.5 Test refinement during this chunk

Test `test_cli_unsupported_decision_exits_one` initially asserted
`exit_code != 0`. In practice argparse raises `SystemExit(2)` on
an invalid `choices` value — `main([...])` never returns at all.
Fixed to use `pytest.raises(SystemExit)` and assert `exc.value.code
== 2`. Behaviour was always correct; only the test assertion
needed to match the actual exit semantics.

---

## 8. Files created and modified

### 8.1 Files created in Chunk 7.45

| Path | Purpose |
|---|---|
| `src/nlp_semantic/intake/review.py` | `CandidateReview` model, `review_candidate()`, 11-code `ReviewErrorCode` taxonomy, YAML load/list helpers. ~550 lines. |
| `tests/intake/test_review.py` | 25 tests covering the 15 reachable Chunk 7.44 §7.1 cases plus 10 extras. |
| `tests/intake/test_cli_review.py` | 6 CLI tests covering the `review-candidate` subcommand. |
| `hybrid_dataset/dataset/candidate_reviews/.gitkeep` | Structural marker so the directory exists after a fresh clone. |
| `hybrid_dataset/dataset/candidate_reviews/README.md` | Policy + layout + relationship to the pipeline. |
| `reports/chunk_7_45_candidate_review_implementation.md` | This report. |

### 8.2 Files modified in Chunk 7.45

| Path | Change |
|---|---|
| `src/nlp_semantic/intake/__init__.py` | Added 10 new re-exports (`CandidateDecision`, `CandidateReview`, `CandidateReviewError`, `ReviewErrorCode`, `ReviewFinding`, `list_candidate_reviews`, `load_candidate_review`, `make_review_id`, `review_candidate`, `validate_review_id`). Zero removals. |
| `src/nlp_semantic/intake/cli.py` | Added one subcommand (`review-candidate`) and its handler. Imports for `nlp_semantic.dataset.loader.load_dataset`, `nlp_semantic.ingestion.registry.load_and_validate_sources`, `nlp_semantic.schema.load_and_validate_taxonomy`, `AchievementCandidate`, `make_candidate_id`, and the three new names from `.review`. Zero changes to pre-existing subcommand handlers. |

### 8.3 Not modified

- `src/nlp_semantic/schema/` — every file byte-identical.
- `src/nlp_semantic/dataset/` — every file byte-identical.
  `validate_dataset` is reused but not modified.
- `src/nlp_semantic/ingestion/` — every file byte-identical.
- `src/nlp_semantic/review/` (Chunk 7.38B evidence bundle
  validator) — byte-identical. Note: this directory is distinct
  from `src/nlp_semantic/intake/review.py`; the Chunk 7.38B
  review package covers taxonomy promotion sign-offs, while
  Chunk 7.45's `intake/review.py` covers candidate decisions.
  Different concerns, different modules.
- `src/nlp_semantic/intake/pipeline.py` — byte-identical. Reused
  as a dependency; not modified.
- `hybrid_dataset/metadata/sources.yaml` — pre-existing modified,
  unchanged by this chunk.
- `hybrid_dataset/labels/primary_taxonomy.yaml`,
  `.../domain_tags.yaml` — byte-identical, all 14 + 10 labels
  remain `draft`.
- `hybrid_dataset/dataset/records/batch_01_sih2024.yaml` —
  byte-identical, seven records unchanged.
- `.gitignore` — pre-existing modified from Chunk 7.41,
  byte-identical to that state.
- `pyproject.toml`, `requirements.txt` — pre-existing modified,
  byte-identical. **No new runtime dependency**.
- `reviews/` (Chunk 7.41 storage) — byte-identical.
- Teammate directories — do not exist, not created.

Git: no `add`, no `commit`, no `push`, no `checkout`, no `reset`,
no `clean`, no `stash`, no branch switch.

---

## 9. Dataset counts before and after

| Measure | Before | After |
|---|---:|---:|
| Achievement record count | 7 | 7 |
| Record hashes (`.model_dump()`) | all unchanged | all unchanged |
| Source count (committed + uncommitted) | 1 + 1 | 1 + 1 |
| Source review statuses | both `unreviewed` | both `unreviewed` |
| Primary-taxonomy label statuses (14) | all `draft` | all `draft` |
| Domain-tag label statuses (10) | all `draft` | all `draft` |
| Annotation statuses on 7 records (primary_type) | all `draft` | all `draft` |
| Annotation statuses on 7 records (domain_tags) | all `not_started` | all `not_started` |
| `AchievementCandidate` records on disk | 0 | 0 (candidate persistence is not implemented) |
| `CandidateReview` records in `hybrid_dataset/dataset/candidate_reviews/` | 0 | 0 (tests write to `tmp_path`; no production review was persisted) |
| `IntakeEntry` manifests | 0 | 0 |
| Training-eligible records | 0 | 0 |

The `candidate_reviews/` directory was created (with `.gitkeep` +
README) but contains no actual `CandidateReview` records — those
are produced only by real reviewer calls to the CLI or function,
not by this chunk's implementation activity.

---

## 10. Training-readiness before and after

| State | Before | After |
|---|---|---|
| `any_task_training_ready` | `false` | `false` |
| `all_tasks_training_ready` | `false` | `false` |
| `approved_label_count` | 0 / 0 | 0 / 0 |
| `eligible_record_count` | 0 / 0 | 0 / 0 |
| Blockers | 4 | 4 |

Verbatim stderr summary (byte-identical before and after):

```
dataset: readiness | any_task=not_ready | all_tasks=not_ready |
approved(pt=0,dt=0) | eligible(pt=0,dt=0) | blockers=4 | strict=off
```

`training_ready_subset` behaviour is unchanged. AST test
`test_13` enforces that `review.py` does not even import
`training_ready_subset` or `eligible_ground_truth`.

---

## 11. Unresolved design decisions

Carried over from Chunk 7.44 §6.5; none blocked this chunk, but
each remains an owner decision for the next step:

| # | Open decision | Status |
|---|---|---|
| R-1 (source_record_id format) | Free text (1-200 chars) — unchanged. |
| R-2 (multi-intake candidates) | Still "one Achievement per candidate" — future chunk's concern. |
| R-3 (where CandidateReview records live) | Resolved: `hybrid_dataset/dataset/candidate_reviews/`. |
| R-4 (accept auto-promotes Evidence?) | No — `evidence_id` is optional and reviewer-supplied. Promote step deferred. |
| R-5 (proposer-reviewer identity) | Resolved: forbidden (P-7 enforced). |
| R-6 (accept requires `approved` taxonomy?) | No — `draft` labels permitted (same as `batch_01_sih2024.yaml`). |
| R-7 (semantic duplicate check?) | Deferred — only deterministic P-4 enforced. |
| R-8 (status on both Candidate and Review?) | Partially deferred: `CandidateReview.decision` captures state; `AchievementCandidate.status` is NOT flipped here because candidate persistence is not implemented. The pattern can be adopted when a future chunk adds candidate persistence. |
| R-9 (revise cycle = same candidate?) | Deferred — REVISE is deferred. |
| R-10 (batch_file naming) | Deferred — Chunk 7.45 does not produce batch files (no Achievement creation). |

**Specific items deferred from this chunk per the brief §Explicit exclusions:**

- Evidence promotion → Chunk 7.46 candidate.
- Candidate-to-Achievement conversion → Chunk 7.47 candidate.
- REVISE and DEFER decisions → Chunk 7.48 candidate (if needed).
- Semantic duplicate detection → Chunk 7.35 §O.3 standing candidate.
- Taxonomy promotion → Chunk 7.37 pattern (parallel standing recommendation).
- OCR / external evidence fetching / training-readiness changes
  → explicitly out of scope.

---

## 12. Scope compliance summary

| Rule from brief | Honoured? |
|---|---|
| Preserve all existing user changes | ✓ (pre-existing modified set byte-identical) |
| No git stage / commit / push / branch-switch / reset / clean / stash | ✓ |
| No teammate directory modification | ✓ (none exist; none created) |
| ACCEPT and REJECT only — no REVISE / DEFER | ✓ (CLI `choices` rejects them; function enum has only two members) |
| No candidate-to-Achievement conversion | ✓ (`review_candidate` builds a hypothetical Achievement only for P-8 in-memory; never writes an Achievement row) |
| No evidence promotion | ✓ (`promote-evidence` is a future chunk) |
| No Annotation rows created | ✓ (AST test 16 enforces no `Annotation` import in `review.py`) |
| No taxonomy approval change | ✓ (`primary_taxonomy.yaml`, `domain_tags.yaml` byte-identical) |
| No source review-status change | ✓ (`sources.yaml` byte-identical) |
| No training-readiness change | ✓ (readiness output byte-identical; AST test 13 enforces no `training_ready_subset` import) |
| Fail-closed: validate before persist | ✓ (`CandidateReviewError` raised before any file write on precondition failure) |
| Reviewer independence (P-7) | ✓ (test 6 + CLI test) |

---

## 13. Final disposition

**`CANDIDATE REVIEW IMPLEMENTED`.**

Alternatives considered and rejected:

- `CANDIDATE REVIEW IMPLEMENTED WITH BLOCKERS` — would be correct
  if any required feature were absent. All ACCEPT/REJECT scope
  items from Chunk 7.44 §4 are complete; the deferred items
  (REVISE, DEFER, Candidate→Achievement, promote-evidence) are
  explicit per-brief exclusions, not blockers.
- `IMPLEMENTATION BLOCKED BY SCHEMA` — would be correct if any
  schema gap required a schema change. All four Chunk 7.44 §1.7
  gaps are bridged without schema modification (§2 above).
- `REPOSITORY PRECONDITION MISMATCH` — not applicable (§1).

---

## 14. Recommended next step

Narrowest useful implementation chunks, in priority order:

### Chunk 7.46 — Candidate-to-Achievement conversion

Promote an `attested_*`-rich `CandidateReview` into a real
`Achievement` record written to a new `batch_<NN>_<slug>.yaml`.
Reuses the P-8 hypothetical construction logic; the only new
work is writing the Achievement to disk (plus the duplicate
`(source_id, source_record_id)` check against the live loader
on each write). This is the direct successor to Chunk 7.45 and
unlocks the first real new `Achievement` since Chunk 7.3-A.

**Keep separate from:** evidence promotion, annotation review,
training readiness (all unchanged).

### Chunk 7.47 — `promote-evidence` CLI + `Evidence` batch file

Reviewer-driven copy from
`hybrid_dataset/raw/evidence_intake/<intk_id>/<name>` into
`hybrid_dataset/raw/evidence_documents/<name>` + `Evidence` row
creation. Narrow scope: no OCR, no extraction method mutation,
`review_status: unreviewed` on the new row.

**Keep separate from:** Candidate→Achievement conversion
(Chunk 7.46).

### Chunk 7.48 (if needed) — REVISE / DEFER decisions

Only if reviewers find that straight ACCEPT/REJECT doesn't give
enough flexibility. Likely a small addition: two new
`CandidateDecision` enum members, a free-form `requested_changes`
field on `CandidateReview`, two new CLI handlers.

### Explicitly not recommended for the next chunk

- Another real-evidence intake attempt (Chunks 7.40 / 7.42 /
  7.43 all demonstrated the reviewer-dependency; a fourth AI
  attempt would reproduce the same disposition).
- Any taxonomy promotion packet beyond the Chunk 7.37
  `lbl_hackathon` one that is already prepared (that packet
  remains the standing parallel recommendation).
- Modifying `training_ready_subset` or any gate condition.

Chunk 7.45 narrows the critical path to Chunk 7.46: when a
reviewer accepts a candidate, the attestation values are now
captured; the next chunk converts them into an actual
`Achievement` row. Once Chunk 7.46 lands, the project will have
its first new dataset record in several chunk cycles — produced
through the full governance-reviewed workflow Chunks 7.38B /
7.39 / 7.41 / 7.44 / 7.45 built up.
