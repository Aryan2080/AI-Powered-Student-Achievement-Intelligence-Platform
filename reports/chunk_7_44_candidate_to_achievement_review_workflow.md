# Chunk 7.44 — Candidate-to-Achievement Reviewer Workflow Design

**Generated:** 2026-10-25
**Chunk type:** design-only (no code change, no tests, no dataset change).
**Final disposition:** `WORKFLOW DESIGN COMPLETED`

> Scope: design the human-reviewed workflow that converts a
> genuine evidence-grounded `AchievementCandidate` (Chunk 7.39)
> into an approved `Achievement` record (Chunk 2 schema). The
> design identifies the schema gaps the transition must bridge,
> proposes a reviewer-decision vocabulary that reuses existing
> project terminology where it fits, lays out the field mapping,
> and recommends the smallest implementation chunk the owner
> could reach for next. Nothing is implemented in this chunk —
> no new file in `src/`, no new test, no dataset mutation, no
> source approval, no taxonomy promotion.

---

## 9. Repository preconditions (brief §9)

| Field | Observed | Match |
|---|---|---|
| Branch | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` | ✓ |
| Working tree | Byte-identical to the Chunk 7.43 end state outside this new report | ✓ |

Not `REPOSITORY PRECONDITION MISMATCH`. No git stage / commit /
push / branch-switch / reset / clean / stash. Teammate
directories remain absent.

---

## 10. No dataset records were changed (brief §10)

Confirmed:

- `batch_01_sih2024.yaml` — unchanged.
- `sources.yaml` — unchanged (both entries still
  `review_status: unreviewed`).
- `primary_taxonomy.yaml`, `domain_tags.yaml` — unchanged (all
  14 + 10 labels still `draft`).
- No `Annotation` row added. No `Evidence` row added. No
  `AchievementCandidate` created. No `IntakeEntry` ingested.
- `cli readiness hybrid_dataset` would print the same
  `any_task=not_ready | all_tasks=not_ready | approved(pt=0,dt=0)
  | eligible(pt=0,dt=0) | blockers=4 | strict=off` summary as
  Chunk 7.41.

Chunk 7.44 is pure documentation; no re-execution of the test
suite is warranted and none was performed.

---

## 1. Existing schema findings

Audited (read-only) in this chunk:

- `src/nlp_semantic/schema/achievement.py` — `Achievement` + `AnnotationStatusMap`.
- `src/nlp_semantic/schema/evidence.py` — `Evidence`.
- `src/nlp_semantic/schema/annotation.py` — `Annotation`.
- `src/nlp_semantic/schema/enums.py` — `AnnotationStatus`, `ReviewStatus`, `AnnotationTask`, `TaxonomyStatus`, `DocumentFileType`, `ExtractionMethod`.
- `src/nlp_semantic/schema/identifiers.py` — `make_id`, `validate_prefixed_id`, `validate_label_id`.
- `src/nlp_semantic/intake/pipeline.py` — `IntakeEntry`, `AchievementCandidate`, `IntakeStatus`, `IntakeFinding`, `IntakeValidationCode`, hashing + file-ops surface.
- `src/nlp_semantic/dataset/validator.py` — `training_ready_subset`, `eligible_ground_truth`, `validate_dataset`.
- `src/nlp_semantic/dataset/loader.py` — `load_dataset`, `DatasetLoadReport`.
- `src/nlp_semantic/dataset/duplicates.py` — four deterministic duplicate rules.
- `hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md` — annotation rubric.
- `hybrid_dataset/dataset/README.md` — batch-file shape and GT eligibility.

### 1.1 `AchievementCandidate` (Chunk 7.39, `nlp_semantic.intake`)

| Field | Type | Notes |
|---|---|---|
| `candidate_id` | `str` | `cand_<32-hex>` — local pattern, not in `_RECORD_PREFIXES` |
| `evidence_intake_ids` | `list[str]` | each `intk_<32-hex>`; unique within the list |
| `source_id` | `str | None` | `src_<32-hex>` if set |
| `extracted_text_inline` | `str | None` | ≤ 2000 chars |
| `proposed_achievement_text` | `str | None` | ≤ 4000 chars |
| `proposed_primary_type` | `str | None` | `lbl_<snake>` if set |
| `proposer` | `str | None` | pseudonym; emails rejected |
| `status` | `IntakeStatus` | `received | validated | rejected` |
| `validation_findings` | `list[IntakeFinding]` | advisory + fatal |

### 1.2 `Achievement` (Chunk 2 schema)

Fields required by the schema for a well-formed record:

- `achievement_id` (`ach_<32-hex>`), `source_id` (`src_<32-hex>`), `source_record_id` (1-200 chars), `achievement_text` (1-4000 chars).
- `annotation_status` is a required `AnnotationStatusMap` with
  per-task values; defaults to `primary_type: NOT_STARTED` and
  `domain_tags: NOT_STARTED`.
- `is_synthetic` defaults to `False`.

Fields optional per the schema:

- `primary_type`, `domain_tags`, `level`, `outcome`, `event_name`,
  `organization`, `achievement_date`, `rank`, `skills`,
  `evidence_id`.

Schema-level invariants:

- `primary_type` set + `annotation_status.primary_type == NOT_STARTED` → rejected
  (`_check_annotation_consistency` in `achievement.py` lines 134-144).
- Similarly for `domain_tags` non-empty + `annotation_status.domain_tags == NOT_STARTED`.
- `achievement_date` must be ≤ today + 1 day.
- `rank` must be ≥ 1 if set.
- `skills` must be unique and ≤ 120 chars per entry.
- `domain_tags` must be unique.

### 1.3 `Evidence` (Chunk 2 schema)

Fields required:

- `evidence_id` (`evd_<32-hex>`), `relative_path` (must start with `APPROVED_EVIDENCE_PREFIX = "hybrid_dataset/raw/evidence_documents/"`), `file_type` (`DocumentFileType` enum).

Fields optional:

- `linked_achievement_id`, `original_filename`, `document_type`,
  `extraction_method` (defaults to `NONE_YET`), `extracted_text_ref`,
  `extracted_text_inline` (≤ 2000 chars), `ocr_confidence` (only
  if `extraction_method` is an OCR method), `review_status`
  (defaults to `UNREVIEWED`), `is_synthetic` (defaults to `False`).

Cross-field invariant: `extracted_text_ref` and
`extracted_text_inline` are mutually exclusive.

### 1.4 `IntakeEntry` (Chunk 7.39)

Produces files under `hybrid_dataset/raw/evidence_intake/<intk_id>/<name>`
— a path that does **not** start with
`APPROVED_EVIDENCE_PREFIX`. This is the first schema finding
with workflow consequences.

### 1.5 `Annotation` (Chunk 2 schema)

Fields required: `annotation_id` (`ann_<32-hex>`), `achievement_id` (`ach_<32-hex>`), `task` (`primary_type | domain_tags | extraction_review`), `label_ids` (arity per task), `annotator` (pseudonym), `review_status`, `created_at` (timezone-aware), `is_synthetic`.

Note the per-task arity: `primary_type` exactly 1 label,
`domain_tags` 0..N, `extraction_review` 0.

### 1.6 `training_ready_subset` gate (Chunk 2 / Chunk 5)

Four AND-conditions, from
`src/nlp_semantic/dataset/validator.py` lines 321-371:

1. `Achievement.annotation_status.<task> == AnnotationStatus.VERIFIED`.
2. Every referenced `label_id` has `LabelTaxonomy.status == APPROVED` for the task.
3. The record's source has `review_status == ReviewStatus.VERIFIED`.
4. The record's source has `license.strip().upper() != "UNKNOWN"`.

Chunk 7.44 preserves all four unchanged.

### 1.7 Schema gaps between Candidate and Achievement

Four gaps that the workflow design must address, none of which
is a blocker — each is bridgeable with reviewer input or an
additive helper, not a schema change:

| # | Gap | Side causing the gap | Bridge |
|---|---|---|---|
| G-1 | `Candidate` has no `source_record_id` | `Achievement.source_record_id` is required | Reviewer supplies the record id during the accept decision (same pattern as `batch_01_sih2024.yaml` lines 73-74). |
| G-2 | `Candidate` has `evidence_intake_ids` but not `evidence_id` | `Achievement.evidence_id` optional, `Evidence.relative_path` must start with `APPROVED_EVIDENCE_PREFIX` | Introduce an **evidence-promotion** step: reviewer-driven copy from `hybrid_dataset/raw/evidence_intake/<intk_id>/<file>` into `hybrid_dataset/raw/evidence_documents/<new-name>`, then create an `Evidence` row with that path. The intake original is preserved; a new on-disk copy sits under the approved-evidence prefix. |
| G-3 | `Candidate` has no `annotation_status` | `Achievement.annotation_status` is required (`AnnotationStatusMap`) | Derived at Achievement creation. If `Candidate.proposed_primary_type` is set, the new Achievement starts with `annotation_status.primary_type: DRAFT` (same pattern as `batch_01_sih2024.yaml`). If not set, `NOT_STARTED`. `domain_tags` always starts `NOT_STARTED`. |
| G-4 | `Candidate` has no extraction fields (`level`, `outcome`, `event_name`, `organization`, `achievement_date`, `rank`, `skills`, `domain_tags`) | `Achievement` supports all as optional (nullable / empty list) | Reviewer supplies any fields the source + their inspection supports; unsupported fields stay null / empty per guidelines §240-251 ("fill them when the source makes them unambiguous, leave it null otherwise"). |

### 1.8 What the schema already prevents (no new rule needed)

- A duplicate `(source_id, source_record_id)` is caught by
  `validate_dataset`'s `duplicate_source_record_pairs` check in
  `validator.py` lines 212-214.
- Unknown source references, unknown taxonomy labels, deprecated
  labels, orphan annotations — all already caught by
  `validate_dataset`.
- `Achievement` with `primary_type` set but
  `annotation_status.primary_type: NOT_STARTED` — rejected at
  Pydantic layer by `_check_annotation_consistency`.
- Unsafe `Evidence.relative_path` — rejected by `reject_unsafe_relative_path`.
- `training_ready_subset` already fails closed on any record
  that does not clear the four conditions.

**Conclusion:** the Candidate→Achievement workflow does not need
new schema invariants or new eligibility rules. It needs a
reviewer-decision model, a decision CLI, an evidence-promotion
helper, and documented field-mapping rules.

---

## 2. Proposed reviewer workflow

### 2.1 Overview

```
IntakeEntry       (Chunk 7.39: reviewer-supplied file + hash + manifest)
     │
     ├────────── Reviewer promotes to Evidence (new step: Phase 2)
     │             → creates evd_<hex> + copies file under
     │               hybrid_dataset/raw/evidence_documents/
     │
     ▼
