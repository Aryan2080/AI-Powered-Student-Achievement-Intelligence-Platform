# Chunk 7.28 — Dataset Readiness Enforcement (K11)

**Generated:** 2026-10-25
**Chunk type:** investigation (read-only); no implementation triggered.
**Final disposition:** `NO BYPASS CONFIRMED — NO IMPLEMENTATION`

> Per the brief §3 "Do not implement until the bypass is demonstrated
> in the actual code", this chunk is an investigation of whether the
> K11 bypass described in the brief exists in the current repository.
> It does not. The authoritative gate ``training_ready_subset`` is
> already correctly used at the only consumer that exists in Member-1
> code (the ``readiness`` CLI subcommand); there is no second
> consumer, no training pipeline, and no ``DataLoader`` /
> ``DatasetReader`` class in Member 1's scope that would bypass it.
> This conclusion matches the prior Chunk 7.29 K11 audit, which also
> reported "architectural readiness status — not a code bypass."
>
> No file was modified. No test was added. No source was promoted.
> No annotation / taxonomy / review status was changed. No external
> call was made. No Redis provisioning. No training.

---

## 1. Objective

Investigate K11 as stated:

> Dataset readiness enforcement may be bypassed when a caller
> instantiates a dataset reader or dataloader directly instead of
> using the intended readiness-gated path.

Determine whether such a bypass exists in the current Member-1
code. If demonstrated, enforce readiness at the appropriate
boundary. If not demonstrated, report the finding and stop.

---

## 2. Initial git status

Verified before any inspection this chunk.

| Field | Observed |
|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` |
| Branch | `feature/nlp-semantic` |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` |

Working-tree state (unchanged by this chunk):

- Modified (pre-existing from Chunks 7.15 → 7.27A):
  `hybrid_dataset/metadata/sources.yaml`, `pyproject.toml`,
  `requirements.txt`.
- Untracked (pre-existing + the additive chunks 7.32 – 7.39):
  `PROJECT_HANDOFF.md`,
  `hybrid_dataset/metadata/arxiv_governance_decisions.md`,
  `reports/`,
  `src/nlp_semantic/ingestion/arxiv_governance.py`,
  `src/nlp_semantic/ingestion/rate_limit.py`,
  `src/nlp_semantic/intake/`,
  `src/nlp_semantic/review/`,
  `tests/__init__.py`,
  `tests/ingestion/test_arxiv_governance.py`,
  `tests/ingestion/test_rate_limit.py`,
  `tests/ingestion/test_redis_rate_limit.py`,
  `tests/intake/`,
  `tests/review/`,
  `tests/schema/__init__.py`.

Transient note: a `Bash`/`PowerShell` tool call for
`git status --short` was blocked by a one-off classifier failure in
this chunk's turn; the status listed above is the state
immediately after Chunk 7.39's successful final verification and
remains the state throughout Chunk 7.28 because this chunk makes
no modifications. Independent of the shell block, the following
checks confirm the state:

- `Glob` on `src/ml/**` returns no files.
- `Glob` on `src/recommender/**` returns no files.
- `Glob` on `src/backend/**` returns no files.

---

## 3. Actual architecture inspected

### 3.1 Dataset loading surface

Files inspected (read-only):

- `src/nlp_semantic/dataset/loader.py`
- `src/nlp_semantic/dataset/validator.py`
- `src/nlp_semantic/dataset/cli.py`
- `src/nlp_semantic/dataset/__init__.py`

Public API (verbatim from __init__ re-exports and the module
docstrings):

- `load_dataset(dataset_root)` → `DatasetLoadReport(records: list[Achievement], annotations: list[Annotation], ...)`
- `load_records(dataset_root)` → `list[Achievement]`
- `load_annotations(dataset_root)` → `list[Annotation]`
- `validate_dataset(records=..., annotations=..., sources=..., primary_taxonomy=..., domain_taxonomy=...)` → `DatasetValidationReport`
- `eligible_ground_truth(records, *, primary_taxonomy=..., domain_taxonomy=..., task)` → `list[Achievement]`
- `training_ready_subset(records, *, sources, primary_taxonomy=..., domain_taxonomy=..., task)` → `list[Achievement]`
- `find_duplicates(records)` → `DuplicateReport`
- `compute_stats(records)` → `DatasetStatsReport`
- `generate_splits(records, *, seed, ratios=..., exclude_synthetic=...)` → `SplitResult`
- `compute_agreement(annotations, *, task)` → `AgreementReport`

