# AI-Powered Student Achievement Intelligence Platform

> **Status:** Under active development. Dataset pipeline, models, OCR, and
> deployment components are **not** complete; this repository currently
> contains only the project scaffold.

A university supervised-learning project that aims to convert student
achievement records and supporting evidence documents into structured,
analyzable data so a classifier, categorizer, and recommender can operate on
them.

## Project description

The platform intends to ingest heterogeneous student achievement evidence
(certificates, letters, project write-ups, publications, etc.), extract
structured fields and skills, categorize achievements, and surface
personalised opportunity recommendations. The system is intentionally split
into independent layers so three team members can work in parallel.

## Five-layer system overview

| # | Layer | Member | Purpose |
|---|-------|--------|---------|
| 1 | Data & evidence ingestion | 1 | Collect raw records, OCR, text extraction |
| 2 | NLP & semantic intelligence | 1 | Information extraction, embeddings, duplicate detection |
| 3 | ML & transformer classification | 2 | Supervised classification, multi-label categorization |
| 4 | Recommendation intelligence | 3 | Semantic matching between students and opportunities |
| 5 | Backend, dashboard & deployment | 3 | FastAPI, Streamlit, database, hosting |

## Member 1 — NLP & Semantic Intelligence (this scope)

Responsibility: dataset construction, OCR, text extraction, information
extraction, skill extraction and normalization, sentence-transformer
embeddings, and duplicate detection. Implementation lands in
`src/nlp_semantic/` and dataset artifacts in `hybrid_dataset/`.

Nothing in this repository is production-ready yet. Members 2 and 3 will
add their packages (`src/ml/`, `src/recommender/`, `src/backend/`) in
parallel.

## Repository structure

```
.
├── README.md
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── AI_Powered_Student_Achievement_Intelligence_Project_Development_Document.docx
├── hybrid_dataset/        # dataset artifacts, metadata, templates, docs
│   ├── README.md
│   ├── raw/               # (gitignored) raw public datasets + private evidence
│   ├── processed/         # (gitignored) generated / cleaned outputs
│   ├── labels/            # taxonomies and label definitions (tracked)
│   ├── metadata/          # source registry, dataset cards, data dictionary
│   └── notebooks/         # exploratory analysis
├── src/
│   └── nlp_semantic/      # Member 1 code (this scope)
└── tests/                 # automated tests
```

Space is deliberately reserved for `src/ml/` (Member 2),
`src/recommender/` and `src/backend/` (Member 3). This chunk does **not**
create placeholder implementations for those modules.

## Prerequisites

- **Python 3.10 or newer.** Developed against 3.10+; 3.13 also works.
- Git.

## Setup

```bash
# clone, then from the repo root:
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

The current `requirements.txt` is intentionally minimal (pandas, pydantic,
pytest, pyyaml). OCR, PyMuPDF, sentence-transformers, transformers, and
deep-learning dependencies will be added in later chunks after review.

## Running tests

```bash
pytest
```

A smoke test under `tests/` confirms the `nlp_semantic` package imports and
pytest discovers tests. More tests will be added as schema, taxonomy,
ingestion, and OCR modules are implemented.

## Dataset privacy and licensing principles

- Raw public datasets and private student evidence documents must **not** be
  committed to Git. The `.gitignore` enforces this by default; keep raw
  inputs under `hybrid_dataset/raw/` locally.
- Every dataset we rely on must be registered in `hybrid_dataset/metadata/`
  with its source URL, licence, collection date, and intended use.
- No student personal information (names, roll numbers, emails, phone
  numbers, document images) is to be committed. Tests use only synthetic,
  clearly marked, non-sensitive examples.
- No credentials, API keys, or `.env` files are committed.
- Public datasets are used only for tasks their original labels actually
  support; original labels and provenance are preserved rather than
  silently remapped.

## Development status

This scaffold is the foundation for an incrementally built pipeline. The
dataset construction, OCR, embedding, and duplicate-detection modules will
be added in named follow-up chunks. Do not treat any file here as evidence
that a dataset, trained model, or deployed platform already exists.