AchievementCandidate (Chunk 7.39: optional; reviewer-created with proposed fields)
     │
     ├────────── Reviewer reviews the candidate (new step: Phase 3)
     │             decision ∈ {accept, reject, revise, defer}
     │             writes a CandidateReview record (append-only)
     │
     ▼ (only if decision == accept)
Achievement       (Chunk 2 schema: entered into batch_<NN>_<slug>.yaml)
                  annotation_status.primary_type = DRAFT if primary_type set
                  evidence_id = evd_<hex> from the promotion step (if applicable)
                  source_record_id = reviewer-supplied
                  Still NOT training-ready — needs
                  training_ready_subset's four-condition gate.
```

### 2.2 Phase 1 — Candidate inspection

For each `AchievementCandidate` under review, the reviewer
inspects:

- `candidate_id` — the opaque reference.
- `evidence_intake_ids` — every linked intake entry (there may be
  more than one; the schema permits a list).
- The on-disk file for each intake under
  `hybrid_dataset/raw/evidence_intake/<intk_id>/<name>` — the
  reviewer **opens the file directly** rather than trusting
  the manifest alone.
- `source_id`, if set — cross-checks against `sources.yaml` to
  confirm the source is registered (though registration ≠
  approval).
- `proposed_achievement_text` and `proposed_primary_type` — what
  the proposer suggested.
- `validation_findings` — advisories like
  `AUTHENTICATION_NOT_ESTABLISHED`, `MISSING_SOURCE_ASSOCIATION`,
  `DUPLICATE_HASH`.
- The intake manifest at `hybrid_dataset/intake/manifests/<intk_id>.yaml`
  for timestamp, size, pseudonym of proposer.
- Any `reviews/evidence/<name>.<ext>.notes.yaml` sidecar from
  the capture (Chunk 7.41 §4) for capture-time context the
  intake pipeline does not record.
- `validate_dataset` output after a hypothetical insertion —
  specifically, the `duplicate_source_record_pairs` check.
- Existing `Annotation` rows for related `Achievement` records
  (same `source_id`, similar `achievement_text`) that might
  indicate the candidate is a duplicate of an existing record.

### 2.3 Phase 2 — Evidence promotion (bridging gap G-2)

If the candidate's evidence should become a persistent `Evidence`
row (e.g. for `Achievement.evidence_id` to point at), the
reviewer runs:

```
nlp_semantic.intake.cli promote-evidence <intk_id> \
    --evidence-root hybrid_dataset/raw/evidence_intake \
    --evidence-documents hybrid_dataset/raw/evidence_documents \
    --document-type <optional short descriptor>
