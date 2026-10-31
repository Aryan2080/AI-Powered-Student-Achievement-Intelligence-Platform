# Chunk 7.39 — Reviewer-Gated Evidence Intake Pipeline

**Generated:** 2026-10-25
**Chunk type:** infrastructure (new module + CLI + tests).
**Final disposition:** `EVIDENCE INTAKE IMPLEMENTED`

> Scope: ship a reviewer-gated, additive, fail-closed evidence
> intake pipeline that lets a reviewer hand a file to the project,
> get a stable intake id and SHA-256 hash, and have the file stored
> under an auditable per-intake directory with a tracked YAML
> manifest — without any of that implying source approval,
> annotation verification, taxonomy promotion, or
> training-readiness.

---

## 1. Final disposition

**`EVIDENCE INTAKE IMPLEMENTED`.**

Rationale:

- The pipeline module, CLI, and tests are all in place and all
  tests pass (`47 new` + `620 pre-existing` = `667 passed, 5 skipped`).
- The pipeline accepts reviewer-supplied files today — see §7.
- The CLI is integrated into the project's existing argparse-based
  CLI pattern (not deferred).
- Dataset state is byte-identical to pre-chunk (§11).
- No source status / taxonomy / annotation / training-readiness
  changed (§13).

Alternative dispositions considered and rejected:

- `EVIDENCE INTAKE IMPLEMENTED — CLI DEFERRED` — would be correct
  if the CLI didn't fit the existing architecture. It does (same
  pattern as `nlp_semantic.dataset.cli` and
  `nlp_semantic.review.cli`); no deferral.
- `DESIGN BLOCKED BY EXISTING SCHEMA` — would be correct if the
  existing schemas already represented intake metadata. They don't:
  `Evidence` represents approved evidence tied to a reviewer-signed
  `Achievement`; intake is the stage BEFORE Evidence is created.
  A new, narrow `IntakeEntry` schema is justified.
- `REPOSITORY PRECONDITION MISMATCH` — not applicable; §3 passes.
- `IMPLEMENTATION FAILED` — not applicable; all tests pass.

---

## 2. Branch and HEAD

| Field | Observed | Expected baseline | Match |
|---|---|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` | same | ✓ |
| Branch | `feature/nlp-semantic` | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` | ✓ |

No branch switch, no stage, no commit, no push, no reset.

---

## 3. Working-tree preservation results

Before this chunk the working tree had three pre-existing modified
files (`hybrid_dataset/metadata/sources.yaml`, `pyproject.toml`,
`requirements.txt`) and a known untracked set
(`PROJECT_HANDOFF.md`, arxiv files, review/, prior reports/,
tests/__init__.py). After this chunk:

- **Modified files:** same three, unchanged — verified by
  `git status --short`.
- **New untracked:** `src/nlp_semantic/intake/`,
  `tests/intake/`, plus this report file under `reports/`.
- **Pre-existing untracked (not touched):** `PROJECT_HANDOFF.md`,
  `hybrid_dataset/metadata/arxiv_governance_decisions.md`,
  `reports/*` (all prior chunk reports),
  `src/nlp_semantic/ingestion/arxiv_governance.py`,
  `src/nlp_semantic/ingestion/rate_limit.py`,
  `src/nlp_semantic/review/`, `tests/__init__.py`,
  `tests/ingestion/test_arxiv_governance.py`,
  `tests/ingestion/test_rate_limit.py`,
  `tests/ingestion/test_redis_rate_limit.py`, `tests/review/`,
  `tests/schema/__init__.py` — all byte-identical to pre-chunk.

Teammate directories (`src/ml/`, `src/recommender/`,
`src/backend/`) do not exist on this branch and were not created.

---

## 4. Files created

