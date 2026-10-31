# Chunk 7.38B — Reviewer Evidence Bundle Validator

**Generated:** 2026-10-25
**Chunk type:** infrastructure (new module + tests + CLI).
**Final disposition:** `VALIDATOR IMPLEMENTED`

> Scope: ship a read-only, fail-closed validator that checks the
> structural correctness of two reviewer-evidence bundle types
> (taxonomy promotion; annotation review) against the shape mandated
> by `TAXONOMY_APPROVAL_CHECKLIST.md` and `ANNOTATION_GUIDELINES.md`.
> The validator never writes to the taxonomy, dataset, source
> registry, or annotation files; never authenticates reviewer
> identity; never changes `training_ready_subset` behaviour. These
> commitments are enforced by Python code and by six AST-based tests
> that inspect the module's import / call surface.

---

## 1. Objective and scope

Implement an evidence-bundle validator that lets reviewers prepare
and self-check their sign-off packets *before* opening a promotion
PR. The validator answers one question only:

> **Is this bundle structurally complete and internally consistent?**

It does NOT answer:

- Is this reviewer a real human?
- Did they actually read the materials?
- Is the label genuinely ready for approval?
- Can records now clear `training_ready_subset`?

Those remain reviewer judgement calls. The validator surfaces the
"authentication is out of scope" caveat as an unconditional
`IDENTITY_AUTHENTICATION_NOT_ESTABLISHED` limitation on every report.

### 1.1 Allowed per brief §2 (and done)

- Inspected existing schemas and validation patterns.
- Added a narrowly scoped evidence-bundle validation module.
- Added tests for the new module using synthetic, inline fixtures.
- Added a CLI entry point that follows the existing CLI architecture.
- Added this report under `reports/`.

### 1.2 Forbidden per brief §2 (and respected)

- No change to taxonomy definitions or statuses.
- No change to achievement records, source statuses, annotation
  statuses, source licence values.
- No change to `training_ready_subset()` or its callers.
- No reviewer signatures or approval evidence created.
- No synthetic records added to the real dataset.
- No modifications under `src/ml/`, `src/recommender/`, `src/backend/`.
- No external URL fetched.
- No git stage / commit / push / branch-switch / reset / clean /
  stash.
- No pre-existing user change overwritten.

---

## 2. Repository preconditions

| Field | Observed | Expected baseline | Match |
|---|---|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` | same | ✓ |
| Branch | `feature/nlp-semantic` | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` | ✓ |

Working tree state before this chunk — three modified files
(`sources.yaml`, `pyproject.toml`, `requirements.txt`) and the
pre-existing untracked artefacts (PROJECT_HANDOFF.md, arxiv files,
reports/). This chunk adds two new untracked directories
(`src/nlp_semantic/review/` and `tests/review/`) and one new report
file. **Nothing pre-existing was touched.** Not `REPOSITORY
PRECONDITION MISMATCH`.

---

## 3. Existing schemas and conventions inspected

Read-only inspection:

- `src/nlp_semantic/schema/__init__.py` — the public API; confirms
  that `AnnotationTask`, `TaxonomyStatus`, `validate_label_id`,
  `validate_prefixed_id` are importable from `nlp_semantic.schema`.
- `src/nlp_semantic/schema/identifiers.py` — the exact
  `validate_label_id` and `validate_prefixed_id` behaviour (ID
  format checks).
- `src/nlp_semantic/schema/enums.py` — `AnnotationTask`
  (`primary_type` / `domain_tags` / `extraction_review`),
  `TaxonomyStatus` (`draft` / `under_review` / `approved` /
  `deprecated`).
- `src/nlp_semantic/schema/annotation.py` — the Annotation model's
  per-task label-arity (`primary_type` exactly 1, `domain_tags`
  0..N, `extraction_review` 0) and the annotator pseudonym regex
  (`^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$`), both of which the new
  validator mirrors.
- `src/nlp_semantic/dataset/validator.py` — the
  `validate_dataset(...) → DatasetValidationReport` pattern (fatal
  / advisory distinction; never raises on content; `is_valid`
  derived from fatal set) — the new validator mirrors this.
- `src/nlp_semantic/dataset/cli.py` — the subcommand-based CLI
  pattern (`validate | stats | split | readiness`), stdout JSON +
  stderr one-line summary, exit codes `0` / `1` / `2` — the new
  CLI mirrors this.