```

This proposed subcommand (not yet implemented):

1. Reads the `IntakeEntry` at `hybrid_dataset/intake/manifests/<intk_id>.yaml`.
2. Copies the intake file from
   `hybrid_dataset/raw/evidence_intake/<intk_id>/<name>` to
   `hybrid_dataset/raw/evidence_documents/<intk_id>__<name>` (the
   `<intk_id>__` prefix preserves provenance and avoids
   filename collisions across intakes).
3. Allocates a fresh `evidence_id = evd_<32-hex>` via
   `make_id("evd")`.
4. Creates an `Evidence` row with:
   - `evidence_id` = the fresh id.
   - `linked_achievement_id = None` (set later when the
     Achievement is created).
   - `relative_path = "hybrid_dataset/raw/evidence_documents/<intk_id>__<name>"`.
   - `original_filename = IntakeEntry.original_filename`.
   - `file_type = IntakeEntry.file_type`.
   - `document_type = <arg or None>`.
   - `extraction_method = ExtractionMethod.NONE_YET`.
   - `extracted_text_inline = None` and `extracted_text_ref = None`
     (unless the intake had `extracted_text_inline` and the
     reviewer explicitly passes it through).
   - `ocr_confidence = None`.
   - `review_status = ReviewStatus.UNREVIEWED` (not approval).
   - `is_synthetic = False`.
5. Writes the row to a tracked file under
   `hybrid_dataset/dataset/evidence/batch_<NN>_<slug>.yaml`
   following the batch-file convention (one `Evidence` list per
   batch file; same shape as `records/` and `annotations/`).

**Fail-closed properties the promotion step preserves:**

- Does **not** set `review_status: verified` on the Evidence row.
- Does **not** promote the source referenced by the intake.
- Does **not** approve any taxonomy label.
- Does **not** create an `Achievement` row.
- Does **not** modify the intake's original file (copy semantics,
  not move).
- Does **not** auto-run OCR; `extraction_method: NONE_YET` is
  the honest default.

### 2.4 Phase 3 — Reviewer decision

The reviewer records a decision using one of four outcomes
(brief §2 "Reviewer decisions"), expressed as a
`CandidateDecision` enum (proposed, not yet implemented):

| Decision | Semantics | Candidate `status` after decision | Produces an Achievement? |
|---|---|---|---|
| `accept` | Reviewer confirms the candidate is a genuine achievement with sufficient evidence. | `validated` | **Yes** — one new `Achievement` row in a new batch file |
| `reject` | Reviewer confirms the candidate is not a valid achievement, or the evidence does not support it. | `rejected` | No |
| `revise` | Reviewer requires the proposer to supply more evidence, correct metadata, or clarify ambiguity before another decision. | `received` (unchanged) + a revision request appended | No |
| `defer` | Reviewer wants another reviewer or wants to come back to this later. | `received` (unchanged) | No |

### 2.5 Phase 4 — Candidate-to-Achievement transition (accept only)

Only `accept` triggers Achievement creation. The transition is
the subject of §3 (field mapping) and §4 (decision + validation
rules) below.

### 2.6 Phase 5 — Audit trail

Each decision is persisted as an append-only `CandidateReview`
record (proposed shape in §6.2). The brief §4 "Audit trail
requirements" calls for traceability; the proposal preserves it
through:

- One `CandidateReview` per decision, with ISO 8601 timezone-aware
  timestamp.
- Append-only semantics: a `revise` decision followed by a later
  `accept` yields two records, not one with a later `accept`
  overwriting the earlier `revise`.
- Each decision cites the `candidate_id`, the reviewer pseudonym,
  the rationale, and (for `accept`) the newly produced
  `achievement_id`.

---

## 3. Candidate-to-Achievement field mapping

| `Achievement` field | Source | Reviewer-supplied? | Default on `accept` |
|---|---|---|---|
| `achievement_id` | — | — | `make_id("ach")` — fresh |
| `source_id` | `Candidate.source_id` | required if candidate lacks one (G-1 bridge, see below) | — |
| `source_record_id` | — | **required reviewer input** (G-1) | — |
| `achievement_text` | `Candidate.proposed_achievement_text` | reviewer may revise verbatim | `Candidate.proposed_achievement_text` if present and non-empty |
| `primary_type` | `Candidate.proposed_primary_type` | reviewer may revise or set to null | `Candidate.proposed_primary_type` |
| `domain_tags` | — | reviewer may supply, each `lbl_<snake>`, unique | `[]` |
| `level` | — | reviewer may supply (e.g. `national` / `international`) | `None` |
| `outcome` | — | reviewer may supply (e.g. `winner` / `finalist`) | `None` |
| `event_name` | — | reviewer may supply | `None` |
| `organization` | — | reviewer may supply | `None` |
| `achievement_date` | — | reviewer may supply (ISO date; must be ≤ today + 1) | `None` |
| `rank` | — | reviewer may supply (int ≥ 1) | `None` |
| `skills` | — | reviewer may supply (each ≤ 120 chars, unique) | `[]` |
| `evidence_id` | Phase-2 `Evidence` row (G-2 bridge) | reviewer may link | `None` if no `Evidence` promotion was run |
| `annotation_status.primary_type` | — | derived (G-3) | `DRAFT` if `primary_type` is set, `NOT_STARTED` otherwise |
| `annotation_status.domain_tags` | — | derived (G-3) | `NOT_STARTED` always (reviewer may later flip to `VERIFIED` with `[]` after a deliberate "no tags apply" review) |
| `is_synthetic` | — | — | `False` (candidates from real intake are not synthetic) |

Rationale for the G-3 default: the Chunk 7.4-A.1 extraction
pattern in `batch_01_sih2024.yaml` sets
`annotation_status.primary_type: draft` on records where the
label is a tentative extraction decision supported by event-level
evidence. The accept path mirrors that pattern: the reviewer
accepting a candidate is making the same tentative extraction
decision; `verified` requires a separate annotation review per
`ANNOTATION_GUIDELINES.md`.

### 3.1 How the reviewer supplies the missing fields

Two viable surfaces:

- **CLI flags on a proposed `review-candidate --accept` command**
  (one-shot ergonomics). The reviewer writes:

  ```
  nlp_semantic.intake.cli review-candidate <candidate_id> \
      --decision accept \
      --reviewer labeler_<pseudonym> \
      --rationale "<text>" \
      --source-record-id "<stable id, e.g. pib-prid-2085000-...>" \
      --evidence-id evd_<32-hex>       # from Phase 2, optional \
      --event-name "<...>"              # optional \
      --organization "<...>"            # optional \
      --level national | international | ... \
      --outcome winner | finalist | participant | ... \
      --achievement-date 2024-12-16     # optional \
      --rank 1                          # optional \
      --skill python --skill pytorch    # repeatable, optional \
      --domain-tag lbl_domain_ai        # repeatable, optional \
      --batch-file batch_02_<slug>.yaml # which batch file to append to
  ```

- **A reviewer-authored YAML file** that the command loads
  (`--spec <path>`). Reviewers who want to review many
  candidates in bulk prefer this; one-off reviewers prefer the
  CLI flags. Both should be supported.

Default when the reviewer passes no override: the field stays
unset per the "Default on `accept`" column above.

### 3.2 What the transition does NOT do

- **Does not run `training_ready_subset`.** The accept decision
  creates an Achievement whose `annotation_status.primary_type`
  starts at `DRAFT`; `training_ready_subset` will still return
  `[]` for it until a separate annotation-review step flips the
  status to `VERIFIED` AND the taxonomy is promoted AND the
  source is verified.
- **Does not approve the source.** The candidate's `source_id`
  stays at whatever `review_status` and `license` it already has
  in `sources.yaml`. The accept decision merely cites the source;
  it does not promote it.
- **Does not promote the taxonomy label.** If
  `Candidate.proposed_primary_type` is `lbl_hackathon` and the
  label is `status: draft`, the new Achievement cites a draft
  label (same advisory finding as `batch_01_sih2024.yaml` under
  the current taxonomy).
- **Does not create an `Annotation` row.** Annotation history
  is created separately when a reviewer performs single or dual
  review per `ANNOTATION_GUIDELINES.md`.
- **Does not change existing records.** No in-place mutation of
  prior batch files; new Achievements go into a new batch file.

---

## 4. Decision and validation rules

### 4.1 Preconditions for `accept`

All of the following MUST hold at decision time; otherwise the
command refuses:

| # | Precondition | Enforced by |
|---|---|---|
| P-1 | `candidate_id` exists and loads via `load_candidate(path)` (proposed) | future validator |
| P-2 | At least one `IntakeEntry` referenced in `evidence_intake_ids` exists on disk with intact SHA-256 | reuses Chunk 7.39 `validate_intake_entry` |
| P-3 | Reviewer passes `--source-record-id` (G-1) | CLI argument parser |
| P-4 | `source_record_id` is unique vs every existing `Achievement.(source_id, source_record_id)` pair in the loaded dataset | reuses `validate_dataset`'s `duplicate_source_record_pairs` check |
| P-5 | If reviewer passes `--primary-type`, the label exists in `primary_taxonomy.yaml` (status may be any; `training_ready_subset` later gates on `APPROVED`) | reuses `validate_dataset`'s `unknown_primary_type_refs` check |
| P-6 | If reviewer passes `--domain-tag`, each tag exists in `domain_tags.yaml` and is not `deprecated` | reuses `validate_dataset`'s `unknown_domain_tag_refs` + `deprecated_label_refs` |
| P-7 | Reviewer is NOT the candidate's `proposer` (reviewer-independence; same spirit as `TAXONOMY_APPROVAL_CHECKLIST` §104-106 and Chunk 7.38B `PROPOSER_IS_REVIEWER`) | CLI validation + `CandidateReview` validation |
| P-8 | The resulting `Achievement` row, when added to the loaded dataset, keeps `validate_dataset.is_valid == True` (no new fatal findings) | re-run `validate_dataset` inside the CLI before writing |

Precondition failures are **fatal** (CLI exits 1). The reviewer
sees the specific precondition code so they can correct
(resubmit after fixing) or `revise` (bounce back to proposer).

### 4.2 Preconditions for `reject`

| # | Precondition | Enforced by |
|---|---|---|
| R-1 | `candidate_id` exists | future validator |
| R-2 | Reviewer is NOT the candidate's `proposer` (same independence rule) | future validator |

Rejected candidates are kept in the system — their `status` flips
from `received` to `rejected` and a `CandidateReview` is written.
This matches the existing project convention that duplicate
groups and rejected annotations stay in place for traceability
(`ANNOTATION_GUIDELINES.md` §256-268).

### 4.3 `revise` and `defer`

Neither mutates the candidate's `status`. Both write a
`CandidateReview` row with the decision + rationale. `revise`
requires the reviewer to state what must change; `defer` does
not require a specific blocker but should carry a rationale
indicating what the next reviewer needs to know.

### 4.4 Validation rules carried over from existing project surfaces

- `AchievementCandidate` extra-fields rejection (`extra="forbid"`)
  preserved.
- Pseudonym regex preserved for `reviewer` field (same as
  `Annotation.annotator` and `ReviewerSignOff.reviewer`).
- Timezone-aware timestamps required (same as `Annotation.created_at`).
- Hash integrity preserved for intake-side cross-check (reuses
  `validate_intake_entry`'s `HASH_MISMATCH_ON_DISK` finding).

### 4.5 Fail-closed training-readiness preserved

The accept path writes a new Achievement with
`annotation_status.primary_type: DRAFT`. `training_ready_subset`
requires `VERIFIED`. So the newly accepted candidate is **not**
training-ready, and the four-condition gate in `validator.py`
lines 321-371 is unchanged. The brief §Protected boundaries rule
"Preserve the existing fail-closed training-readiness behavior"
is honoured.

---

## 5. Human-review requirements

Each requirement below is a REVIEWER action, not an AI action.
The design surfaces them so they do not get silently absorbed
into automation.

| # | Requirement | Who |
|---|---|---|
| H-1 | Inspect the on-disk evidence file directly (not only the manifest) | Reviewer |
| H-2 | Verify that `achievement_text` reflects what the evidence actually shows | Reviewer |
| H-3 | Supply `source_record_id` as a stable identifier the source itself exposes (e.g. `pib-prid-<PRID>-...` for PIB press releases) | Reviewer |
| H-4 | Decide whether `primary_type` should be set, revised, or left `None` | Reviewer |
| H-5 | Decide whether the Chunk 7.1 event-centric vs artifact-centric framing is correct for this candidate | Reviewer |
| H-6 | Confirm team-level vs individual framing (see `batch_01_sih2024.yaml` lines 36-47) | Reviewer |
| H-7 | Confirm no `(source_id, source_record_id)` collision with an existing Achievement | Reviewer (CLI will refuse on P-4; reviewer resolves) |
| H-8 | Decide whether an `Evidence` row should be promoted now (Phase 2) or deferred | Reviewer |
| H-9 | Confirm the batch file to append to; typically a new `batch_<NN>_<slug>.yaml` per source | Reviewer |
| H-10 | Record a rationale (free text, 2-3 sentences) in the `CandidateReview` | Reviewer |
| H-11 | Honor reviewer-independence: the proposer cannot accept their own candidate | Enforced by P-7; reviewer must respect it |
| H-12 | Separately drive the subsequent single or dual annotation review per `ANNOTATION_GUIDELINES.md` to flip `annotation_status.primary_type` from `DRAFT` to `VERIFIED` | Reviewer (not scope of Chunk 7.44 implementation) |

---

## 6. Implementation plan

### 6.1 Reusable existing modules (no code change needed)

- `src/nlp_semantic/intake/pipeline.py` — `AchievementCandidate`,
  `IntakeEntry`, `validate_intake_entry`, `load_intake_entry`,
  `make_candidate_id`, `make_intake_id`, hashing helpers.
- `src/nlp_semantic/schema/identifiers.py` — `make_id("ach")`,
  `make_id("evd")`, `validate_prefixed_id`, `validate_label_id`.
- `src/nlp_semantic/schema/achievement.py` — `Achievement`,
  `AnnotationStatusMap`.
- `src/nlp_semantic/schema/evidence.py` — `Evidence`.
- `src/nlp_semantic/schema/path_safety.py` —
  `reject_unsafe_relative_path`, `APPROVED_EVIDENCE_PREFIX`.
- `src/nlp_semantic/dataset/validator.py` — `validate_dataset`
  for pre-write check (P-8), `training_ready_subset` for the
  post-write disclaimer only.
- `src/nlp_semantic/dataset/loader.py` — `load_dataset` to read
  the current records before deciding P-4 / P-5 / P-6 / P-8.

### 6.2 Minimal proposed interfaces (future, not implemented here)

```python
# src/nlp_semantic/intake/review.py  (future, Chunk 7.45 candidate)

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .pipeline import AchievementCandidate, IntakeEntry