| Path | Purpose |
|---|---|
| `src/nlp_semantic/intake/__init__.py` | Public API re-exports. |
| `src/nlp_semantic/intake/pipeline.py` | Models (`IntakeEntry`, `AchievementCandidate`, `IntakeFinding`), enums (`IntakeStatus`, `IntakeValidationCode`), ID helpers, hashing, ingest, validate, list, duplicates. |
| `src/nlp_semantic/intake/cli.py` | `python -m nlp_semantic.intake.cli {ingest\|validate\|status\|duplicates}` subcommands. |
| `tests/intake/__init__.py` | Package marker. |
| `tests/intake/test_pipeline.py` | 39 tests covering the 20 required cases + 19 coverage extras. |
| `tests/intake/test_cli.py` | 8 CLI tests. |
| `reports/chunk_7_39_reviewer_gated_evidence_intake_pipeline.md` | This report. |

---

## 5. Files modified

**None.** Verified by `git status --short`: the only files in the
"modified" column remain the three pre-existing uncommitted ones.
No pre-existing file was touched.

Git: no `add`, no `commit`, no `push`, no `checkout`, no `reset`,
no `clean`, no `stash`.

---

## 6. Evidence storage design

The pipeline keeps two disjoint stores to make intake visibly
distinct from approved Evidence:

### 6.1 Repository-relative prefix constants

- `INTAKE_ROOT_PREFIX = "hybrid_dataset/raw/evidence_intake/"` —
  the new intake raw-file prefix (declared locally in
  `pipeline.py`). Falls under `hybrid_dataset/raw/*` which is
  already gitignored (per Chunk 1), so uploaded files never land
  in Git.
- `APPROVED_EVIDENCE_PREFIX = "hybrid_dataset/raw/evidence_documents/"`
  (pre-existing in `schema.path_safety`) — reserved for files
  referenced by approved `Evidence` records. **Not touched.**

The two prefixes do not overlap, so a reviewer or future auditor
can tell at a glance which store a file came from.

### 6.2 Default directories

Both are overridable per CLI invocation; the defaults are:

- `DEFAULT_EVIDENCE_ROOT = "hybrid_dataset/raw/evidence_intake"`
  — the on-disk raw-file store.
- `DEFAULT_MANIFEST_DIR = "hybrid_dataset/intake/manifests"` —
  the tracked YAML manifest directory. Lives outside `raw/` so
  manifests (which contain no PII — only pseudonyms, hashes, and
  the stored filename) can be committed when a reviewer chooses.

### 6.3 On-disk layout for one ingest

Given `evidence_root=<root>` and intake id `intk_<hex>`:

```
<root>/intk_<hex>/<original_filename>              # raw bytes
<manifest_dir>/intk_<hex>.yaml                     # metadata
```

Rationale:

- One directory per intake id prevents filename collisions
  across intakes.
- A per-intake YAML manifest (one file per intake) makes the
  manifest directory trivially mergeable in a reviewer PR
  (no multi-write-conflict).
- Both paths are computed from the intake id, which is a UUID4
  derivation — so there is never a predictable overwrite target.

### 6.4 File-type detection

Extension-based allowlist in `SUPPORTED_EXTENSIONS` (see §9).
Unknown extensions are **rejected** — the pipeline never
auto-coerces to `DocumentFileType.OTHER` without an explicit
`--file-type other` passed by the reviewer (reserved for the
very narrow case the reviewer identifies).

---

## 7. Intake manifest schema

