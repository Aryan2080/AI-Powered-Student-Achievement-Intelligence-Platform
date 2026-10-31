# Chunk 7.46 — Reviewer-Gated Evidence Promotion

**Generated:** 2026-10-25
**Chunk type:** implementation (new module + CLI subcommand + tests + storage).
**Final disposition:** `EVIDENCE PROMOTION IMPLEMENTED`

> Scope: materialise the Chunk 7.44 §2.3 design for the
> reviewer-driven `IntakeEntry → Evidence` promotion step. Ships
> `src/nlp_semantic/intake/promote_evidence.py`, the
> `promote-evidence` CLI subcommand, the
> `hybrid_dataset/dataset/evidence/` storage directory, and 21
> tests covering the 17 required cases from the brief §Phase 5
> plus 4 coverage extras. All 719 repo tests pass (+21 vs. Chunk
> 7.45). The dataset is byte-identical: no production
> `IntakeEntry` was promoted (none exists yet — this is the same
> reviewer-driven blocker that Chunks 7.40 / 7.42 / 7.43
> documented), but the implementation is fully exercised against
> synthetic `tmp_path` fixtures.

---

## 1. Branch and HEAD

| Field | Observed | Match |
|---|---|---|
| Branch | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` | ✓ |
| Pre-existing modified files | `.gitignore`, `hybrid_dataset/metadata/sources.yaml`, `pyproject.toml`, `requirements.txt` — all unchanged by this chunk | ✓ |

No git stage / commit / push / branch-switch. Teammate
directories (`src/ml/`, `src/recommender/`, `src/backend/`)
remain absent.

### 1.1 Intake-discovery result (brief §Phase 1)

`Glob hybrid_dataset/raw/evidence_intake/**/*` → 0 files.
`Glob hybrid_dataset/intake/manifests/*.yaml` → 0 files.

**No genuine intake entry exists in production.** This confirms
the Chunk 7.40 / 7.42 / 7.43 reviewer-blocker is unchanged: the
PIB SIH 2024 screenshot capture step has not been executed. Per
the brief §Phase 1, the chunk does not fabricate an intake id,
hash, or placeholder; the implementation targets this same
reviewer workflow and will be callable the moment a real intake
lands.

The implementation ships regardless, exercised through synthetic
`tmp_path` fixtures (same pattern as Chunks 7.39 and 7.45).

---

## 2. Existing schema findings

Audited (read-only) before implementation:

- `nlp_semantic.schema.evidence.Evidence` — required `evidence_id`
  (`evd_<32-hex>`), `relative_path` (must start with
  `APPROVED_EVIDENCE_PREFIX = "hybrid_dataset/raw/evidence_documents/"`
  and pass the shared `reject_unsafe_relative_path`), `file_type`
  (`DocumentFileType` enum). Optional: `linked_achievement_id`,
  `original_filename`, `document_type`, `extraction_method`
  (default `NONE_YET`), `extracted_text_ref` /
  `extracted_text_inline` (mutually exclusive), `ocr_confidence`
  (only if `extraction_method` is OCR), `review_status` (default
  `UNREVIEWED`), `is_synthetic` (default `False`).
- `nlp_semantic.schema.path_safety.APPROVED_EVIDENCE_PREFIX`
  reused unchanged.
- `nlp_semantic.schema.path_safety.reject_unsafe_relative_path`
  reused unchanged.
- `nlp_semantic.schema.identifiers.make_id("evd")` — produces a
  valid `evd_<32-hex>` id.
- `nlp_semantic.schema.enums.ReviewStatus`,
  `nlp_semantic.schema.enums.ExtractionMethod` reused.
- `nlp_semantic.intake.pipeline.IntakeEntry` — supplies
  `intake_id`, `original_filename`, `file_type`, `relative_path`
  (starts with `INTAKE_ROOT_PREFIX`), `sha256`, `size_bytes`,
  `proposer`.
- `nlp_semantic.intake.pipeline.INTAKE_ROOT_PREFIX` reused for
  file resolution.
- `nlp_semantic.intake.pipeline.sha256_of_file` reused.

**No schema change required.** The promotion bridges the Chunk
7.39 intake pipeline to the Chunk 2 `Evidence` model with
reviewer-driven logic, no schema invariants weakened.

---

## 3. Implemented interface

### 3.1 Module `src/nlp_semantic/intake/promote_evidence.py`

Public API (all re-exported from `nlp_semantic.intake`):

- **Constants:**
  - `DEFAULT_EVIDENCE_DOCUMENTS_ROOT = "hybrid_dataset/raw/evidence_documents"`
  - `DEFAULT_EVIDENCE_RECORD_DIR = "hybrid_dataset/dataset/evidence"`
- **Error codes (`PromoteEvidenceErrorCode` string constants):**
  `MISSING_ORIGINAL_FILE`, `HASH_MISMATCH_ON_DISK`,
  `EVIDENCE_FILE_ALREADY_EXISTS`,
  `EVIDENCE_RECORD_ALREADY_EXISTS`,
  `DUPLICATE_EVIDENCE_HASH`, `REVIEWER_IS_PROPOSER`,
  `INVALID_DESTINATION_PATH`, `INVALID_REVIEWER`,
  `EVIDENCE_RECORD_INVALID`, `EVIDENCE_ROOT_NOT_FOUND`.
- **Models / dataclasses:**
  - `PromoteEvidenceFinding(code, message, field)` — one
    precondition finding.
  - `PromoteEvidenceResult(evidence, source_intake_id,
    source_file_path, destination_file_path,
    evidence_record_path, duplicate_of_evidence_ids)` — return
    value of a successful promotion.
- **Exceptions:**
  - `PromoteEvidenceError(ValueError)` — raised on precondition
    failure; carries `findings: list[PromoteEvidenceFinding]`.
- **Functions:**
  - `promote_evidence(intake, *, reviewer, evidence_root,
    evidence_documents_root, evidence_record_dir, document_type,
    existing_evidence)` — the workflow entry point.
  - `load_evidence_record(path)` — load one Evidence YAML.
  - `list_evidence_records(evidence_record_dir)` — iterate the
    directory.

### 3.2 Package exports

`src/nlp_semantic/intake/__init__.py` extended to re-export all
nine new symbols above.

### 3.3 CLI subcommand

Added `promote-evidence` to `nlp_semantic.intake.cli`:

```
python -m nlp_semantic.intake.cli promote-evidence <intake_manifest> \
    --reviewer labeler_<name> \
    [--evidence-root <path>] \
    [--evidence-documents-root <path>] \
    [--evidence-record-dir <path>] \
    [--document-type <text>]
```

Follows the existing CLI conventions:

- stdout: JSON report with `ok`, `evidence_id`, paths, and
  `review_status`.
- stderr: concise `promote-evidence ok | ...` or
  `promote-evidence fatal | findings=<n>` summary.
- Exit codes: `0` on success, `1` on precondition failure or
  load error, `2` on argparse usage error.
- Pre-existing subcommand handlers untouched.

---

## 4. Reviewer requirements

Documented in `hybrid_dataset/dataset/evidence/README.md`:

1. The reviewer must be a pseudonym distinct from
   `intake.proposer` (reviewer independence).
2. The intake original file must exist on disk and its SHA-256
   must match the manifest (file integrity).
3. The destination filename must produce a safe repository-
   relative path under `APPROVED_EVIDENCE_PREFIX`.
4. No existing Evidence row's on-disk file may share the
   intake's SHA-256 (deterministic duplicate guard).

The reviewer cannot:

- Mark the Evidence row verified (default is
  `review_status: unreviewed`).
- Approve the source cited by the intake.
- Promote a taxonomy label.
- Create an Achievement, Annotation, or Candidate.

---

## 5. Validation rules

Verified by the 17 required test cases + 4 extras:

| # | Precondition | Finding code | Test |
|---|---|---|---|
| 1 | Reviewer pseudonym valid (non-email, `^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$`) | `INVALID_REVIEWER` | `test_06_invalid_reviewer_attestation` |
| 2 | Reviewer ≠ intake.proposer | `REVIEWER_IS_PROPOSER` | `test_07_reviewer_independence_failure` |
| 3 | Intake file exists on disk at the path encoded by `intake.relative_path` | `MISSING_ORIGINAL_FILE` | `test_04_missing_original_file` |
| 4 | On-disk SHA-256 matches `intake.sha256` | `HASH_MISMATCH_ON_DISK` | `test_05_hash_mismatch` |
| 5 | Destination filename yields a repository-relative path starting with `APPROVED_EVIDENCE_PREFIX` and passing `reject_unsafe_relative_path` | `INVALID_DESTINATION_PATH` | `test_08_invalid_destination_path` |
| 6 | Destination file does not already exist | `EVIDENCE_FILE_ALREADY_EXISTS` | `test_10_destination_file_already_exists` |
| 7 | No existing Evidence row shares the intake's SHA-256 | `DUPLICATE_EVIDENCE_HASH` or `EVIDENCE_FILE_ALREADY_EXISTS` | `test_09_duplicate_evidence_refused` |
| 8 | Hypothetical Evidence row is Pydantic-valid | `EVIDENCE_RECORD_INVALID` | Covered by `test_01_valid_promotion` (success) and the schema's own validators |

All eight run **before** any file is written to disk. On failure
the function raises `PromoteEvidenceError` with the finding list;
the filesystem is unchanged.

---

## 6. CLI behavior

Covered by the two synthetic-fixture test flows:

- `test_01_valid_promotion` exercises the Python API including
  the exact fields the CLI would surface (`evidence_id`,
  `destination_file_path`, `evidence_record_path`,
  `review_status`).
- The CLI handler `_cmd_promote_evidence` reuses the same
  function and the same error path; the brief did not require a
  dedicated CLI test, so none was added (brief §Phase 5 did not
  list CLI-specific cases, and the brief §Phase 5 says "Use
  actual project test conventions"; adding CLI tests to match
  Chunk 7.45 style was considered but kept narrow to the
  required cases).

Exit-code contract:

- `0` — Evidence row written, file copied, result on stdout.
- `1` — intake load failure, precondition failure, or Pydantic
  validation failure. JSON `ok: false` + `findings` to stdout;
  concise `promote-evidence fatal` to stderr.
- `2` — argparse usage error (missing `--reviewer`, bad
  `intake_manifest` positional).

---

## 7. Storage behavior

### 7.1 Layout

```
hybrid_dataset/
├── raw/
│   ├── evidence_intake/<intake_id>/<name>       (Chunk 7.39; gitignored)
│   └── evidence_documents/<intake_id>__<name>   (NEW — gitignored, from APPROVED_EVIDENCE_PREFIX)
└── dataset/
    ├── evidence/                                 (NEW this chunk)
    │   ├── .gitkeep                             (TRACKED)
    │   ├── README.md                            (TRACKED)
    │   └── evd_<32-hex>.yaml                    (produced by promote-evidence)
    └── ...
```

### 7.2 File-write order (fail-closed, no partial writes on precondition fail)

1. All eight preconditions evaluated.
2. If any fails → raise `PromoteEvidenceError`; filesystem
   unchanged.
3. Write the Evidence YAML to
   `<evidence_record_dir>/<evd_id>.yaml`.
4. Copy the intake bytes to
   `<evidence_documents_root>/<intake_id>__<original_filename>`.

Order rationale: writing the record first means a mid-crash can
leave an orphan record pointing at a non-existent file (easy to
detect via a future validator), rather than an orphan file with
no index (hard to notice). For true atomicity the owner could
layer a tmp-file + rename pattern on top later; the current
implementation satisfies "avoid partial writes on precondition
failure" (brief §Phase 2 requirement 13) because the writes only
begin after all validations pass.

### 7.3 Original intake preserved

The intake original at
`hybrid_dataset/raw/evidence_intake/<intk_id>/<name>` is **copied**
(not moved). Verified by `test_01_valid_promotion` and
`test_13_existing_record_preservation` which both read the
intake original bytes after promotion. The brief §Phase 2
requirement 14 is satisfied.

### 7.4 Duplicate detection

`_duplicate_hashes_in` iterates every existing `Evidence` row's
on-disk file under `evidence_documents_root`, recomputes SHA-256,
and compares against the intake's `sha256`. Matches trigger
`DUPLICATE_EVIDENCE_HASH`. The destination collision check also
catches the same-intake-twice case via
`EVIDENCE_FILE_ALREADY_EXISTS` (filename includes `<intake_id>__`
so the same intake maps to the same destination).

The strict hash recomputation is O(N × file-size); acceptable at
the project's current corpus size (0 Evidence rows today;
dozens expected after reviewer activity).

---

## 8. Tests actually executed

### 8.1 Focused promotion tests

```
.\.venv\Scripts\python.exe -m pytest tests/intake/test_promote_evidence.py -v
→ 21 passed in 1.43s
```

### 8.2 Mapping to the brief §Phase 5 required cases

| # Brief case | Test name | Pass |
|---|---|---|
| 1 Valid promotion | `test_01_valid_promotion` | ✓ |
| 2 Missing intake | `test_02_missing_intake` | ✓ |
| 3 Invalid intake | `test_03_invalid_intake` | ✓ |
| 4 Missing original file | `test_04_missing_original_file` | ✓ |
| 5 Hash mismatch | `test_05_hash_mismatch` | ✓ |
| 6 Invalid reviewer attestation | `test_06_invalid_reviewer_attestation` | ✓ |
| 7 Reviewer-independence failure | `test_07_reviewer_independence_failure` | ✓ |
| 8 Invalid destination path | `test_08_invalid_destination_path` | ✓ |
| 9 Duplicate evidence | `test_09_duplicate_evidence_refused` | ✓ |
| 10 Invalid proposed dataset (destination collision) | `test_10_destination_file_already_exists` | ✓ |
| 11 Persistence failure | `test_11_persistence_failure_no_record_without_file` | ✓ |
| 12 No partial writes | `test_12_no_partial_writes_on_precondition_failure` | ✓ |
| 13 Existing record preservation | `test_13_existing_record_preservation` | ✓ |
| 14 Default unreviewed status | `test_14_default_unreviewed_status` | ✓ |
| 15 Source status preservation | `test_15_source_status_preservation` (AST) | ✓ |
| 16 No Achievement creation | `test_16_no_achievement_creation` (AST) | ✓ |
| 17 No training-readiness mutation | `test_17_no_training_readiness_mutation` (AST) | ✓ |

Four extras: `test_promote_evidence_result_has_expected_shape`,
`test_list_evidence_records_returns_promoted`,
`test_document_type_is_captured`,
`test_promote_evidence_bytes_identical`.

### 8.3 Full repository suite

```
.\.venv\Scripts\python.exe -m pytest -q
→ 719 passed, 5 skipped in 28.96s (exit 0)
```

Pre-chunk baseline (Chunk 7.45 end): `698 passed, 5 skipped`.
Delta: **+21 passed** = exactly the new promotion tests. **Zero
regression** on any pre-existing test. The five skips are the
same four Windows-symlink + one fakeredis skips as every chunk
since 7.32.

---

## 9. Exact pass / fail counts

| Scope | Pass | Fail | Skip |
|---|---:|---:|---:|
| `tests/intake/test_promote_evidence.py` (new) | 21 | 0 | 0 |
| Full repo | 719 | 0 | 5 |

---

## 10. Files created and modified

### 10.1 Created in Chunk 7.46

| Path | Purpose |
|---|---|
| `src/nlp_semantic/intake/promote_evidence.py` | Promotion workflow, error codes, models, loader helpers. |
| `tests/intake/test_promote_evidence.py` | 21 tests covering 17 brief-required cases + 4 extras. |
| `hybrid_dataset/dataset/evidence/.gitkeep` | Structural marker. |
| `hybrid_dataset/dataset/evidence/README.md` | Storage layout and reviewer policy. |
| `reports/chunk_7_46_evidence_promotion_implementation.md` | This report. |

### 10.2 Modified in Chunk 7.46

| Path | Change |
|---|---|
| `src/nlp_semantic/intake/__init__.py` | Added 9 new re-exports. Zero removals. |
| `src/nlp_semantic/intake/cli.py` | Added one subcommand (`promote-evidence`) + handler. Zero changes to pre-existing handlers or exits. |

### 10.3 Not touched

- `src/nlp_semantic/schema/` — every file byte-identical.
- `src/nlp_semantic/dataset/` — byte-identical.
- `src/nlp_semantic/ingestion/` — byte-identical.
- `src/nlp_semantic/review/` (Chunk 7.38B) — byte-identical.
- `src/nlp_semantic/intake/pipeline.py` — byte-identical.
- `src/nlp_semantic/intake/review.py` (Chunk 7.45) — byte-identical.
- `hybrid_dataset/metadata/sources.yaml` — pre-existing modified,
  unchanged by this chunk.
- `hybrid_dataset/labels/primary_taxonomy.yaml`,
  `.../domain_tags.yaml` — byte-identical.
- `hybrid_dataset/dataset/records/batch_01_sih2024.yaml` —
  byte-identical.
- `.gitignore` — pre-existing modified (from Chunk 7.41),
  byte-identical.
- `pyproject.toml`, `requirements.txt` — pre-existing modified,
  byte-identical. **No new runtime dependency.**
- `reviews/` (Chunk 7.41) — byte-identical.
- Teammate directories — do not exist, not created.

Git: no `add`, no `commit`, no `push`, no `checkout`, no
`reset`, no `clean`, no `stash`, no branch switch.

---

## 11. Evidence counts before and after

| Measure | Before | After |
|---|---:|---:|
| `Evidence` rows in `hybrid_dataset/dataset/evidence/` | 0 | 0 (tests write to `tmp_path`) |
| Files in `hybrid_dataset/raw/evidence_documents/` | 0 | 0 |
| Files in `hybrid_dataset/raw/evidence_intake/` | 0 | 0 |
| Intake manifests in `hybrid_dataset/intake/manifests/` | 0 | 0 |

The `hybrid_dataset/dataset/evidence/` directory was created
with `.gitkeep` + README, but contains no actual `Evidence`
record — those are produced only by real reviewer invocations
against real intake entries, neither of which happened in this
chunk.

---

## 12. Dataset counts before and after

| Measure | Before | After |
|---|---:|---:|
| Achievement record count | 7 | 7 |
| Record hashes | all unchanged | all unchanged |
| Source count (committed + uncommitted) | 1 + 1 | 1 + 1 |
| Source review statuses | both `unreviewed` | both `unreviewed` |
| Primary-taxonomy label statuses (14) | all `draft` | all `draft` |
| Domain-tag label statuses (10) | all `draft` | all `draft` |
| Annotation statuses on 7 records | `primary_type: draft`, `domain_tags: not_started` | unchanged |
| `AchievementCandidate` records | 0 | 0 |
| `CandidateReview` records | 0 | 0 |
| `Evidence` records | 0 | 0 |

No field of `batch_01_sih2024.yaml`, `sources.yaml`,
`manifest.yaml`, `primary_taxonomy.yaml`, or `domain_tags.yaml`
was modified. Brief §Phase 5 case 15 ("source status
preservation") verified at the AST level.

---

## 13. Training-readiness before and after

Byte-identical:

```
dataset: readiness | any_task=not_ready | all_tasks=not_ready |
approved(pt=0,dt=0) | eligible(pt=0,dt=0) | blockers=4 | strict=off
```

AST test 17 (`test_17_no_training_readiness_mutation`) enforces
that `promote_evidence.py` does not import `training_ready_subset`
or `eligible_ground_truth`.

---

## 14. Blockers

### 14.1 Chunk-level blockers

**None.** All 17 required test cases pass. All brief §Phase 2
functional requirements (1-14) are implemented. The CLI
integrates. Storage directory is in place with README.

### 14.2 Project-level blockers (unchanged by this chunk)

The three standing training-readiness blockers from Chunk 7.36
§13.1 remain:

1. PIB-policy applicability decision (Chunk 7.26A packet).
2. `lbl_hackathon` taxonomy promotion (Chunk 7.37 packet).
3. Per-record annotation review for the seven SIH records.

Plus, specific to the real-evidence intake exercise:

4. Reviewer screenshot capture of PIB SIH 2024
   (`reviews/README.md` §6 workflow — unexecuted after Chunks
   7.40 / 7.42 / 7.43 attempts).

Chunk 7.46 does not resolve any of these. It materialises the
tool that Chunk 7.47-candidate / future reviewer sessions will
use once (4) completes.

### 14.3 Known limitations documented in the module

- Duplicate detection re-hashes every existing Evidence file on
  disk — O(N × file-size). Fine for the project's expected
  corpus size (dozens, not millions).
- Partial-write resilience is "preconditions before writes," not
  full transaction atomicity. A mid-crash between step 3 (write
  record) and step 4 (copy file) leaves an orphan record. The
  trade-off was chosen deliberately (orphan record is easier to
  detect than orphan file); a future chunk could layer tmp-file +
  rename atomicity if the owner decides it's needed.

---

## 15. Final disposition

**`EVIDENCE PROMOTION IMPLEMENTED`.**

Rationale:

- All brief §Phase 2 functional requirements (1-14) are
  implemented in `promote_evidence.py`.
- All 17 brief §Phase 5 required test cases pass (plus 4
  extras).
- The CLI integrates with the existing `nlp_semantic.intake.cli`
  argparse pattern.
- The storage directory `hybrid_dataset/dataset/evidence/` is
  created with `.gitkeep` + README documenting policy and
  workflow.
- Full repo suite passes without regression.

Alternatives considered and rejected:

- `EVIDENCE PROMOTION IMPLEMENTED WITH BLOCKERS` — would be
  correct if a specific implementation defect prevented part of
  the brief's scope. All brief §Phase 2 items 1-14 are complete.
- `IMPLEMENTATION BLOCKED BY SCHEMA` — would be correct if a
  schema change were required. None was: all four Chunk 7.44
  §1.7 gaps + the Chunk 2 Evidence model combined bridge the
  intake-to-Evidence path cleanly.
- `REPOSITORY PRECONDITION MISMATCH` — not applicable (§1).
- `REVIEWER EVIDENCE ARTIFACT NOT AVAILABLE` — the brief
  provides this disposition for the case where the chunk's
  purpose is to run promotion against actual intake and no
  intake exists. This chunk's purpose is to **implement** the
  promotion workflow (verified against synthetic fixtures). The
  absence of production intake is noted in §1.1 and documented
  as a reviewer-driven blocker, but it does not block the
  implementation itself.

---

## 16. Recommended next step

Narrowest useful implementation chunks, in priority order:

### Chunk 7.47 — Candidate-to-Achievement conversion (unchanged recommendation)

Materialise an ACCEPT-ed `CandidateReview` (Chunk 7.45) into a
real `Achievement` row written to a new
`batch_<NN>_<slug>.yaml`. This is still the first chunk that
would **produce a new dataset record** since Chunk 7.3-A. It
can reuse:

- The `CandidateReview.attested_*` fields (Chunk 7.45) as the
  source of Achievement field values.
- The `Evidence.evidence_id` produced by this chunk's
  `promote_evidence` as the Achievement's `evidence_id`.
- The Chunk 7.4-A.1 Draft default for
  `annotation_status.primary_type` (same as
  `batch_01_sih2024.yaml`).

### Chunk 7.48 (if needed) — REVISE / DEFER on CandidateReview

Only if reviewers find straight ACCEPT/REJECT doesn't give
enough flexibility.

### Chunk 7.49 (if needed) — Evidence batch loader + validator integration

Current `_duplicate_hashes_in` reads individual `evd_*.yaml`
files via `list_evidence_records`. If the Evidence corpus grows
large enough to make per-promotion re-hashing expensive, a
future chunk could add a cached hash index.

### Explicitly not recommended for the next chunk

- Another real-evidence intake attempt (Chunks 7.40 / 7.42 /
  7.43 all landed at `REVIEWER EVIDENCE ARTIFACT NOT AVAILABLE`
  for the same reviewer-driven reason).
- Modifying `training_ready_subset` or any eligibility
  condition.
- Adding OCR / sentence-transformer / embedding dependencies.
- Modifying the Chunk 7.39 intake pipeline or the Chunk 7.45
  review workflow — neither needed changes for this chunk, and
  neither should be touched speculatively.
- Any work in `src/ml/`, `src/recommender/`, or `src/backend/`.

Chunk 7.46 completes the second of the two deferred steps from
Chunk 7.44 §12 (CandidateReview was first in Chunk 7.45). Both
reviewer-driven workflows are now implementable from code:
accept a candidate, promote evidence. Chunk 7.47 will stitch
them together into the first new Achievement record of the
post-pilot dataset.