class CandidateDecision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    REVISE = "revise"
    DEFER  = "defer"


class CandidateReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    review_id: str                      # crev_<32-hex>  (new local pattern)
    candidate_id: str                   # cand_<32-hex>
    reviewer: str                       # pseudonym; emails rejected
    decision: CandidateDecision
    rationale: str = Field(min_length=1, max_length=4000)
    created_at: datetime                # timezone-aware required

    # Set only when decision == accept and the acceptance produced an Achievement
    accepted_achievement_id: str | None = None
    # Set only when accept supplied a reviewer-promoted Evidence
    accepted_evidence_id: str | None = None
    # Set only when accept wrote to a batch file
    batch_file: str | None = None       # e.g. "batch_02_<slug>.yaml"


def review_candidate(
    candidate: AchievementCandidate,
    *,
    decision: CandidateDecision,
    reviewer: str,
    rationale: str,
    source_record_id: str | None = None,
    evidence_id: str | None = None,
    overrides: dict | None = None,       # explicit field overrides for Achievement
    dataset_root: str | Path,
    sources: Iterable[SourceRegistry],
    primary_taxonomy: Iterable[LabelTaxonomy],
    domain_taxonomy: Iterable[LabelTaxonomy],
    batch_file: str | None = None,
) -> CandidateReviewResult:
    """Execute the Phase-3 reviewer decision.

    Pre-write checks (P-1 through P-8) are run before any file is
    written. Fail-closed: any precondition miss raises
    CandidateReviewError and nothing is persisted. On accept,
    produces one new Achievement row in `dataset/records/<batch_file>`,
    the companion CandidateReview, and (optionally) the
    linked Evidence row (if an evidence promotion ran earlier).
    """