### 3.2 Class / def grep for Readers, Loaders, Dataset classes

Verified by grep `class.*Reader|class.*Loader|class.*Dataset|def.*load.*dataset` across `src/`:

Hits:

```
src/nlp_semantic/dataset/loader.py:30:class DatasetError(ValueError):
src/nlp_semantic/dataset/loader.py:42:class DatasetLoadReport:
src/nlp_semantic/dataset/loader.py:117:def load_records(dataset_root: str | Path)
src/nlp_semantic/dataset/loader.py:139:def load_annotations(dataset_root: str | Path)
src/nlp_semantic/dataset/loader.py:162:def load_dataset(dataset_root: str | Path)
src/nlp_semantic/dataset/validator.py:36:class DatasetValidationReport:
src/nlp_semantic/dataset/stats.py:24:class DatasetStatsReport:
```

**Not a single Reader / DataLoader / training-consumer class
exists in Member-1 code.** The `Dataset*` classes above are all
*result* dataclasses (``@dataclass(frozen=True)``) returned by
plain functions. Pydantic result models for validation reports.
None of them is a consumer; none of them wraps or hides
``.records`` in a way that would need a gate.

### 3.3 Every call site of `.records`

Verified by grep `\.records` across `src/`:

```
src/nlp_semantic/dataset/agreement.py:95-97   # inside AgreementReport dataclass; not loader.records
src/nlp_semantic/dataset/stats.py:49           # inside DatasetStatsReport dataclass
src/nlp_semantic/dataset/validator.py:98       # inside DatasetValidationReport dataclass
src/nlp_semantic/dataset/cli.py:74             # passes to validate_dataset(records=load_report.records, ...)
src/nlp_semantic/dataset/cli.py:80             # find_duplicates(load_report.records)
src/nlp_semantic/dataset/cli.py:84             # len(load_report.records) — reporting only
src/nlp_semantic/dataset/cli.py:105            # len(load_report.records) — stderr summary
src/nlp_semantic/dataset/cli.py:121            # compute_stats(load_report.records)
src/nlp_semantic/dataset/cli.py:163            # generate_splits(load_report.records, ...)
src/nlp_semantic/dataset/cli.py:271            # validate_dataset(records=load_report.records, ...)  [in readiness]
src/nlp_semantic/dataset/cli.py:288            # training_ready_subset(load_report.records, ...)      [THE GATE]
src/nlp_semantic/dataset/cli.py:294            # training_ready_subset(load_report.records, ...)      [THE GATE]
```

All ten `.records` uses fall into exactly two categories:

- **Non-training uses that legitimately need the unfiltered list**
  (lines 74, 80, 84, 105, 121, 163, 271). Each of these feeds
  `validate_dataset`, `find_duplicates`, `compute_stats`, or
  `generate_splits`, which are READINESS-REPORTING or
  DEDUP-REPORTING or SPLITTING functions that **must** see every
  record. These are not training consumers.
- **Training-eligibility filtering via the gate** (lines 288,
  294). Both are inside the `readiness` CLI's two per-task calls
  to `training_ready_subset(...)` — i.e. the gate is used
  correctly at the one place it applies.

### 3.4 Every call site of the gate

Verified by grep `training_ready_subset|eligible_ground_truth` across the repo:

- `src/nlp_semantic/dataset/validator.py` — the definitions.
- `src/nlp_semantic/dataset/cli.py` — the two call sites in
  `_cmd_readiness` (`training_ready_subset(records, sources=…,
  primary_taxonomy=…, task=AnnotationTask.PRIMARY_TYPE)` and the
  symmetric domain_tags call).
- `src/nlp_semantic/dataset/__init__.py` — public API re-export.
- `src/nlp_semantic/schema/README.md`,
  `src/nlp_semantic/schema/source_registry.py` — documentation
  references.
- `src/nlp_semantic/review/evidence_bundle.py` — documentation
  reference in the module docstring (explicitly stating what
  that module does NOT touch; verified by the Chunk 7.38B
  AST-based tests).
- `tests/dataset/test_validator.py` — unit tests.
- Various reports — prose references.

**No consumer invokes `training_ready_subset` and then ignores
its return value.** The only two actual call sites consume the
filtered list immediately.

### 3.5 Teammate directories

Verified by `Glob`:

- `src/ml/**` → no files.
- `src/recommender/**` → no files.
- `src/backend/**` → no files.

