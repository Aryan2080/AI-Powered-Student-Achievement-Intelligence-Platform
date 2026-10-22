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

## `dataset/` — curated records and annotation history (Chunk 5)

Tracked, PR-reviewed curated achievement records and (optional)
annotation history live here. One YAML list file per annotation
batch:

```
dataset/
├── README.md                       (shape, rules, GT eligibility)
├── ANNOTATION_GUIDELINES.md        (rubric + dispute workflow + examples)
├── records/batch_<NN>.yaml         (list of Achievement entries)
└── annotations/batch_<NN>.yaml     (list of Annotation entries, for dual-reviewed records)
```

See `dataset/README.md` for the file format, cross-record validation
rules, and the ground-truth eligibility contract (both
`annotation_status.<task> == VERIFIED` **and** the referenced label's
`status == approved` are required; the current all-draft taxonomies
mean the eligible-GT set is empty by design).

### Dataset CLI

Validate records, print statistics, or generate reproducible
train/val/test splits. The package is not pip-installed, so `src/`
must be on `PYTHONPATH`.

```powershell
# Windows PowerShell
$env:PYTHONPATH = "src"
python -m nlp_semantic.dataset.cli validate hybrid_dataset
python -m nlp_semantic.dataset.cli stats    hybrid_dataset
python -m nlp_semantic.dataset.cli split    hybrid_dataset --seed 42
```

```bash
# bash / zsh / Git Bash
PYTHONPATH=src python -m nlp_semantic.dataset.cli validate hybrid_dataset
PYTHONPATH=src python -m nlp_semantic.dataset.cli stats    hybrid_dataset
PYTHONPATH=src python -m nlp_semantic.dataset.cli split    hybrid_dataset --seed 42
```

All three subcommands print JSON to stdout and a one-line ASCII
summary to stderr. Exit codes: `0` success, `1` dataset/build error,
`2` CLI usage error.

Split output lands under `hybrid_dataset/processed/splits/` (which is
gitignored). The split generator groups records by `source_id` so no
`source_id` ever crosses splits; synthetic records are excluded by
default. Infeasibility (too few source groups, empty split) surfaces
as warnings in the manifest — the generator does **not** silently
claim stratification or leakage prevention it cannot deliver.

## `metadata/` — registry, dataset cards, data dictionary

Source registry entries (one per dataset we rely on), dataset cards,
data-dictionary files, and extraction-method logs. OCR output and
embedding files produced here are gitignored; textual metadata files
are tracked.

Tracked files (Chunk 4):

- `sources.yaml` — tracked YAML list of `SourceRegistry` entries. Ships
  as `[]`; see the file's top-of-file comment block for the schema and
  the "registration ≠ approval" rule.
- `manifest.yaml` — tracked YAML list of `ManifestEntry` records keyed
  off `source_id`, describing where each source's raw files are
  expected to live. Ships as `[]`.

Neither file is approval. `sources.yaml` is a registry of what we have
chosen to track; `manifest.yaml` records expectations about on-disk
layout. Suitability for training is a separate downstream decision
that gates on `review_status: verified` and a human-approved license
determination outside these files.

### Inventory CLI

To see what is actually present under `raw/` on your local machine (no
contents are read, only filesystem metadata), run the inventory as a
module. The package lives under `src/`, so `src/` must be on
`PYTHONPATH` unless the project is installed as a package (not shipped
in Chunk 4). From the project root:

```powershell
# Windows PowerShell
$env:PYTHONPATH = "src"
python -m nlp_semantic.ingestion.inventory hybrid_dataset
```

```cmd
:: Windows cmd.exe
set PYTHONPATH=src
python -m nlp_semantic.ingestion.inventory hybrid_dataset
```

```bash
# bash / zsh (POSIX, Git Bash)
PYTHONPATH=src python -m nlp_semantic.ingestion.inventory hybrid_dataset
```

The command prints a JSON `InventoryReport` to stdout and a one-line
summary to stderr. Exit code is 0 on success, 2 on CLI usage error, 1
on a build failure. Symlinks are never followed; they are reported as
`symlink_skipped` warnings. A scan that emitted warnings is a partial
scan, not a silently-successful one — the stderr summary prints the
warning count so partial scans are always visibly partial.

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