```

```python
# src/nlp_semantic/intake/promote_evidence.py  (future, Chunk 7.45 candidate)

def promote_intake_to_evidence(
    intake: IntakeEntry,
    *,
    evidence_root: str | Path,                 # hybrid_dataset/raw/evidence_intake
    evidence_documents_root: str | Path,       # hybrid_dataset/raw/evidence_documents
    evidence_batch_file: str | Path,           # dataset/evidence/batch_<NN>.yaml
    document_type: str | None = None,
) -> Evidence:
    """Copy the intake file into evidence_documents/ and create an
    Evidence row. Idempotent: if the same intake has already been
    promoted (same sha256), returns the existing Evidence.
    """
```

### 6.3 Proposed new CLI subcommands

Extend `src/nlp_semantic/intake/cli.py` with two new subcommands
(additive; no change to existing `ingest | validate | status |
duplicates`):

- `promote-evidence <intake_id> --document-type <optional>`
- `review-candidate <candidate_id> --decision {accept|reject|revise|defer} [overrides...]`

Both would reuse the existing CLI's argparse-based pattern,
stdout-JSON + stderr-summary convention, and exit codes.

### 6.4 Proposed storage layout for review records

```
hybrid_dataset/
├── dataset/
│   ├── candidate_reviews/
│   │   ├── .gitkeep
│   │   └── batch_<NN>.yaml      # append-only list of CandidateReview rows
│   ├── evidence/
│   │   ├── .gitkeep
│   │   └── batch_<NN>.yaml      # Evidence rows produced by promote-evidence
│   ├── records/
│   │   ├── batch_01_sih2024.yaml  (unchanged)
│   │   └── batch_02_<slug>.yaml   (new, produced by accept decisions)
│   └── annotations/              (unchanged; produced by separate review)
```

Rationale: parallels the existing `records/` and `annotations/`
directories; keeps candidate-review audit records separate from
annotation records; keeps evidence-row YAML separate from the raw
files (which remain under `raw/evidence_documents/`).

### 6.5 Risks and unresolved decisions

| # | Risk / open decision | Options | Recommendation |
|---|---|---|---|
| R-1 | Should `source_record_id` be mechanized to prevent typos? | (a) free text; (b) regex-validated; (c) must match a reviewer-maintained lookup table | (a) free text per existing `Achievement.source_record_id` type (1-200 chars); reviewer discipline suffices |
| R-2 | How to deal with multi-intake candidates? | (a) one Achievement per candidate; (b) allow one candidate to produce multiple Achievements | (a) — matches the existing one-row-per-achievement contract and avoids ambiguity on `achievement_id` allocation |
| R-3 | Where should `CandidateReview` records live if the reviewer wants to track them outside the dataset? | (a) `hybrid_dataset/dataset/candidate_reviews/`; (b) `reviews/candidate_reviews/`; (c) `reports/` | (a) — the dataset directory is where reviewer-reviewed artifacts belong; `reports/` is for prose reports |
| R-4 | Does the accept path create an `Evidence` row even if the reviewer did not run `promote-evidence` first? | (a) accept requires `evidence_id` from a prior promote-evidence; (b) accept optional; (c) accept auto-promotes | (b) — `evidence_id` is optional on Achievement; the SIH records all have `evidence_id: null` by design. Promotion is a separate reviewer-driven step the reviewer chooses to run when they want a persistent Evidence row |
| R-5 | Can the proposer and the reviewer be the same person? | (a) forbidden (reviewer-independence); (b) allowed with a warning | (a) — matches Chunk 7.38B `PROPOSER_IS_REVIEWER` fatal finding and `TAXONOMY_APPROVAL_CHECKLIST` §104-106 |
| R-6 | Should `accept` require the taxonomy label to be `approved`? | (a) yes (strict); (b) no (allow drafts, flag advisory) | (b) — the existing dataset tolerates draft label refs as advisories (`batch_01_sih2024.yaml` works today). Requiring `approved` would block Achievement creation until Chunk 7.37 lands |
| R-7 | How does the accept path interact with semantic duplicate detection? | (a) deterministic duplicate check only; (b) require semantic duplicate check | (a) — Chunk 7.35 §O.3 flagged semantic duplicate detection as a separate deferred chunk; the accept path uses the four deterministic rules only |
| R-8 | Should candidate statuses `accept` and `reject` be reflected on the `AchievementCandidate.status` field, or only via `CandidateReview`? | (a) both (duplicated); (b) only on `CandidateReview`; (c) only on `AchievementCandidate.status` | (a) — the Candidate's `status` becomes the latest decision summary (`validated` or `rejected`); the `CandidateReview` holds the full audit trail |
| R-9 | Should a `revise` cycle count as a new candidate or an update to the same candidate? | (a) same candidate; (b) new candidate on each revise | (a) — a `revise` request + a resubmitted proposed-text update stays on the same `candidate_id`; the audit trail is in `CandidateReview` records |
| R-10 | How is the `batch_file` name chosen? | (a) auto-named `batch_<NN>_<timestamp>.yaml`; (b) reviewer picks via `--batch-file`; (c) one-batch-per-source `batch_<NN>_<src_slug>.yaml` | (c) — mirrors `batch_01_sih2024.yaml`'s naming (`sih2024` is the source slug) and keeps all records from one source in one file; reviewer may still pass `--batch-file` to override |

None of these risks is a workflow-level blocker; each is a
reviewer-decision question that can be set during the
implementation chunk's design review.

---

## 7. Tests proposed for the future implementation

Not implemented in this chunk. The brief §Scope §6 asks the
design to "Identify … Necessary future tests." The following
are the minimum coverage items the implementation chunk should
land:

### 7.1 `review_candidate` (future)

1. **Valid accept** — produces a well-formed Achievement in a new batch file + a CandidateReview record.
2. **Accept with missing `source_record_id`** — fails precondition P-3.
3. **Accept with duplicate `(source_id, source_record_id)`** — fails precondition P-4.
4. **Accept with unknown `primary_type`** — fails P-5.
5. **Accept with unknown `domain_tag`** — fails P-6.
6. **Accept by the candidate's own proposer** — fails P-7 (reviewer-independence).
7. **Accept producing a record that would fail `validate_dataset`** — fails P-8.
8. **Reject** — flips Candidate.status to `rejected`, writes CandidateReview, no Achievement.
9. **Revise** — leaves Candidate.status unchanged, writes CandidateReview with revision request.
10. **Defer** — leaves Candidate.status unchanged, writes CandidateReview.
11. **Audit append-only** — a `revise` followed by `accept` writes two CandidateReview rows; the second does not overwrite the first.
12. **Candidate review does not modify existing records** — assertion that `batch_01_sih2024.yaml` is byte-identical after a review of a different candidate.
13. **Candidate review does not change training-readiness output** — assertion that `cli readiness` is byte-identical after a `revise` or `defer`.
14. **Candidate review does not promote any source status** — assertion that `sources.yaml` is byte-identical.
15. **Candidate review does not approve any taxonomy label** — assertion that `primary_taxonomy.yaml` / `domain_tags.yaml` are byte-identical.
16. **Candidate review does not create an Annotation row** — assertion that `annotations/` is unchanged.
17. **Accepted Achievement has `annotation_status.primary_type: DRAFT`** if `primary_type` is set, `NOT_STARTED` otherwise.
18. **Timezone-naive `created_at` on CandidateReview is rejected** — Pydantic layer.

### 7.2 `promote_intake_to_evidence` (future)

19. **Valid promotion** — produces a well-formed Evidence row + a file copy under `evidence_documents/`.
20. **Idempotency** — same intake promoted twice returns the same Evidence row.
21. **Hash mismatch** — on-disk file hash disagrees with the intake manifest; promotion fails.
22. **Does not move the intake file** — the original under `evidence_intake/` is byte-identical after promotion.
23. **Does not mark the Evidence verified** — `review_status: UNREVIEWED` on new rows.
24. **File-type consistency** — `Evidence.file_type` matches `IntakeEntry.file_type`.

### 7.3 CLI (future)

25. CLI `promote-evidence` round-trip against a temporary tree.
26. CLI `review-candidate --decision accept` with a temporary candidate + taxonomy + source fixture.
27. CLI `review-candidate --decision reject` + rationale required.
28. CLI exits 1 on each precondition miss, 0 on success, 2 on argparse usage error.

Each test must use synthetic fixtures under `tmp_path` and must
not insert anything into the real `hybrid_dataset/` or
`reviews/` trees — same convention as Chunk 7.38B and Chunk
7.39 tests.

### 7.4 AST-based non-mutation guards (same pattern as Chunk 7.38B / 7.39)

29. The new module imports neither `training_ready_subset` nor `eligible_ground_truth` outside of a hypothetical post-write assertion that `is not changed by this call`.
30. The new module does not import `TaxonomyStatus` for mutation.
31. The new module does not import `ReviewStatus` for mutation of SourceRegistry entries.

---

## 8. Files created or modified

In Chunk 7.44:

- **Created:** `reports/chunk_7_44_candidate_to_achievement_review_workflow.md` (this report).
- **Modified:** none.

Nothing in `src/`, `hybrid_dataset/`, `reviews/`, `tests/`, or
the top-level `.gitignore` was touched. No git stage / commit
/ push / branch-switch / reset / clean / stash.

---

## 11. Final disposition

**`WORKFLOW DESIGN COMPLETED`.**

Rationale:

- Every brief §Scope item has a concrete design (§2 overview,
  §2.2–2.6 phases, §3 field mapping, §4 decision + validation
  rules, §5 reviewer requirements).
- Every schema gap (§1.7) is bridged without a schema change
  (reviewer-supplied `source_record_id`; new `promote-evidence`
  helper for `evidence_id`; derived `annotation_status`;
  reviewer-supplied extraction fields).
- The implementation plan (§6) identifies reusable modules,
  minimal new interfaces, proposed storage layout, and ten
  risks with recommended resolutions.
- Future test coverage (§7) is enumerated.
- Dataset is unchanged (§10); no record / source / taxonomy /
  annotation state mutated.

Alternatives considered and rejected:

- `WORKFLOW DESIGN BLOCKED BY SCHEMA` — would be correct if any
  §1.7 gap required a schema change. All four gaps are
  bridgeable with reviewer input or additive helpers; no
  schema change required.
- `REPOSITORY PRECONDITION MISMATCH` — not applicable; §9 passes.

---

## 12. Recommended next step (brief §Next step)

The smallest implementation chunk that advances the workflow
from design to code:

### Chunk 7.45 (recommended) — `review_candidate` + `CandidateReview` schema (accept + reject only)

A tight scope that would ship:

1. `src/nlp_semantic/intake/review.py` with `CandidateDecision`
   (ACCEPT, REJECT only — REVISE and DEFER deferred),
   `CandidateReview`, and a `review_candidate(...)` function
   covering preconditions P-1 through P-8.
2. A new CLI subcommand `review-candidate` on
   `nlp_semantic.intake.cli`.
3. A new storage directory `hybrid_dataset/dataset/candidate_reviews/`
   with a `.gitkeep` marker and a `README.md`.
4. Tests covering the 18 cases in §7.1 that are reachable
   without `promote-evidence` and without REVISE/DEFER.
5. A `reports/chunk_7_45_...md`.

**Deliberately deferred to a later chunk:**

- `promote_intake_to_evidence` (and the `Evidence` batch file
  storage) — Chunk 7.46 candidate.
- `REVISE` and `DEFER` decisions — Chunk 7.47 candidate.
- Semantic duplicate detection — the Chunk 7.35 §O.3 /
  Chunk 7.38B §16.1 standing candidate.
- `lbl_competition` taxonomy promotion packet (Chunk 7.37
  pattern) — orthogonal to this workflow and remains a parallel
  recommendation.

### Why ACCEPT + REJECT first (and REVISE / DEFER later)

- ACCEPT is the critical path to actually producing new
  Achievement records.
- REJECT is the symmetric fail-closed outcome.
- REVISE and DEFER are process niceties — they do not change
  the dataset or produce records; the first implementation can
  ship without them and the owner can decide whether they are
  needed based on how often REJECT-vs-REVISE ambiguity arises.
- Narrower scope = smaller review surface for the next chunk.

### Explicitly not recommended for Chunk 7.45

- Running the real-evidence intake exercise again (Chunk 7.40 /
  7.42 / 7.43 territory) — reviewer-driven, three failed
  attempts already.
- Modifying the Chunk 7.39 pipeline — out of scope.
- Changing `training_ready_subset` or the four-condition gate —
  explicitly protected by brief §Protected boundaries.

Chunk 7.45 is the smallest step that materializes the Chunk 7.44
design into tested, usable code without entangling it with
pending reviewer-driven work.