### 7.1 `IntakeEntry` (Pydantic v2, `extra="forbid"`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `intake_id` | `str` | ✓ | `intk_<32-hex>`; local regex, not in `schema.identifiers._RECORD_PREFIXES` so intake stays visibly distinct from record ids |
| `original_filename` | `str` | ✓ | 1-255 chars; no path separators, no NUL, not `.` / `..` |
| `file_type` | `DocumentFileType` | ✓ | Reuses the existing enum from `schema.enums` |
| `relative_path` | `str` | ✓ | Must start with `INTAKE_ROOT_PREFIX`; validated by shared `reject_unsafe_relative_path` |
| `sha256` | `str` | ✓ | Exactly 64 lowercase hex |
| `size_bytes` | `int ≥ 0` | ✓ | File size at intake time |
| `intake_timestamp` | `datetime` | ✓ | Timezone-aware; naive datetimes rejected (same contract as `Annotation.created_at`) |
| `source_id` | `str \| None` | optional | If set, validated as `src_<32-hex>` |
| `achievement_candidate_ids` | `list[str]` | optional | Each is `cand_<32-hex>`; must be unique |
| `proposer` | `str \| None` | optional | Pseudonym; emails rejected (same contract as `Annotation.annotator`) |
| `status` | `IntakeStatus` | optional | Default `RECEIVED`; `VALIDATED` / `REJECTED` set by reviewer workflow |
| `validation_findings` | `list[IntakeFinding]` | optional | Codes from `IntakeValidationCode` |

### 7.2 `AchievementCandidate` (Pydantic v2, `extra="forbid"`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `candidate_id` | `str` | ✓ | `cand_<32-hex>` |
| `evidence_intake_ids` | `list[str]` | optional | Each must be `intk_<32-hex>` |
| `source_id` | `str \| None` | optional | `src_<32-hex>` |
| `extracted_text_inline` | `str \| None` | optional | ≤ 2000 chars (same cap as `Evidence.extracted_text_inline`) |
| `proposed_achievement_text` | `str \| None` | optional | ≤ 4000 chars |
| `proposed_primary_type` | `str \| None` | optional | `lbl_<snake>` if set |
| `proposer` | `str \| None` | optional | Pseudonym |
| `status` | `IntakeStatus` | optional | Default `RECEIVED` |
| `validation_findings` | `list[IntakeFinding]` | optional | — |

`AchievementCandidate` is **not** an `Achievement`:

- Different ID prefix (`cand_` vs. `ach_`).
- No `annotation_status` field.
- `proposed_primary_type` instead of `primary_type` — the name
  makes it clear this is a reviewer suggestion, not a labelled
  record.
- Lives in `nlp_semantic.intake`, not `nlp_semantic.schema` — the
  schema's Achievement model is untouched.

### 7.3 `IntakeStatus` enum

```
RECEIVED   = "received"    # initial state after ingest()
VALIDATED  = "validated"   # reviewer promoted (manually, by edit)
REJECTED   = "rejected"    # reviewer rejected (manually, by edit)
```

Disjoint from `AnnotationStatus`, `ReviewStatus`, `TaxonomyStatus`
by design — "VALIDATED intake" is NOT "verified annotation" or
"approved source".

### 7.4 Representative on-disk manifest

```yaml
intake_id: intk_1234567890abcdef1234567890abcdef
original_filename: certificate_scan.pdf
file_type: pdf
relative_path: hybrid_dataset/raw/evidence_intake/intk_12345.../certificate_scan.pdf
sha256: a1b2c3d4...                            # 64 hex chars
size_bytes: 123456
intake_timestamp: '2026-10-25T19:03:29.351737+00:00'
source_id: null
achievement_candidate_ids: []
proposer: labeler_001
status: received
validation_findings:
  - code: MISSING_SOURCE_ASSOCIATION
    message: no source_id supplied; a reviewer must link ...
    field: source_id
  - code: MISSING_ACHIEVEMENT_ASSOCIATION
    message: no achievement_candidate_ids supplied; ...
    field: achievement_candidate_ids
  - code: AUTHENTICATION_NOT_ESTABLISHED
    message: Intake records what a reviewer supplied; it does NOT ...
    field: null
```

The `AUTHENTICATION_NOT_ESTABLISHED` finding is **unconditional**
on every ingest, mirroring the Chunk 7.38B validator's
fail-closed limitation.

---

## 8. CLI commands