- `src/nlp_semantic/ingestion/registry.py` /
  `src/nlp_semantic/ingestion/manifest.py` — the YAML loader
  pattern (file-level errors raise a custom `*Error`; per-entry
  format problems surface as `pydantic.ValidationError`) — the new
  loader mirrors this.
- `hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md` — the
  sign-off template (§110-131), the reviewer-independence rule
  (§84-107), the proposer-cannot-be-reviewer rule (§104-106), the
  two-sign-off requirement (§76-77), the preliminary-exercise
  option (§201-247).
- `hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md` — the single
  vs dual review workflows, the pseudonym convention (§15-23).

### 3.1 Did any existing schema already cover reviewer evidence?

No. The `Annotation` model represents the result of a reviewer
decision on a specific achievement, but it does not represent the
*sign-off packet* a promotion PR carries (two or more reviewer
comments, a target label, a target current status, evidence refs).
Likewise, no existing module models the shape of the per-source
Chunk 7.2 two-reviewer sign-off packet. Reviewer evidence has lived
exclusively in prose on PR comments and inside `reports/`. This
chunk introduces the first typed representation.

**Result:** no `DESIGN BLOCKED BY EXISTING SCHEMA`. A new, narrow
schema is justified.

---

## 4. Evidence bundle design

A single `EvidenceBundle` Pydantic model represents both bundle
types; the `bundle_type` field discriminates per-type checks. This
keeps the loader, serializer, and CLI uniform across both types.

### 4.1 `EvidenceBundle` schema (verbatim)

```
class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    bundle_id: str                        # 1-200 chars
    bundle_type: BundleType               # taxonomy_promotion | annotation_review
    target_id: str                        # 1-120 chars; lbl_... or ach_... per type
    proposer: str | None = None           # pseudonym; checked when present
    reviewers: list[ReviewerSignOff] = []

    # taxonomy_promotion-only fields
    target_current_status: TaxonomyStatus | None = None

    # annotation_review-only fields
    task: AnnotationTask | None = None
    proposed_label_ids: list[str] = []
```

### 4.2 `ReviewerSignOff` schema (verbatim)

```
class ReviewerSignOff(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reviewer: str              # pseudonym; emails rejected
    date: date                 # datetime.date
    decision: Decision         # approve | revise
    rationale: str             # 1-4000 chars after strip
    evidence_refs: list[str] = []
```

### 4.3 Why one model, not two

- The two bundle types share eight of eleven fields (`bundle_id`,
  `bundle_type`, `target_id`, `proposer`, `reviewers`, and the
  reviewer sub-fields).
- Keeping them in one model means callers can load any bundle
  with one function, and the CLI needs no per-type branching.
- The two per-type fields (`target_current_status`, `task` /
  `proposed_label_ids`) are schema-optional at the model level and
  semantically-required at the validator level — the validator
  surfaces the required-but-missing case as a `MISSING_REQUIRED_FIELD`
  fatal finding rather than a Pydantic `ValidationError`, which
  keeps the fatal/advisory distinction uniform.
- Mixed per-type fields (e.g. `task` set on a taxonomy_promotion
  bundle) raise an advisory `MIXED_BUNDLE_FIELDS`, not a fatal
  error — mirroring the Chunk 7.32 validator's advisory style for
  non-blocking inconsistencies.

### 4.4 Source review evidence — intentionally not modelled

Brief §4.C says to implement source-review validation "only if the
repository already has a defined source-review evidence structure".
Inspection: the repository has source-governance *procedure*
(SOURCE_REGISTRATION_GUIDE.md and the Chunk 7.26A reviewer packet
prose), but no typed source-review evidence schema. **This chunk
does not create one.** The brief's §4.C "report that limitation
rather than creating an unsupported approval workflow" direction
is honoured by this report (§14 below).

---

## 5. Validation rules implemented

### 5.1 Shared (all bundle types)

| Check ID | Description | Finding kind |
|---|---|---|
| `reviewers.pseudonyms_distinct` | No pseudonym appears twice | fatal `DUPLICATE_REVIEWER` |
| `reviewers.proposer_not_in_reviewers` | Proposer is not among reviewers (TAXONOMY_APPROVAL_CHECKLIST §104-106) | fatal `PROPOSER_IS_REVIEWER` |
| `reviewers.evidence_refs_recommended` | Each reviewer has evidence_refs populated | advisory `MISSING_EVIDENCE_REFERENCE` |
| `identity_authentication_scope_disclaimer` | Unconditional | limitation `IDENTITY_AUTHENTICATION_NOT_ESTABLISHED` |

