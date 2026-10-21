# `nlp_semantic.schema` — data contract (data dictionary)

Pydantic v2 models for the hybrid achievement dataset. Chunk 2 scope.

## Design principles

1. **Format validation only.** The models reject malformed values. They do
   NOT verify cross-record existence (foreign-key presence), filesystem
   presence, or license eligibility — those are dataset-level checks run
   separately in a later chunk.
2. **Missing ≠ negative.** An empty `domain_tags` list with
   `annotation_status.domain_tags = NOT_STARTED` means *no annotation yet*,
   NOT *no tags apply*. Only `annotation_status.<task> = VERIFIED` makes a
   record eligible as ground truth; `DRAFT`, `PENDING`, `REJECTED`, and
   `CONFLICTED` must not be silently promoted.
3. **Classification vs. extraction.** `primary_type` is the one multi-class
   target. `domain_tags` is the multi-label target. `level`, `outcome`,
   `event_name`, `organization`, `achievement_date`, `rank`, `skills` are
   extraction outputs — they are never classification labels and must not
   be auto-added to any taxonomy.
4. **Taxonomy stays a draft.** `LabelTaxonomy.status` defaults to `draft`.
   This chunk ships the model only; no finalized taxonomy YAML is
   produced here.
5. **Privacy.** `annotator`, `original_filename`, `extracted_text_inline`
   can carry personal data. Ingestion and OCR code (future chunks) must
   not log these fields indiscriminately. The pseudonym → identity
   mapping is NOT stored in this repository.

## Identifiers

| Entity | Pattern | Example |
|---|---|---|
| Achievement | `ach_<32 lowercase hex>` | `ach_6d4a…b1f` (UUID4 hex) |
| Evidence | `evd_<32 lowercase hex>` | `evd_…` |
| Annotation | `ann_<32 lowercase hex>` | `ann_…` |
| SourceRegistry | `src_<32 lowercase hex>` | `src_…` |
| LabelTaxonomy | `lbl_<snake_case 2-60 chars>` | `lbl_hackathon`, `lbl_domain_ai` |

Use `make_id("ach"|"evd"|"ann"|"src")` to generate record IDs.
Label IDs are hand-written and stable; renaming uses `supersedes`.

## Missing-value conventions

- Scalar fields that may be absent are typed `Optional[...]` with default
  `None`. Reading `None` means *unknown*, not *empty*.
- List fields default to `[]`. For `domain_tags` and `skills`, `[]` plus
  `annotation_status.<task> = NOT_STARTED` means *not annotated yet*; the
  same `[]` with status `VERIFIED` means *reviewer confirmed none apply*.
- `annotation_status` tracks each task independently, so missing/draft on
  one task does not propagate to the other.

## Entity summaries

### `Achievement`
- IDs: `achievement_id` (ach_), `source_id` (src_), `evidence_id?` (evd_).
- Text: `achievement_text` (1–4000 chars).
- Classification targets: `primary_type?` (label_id), `domain_tags` (list of label_ids, no dupes).
- Extraction fields: `level?`, `outcome?`, `event_name?`, `organization?`, `achievement_date?`, `rank?` (≥1), `skills` (list).
- `annotation_status`: `AnnotationStatusMap` with independent status per task; `NOT_STARTED` on a task blocks that task's target field from being non-empty.
- `is_synthetic: bool` (default `False`).

### `Evidence`
- `evidence_id` (evd_), `linked_achievement_id?` (ach_).
- `relative_path`: must start with `hybrid_dataset/raw/evidence_documents/`; no absolute paths, no `..`, no backslashes.
- `original_filename?`: basename only; no path separators.
- `file_type`: `DocumentFileType`.
- `extraction_method`: `ExtractionMethod` (default `NONE_YET`).
- `extracted_text_ref?` (under `hybrid_dataset/processed/`) XOR `extracted_text_inline?` (≤2000 chars). Mutually exclusive.
- `ocr_confidence?`: only allowed when `extraction_method ∈ {OCR_TESSERACT, OCR_OTHER}`; range `[0.0, 1.0]`.
- `review_status`: `ReviewStatus`.