Shared contract with `nlp_semantic.dataset.cli` and
`nlp_semantic.review.cli`: JSON to stdout, concise summary with
ASCII `|` separators to stderr, exit codes `0` / `1` / `2`.

### 8.1 `ingest`

```
python -m nlp_semantic.intake.cli ingest <source_file>
  [--evidence-root <path>]
  [--manifest-dir <path>]
  [--source-id src_<hex>]
  [--candidate-id cand_<hex>]        # repeatable
  [--proposer labeler_<name>]
```

- Hashes the source file (SHA-256).
- Allocates `intk_<32-hex>` and copies the bytes to
  `<evidence_root>/<intake_id>/<filename>`.
- Writes `<manifest_dir>/<intake_id>.yaml`.
- Scans existing manifests for same-hash duplicates and records
  advisory findings.
- Exit 0 on success; 1 on missing file / unsupported type /
  Pydantic failure.

### 8.2 `validate`

```
python -m nlp_semantic.intake.cli validate <manifest_file>
  [--evidence-root <path>]
  [--sources-yaml <path>]
```

- Loads a manifest.
- Checks on-disk file existence under `<evidence_root>` and
  verifies SHA-256 integrity.
- If `--sources-yaml` is supplied, cross-checks `source_id`
  against the registered sources.
- Exit 0 if no fatal cross-reference finding; 1 otherwise.

### 8.3 `status`

```
python -m nlp_semantic.intake.cli status [--manifest-dir <path>]
```

- Lists every intake entry under the manifest directory.
- JSON output; exit 0.

### 8.4 `duplicates`

```
python -m nlp_semantic.intake.cli duplicates [--manifest-dir <path>]
```

- Groups entries by SHA-256; reports hashes with > 1 entry.
- JSON output; exit 0.

---

## 9. Validation rules

### 9.1 At ingest time