### 5.2 Taxonomy promotion

| Check ID | Description | Finding kind |
|---|---|---|
| `taxonomy_promotion.target_id_shape` | `target_id` matches `lbl_...` label regex | fatal `TARGET_ID_MISMATCH` |
| `taxonomy_promotion.target_current_status_present` | `target_current_status` is set | fatal `MISSING_REQUIRED_FIELD` |
| `taxonomy_promotion.reviewer_count_is_two` | Exactly two reviewers (TAXONOMY_APPROVAL_CHECKLIST §76-77) | fatal `WRONG_REVIEWER_COUNT` |
| `taxonomy_promotion.proposer_identity_present` | Proposer is set (needed to check §104-106) | advisory `REVIEWER_INDEPENDENCE_NOT_ESTABLISHED` |
| `taxonomy_promotion.annotation_fields_absent` | `task` / `proposed_label_ids` not set | advisory `MIXED_BUNDLE_FIELDS` |

### 5.3 Annotation review

| Check ID | Description | Finding kind |
|---|---|---|
| `annotation_review.target_id_shape` | `target_id` matches `ach_<32-hex>` achievement regex | fatal `TARGET_ID_MISMATCH` |
| `annotation_review.task_present` | `task` is set | fatal `MISSING_REQUIRED_FIELD` |
| `annotation_review.label_arity_for_<task>` | Per-task arity: `primary_type` = 1, `extraction_review` = 0, `domain_tags` = any | fatal `INVALID_LABEL_ARITY` |
| `annotation_review.proposed_label_id_shapes` | Each proposed label matches `lbl_...` regex | fatal `TARGET_ID_MISMATCH` |
| `annotation_review.reviewer_count_at_least_one` | At least one reviewer (single-review workflow permitted) | fatal `WRONG_REVIEWER_COUNT` |
| `annotation_review.taxonomy_fields_absent` | `target_current_status` not set | advisory `MIXED_BUNDLE_FIELDS` |

### 5.4 Error-code taxonomy

Stable identifiers:

```
MISSING_REQUIRED_FIELD
INVALID_DECISION                       # caught at Pydantic layer
DUPLICATE_REVIEWER
REVIEWER_INDEPENDENCE_NOT_ESTABLISHED  # advisory, triggered by missing proposer
MISSING_EVIDENCE_REFERENCE             # advisory
TARGET_ID_MISMATCH
UNSUPPORTED_BUNDLE_TYPE                # defensive; unreachable with current enum
IDENTITY_AUTHENTICATION_NOT_ESTABLISHED  # always a limitation
PROPOSER_IS_REVIEWER
WRONG_REVIEWER_COUNT
INVALID_LABEL_ARITY
MIXED_BUNDLE_FIELDS                    # advisory
```

Codes are string constants on an `ErrorCode` class rather than an
enum because they are machine identifiers consumed by downstream
tooling; keeping them string constants avoids forcing enum
serialisation.

---

## 6. Independence and authentication limitations

The brief's §5 is explicit:

> The validator must not: … Infer independence from different
> display names.

The implementation respects this:

- **Pseudonym distinctness** is a *necessary* condition for
  independence, so the validator emits `DUPLICATE_REVIEWER` when
  pseudonyms repeat. It does **not** emit "independent" as a
  positive finding — distinct pseudonyms are consistent with
  independent reviewers but do not prove them.
- **Proposer-reviewer overlap** is a *sufficient* condition for
  non-independence, so the validator emits `PROPOSER_IS_REVIEWER`
  when the proposer appears among the reviewers.
- **Missing proposer** means the validator cannot run the
  proposer-reviewer check, so it emits
  `REVIEWER_INDEPENDENCE_NOT_ESTABLISHED` as an *advisory*. This
  code name follows the brief's §5 vocabulary.
- **Identity authentication** is always `IDENTITY_AUTHENTICATION_NOT_ESTABLISHED`
  — unconditionally, on every report. The brief states "If
  reviewer identity cannot be authenticated by the available
  repository evidence, explicitly report
  `IDENTITY_AUTHENTICATION_NOT_ESTABLISHED`"; since this validator
  has no mechanism to authenticate (no PGP signatures, no GitHub
  OIDC claim, no PR event stream), authentication is never
  established.