### `Annotation`
- `annotation_id` (ann_), `achievement_id` (ach_).
- `task`: `AnnotationTask` (`primary_type` / `domain_tags` / `extraction_review`).
- `label_ids` arity by task:
  - `primary_type`: exactly 1.
  - `domain_tags`: 0..N.
  - `extraction_review`: must be `[]` (it has no labels).
- `annotator`: pseudonym regex `^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$`; emails rejected.
- `review_status`: `AnnotationStatus` minus `NOT_STARTED` (an existing row is at least `DRAFT`).
- `created_at`: timezone-aware UTC datetime, auto-filled on construction.

### `SourceRegistry`
- `source_id` (src_), `source_name`, `source_url?` (http/https only), `license` (free text; `UNKNOWN` allowed but implies no permission).
- `collection_date` (≤ today + 1 day), `original_labels` (verbatim), `intended_use` (free text in Chunk 2, promoted to enum later), `mapping_notes?`.
- `review_status`: `ReviewStatus`.

### `LabelTaxonomy`
- `label_id` (`lbl_…`), `task_name` (`TaxonomyTask`, strict subset of annotation tasks).
- `display_name`, `definition`, `inclusion_rules`, `exclusion_rules`, `examples`.
- `status`: `TaxonomyStatus` (default `DRAFT`).
- `supersedes?`: previous `label_id` this one replaces.

## Status enums

- `AnnotationStatus` (task-level): `not_started | draft | pending | verified | rejected | conflicted`.
- `ReviewStatus` (artifact-level): `unreviewed | in_review | verified | rejected`.
- `TaxonomyStatus`: `draft | under_review | approved | deprecated`.

## JSON serialization

Every model supports `model.model_dump_json()` / `Model.model_validate_json(...)`.
Round-trip is lossless and is covered by `tests/schema/test_roundtrip.py`.

## Safe ingestion for `SourceRegistry.source_url`

**Rule:** When any field of a `SourceRegistry` record (particularly
`source_url`) originates outside this repository — parsed YAML / JSON,
downloaded manifest, user form input, API response — construct the
record through the **safe ingestion boundary**:

```python
from nlp_semantic.schema import SourceRegistry

SourceRegistry.from_untrusted(data)   # safe path for untrusted input
```

### Why the boundary exists

A credential-bearing URL (`https://user:pass@host/…`) must be rejected.
The field validator inside `SourceRegistry` does reject such URLs on
the direct constructor path too, but Pydantic captures the raw input
value in `ValidationError.errors()[*]["input"]` and in
`ValidationError.json()`. The model-level flag
`hide_input_in_errors=True` only redacts the input from `str()` and
`repr()`; it does **not** affect the structured error list or JSON
form. Any logger or framework reading `.errors()` or `.json()` would
therefore see the raw URL — including the credentials.

`SourceRegistry.from_untrusted` scans `data["source_url"]` for an
embedded `user:password@` component **before** Pydantic sees the value,
and raises `CredentialInUrlError("source_url")`. That exception:

- Has a fixed message that does not include the URL, username, or
  password.
- Carries only the field name (`exc.field == "source_url"`), no `input`
  attribute.
- Is a subclass of `ValueError`, so handlers catching `ValueError` still
  see it without widening their catch.
- Suppresses implicit exception chaining (`from None`) so no inner
  exception context carries URL fragments.
- Clears local references to the raw URL before raising, so a
  frame-walking logger cannot find them in locals.

Credential-bearing URLs are **rejected**, not silently sanitized. The
caller must strip credentials themselves before registering the source.

### Documented limitation

Constructing `SourceRegistry` directly with untrusted input —
`SourceRegistry(**data)` or `SourceRegistry.model_validate(data)` —
is **not** safe when `data["source_url"]` is untrusted. The field
validator rejects the URL, but Pydantic's `ValidationError.errors()`
and `ValidationError.json()` still carry the raw URL under the
`"input"` key. `hide_input_in_errors=True` does not cover these paths.
Reserve the direct constructor for inputs that originated inside this
repository.

The test suite includes
`test_direct_constructor_leak_in_structured_errors_is_documented_limitation`
which asserts the leak is still present on the direct path; if that
test ever starts failing, the limitation has been closed upstream and
this note should be retired.

## Taxonomy

The actual label content lives under `hybrid_dataset/labels/`:

| File | Task | Count | Status |
|---|---|---|---|
| `primary_taxonomy.yaml` | `primary_type` (multi-class) | 14 | all `draft` |
| `domain_tags.yaml` | `domain_tags` (multi-label) | 10 | all `draft` |

Both files are structured as a YAML list of `LabelTaxonomy` records (one
mapping per entry; unknown fields rejected). The two files are
intentionally kept separate so a reviewer can promote one task's
taxonomy without touching the other.

### Load and validate

```python
from nlp_semantic.schema import load_and_validate_taxonomy

primary = load_and_validate_taxonomy("hybrid_dataset/labels/primary_taxonomy.yaml")
domain  = load_and_validate_taxonomy("hybrid_dataset/labels/domain_tags.yaml")
```

`load_taxonomy(path)` returns the raw entries; `validate_taxonomy(entries)`
enforces file-local invariants:

- All entries share a single `task_name` (one file, one task).
- `label_id` values are unique within the file.
- Every `supersedes` reference points to a `label_id` present in the same file.
- The `supersedes` graph is acyclic.

Per-entry validation (format of `label_id`, `supersedes != label_id`,
enum values, no unknown fields, required `definition`) runs inside
`LabelTaxonomy` itself and surfaces as `pydantic.ValidationError`.
File-level problems surface as `TaxonomyError`.

Cross-record / dataset-wide checks (does a `label_id` referenced from
an `Achievement` actually appear in the taxonomy?) are **not** done
here. They remain a concern for a later dataset-level validator.

### Review workflow — `draft → under_review → approved`

Every taxonomy entry ships with `status: draft`. The intent of each
status:

- `draft` — the maintainer added or edited this entry. **Not** usable
  as ground truth; downstream code must treat records labelled with a
  `draft` label as unverified.
- `under_review` — a reviewer other than the author is actively
  discussing or approving the entry. Still not usable as ground truth.
- `approved` — the team has signed off. Only `approved` entries are
  eligible for use as verified training ground truth. Pair this with
  the `annotation_status` field on an `Achievement` — a record is
  verified ground truth **only** when its `annotation_status.<task>`
  is `VERIFIED` **and** every referenced `label_id` has
  `status == approved`.
- `deprecated` — the entry is retired. New annotations must not
  reference it; historical annotations referencing it stay readable
  because the row is kept with a `supersedes` pointer from the
  replacement entry.

Promoting a label is a one-field YAML edit plus a PR. Deprecating is
the same, plus adding a replacement entry (new `label_id`, same
`task_name`) whose `supersedes` points at the deprecated one.

### Adding or renaming a label

- **Add:** append a new entry to the correct file. Choose a stable
  snake-case `label_id`; stick with `status: draft`; write a definition
  that is specific enough that two annotators would classify an
  identical record the same way; include at least one inclusion rule
  and one exclusion rule, and at least two realistic examples.
- **Rename:** the schema does not allow mutating a `label_id` in place.
  Add a new entry with the new `label_id`, set `supersedes` to the old
  `label_id`, and change the old entry's `status` to `deprecated`.
  Both rows stay committed; the test suite enforces that the
  `supersedes` graph remains acyclic.
- **Delete:** avoid. Deprecate instead (see above) so historical
  annotations stay interpretable.

### Current taxonomy status (Chunk 3)

All 24 entries (14 primary + 10 domain) ship with `status: draft`.
Nothing here is approved. Downstream training code must not treat a
`primary_type` or `domain_tags` value as verified until **both**
conditions hold:

1. The referenced `label_id` has `status == approved` in its
   taxonomy file.
2. The record's `annotation_status.<task>` is `VERIFIED`.

Loader tests ship under `tests/schema/test_loader.py`.

## What this chunk does NOT do

- No cross-record foreign-key existence check between an
  `Achievement`'s `primary_type` / `domain_tags` and the taxonomy
  files. That is a dataset-level concern.
- No filesystem existence check for `relative_path` or
  `extracted_text_ref`.
- No license eligibility decision; `UNKNOWN` passes but is not
  permission.
- No duplicate detection on achievements, no OCR, no ingestion.
- No automatic promotion of taxonomy status; `draft → approved` is a
  human-reviewed PR edit.
