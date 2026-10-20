# `hybrid_dataset/` — data directory layout

This directory holds dataset artifacts, metadata, taxonomies, and
templates for the hybrid dataset pipeline (Member 1 scope). Raw and
generated contents are not committed to Git; the folder structure is
tracked via `.gitkeep` markers so a fresh clone has a predictable layout.

```
hybrid_dataset/
├── raw/           # IMMUTABLE source inputs — NOT tracked in Git
├── processed/     # Generated / cleaned outputs — NOT tracked in Git
├── labels/        # Taxonomies, label definitions, label schemas — TRACKED
├── metadata/      # Source registry, dataset cards, data dictionary — TRACKED
└── notebooks/     # Exploratory analysis notebooks — TRACKED
```

## `raw/` — immutable source inputs

Place downloaded public datasets, manually authored achievement records,
and private evidence documents (PDFs, images) here on your local machine.
These are **ignored by Git** by default. Treat the contents as read-only
after they are placed here; downstream pipelines must write to
`processed/` instead of mutating `raw/`.

Expected eventual sub-structure (created on demand, not in this chunk):

```
raw/
├── public_datasets/      # third-party CSV/JSON datasets with their licences
├── achievement_records/  # our own manually labeled records
└── evidence_documents/   # PDFs, images — private; never committed
```

## `processed/` — generated outputs

Cleaned CSVs, extracted text, embeddings, duplicate-review reports, and
other derived artifacts live here. **Ignored by Git** by default. Everything
in this folder must be reproducible from `raw/` plus code in `src/`.

## `labels/` — taxonomies

Small, version-controlled YAML/JSON files that define the primary
achievement taxonomy, multi-label domain tags, and label validation rules.
These are committed so the team shares a single source of truth. Taxonomy
contents are **not yet implemented** in this chunk.

## `metadata/` — registry, dataset cards, data dictionary

Source registry entries (one per dataset we rely on), dataset cards,
data-dictionary files, and extraction-method logs. OCR output and
embedding files produced here are gitignored; textual metadata files
are tracked.

## `notebooks/` — exploration

Jupyter notebooks for EDA and prototyping. Checkpoints
(`.ipynb_checkpoints`) are gitignored. Keep notebooks lightweight and
non-sensitive; move substantive logic into `src/nlp_semantic/` modules.

## Data safety rules

- **No private student information in Git.** Names, roll numbers, emails,
  phone numbers, scanned IDs, and document images must stay in `raw/`
  locally (or in a secure external store), never committed.
- **No arbitrary downloads.** Every external dataset must be registered
  with URL, licence, collection date, and intended use before use.
- **Synthetic examples only in tests.** Tests must use clearly labelled
  non-sensitive synthetic fixtures.
- **Raw files are immutable.** Mutating `raw/` breaks reproducibility.