- **`ValidationReport.authenticated` is a Python property that
  always returns `False`** — not configurable, not overridable.
  Downstream code that treats `.structurally_valid is True` as
  approval cannot cite this validator as the ground truth, because
  the companion `.authenticated` is unambiguously False.

---

## 7. Fail-closed behavior

The validator distinguishes the five states listed in brief §7:

1. **Structurally valid bundle.** `structurally_valid=True`,
   `authenticated=False`, `fatal_count=0`, one or more
   `limitations` entries (always at least `IDENTITY_AUTHENTICATION_NOT_ESTABLISHED`).
2. **Fatal validation errors.** `structurally_valid=False`,
   `fatal_errors` non-empty with specific codes.
3. **Advisory findings.** Zero fatal, non-empty `advisories` — the
   bundle still clears `structurally_valid`, but the advisories
   are reported to the reviewer.
4. **Authenticity / independence not established.** Either
   advisory `REVIEWER_INDEPENDENCE_NOT_ESTABLISHED` (proposer
   missing) or the unconditional
   `IDENTITY_AUTHENTICATION_NOT_ESTABLISHED` limitation.
5. **Incomplete for the applicable checklist.** Specific codes:
   `WRONG_REVIEWER_COUNT` for taxonomy promotions with !=2
   reviewers; `MISSING_REQUIRED_FIELD` for missing per-type fields
   like `target_current_status` or `task`.

Fail-closed invariants:

- `.structurally_valid` is derived from `fatal_errors` alone, so a
  bundle with advisories but no fatal findings is "structurally
  valid" but **not** "approved".
- `.authenticated` is always False (hard-coded property).
- The validator never mutates `bundle` (verified by test 13).
- The validator never calls `training_ready_subset`,
  `eligible_ground_truth`, `load_dataset`, `load_records`,
  `load_annotations`, `load_and_validate_taxonomy`,
  `load_taxonomy`, or `validate_taxonomy` (verified by AST-based
  tests 14 / 15 / 18).
- The validator never references `AnnotationStatus`,
  `AnnotationStatusMap`, `SourceRegistry`, or `ReviewStatus` in
  its code (verified by AST-based tests 16 / 17).

The last two bullets are enforced by six AST-based tests that
parse the module source, strip docstrings, and inspect every
`ast.Name`, `ast.Attribute`, `ast.ImportFrom`, and `ast.Import`
node. Mentioning these names in the module docstring (for the
fail-closed-contract explanation) is allowed; using them is not.

---

## 8. Tests added

Two test files under `tests/review/`:

### 8.1 `tests/review/test_evidence_bundle.py` (35 cases)

Required 18 cases from the brief §8:

1. ✓ `test_01_valid_structural_taxonomy_bundle`
   (+ `test_01b_valid_structural_annotation_bundle`)
2. ✓ `test_02_missing_required_field`
3. ✓ `test_03_invalid_reviewer_decision`
4. ✓ `test_04_duplicate_reviewer_identity`
5. ✓ `test_05_missing_reviewer_rationale_when_required`
6. ✓ `test_06_missing_evidence_reference_advisory`
7. ✓ `test_07_mismatched_taxonomy_label_id`
8. ✓ `test_08_mismatched_achievement_record_id`
9. ✓ `test_09_unsupported_bundle_type`
10. ✓ `test_10_reviewer_independence_proposer_overlap`
11. ✓ `test_11_structurally_valid_but_authentication_unavailable`
12. ✓ `test_12_incomplete_bundle_remains_incomplete`
13. ✓ `test_13_validation_does_not_mutate_input`
14. ✓ `test_14_validation_does_not_modify_taxonomy_file` (AST)
15. ✓ `test_15_validation_does_not_modify_achievement_records` (AST)
16. ✓ `test_16_validation_does_not_modify_annotation_statuses` (AST)
17. ✓ `test_17_validation_does_not_modify_source_statuses` (AST)
18. ✓ `test_18_validation_does_not_change_training_readiness` (AST)

Additional coverage:

- `test_annotation_review_primary_type_arity_zero_fatal`
- `test_annotation_review_primary_type_arity_two_fatal`
- `test_annotation_review_extraction_review_arity_zero_ok`
- `test_annotation_review_domain_tags_arity_any`
- `test_reviewer_pseudonym_email_rejected`
- `test_taxonomy_bundle_missing_proposer_advisory`
- `test_taxonomy_bundle_three_reviewers_fatal`
- `test_taxonomy_bundle_annotation_fields_advisory`
- `test_annotation_bundle_taxonomy_fields_advisory`
- `test_report_is_json_serializable`
- `test_report_structurally_valid_property`
- `test_load_bundle_from_yaml`
- `test_load_bundle_malformed_yaml_raises`
- `test_load_bundle_missing_file_raises`
- `test_authenticated_is_always_false`
- `test_extra_fields_forbidden_on_bundle`

### 8.2 `tests/review/test_cli.py` (6 cases)

- `test_cli_valid_bundle_exits_zero`
- `test_cli_wrong_reviewer_count_exits_one`
- `test_cli_missing_file_exits_one`
- `test_cli_malformed_toplevel_exits_one`
- `test_cli_pydantic_validation_error_exits_one`
- `test_cli_requires_subcommand`

All fixtures are inline YAML strings or in-memory Pydantic
objects. No file in `hybrid_dataset/` or any other project
directory is read or written by the tests. No real reviewer
identity is referenced — pseudonyms are suffixed `_test` to
visibly separate them from any real labeler ids a future dataset
might carry.

---

## 9. Actual test results

### 9.1 New review tests (focused run)

```
cd AI-Powered-Student-Achievement-Intelligence-Platform
.\.venv\Scripts\python.exe -m pytest tests/review -q
```

Result:

```
41 passed in 1.20s
```

Exit code: `0`.

### 9.2 Full repository suite (regression check)