- Source file must exist and be a regular file.
- Filename must not contain `/` / `\` / NUL and must not be `.`
  / `..`.
- File extension must be in `SUPPORTED_EXTENSIONS` (unless
  `file_type` is passed explicitly in the API) — unknown
  extensions raise `ValueError`.
- Destination intake directory must not already exist.
- Destination manifest file must not already exist.

### 9.2 At schema level (Pydantic)

- `intake_id` must match `^intk_[0-9a-f]{32}$`.
- `relative_path` must start with `INTAKE_ROOT_PREFIX` and pass
  shared `reject_unsafe_relative_path` (no backslash, no `..`,
  no absolute paths, no empty segments).
- `sha256` must be exactly 64 lowercase hex chars.
- `intake_timestamp` must be timezone-aware (naive datetimes
  rejected).
- `source_id` must be `src_<32-hex>` if set.
- `achievement_candidate_ids` entries must each be
  `cand_<32-hex>` and distinct.
- `proposer` must be a non-email pseudonym.
- `status` must be one of `RECEIVED` / `VALIDATED` / `REJECTED`.
- `extra="forbid"` on every model — typos become errors.

### 9.3 At `validate_intake_entry` time (cross-reference)

- On-disk file existence check (surface `FILE_NOT_FOUND`).
- On-disk SHA-256 vs. manifest SHA-256 (surface
  `HASH_MISMATCH_ON_DISK` for tampering).
- `source_id` membership in `sources.yaml` when path supplied
  (surface `UNKNOWN_SOURCE_REFERENCE`).
- `achievement_candidate_ids` membership in a supplied set
  (surface `UNKNOWN_ACHIEVEMENT_REFERENCE`).

### 9.4 Error-code taxonomy

```
MISSING_REQUIRED_FIELD
UNSUPPORTED_FILE_TYPE
FILE_NOT_FOUND
EMPTY_FILE
UNSAFE_FILENAME
UNSAFE_RELATIVE_PATH
DUPLICATE_HASH
FILENAME_COLLISION_DIFFERENT_HASH
HASH_MISMATCH_ON_DISK
UNKNOWN_SOURCE_REFERENCE
UNKNOWN_ACHIEVEMENT_REFERENCE
INVALID_INTAKE_ID
INVALID_CANDIDATE_ID
INVALID_SOURCE_ID
MISSING_SOURCE_ASSOCIATION
MISSING_ACHIEVEMENT_ASSOCIATION
AUTHENTICATION_NOT_ESTABLISHED
```

---

## 10. Test results

### 10.1 Focused run

```
.\.venv\Scripts\python.exe -m pytest tests/intake -q
→ 47 passed in 3.16s (exit 0)
```

### 10.2 Full suite regression check

```
.\.venv\Scripts\python.exe -m pytest -q
→ 667 passed, 5 skipped in 47.61s (exit 0)
```

Pre-chunk baseline: `620 passed, 5 skipped`. Delta: exactly
`+47 passed` matching the new intake tests. Zero regression on
pre-existing tests. The five skips are the same as before (four
Windows-symlink; one `fakeredis-not-installed`).

### 10.3 Required-case coverage

Each of the 20 brief §5 cases is covered. Mapping to specific
test functions:

| Brief case | Test |
|---|---|
| 1 Successful intake | `test_01_successful_intake` |
| 2 Missing file | `test_02_missing_evidence_file` |
| 3 Unsupported file type | `test_03_unsupported_file_type` + `_03b` |
| 4 Duplicate content | `test_04_duplicate_content_flagged` |
| 5 Hash stability | `test_05_hash_stability` |
| 6 Existing evidence preservation | `test_06_existing_evidence_preservation` |
| 7 Manifest validation | `test_07_manifest_round_trip` + `_07b` |
| 8 Invalid source reference | `test_08_invalid_source_reference_rejected_at_pydantic_layer` + `_08b_unknown_source_reference_cross_check` |
| 9 Invalid achievement reference | `test_09_invalid_achievement_reference` + `_09b_unknown_candidate_cross_check` |
| 10 Missing source/achievement association | `test_10_missing_source_and_achievement_associations_flagged` |
| 11 Invalid intake status | `test_11_invalid_intake_status` |
| 12 Path traversal attempts | `test_12_*` × 4 (traversal, backslash, absolute, path-separator-in-filename) |
| 13 Filename collisions | `test_13_filename_collisions_get_distinct_intake_ids` |
| 14 Empty file | `test_14_empty_file_flagged` |
| 15 Original bytes preserved | `test_15_original_bytes_preserved` |
| 16 No auto reviewer approval | `test_16_status_starts_received_never_auto_validated` |
| 17 No source-review status changes | `test_17_pipeline_does_not_touch_source_statuses` (AST-based) |
| 18 No annotation verification changes | `test_18_pipeline_does_not_touch_annotation_statuses` (AST-based) |
| 19 No taxonomy status changes | `test_19_pipeline_does_not_touch_taxonomy_status` (AST-based) |
| 20 No training-readiness changes | `test_20_pipeline_does_not_touch_training_readiness` (AST-based) |

Tests 17-20 use the AST-strip-docstring approach proven in Chunk
7.38B: they parse the module source, strip docstrings, and
inspect every `Name` / `Attribute` / `ImportFrom` / `Import`
node. This way the module docstring can legitimately mention
what it does NOT do (fail-closed contract) while still catching
accidental imports or calls.

### 10.4 Environmental limitations

- `fakeredis` skip persists (dep not installed in the venv per
  "no deps without authorization"); this chunk did not change
  that.
- Windows-symlink skips persist; this chunk did not touch
  developer-mode or symlink behaviour.

### 10.5 Test refinement during this chunk

Test 06 initially failed because its fixture helper wrote both
source files to the same path (reviewer_inbox/x.pdf), silently
overwriting the first file before ingest ran. Fixed by placing
each source in a distinct inbox subdirectory. The pipeline
behaviour was always correct; only the test fixture was wrong.
After the fix, 47/47 intake tests pass.

---

## 11. Dataset before/after comparison

Baseline recorded per brief §7:

| Measure | Before | After | Changed? |
|---|---:|---:|---|
| Achievement record count | 7 | 7 | no |
| `is_synthetic: true` count | 0 | 0 | no |
| Fatal validation findings | 0 | 0 | no |
| Advisory validation findings | 9 | 9 | no |
| Duplicate groups | 0 | 0 | no |
| Approved primary labels | 0 | 0 | no |
| Approved domain tags | 0 | 0 | no |
| Training-eligible primary_type records | 0 | 0 | no |
| Training-eligible domain_tags records | 0 | 0 | no |
| Registered sources | 2 (1 committed + 1 uncommitted) | 2 (same) | no |
| Taxonomy status of 14 primary + 10 domain labels | all `draft` | all `draft` | no |
| Annotation status of 7 records | all `primary_type: draft`, `domain_tags: not_started` | identical | no |

`cli readiness` output verbatim before AND after this chunk:

```
dataset: readiness | any_task=not_ready | all_tasks=not_ready |
approved(pt=0,dt=0) | eligible(pt=0,dt=0) | blockers=4 |
strict=off
```

No field of `batch_01_sih2024.yaml`, `sources.yaml`,
`primary_taxonomy.yaml`, `domain_tags.yaml`, or
`manifest.yaml` was modified by this chunk. No new batch created.

---

## 12. Remaining review blockers (unchanged)

The project's critical path to training-readiness remains the
Chunk 7.36 §13.1 list:

1. **PIB-policy applicability decision** — pending Chunk 7.26A
   two-reviewer sign-off packet.
2. **`lbl_hackathon` taxonomy promotion** — Chunk 7.37 packet
   ready; awaiting reviewer-driven promotion PR with two
   independent sign-offs.
3. **Per-record annotation review** for the seven SIH records.
4. **PIB source `license` field populated** with the verbatim
   policy clause.

**This chunk does not resolve any of them.** It is infrastructure
that lowers the friction of a different workflow (reviewer
hand-off of new evidence files), not a shortcut for the
reviewer-gated promotions above.

---

## 13. Limitations

### 13.1 By design (fail-closed, documented)

- Intake does **not** authenticate reviewer identity. Every
  manifest carries `AUTHENTICATION_NOT_ESTABLISHED` as a
  finding, and `IntakeStatus.VALIDATED` means "structural checks
  passed" not "reviewer verified".
- Intake does **not** approve sources. A `source_id` link is a
  pointer; it is not a license approval.
- Intake does **not** verify annotations. An
  `AchievementCandidate` is not an `Achievement`.
- Intake does **not** promote taxonomy. No field of
  `primary_taxonomy.yaml` is touched.
- Intake does **not** fetch external URLs. The `source_file`
  argument must be a local path handed over by a reviewer.
- Intake does **not** run OCR, embeddings, LLM extraction, or
  automatic duplicate detection beyond exact-hash comparison.

### 13.2 Scope deferred

- `AchievementCandidate` has `extracted_text_inline` and
  `proposed_achievement_text` fields but **no automated
  extractor** writes them. A reviewer must supply the text
  manually. OCR / PyMuPDF integration remains deferred until
  dependency approval (PROJECT_HANDOFF.md §9).
- `find_duplicate_hashes` returns exact-content duplicates only.
  Semantic / near-duplicate detection is a separate chunk
  candidate (Chunk 7.35 §O.3 Alt 1 / "Chunk 7.38C" in Chunk 7.38B
  §16.1).
- Source-review evidence bundles (brief §4.C) remain
  unmodelled; the Chunk 7.38B validator only covers taxonomy
  promotion and annotation review. A `BundleType.SOURCE_REVIEW`
  extension of that validator is a future chunk, not this one.

### 13.3 What the pipeline can and cannot accept today

- **Can accept today:** a local `.pdf` / `.jpg` / `.jpeg` /
  `.png` / `.tif` / `.tiff` / `.txt` / `.md` / `.html` / `.htm`
  / `.json` / `.yaml` / `.yml` file supplied by a reviewer.
  Hashes it, stores it under `<evidence_root>/<intake_id>/`,
  writes a tracked manifest. Reports duplicates, missing
  associations, authentication-not-established.
- **Cannot accept today:** any file whose extension is not in
  the allowlist (without an explicit `--file-type` override — a
  CLI flag the current CLI does not yet expose; adding it is a
  one-line follow-up if `other` becomes necessary). Also:
  cannot authenticate the reviewer, cannot verify the file's
  content against claims, cannot label a candidate as
  `lbl_hackathon` without reviewer input.

---

## 14. Recommended next action

Per the brief §9's three-category distinction:

### 14.1 Human reviewer action for `lbl_hackathon` promotion

The Chunk 7.37 packet is still the right starting point. A human
reviewer opens the promotion PR against the current
`primary_taxonomy.yaml`, cites the Chunk 7.37 packet, two
reviewers post independent sign-off comments using the
TAXONOMY_APPROVAL_CHECKLIST §110-131 template. Those sign-offs
can optionally be captured as a Chunk 7.38B evidence bundle,
which the Chunk 7.38B validator will self-check structurally.

### 14.2 Technical work that can continue without reviewer approval

Candidates:

1. **Chunk 7.40 — First real-evidence intake exercise.** Hand a
   genuine piece of evidence (e.g. a copy of the Chunk 7.3-A.4
   reviewer screenshot of PIB PRID 2085000) through the intake
   pipeline to confirm the end-to-end path works on a real
   artefact — not a synthetic fixture. The screenshot itself
   lives outside the intake pipeline today; running it through
   intake produces the first `IntakeEntry` on disk and gives the
   reviewer a stable `intake_id` to link to the eventual
   Evidence row.
2. **Chunk 7.41 — Candidate-to-Achievement reviewer workflow.**
   Design the explicit reviewer-driven transition from
   `AchievementCandidate` (intake-side) to `Achievement`
   (dataset-side). Likely small schema addition to express the
   link + a reviewer-driven CLI subcommand that writes a new
   batch file.
3. **Chunk 7.38C — Semantic duplicate design.** Still valid from
   Chunk 7.35 §O.3 / Chunk 7.38B §16.1.

### 14.3 Genuine source-evidence collection for dataset expansion

Reviewer-driven. The highest-leverage next sources remain:

- **PRID 2082460 content determination** (Chunk 7.34 §M) —
  requires a reviewer screenshot + "no new / partial new / full
  new content" determination.
- **GSoC year-by-year archive capture** (Chunk 7.35 §O.2) —
  requires reviewer screenshots of the archive index + per-year
  page + eligibility page.

With the Chunk 7.39 intake pipeline in place, both of those
reviewer actions can now produce stable intake entries pointing
at the captured screenshot files — which is a concrete step
forward from the "evidence lives in prose on PR comments"
situation Chunk 7.36 §9.2 flagged.

### 14.4 Explicitly not recommended as the next chunk

- Another AI-driven "verify external source X" chunk of the
  same shape as 7.34 / 7.35. The governance block remains
  structural.
- Automated extraction from intake files (OCR, LLM) without
  reviewer approval and without dependency approval.
- Any modification to `training_ready_subset` or its callers to
  make unreviewed intake entries training-eligible. The
  eligibility gate is the project's guarantee that no record is
  training-fed without governance; loosening it bypasses the
  guarantee rather than earning past it.

The brief's final sentence — "The next project objective after
this chunk is to use the intake pipeline for genuine evidence
collection and candidate preparation, not to continue building
review paperwork indefinitely" — makes §14.3 the natural next
focus.