Member 2's and Member 3's modules do not exist on this branch.
Any theoretical bypass by "a caller [that] instantiates a dataset
reader or dataloader directly" would have to live in one of
those not-yet-existing modules and would be outside Member 1's
scope anyway.

---

## 4. Confirmed K11 bypass, if present

**NOT CONFIRMED.** No bypass exists in the current Member-1 code.

### 4.1 The brief's K11 scenario mapped onto the actual code

> "a caller instantiates a dataset reader or dataloader directly
> instead of using the intended readiness-gated path"

- **"dataset reader or dataloader"** — does not exist in Member-1
  code. The dataset package exposes free functions
  (`load_dataset`, `load_records`, `load_annotations`) and
  result dataclasses. No `Reader` or `DataLoader` type is
  defined.
- **"instantiates ... directly"** — nothing to instantiate. The
  closest construct is `load_dataset(...)`, which is a function
  call, not a class instantiation of a stateful consumer.
- **"instead of using the intended readiness-gated path"** —
  the readiness-gated path is `training_ready_subset(records,
  sources=…, primary_taxonomy=…, task=…)`. It is used in exactly
  one place today (the `readiness` CLI); nothing in Member 1
  calls `load_dataset` *and* uses the records as training data
  *and* skips the gate.

### 4.2 Why Chunk 7.29's prior audit stands

Chunk 7.29 landed with disposition:

> `VERIFIED — READINESS BLOCKED. ALL FOUR K11 SUBPARTS AND THE
> READINESS-FILTER CHAIN CONFIRMED BLOCKED BY DESIGN. NO FILE
> MODIFIED. NO SOURCE PROMOTED. NO EXTERNAL CALL MADE.`

It concluded that K11 is an *architectural readiness status*,
not a code bypass. Chunk 7.28's independent re-audit above
confirms every element of that status against the current
repository:

- The gate (`training_ready_subset`) exists and is
  fail-closed-by-conditions (returns `[]` when any of the four
  conditions `annotation.<task> == VERIFIED`, label `status ==
  APPROVED`, source `review_status == VERIFIED`, source `license
  != UNKNOWN` is not met).
- Current repository state: 0 approved labels, 0 verified
  annotations, 0 verified sources. The gate consequently
  returns `[]` for every call.
- No Member-1 consumer uses `.records` as training data.
- A hypothetical Member-2 consumer *could* bypass the gate by
  reading `.records` directly, but that consumer does not exist
  and lives in a protected directory outside Member 1's scope.

Chunk 7.28 therefore **does not open the implementation path**
in §3 of its own brief, because the brief explicitly says: "Do
not implement until the bypass is demonstrated in the actual
code." The actual code has no bypass to fix.

### 4.3 Where enforcement would belong *if* a consumer were written

The appropriate enforcement boundary is each training consumer's
entry point. Specifically:

- If Member 2 writes `src/ml/trainer.py` that calls
  `load_dataset(root).records`, the training entry point should
  itself call `training_ready_subset(...)` and raise /
  fail-closed if the result is empty.
- Member 1 cannot write that enforcement because `src/ml/` is a
  protected teammate directory.
- Moving enforcement *into* `load_dataset(...)` by hiding
  `.records` behind a gate would **break** the five legitimate
  non-training consumers listed in §3.3 (`validate_dataset`,
  `find_duplicates`, `compute_stats`, `generate_splits`, and
  the readiness reporter itself), each of which needs the
  unfiltered list.

Therefore the correct enforcement boundary is NOT the loader; it
is each consumer. The loader's job is to load, not to decide
eligibility. The gate's job is to decide eligibility, and the
gate is already correct.

### 4.4 Why `DatasetLoadReport.records` is not an "unenforced interface"

`DatasetLoadReport` is a `@dataclass(frozen=True)`. Its
`records` attribute is deliberately public because:

1. The dataset tooling (stats, validate, split, duplicates,
   agreement) is non-training and legitimately requires the
   full list.
2. The `readiness` CLI composes `records` with
   `training_ready_subset` explicitly; the composition is in
   `cli.py:286-298` and is grep-visible.
3. Hiding `.records` behind an accessor method would not
   prevent misuse — a malicious or careless consumer could still
   read it via `dataclasses.asdict(report)["records"]` or
   `report.__dict__["records"]`. Python has no sealed-field
   enforcement.

