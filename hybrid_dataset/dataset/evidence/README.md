# `hybrid_dataset/dataset/evidence/` — Promoted Evidence records

**Purpose:** per-Evidence YAML records produced by the Chunk 7.46
`promote-evidence` workflow. Each file is one
`nlp_semantic.schema.Evidence` row linking an intake artifact to
an approved-evidence location.

## 1. Storage convention

- One YAML file per Evidence record: `evd_<32-hex>.yaml`.
- Files are written only by
  `nlp_semantic.intake.promote_evidence.promote_evidence(...)` (or
  the equivalent `nlp_semantic.intake.cli promote-evidence` CLI
  subcommand).
- The accompanying file bytes live under
  `hybrid_dataset/raw/evidence_documents/<intake_id>__<original_filename>`
  (gitignored).
- Append-only: a new promotion writes a new YAML; existing records
  are never mutated or overwritten.

## 2. What a promotion establishes

- A persistent `Evidence` row with:
  - `evidence_id = evd_<32-hex>`
  - `relative_path = hybrid_dataset/raw/evidence_documents/<intake_id>__<name>`
  - `original_filename = <intake.original_filename>`
  - `file_type = <intake.file_type>`
  - `extraction_method = none_yet`
  - `review_status = unreviewed`
  - `is_synthetic = false`
- A byte-for-byte copy of the intake original under
  `evidence_documents/`.

## 3. What a promotion does NOT establish

- Not evidence verification. `review_status: unreviewed` is the
  honest default; verification is a separate reviewer workflow.
- Not source approval. `sources.yaml` is byte-identical after a
  promotion.
- Not taxonomy promotion.
- Not annotation verification.
- Not Achievement creation. The Evidence row's
  `linked_achievement_id` is `None`; a future
  Candidate-to-Achievement chunk will attach it.
- Not training-eligibility. `training_ready_subset` behaviour is
  unchanged.

## 4. Reviewer workflow summary

```
IntakeEntry             (Chunk 7.39)
  ├─ hybrid_dataset/raw/evidence_intake/intk_<hex>/<name>  (file)
  └─ hybrid_dataset/intake/manifests/intk_<hex>.yaml       (manifest)
                     │
                     │  promote-evidence (Chunk 7.46)
                     ▼
Evidence                (Chunk 2 schema)
  ├─ hybrid_dataset/raw/evidence_documents/<intk_id>__<name>  (COPY)
  └─ hybrid_dataset/dataset/evidence/evd_<hex>.yaml           (this directory)
```

The reviewer runs:

```
PYTHONPATH=src python -m nlp_semantic.intake.cli promote-evidence \
    hybrid_dataset/intake/manifests/intk_<hex>.yaml \
    --reviewer labeler_<name>
```

## 5. Fail-closed guarantees preserved

- Reviewer independence: the reviewer must differ from the intake's
  proposer.
- Path safety: destination `relative_path` must start with
  `APPROVED_EVIDENCE_PREFIX = "hybrid_dataset/raw/evidence_documents/"`
  and pass `reject_unsafe_relative_path`.
- Duplicate guard: if an existing Evidence row's on-disk file
  shares the intake's SHA-256, the promotion is refused.
- No partial writes: all preconditions run before any disk write.

## 6. Related

- Design: `reports/chunk_7_44_candidate_to_achievement_review_workflow.md`
  §2.3.
- Implementation: `reports/chunk_7_46_evidence_promotion_implementation.md`.
- Module: `src/nlp_semantic/intake/promote_evidence.py`.
- CLI: `python -m nlp_semantic.intake.cli promote-evidence`.
