# `hybrid_dataset/dataset/candidate_reviews/` — Candidate review audit trail

**Purpose:** append-only storage for `CandidateReview` records
produced by the Chunk 7.45 `review-candidate` workflow (ACCEPT and
REJECT decisions on an `AchievementCandidate`).

## 1. Storage convention

- One YAML file per review: `crev_<32-hex>.yaml`.
- Files are written only by
  `nlp_semantic.intake.review.review_candidate(...)` (or the
  equivalent `nlp_semantic.intake.cli review-candidate` CLI
  subcommand).
- Append-only: a later decision for the same candidate writes a
  **new** file with a different `review_id`. Existing files are
  never overwritten or mutated.
- `.gitkeep` keeps this directory present after a fresh clone.
  Review files produced in day-to-day use may be tracked in Git
  (they contain pseudonyms and attestation text — no raw
  evidence bytes, no PII beyond what the reviewer deliberately
  wrote in their rationale).

## 2. What belongs here

Only `CandidateReview` records matching the Chunk 7.45 schema in
`src/nlp_semantic/intake/review.py`. No `Achievement` row, no
`Annotation` row, no `IntakeEntry` manifest.

## 3. What a review record attests

- A reviewer pseudonym made a specific ACCEPT or REJECT decision
  on a specific candidate at a specific timezone-aware timestamp.
- For ACCEPT: the reviewer-attested `source_record_id`,
  `primary_type`, `domain_tags`, extraction fields, and
  optionally an `evidence_id` for a future Candidate-to-Achievement
  chunk to pick up.

## 4. What a review record does NOT establish

- Not source approval. `sources.yaml` is unchanged by any review.
- Not taxonomy promotion. The referenced labels are not approved.
- Not annotation verification. No `Annotation` row is created.
- Not Achievement creation. ACCEPT only attests the intent; the
  Achievement row is created by a future chunk.
- Not training-readiness. All four `training_ready_subset`
  conditions are unchanged.

## 5. Related

- Design: `reports/chunk_7_44_candidate_to_achievement_review_workflow.md`.
- Implementation: `reports/chunk_7_45_candidate_review_implementation.md`.
- Workflow module: `src/nlp_semantic/intake/review.py`.
- CLI subcommand: `python -m nlp_semantic.intake.cli review-candidate`.