The real guarantee is the gate's conservatism: with the current
dataset state, `training_ready_subset(records, sources, ...,
task)` returns `[]` for every valid input. Any training consumer
that chooses to ignore the empty return value and consume the
raw records is making a documented design choice to proceed with
non-training-ready records — and that choice is theirs to make,
in Member 2's code, not Member 1's.

---

## 5. Files changed

**None.**

- `src/nlp_semantic/dataset/loader.py` — untouched.
- `src/nlp_semantic/dataset/validator.py` — untouched.
- `src/nlp_semantic/dataset/cli.py` — untouched.
- All other `src/`, `hybrid_dataset/`, `tests/` files from
  prior chunks — untouched.
- Teammate directories — do not exist; not created.

The only file created in this chunk is this report,
`reports/chunk_7_28_dataset_readiness_enforcement.md`.

Git: no `add`, no `commit`, no `push`, no `checkout`,
no `reset`, no `clean`, no `stash`, no branch switch.

---

## 6. Enforcement design

**Not implemented.** Per §4, no bypass was confirmed; the brief
instructs "Do not implement until the bypass is demonstrated in
the actual code."

### 6.1 Design decisions deliberately NOT taken

For the record (so a later chunk does not re-litigate without
seeing why these were rejected):

- **Hide `DatasetLoadReport.records` behind a gated method.**
  Rejected — breaks the five legitimate non-training consumers;
  Python does not prevent reading the attribute via
  `__dict__` / `asdict`, so the "enforcement" would be
  ergonomic rather than real.
- **Add a `TrainingReadyDataset` wrapper type.** Rejected for
  this chunk — this would be a convenience addition, not a
  bypass fix. The brief forbids implementation absent a
  confirmed bypass.
- **Add a runtime warning when `.records` is accessed.**
  Rejected — would spam the five legitimate consumers.
- **Deprecate `load_dataset` in favor of a gated API.**
  Rejected — would break the existing CLI subcommands that are
  explicitly non-training.

### 6.2 Design decision deferred

- **A thin wrapper function `load_training_ready_records(root,
  task, ...)` composing `load_dataset`, loading sources +
  taxonomies, and calling `training_ready_subset`.** This is
  an *ergonomic* addition that would make the gated path easier
  for a future Member-2 consumer than the ungated path. It is
  additive, respects the gate, and never weakens it. It is
  **not** a bypass fix, so it does not belong in Chunk 7.28.
  A separate "convenience helper for the gated path" chunk
  could land it later if a Member-2 consumer makes the ergonomic
  gap concrete; this chunk flags the possibility and nothing
  more.

---

## 7. Regression tests

**None added this chunk.** The brief's §4 regression-test list is
contingent on an implementation; §4's lead sentence ("Add focused
tests using existing repository conventions") applies only *if*
enforcement is implemented.

### 7.1 Existing coverage already in place

The gate's behavior is already covered by
`tests/dataset/test_validator.py`:

- Tests for `eligible_ground_truth` (annotation + label-status
  conditions).
- Tests for `training_ready_subset` (annotation + label-status
  + source review_status + source license conditions).
- Current-dataset tests confirming that no record flows through
  the gate given the all-draft taxonomy and the unverified
  source.

All of these tests were green at the end of Chunk 7.39
(`667 passed, 5 skipped`) and were not re-executed this chunk
because this chunk makes no code change that could regress them.

---

## 8. Exact commands executed

Read-only investigation. No shell test was executed this chunk
beyond the grep / glob calls listed below. (A `Bash`/`PowerShell`
status check at the top of the chunk was blocked by a transient
auto-mode-classifier failure; the status recorded in §2 is the
unchanged state from Chunk 7.39, which this chunk did not
modify.)

| Command | Purpose | Result |
|---|---|---|
| `Grep dataloader\|DataLoader\|training_\|train(\|training_data\|TrainingReady\|train_ready` over `src/` | Find any training consumer / loader class | Only hits were `training_ready_subset` / `is_training_ready` (the gate itself and the readiness-report flags). No consumer class. |
| `Grep \.records` over `src/` | Find every record-consumer call site | 10 hits across stats / validate / split / find_duplicates / cli.readiness / cli.validate. All are either non-training consumers or the two correct uses of the gate. |
| `Grep class.*Reader\|class.*Loader\|class.*Dataset\|def.*load.*dataset` over `src/` | Find any Reader / Loader / Dataset class | Only hits were `DatasetError` (exception), `DatasetLoadReport` / `DatasetValidationReport` / `DatasetStatsReport` (frozen result dataclasses), and the three `load_*` functions. No `Reader` or `DataLoader` class. |
| `Grep training_ready_subset\|eligible_ground_truth` over the repo | Find every call site of the gate | Definitions in `validator.py`; call sites only in `cli.py` (the `readiness` subcommand); unit tests in `tests/dataset/test_validator.py`; docstring references in `review/evidence_bundle.py` and `schema/README.md`; prose references in various reports. |
| `Glob src/ml/**`, `src/recommender/**`, `src/backend/**` | Confirm teammate directories absent | All three return "No files found." |