```
cd AI-Powered-Student-Achievement-Intelligence-Platform
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```
620 passed, 5 skipped in 26.17s
```

Exit code: `0`.

**Pre-chunk baseline** was `579 passed, 5 skipped`. The delta is
exactly `+41 passed`, matching the number of new tests. The five
skips are the same as before: four Windows-symlink skips in
`tests/ingestion/test_inventory.py` and one `fakeredis`-not-
installed skip in `tests/ingestion/test_redis_rate_limit.py`. No
pre-existing test was modified; no pre-existing test regressed.

### 9.3 Environmental limitations

- The `fakeredis` skip persists; this chunk did not add the
  `fakeredis[lua]>=2,<3` requirement to the venv, consistent with
  "do not install dependencies without authorization".
- The Windows-symlink skips persist; this chunk did not touch
  developer-mode or symlink behaviour.

### 9.4 Test refinement during this chunk

The initial run showed test 18 failing: the module docstring
intentionally mentioned `training_ready_subset` to explain the
fail-closed contract, and the first implementation of test 18 did
a naive substring search. Tests 14-18 were rewritten to use an
AST-based identifier scan that strips docstrings (via
`ast.walk` + body-first-element pruning) before collecting
identifier references. This change made the test robust against
documentation that explains what the module does NOT do, while
still catching accidental imports or calls. After the rewrite,
all 41 tests pass.

---

## 10. CLI integration

The CLI is integrated as a sibling to the existing dataset and
inventory CLIs, following the same conventions:

- Module: `src/nlp_semantic/review/cli.py`.
- Invocation: `PYTHONPATH=src python -m nlp_semantic.review.cli
  validate <bundle_path>`.
- Subcommand name: `validate`. This mirrors the dataset CLI's
  `validate` subcommand name but lives in a distinct module, so
  there is no overlap or ambiguity.
- stdout: JSON report (indented).
- stderr: concise one-line summary with ASCII `|` separators (so
  Windows code pages render it correctly).
- Exit codes: `0` structurally valid, `1` fatal / load failure,
  `2` argparse usage error.
- Suppresses no messages that would hide failures; prints no
  secrets or personal information (bundles themselves do not
  carry PII beyond pseudonyms).

CLI tests (`tests/review/test_cli.py`) cover:

- Valid bundle → exit 0, `structurally_valid: True`, stderr `ok`.
- Wrong reviewer count → exit 1, stderr `fatal`.
- Missing file → exit 1, stderr `FileNotFoundError`.
- Non-mapping top-level YAML → exit 1, stderr `BundleLoadError`.
- Missing required field (Pydantic) → exit 1, stderr
  `ValidationError`.
- No subcommand → `SystemExit(2)` from argparse.

**No CLI integration deferral.** Not `VALIDATOR IMPLEMENTED — CLI
DEFERRED`.

---

## 11. Files created and modified

Files **created** in Chunk 7.38B:

| Path | Purpose |
|---|---|
| `src/nlp_semantic/review/__init__.py` | Public API re-exports. |
| `src/nlp_semantic/review/evidence_bundle.py` | The validator module (schemas, loader, `validate_bundle`). |
| `src/nlp_semantic/review/cli.py` | The `python -m nlp_semantic.review.cli validate <path>` CLI. |
| `tests/review/__init__.py` | Package marker. |
| `tests/review/test_evidence_bundle.py` | 35 tests covering the 18 required cases plus coverage extras. |
| `tests/review/test_cli.py` | 6 CLI tests. |
| `reports/chunk_7_38B_reviewer_evidence_bundle_validator.md` | This report. |

Files **modified** in Chunk 7.38B: **none.**

Git: no `add`, no `commit`, no `push`, no `checkout`, no `reset`,
no `clean`, no `stash`.

---

## 12. Confirmation of protected-file preservation

- `src/ml/`, `src/recommender/`, `src/backend/` — do not exist on
  this branch; not created.
- Teammate-owned code: none exists on `feature/nlp-semantic`;
  nothing touched.
- `src/nlp_semantic/schema/`, `src/nlp_semantic/dataset/`,
  `src/nlp_semantic/ingestion/` — not modified. Reused via import
  only. Verified by `git status --short`: none of these paths
  appears in the modified list.
- Pre-existing uncommitted changes (`sources.yaml`,
  `pyproject.toml`, `requirements.txt`) — unchanged.
- Pre-existing untracked artefacts (PROJECT_HANDOFF.md,
  arxiv_governance.py, rate_limit.py, test files, prior
  reports/) — all still present and unchanged.

---

## 13. Confirmation of unchanged state

The brief §12-13 asks for explicit confirmation. Each is verified
by running the respective CLI or by `git status`:

- **Taxonomy status unchanged.** 14 primary + 10 domain labels
  all remain `status: draft`. No field of
  `primary_taxonomy.yaml` or `domain_tags.yaml` modified.
- **Dataset unchanged.** `batch_01_sih2024.yaml` is byte-identical
  to its pre-chunk state. No new batch created.
- **Source statuses unchanged.** `src_5a8a2998…`
  `review_status: unreviewed`, `license: UNKNOWN`;
  `src_08ee850b…` `review_status: unreviewed`, `license: CC0-1.0`.
  Both unchanged.
- **Annotation statuses unchanged.** All seven SIH records remain
  at `annotation_status.primary_type: draft`,
  `annotation_status.domain_tags: not_started`.
- **Readiness-logic unchanged.** `training_ready_subset` behaviour
  is byte-identical (`validator.py` not touched). `cli readiness`
  continues to report `any_task=not_ready | all_tasks=not_ready
  | approved(pt=0,dt=0) | eligible(pt=0,dt=0) | blockers=4`.
- **No reviewer decision or source approval created.** The
  validator does not write; the CLI reads only; the tests use
  synthetic fixtures.

The six AST-based tests (14 / 15 / 16 / 17 / 18) encode these
guarantees as regression tests for any future change to
`evidence_bundle.py`.

---

## 14. Remaining human-review requirements

This chunk does **not** resolve any of the project's
training-readiness blockers (brief §14 explicit warning). The
Chunk 7.36 §13.1 critical path remains:

1. PIB-policy applicability decision — pending human reviewer
   action on the Chunk 7.26A packet.
2. `lbl_hackathon` taxonomy promotion — the Chunk 7.37 packet is
   ready for review; a human reviewer must open the promotion PR
   and two human reviewers must post sign-off comments.
3. Per-record annotation review for the seven SIH records.

**What this chunk changes about those requirements:** when a
reviewer opens the Chunk 7.2 promotion PR for `lbl_hackathon`,
they (or the proposer) can now author a small YAML bundle
matching the schema in §4, run
`python -m nlp_semantic.review.cli validate <bundle>.yaml`, and
self-check for structural omissions (missing proposer, missing
rationale, wrong reviewer count, missing evidence refs) before
posting on the PR. The validator **does not** replace the
reviewer-independence rule — it only names its own blind spot and
asks reviewers to respect the procedural rule.

### 14.1 Source-review evidence (deferred)

Per §4.4, the repository does not yet have a typed source-review
evidence structure. Options for a future chunk:

- Add a third `BundleType.SOURCE_REVIEW` with fields mirroring
  the `SourceRegistry` columns a reviewer must confirm
  (`source_url`, `license`, `usage_restrictions`,
  `collection_date`, `original_labels`, `intended_use`).
  Preserve the shared reviewer / proposer / decision shape.
- Alternatively, keep source-review evidence as prose inside the
  Chunk 7.26A reviewer packet and never model it typed.

Neither option is this chunk's concern; both are reviewer /
owner judgement calls for later.

---

## 15. Final disposition

**`VALIDATOR IMPLEMENTED`**

Rationale:

- The validator module is in place and all tests pass
  (41 focused + 579 pre-existing = 620 passed, 5 skipped).
- The CLI is integrated into the existing CLI pattern — not
  deferred.
- The fail-closed contract is enforced by Python code and by
  AST-based regression tests.
- No protected file was touched; no taxonomy / dataset / source /
  annotation status changed; no reviewer decision created; no
  external HTTP request issued; no git stage / commit / push.
- The brief's §15-category "forbidden" list is honoured
  item-by-item (§1.2 above).

Alternative dispositions considered and rejected:

- `VALIDATOR IMPLEMENTED — CLI DEFERRED` — would be correct if
  the CLI did not fit the existing architecture. It does (same
  argparse pattern as the dataset CLI, same output conventions,
  same exit codes), so no deferral.
- `DESIGN BLOCKED BY EXISTING SCHEMA` — would be correct if an
  existing schema (`Annotation`, `SourceRegistry`, …) already
  modelled reviewer-evidence packets. None does. The new
  `EvidenceBundle` + `ReviewerSignOff` models are additive.
- `REPOSITORY PRECONDITION MISMATCH` — would be correct if branch
  or HEAD differed from the baseline. §2 passes.
- `VALIDATION FAILED` — would be correct if any test failed after
  the fix. All 620 tests pass.

---

## 16. Final response fields

- **Branch:** `feature/nlp-semantic`
- **HEAD:** `c8c1b80 feat: add SIH 2024 achievement pilot`
- **Working-tree preservation:** confirmed; pre-existing modified
  and untracked files unchanged.
- **Report path:**
  `reports/chunk_7_38B_reviewer_evidence_bundle_validator.md`
- **Files created:** 7 (see §11).
- **Files modified:** 0.
- **Tests executed:**
  - `pytest tests/review -q` → `41 passed in 1.20s`, exit 0.
  - `pytest -q` → `620 passed, 5 skipped in 26.17s`, exit 0.
- **CLI integration:** complete, following existing
  argparse-based pattern (`python -m nlp_semantic.review.cli
  validate <path>`).
- **Protected files touched:** none.
- **Taxonomy / dataset changed:** no (verified §13).
- **Reviewer decision or source approval created:** no.
- **Final disposition:** `VALIDATOR IMPLEMENTED`.

### 16.1 Recommended next action

Per the brief's instruction to distinguish three categories:

1. **Human reviewer action for `lbl_hackathon` promotion.** The
   Chunk 7.37 promotion packet is ready. A human reviewer should
   open the promotion PR, cite the packet, and two reviewers
   should post sign-off comments. The new validator here can be
   used to self-check the sign-off bundle before posting but
   **does not** short-circuit the reviewer-independence or
   authenticity rules.
2. **Technical work that can continue without reviewer approval.**
   Chunk 7.35 §O.3 listed two other AI-driven candidates besides
   this one:
   - **Chunk 7.38A — `lbl_competition` taxonomy promotion
     packet.** Same packet pattern as Chunk 7.37, next label in
     the checklist's recommended review order.
   - **Chunk 7.38C — `src/nlp_semantic/dataset/duplicates_semantic.py`
     design chunk.** Widens the duplicate detector's coverage
     for future multi-source batches without new runtime deps.
3. **Genuine source-evidence collection for dataset expansion.**
   Only reviewer-driven. Chunk 7.34 §M (PRID 2082460 content
   determination) and Chunk 7.35 §O.2 (GSoC source review) are
   the two highest-leverage reviewer-driven next sources.

The validator **does not** resolve the project's source-
verification or training-readiness blockers (brief §14 explicit).
It is infrastructure that lowers the friction of the reviewer
actions those blockers require.
