# `hybrid_dataset/dataset/` — curated records and annotation history

This directory holds **tracked, human-reviewed** achievement records
and (optional) annotation history. It is the input to the Chunk 5
dataset tooling (`src/nlp_semantic/dataset/`): loader, cross-record
validator, duplicate detector, statistics, and reproducible splits.

## Layout

```
hybrid_dataset/dataset/
├── README.md                       (this file)
├── ANNOTATION_GUIDELINES.md        rubric + examples + dispute workflow
├── records/
│   ├── .gitkeep
│   └── batch_<NN>.yaml             YAML list of Achievement records
└── annotations/
    ├── .gitkeep
    └── batch_<NN>.yaml             YAML list of Annotation history rows
```

Generated outputs (train/val/test splits, split manifests, stats
reports) live under `hybrid_dataset/processed/splits/` and are
gitignored.

## File format — `records/batch_<NN>.yaml`

A YAML list of mappings; each mapping is a `nlp_semantic.schema.Achievement`.
Shape mirrors the Pydantic model exactly; the loader rejects unknown
fields (`extra="forbid"`). Minimum legal content for an unannotated
record:

```yaml
- achievement_id: ach_<32 lowercase hex>
  source_id:      src_<32 lowercase hex>   # must exist in sources.yaml
  source_record_id: "upstream-primary-key"
  achievement_text: "First line of what the student achieved."
  is_synthetic: false
```

Add classification fields once annotation begins:

```yaml
  primary_type: lbl_hackathon              # must exist in primary_taxonomy.yaml
  domain_tags: [lbl_domain_ai]             # deduped; each must exist in domain_tags.yaml
  annotation_status:
    primary_type: verified
    domain_tags: verified
```

Extraction fields (`level`, `outcome`, `event_name`, `organization`,
`achievement_date`, `rank`, `skills`, `evidence_id`) are optional and
information-extraction outputs — never treated as classification
labels.

## File format — `annotations/batch_<NN>.yaml`

Optional. Store full `nlp_semantic.schema.Annotation` rows when a
record was dual-reviewed (used for inter-annotator-agreement
analysis). Shape mirrors the Annotation model. Single-review records
need no row here; their current status lives in the Achievement's
`annotation_status`.

```yaml
- annotation_id:   ann_<32 lowercase hex>
  achievement_id:  ach_<32 lowercase hex>  # must match a record in records/
  task:            primary_type            # or domain_tags, extraction_review
  label_ids:       [lbl_hackathon]         # arity per task
  annotator:       labeler_001             # pseudonym convention
  review_status:   verified
  notes:           "clear case; event archive confirms"
  created_at:      2026-11-05T14:22:00+00:00
  is_synthetic:    false
```

## Rules enforced by the loader + validator

1. **Every `source_id` must exist in `hybrid_dataset/metadata/sources.yaml`.**
2. **Every `primary_type` and `domain_tag` must exist in the taxonomy YAMLs** and must not be `deprecated`.
3. **No duplicate `achievement_id`** across all batches.
4. **No duplicate `(source_id, source_record_id)` pair** across all batches.
5. **No duplicate `annotation_id`** across all annotation batches.
6. **Every `Annotation.achievement_id` must reference an existing record**.
7. **`extra="forbid"` on every entry** — typos are errors.
8. **Records with `primary_type` set but `annotation_status.primary_type == NOT_STARTED`** are rejected by the Achievement model itself.

## Ground-truth eligibility (strict)

A record is eligible as **training ground truth for a task** only when
**both** hold:

1. `Achievement.annotation_status.<task> == VERIFIED`, AND
2. Every referenced label has `LabelTaxonomy.status == APPROVED` in
   the taxonomy file for that task.

Chunk 5 ships with all taxonomy labels at `status: draft`, so the
eligible-ground-truth set is **empty by design**. Promotion from
`draft` to `approved` happens via a separate human-reviewed PR; it is
not automated and is not part of Chunk 5.

## Registration is not approval

A record whose `source_id` points at a `SourceRegistry` entry with
`license: UNKNOWN` or `review_status != verified` **still loads**, but
surfaces in the validator's advisory warnings. Downstream training
code must gate on `review_status: verified` plus a human-approved
license decision outside this file. Chunk 5 does not perform
license-eligibility reasoning.

## What this directory does NOT hold

- Raw public datasets or private evidence documents (they live under
  `hybrid_dataset/raw/`, gitignored).
- Model-ready splits (generated into `hybrid_dataset/processed/splits/`,
  gitignored).
- Model artefacts, embeddings, OCR output (none exist in Chunk 5).
- Real student personally identifiable information in any form.