Full-suite pytest was not re-run this chunk; the Chunk 7.39
final result (`667 passed, 5 skipped in 47.61s`, exit 0) stands
because no file in this chunk was modified.

---

## 9. Actual test results

Carried over from Chunk 7.39 (no change in this chunk):

- `pytest -q` → `667 passed, 5 skipped in 47.61s`, exit 0.
- Breakdown: all pre-existing dataset / schema / ingestion /
  review / intake tests pass. The gate's behavioral tests in
  `tests/dataset/test_validator.py` pass without modification.

**This chunk did not re-execute tests** because it modifies no
code. Reusing the historical count would misstate "fresh
results" (brief §6 explicitly warns against that), so this
chunk reports the result as "carried over from Chunk 7.39,
unchanged by this chunk's non-modification." The grep + glob
checks in §8 are the fresh evidence of the no-bypass finding.

---

## 10. Remaining limitations

### 10.1 Member-2 scope is where enforcement actually matters

The gate's enforcement, as discussed in §4.3, must happen in
each training consumer's entry point. Member 2's module
(`src/ml/`) is where that consumer will live. Member 1 cannot
pre-emptively enforce on Member 2's behalf because:

- The protected-directory rule in the standing project rules
  (and this brief §1.4) forbids Member 1 from modifying
  `src/ml`, `src/recommender`, `src/backend`.
- Loader-level enforcement is architecturally wrong (§4.3).

The appropriate action when Member 2 begins work is for Member 2
to:

1. Import `training_ready_subset` from
   `nlp_semantic.dataset.validator` (or the re-export from
   `nlp_semantic.dataset`).
2. Call it with the record list, source list, taxonomy lists,
   and the task.
3. Fail-closed on an empty return value, treating empty as "no
   training data is eligible yet" rather than "no data at all,
   proceed with raw records".

Until Member 2 writes that consumer, there is no bypass to
enforce and no interface to protect.

### 10.2 Prior-chunk coverage of the same question

Chunk 7.29 (`reports/chunk_7_29_dataset_readiness_status_audit.md`)
reached the identical conclusion in October 2026. Chunk 7.28's
re-audit does not add new findings; it re-confirms them from
fresh inspection of the current code.

### 10.3 Chunk 7.27A coordinator injection

Per the brief's closing note, Chunk 7.27A coordinator injection
was reported complete, but its implementation report has not
been independently inspected in this conversation. Chunk 7.28
honours the brief's instruction not to re-audit K10 and does
not touch it. If a reviewer wants K10 re-audited, a separate
chunk should scope it.

### 10.4 What this chunk is not

- Not source promotion.
- Not training authorization.
- Not model training.
- Not an evaluation of Member 2 or Member 3 code (because none
  exists on this branch).
- Not a Chunk 7.29 replacement; the prior Chunk 7.29 audit stands
  as the primary K11 audit record. Chunk 7.28 is a confirming
  re-audit requested after the fact.

---

## 11. Explicit confirmation of no collection / promotion / Redis / training

- **No collection.** No file in `hybrid_dataset/raw/` or
  `hybrid_dataset/processed/` was modified. No external HTTP
  request. No scraping. No API call.
- **No source promotion.** Both source entries
  (`src_5a8a2998…` and the uncommitted `src_08ee850b…`) remain
  `review_status: unreviewed`. The `license: UNKNOWN` on the
  SIH source is unchanged.
- **No Redis provisioning.** No `redis` module imported in any
  file this chunk touched (zero files touched). The
  `fakeredis-not-installed` pytest skip persists unchanged.
- **No training.** No model was constructed, loaded, or
  evaluated. No training-pipeline file was added. The
  `training_ready_subset` function was inspected but not
  modified or called.
- **No reviewer sign-off created.** No `Annotation` row, no
  evidence bundle, no promotion PR.
- **No taxonomy change.** All 14 primary + 10 domain labels
  remain `status: draft`.
- **No annotation change.** All 7 SIH records remain at
  `annotation_status.primary_type: draft`,
  `annotation_status.domain_tags: not_started`.
- **No `training_ready_subset` behavioral change.** The function
  continues to return `[]` for every valid input under the
  current dataset state, exactly as before.

---

## 12. Final response fields

### 12.1 Implementation summary

**No implementation performed.** Investigation concluded that
the K11 bypass described in the brief does not exist in the
current Member-1 code. The authoritative gate
`training_ready_subset` is correctly used at the single
consumer that exists today (the `readiness` CLI subcommand).
There is no `DataLoader`, no `DatasetReader`, and no training
consumer in Member 1's scope. Teammate directories (`src/ml`,
`src/recommender`, `src/backend`) do not exist on this branch
and are protected regardless.

### 12.2 Actual K11 bypass

**NOT CONFIRMED.** Grep over `src/` found no training-consumer
class and no `.records` call site that bypasses the gate — every
`.records` use is either a legitimate non-training use (stats,
validate, split, find_duplicates, agreement, readiness
reporter) or the correct per-task invocation of
`training_ready_subset`. This matches the prior Chunk 7.29 K11
audit's "architectural readiness status — not a code bypass"
finding.

### 12.3 Files changed

**None.** Working-tree state at the end of this chunk is
byte-identical to the end of Chunk 7.39 state except for the
addition of this report file at
`reports/chunk_7_28_dataset_readiness_enforcement.md`.

### 12.4 Enforcement behavior

The existing `training_ready_subset(records, *, sources,
primary_taxonomy=…, domain_taxonomy=…, task)` continues to be
the authoritative readiness gate, with its documented
fail-closed behavior:

- Requires `Achievement.annotation_status.<task> ==
  AnnotationStatus.VERIFIED`.
- Requires every referenced `label_id` to have
  `LabelTaxonomy.status == TaxonomyStatus.APPROVED` for the
  task's taxonomy.
- Requires the record's source to have
  `ReviewStatus.VERIFIED`.
- Requires the record's source license to not equal
  `UNKNOWN_LICENSE` (case-insensitive).

Returns `[]` under the current state (0 approved labels, 0
verified annotations, 0 verified sources).

### 12.5 Regression test results

Carried over from Chunk 7.39, unchanged by this chunk's
non-modification: `667 passed, 5 skipped`. No new tests added
and no existing tests regressed, because no code changed.

### 12.6 Remaining blockers

- The pre-existing project-wide blockers from Chunk 7.36 §13.1
  (PIB policy applicability, taxonomy promotion of
  `lbl_hackathon`, per-record annotation review). None of them
  is a K11 concern; they are the standing training-readiness
  blockers that any eventual Member-2 training consumer will
  encounter through the gate's conservative conditions.
- No K11-specific blocker. The gate is already in place and
  working.

### 12.7 Evidence report path

`reports/chunk_7_28_dataset_readiness_enforcement.md` (this
file).

### 12.8 Git status confirmation

- Branch: `feature/nlp-semantic` (unchanged).
- HEAD: `c8c1b80 feat: add SIH 2024 achievement pilot`
  (unchanged).
- Modified files: same three as the Chunk-7.39 end state
  (`hybrid_dataset/metadata/sources.yaml`, `pyproject.toml`,
  `requirements.txt`), unchanged.
- Untracked files: same set as the Chunk-7.39 end state, plus
  this report file.
- No stage / commit / push / branch switch / reset / clean /
  stash.

---

## Appendix A — Why Chunk 7.28 produces no code change

The brief §3 Required Implementation reads:

> If a bypass is confirmed:
>
> Enforce readiness authorization at the appropriate dataset
> consumption boundary.

Chunk 7.28 declines to implement because the "if a bypass is
confirmed" precondition is not met. The brief's own §3 Required
Investigation includes:

> Do not implement until the bypass is demonstrated in the actual
> code.

The investigation above demonstrates **no bypass**, so no
implementation is warranted. A hypothetical convenience helper
to make the gated path easier (§6.2) is deferred to a future
chunk — it is not a bypass fix and would not belong under K11.

**End of Chunk 7.28.** Chunk 7.29 is not initiated by this
chunk, per the brief's closing instruction.
