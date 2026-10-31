# PROJECT_HANDOFF — AI-Powered Student Achievement Intelligence Platform

> **Purpose:** hand this project off from the current cloud Claude Code
> session to Claude Code running in VS Code on the owner's local Windows
> machine. Everything below is drawn from the verified repository state
> and this session's conversation. Items marked **PROPOSED** or
> **OPEN** are not yet decided — they are flagged so a new session does
> not confuse them with facts.

## 0. How to read this document

- **VERIFIED** — observed in the repo, exerciser, or pytest output in
  this session; or quoted from the owner's explicit instructions.
- **PROPOSED** — a plan drafted here and not yet approved.
- **OPEN** — an unresolved question for the owner.

The owner is Member 1 (NLP & Semantic Intelligence). Members 2 and 3
have **not** started their modules yet; branches exist on origin but
hold no of their work.

---

## 1. Project objective, requirements, deliverables, constraints

### VERIFIED — Objective

An AI-Powered Student Achievement Intelligence Platform (university
supervised-learning project). The platform ingests heterogeneous
student achievement evidence (certificates, letters, publications,
project write-ups), extracts structured fields and skills, classifies
achievements, categorises them with multi-label tags, and surfaces
personalised opportunity recommendations.

The owner's project development document
(`AI_Powered_Student_Achievement_Intelligence_Project_Development_Document.docx`,
tracked at the repo root) is the authoritative scope reference and is
untouched by this session.

### VERIFIED — Core requirements supplied by the owner

- Reproducible **hybrid dataset** pipeline combining:
  1. Public datasets with documented fields.
  2. Our own manually labelled achievement records.
  3. PDF and image evidence documents.
  4. A skills reference (such as ESCO).
- Do **not** assume public resume / placement / education datasets
  carry achievement labels. Preserve their original labels and
  provenance; use them only for tasks their contents support.
- Keep raw files immutable; generated outputs separate from source
  files.
- No large datasets, private evidence, credentials, or sensitive
  student data in Git.
- Separate prediction tasks:
  - Task A — multi-class classification using `primary_type` (one
    primary class per labelled record).
  - Task B — multi-label categorisation using a separately documented
    `domain_tags` taxonomy.
- Information-extraction fields (`event_name`, `organization`,
  `achievement_date`, `rank`, `skills`, etc.) are not classification
  labels.
- Missing multi-label annotations must not be treated as negative
  labels; draft or unreviewed annotations must not silently become
  verified ground truth.

### VERIFIED — Expected deliverables (Member 1 scope)

Dataset construction, OCR, text extraction, information extraction,
skill extraction and normalisation, sentence-transformer embeddings,
duplicate detection. Member 1 code lives under
`src/nlp_semantic/`; dataset artefacts live under `hybrid_dataset/`.

### VERIFIED — Evaluation and process constraints (recurring from
every chunk brief)

- Pydantic v2, Python 3.10+ target.
- Modular, maintainable scaffolding; no premature abstractions.
- No OCR, PyMuPDF, pytesseract, sentence-transformers, transformers,
  or other heavy dependencies without explicit approval.
- Do not commit or push without explicit approval.
- Do not use `git add .` or `git add -A`.
- Do not modify teammate modules.
- Do not fabricate dataset sources, counts, licences, or model
  metrics.
- Report unexecutable checks accurately; do not claim pytest passed if
  it was not run.

---

## 2. System architecture and technology stack

### VERIFIED — Five-layer architecture

| # | Layer | Owner | Purpose |
|---|---|---|---|
| 1 | Data & evidence ingestion | Member 1 | Collect raw records, OCR, text extraction |
| 2 | NLP & semantic intelligence | Member 1 | Information extraction, embeddings, duplicate detection |
| 3 | ML & transformer classification | Member 2 | Supervised classification, multi-label categorisation |
| 4 | Recommendation intelligence | Member 3 | Semantic matching between students and opportunities |
| 5 | Backend, dashboard & deployment | Member 3 | FastAPI, Streamlit, database, hosting |

### VERIFIED — Technology stack

- **Language:** Python 3.10+ (tested under 3.13.16 and 3.13 in the
  cloud container).
- **Data contract:** Pydantic v2 (`>=2,<3`), currently resolving to
  2.14.1 inside the project venv.
- **Testing:** pytest 9.1.1 with configuration in `pyproject.toml`.
- **Config/YAML:** `pyyaml` 6.0.3 for taxonomy files.
- **Tabular / notebooks (declared, barely used so far):** `pandas`.
- **No OCR / transformer / embedding deps** in `requirements.txt` yet.
- VS Code is the owner's editor; development is Windows-local going
  forward.

---

## 3. Team structure, ownership, and integration boundaries

### VERIFIED — Team

Three-member team. The owner of this handoff is **Member 1**.

### VERIFIED — Branches on origin

| Branch | Owner | Current tip |
|---|---|---|
| `main` | shared | `e4a7f42` (project doc commit) |
| `feature/nlp-semantic` | Member 1 | `93a83ef` (Chunk 3) |
| `feature/ml-classification` | Member 2 | `e4a7f42` (empty from Member 2's perspective) |
| `feature/recommendation-platform` | Member 3 | `e4a7f42` (empty from Member 3's perspective) |

### VERIFIED — Module ownership

| Path | Owner | Status |
|---|---|---|
| `src/nlp_semantic/` | Member 1 | partially implemented (schema, loader) |
| `src/ml/` | Member 2 | **not created**; do not touch |
| `src/recommender/` | Member 3 | **not created**; do not touch |
| `src/backend/` | Member 3 | **not created**; do not touch |

Integration points (contract) between members:

- Member 1 ↔ Member 2: Member 2 consumes `Achievement`, `Annotation`,
  and the two taxonomy YAMLs. Only records where
  `annotation_status.<task> == VERIFIED` **and** every referenced
  `label_id` has `status == approved` are eligible as training ground
  truth. Nothing is `approved` yet (see §7).
- Member 1 ↔ Member 3: Member 3 consumes the full `Achievement`
  record (with skills) and matches against an opportunity corpus
  (Member 3 is responsible for that corpus).
- No cross-record FK existence checks are performed in Chunks 1–3.
  Member 2 and Member 3 may rely on Pydantic format validation for
  `label_id` and record IDs but must enforce existence against the
  taxonomy and dataset themselves until the dataset validator (a
  later Chunk) is built.

---

## 4. Completed work: Chunks 1, 2, 3

### VERIFIED — Chunk 1: foundations (`chore: scaffold hybrid dataset pipeline`, commit `1fbd8ad`)

- Fixed malformed `.gitignore` (now 94 lines, properly newline-separated).
  No blanket `*.csv/*.yaml/*.json/*.pdf/*.png/*.jpg` globs. Raw and
  processed dataset trees ignored except `.gitkeep` structural markers.
- Replaced one-line placeholder `README.md` with full project README
  (purpose, five-layer overview, Member 1 scope, repo structure,
  Python 3.10+ setup, test instructions, privacy and licensing
  principles, development-status disclaimer).
- Added minimal `requirements.txt` (`pandas`, `pydantic>=2,<3`,
  `pytest`, `pyyaml`).
- Added minimal `pyproject.toml` with:
  ```toml
  [tool.pytest.ini_options]
  minversion = "7.0"
  testpaths = ["tests"]
  pythonpath = ["src"]
  ```
- Created `src/nlp_semantic/__init__.py` package marker with
  `__version__ = "0.0.1"`.
- Created `hybrid_dataset/` tree with
  `raw/`, `processed/`, `labels/`, `metadata/`, `notebooks/`
  subdirectories (each with a `.gitkeep`) and a top-level
  `hybrid_dataset/README.md` documenting the layout and data-safety
  rules.
- Added `tests/test_smoke.py` (3 tests: pytest wires, package imports,
  version is a non-empty string).
- Attribution rule: every commit on this branch ends with
  `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_011aQNPPYmmpZ1uDvJb9yH8o`.

### VERIFIED — Chunk 2: data contract (`feat: add achievement data contract schemas`, commit `d603b82`)

Pydantic v2 schema package at `src/nlp_semantic/schema/` with the
following models and enums:

- **Enums** (`enums.py`):
  `AnnotationStatus` (`not_started|draft|pending|verified|rejected|conflicted`),
  `ReviewStatus` (`unreviewed|in_review|verified|rejected`),
  `AnnotationTask` (`primary_type|domain_tags|extraction_review`),
  `TaxonomyTask` (`primary_type|domain_tags`),
  `TaxonomyStatus` (`draft|under_review|approved|deprecated`),
  `DocumentFileType` (`pdf|image_jpg|image_png|image_tiff|text|other`),
  `ExtractionMethod` (`digital_text|ocr_tesseract|ocr_other|none_yet`).
  All subclass `(str, Enum)` for JSON-friendly serialization and
  Python 3.10 compatibility (`enum.StrEnum` is 3.11+).
- **Identifiers** (`identifiers.py`):
  Record IDs are `<prefix>_<32 lowercase hex>` (`ach_`, `evd_`, `ann_`,
  `src_`). Label IDs are `lbl_<snake_case>` (regex
  `^lbl_[a-z0-9][a-z0-9_]{1,59}$`). Helpers: `make_id`,
  `validate_prefixed_id`, `validate_label_id`.
- **Achievement + AnnotationStatusMap** (`achievement.py`):
  All fields documented; `primary_type` and `domain_tags` carry label
  IDs; a model-level consistency rule rejects populated label values
  when the matching `annotation_status.<task>` is `NOT_STARTED`.
  `str_strip_whitespace=True`, `extra="forbid"`, `validate_assignment=True`.
- **Evidence** (`evidence.py`):
  Path safety enforced (`relative_path` must start with
  `hybrid_dataset/raw/evidence_documents/`, no `..`, no backslash, no
  absolute paths, no empty segments; `extracted_text_ref` same shape
  but under `hybrid_dataset/processed/`). `extracted_text_inline`
  (≤2000 chars) and `extracted_text_ref` are mutually exclusive.
  `ocr_confidence` is a `float` in `[0.0, 1.0]` and is allowed only
  when `extraction_method ∈ {ocr_tesseract, ocr_other}`.
- **Annotation** (`annotation.py`):
  Per-task label-arity: `primary_type` exactly 1 label, `domain_tags`
  0..N, `extraction_review` 0. Annotator must be a pseudonym (regex
  `^[A-Za-z0-9_][A-Za-z0-9_\-]{1,63}$`); email-like strings are
  rejected explicitly. `created_at` is **timezone-aware required**
  (naive `datetime` rejected). `review_status == NOT_STARTED` is
  forbidden on an actual annotation row.
- **SourceRegistry + CredentialInUrlError + from_untrusted boundary**
  (`source_registry.py`):
  `source_url` must be http/https with a hostname; a URL that carries
  embedded credentials is rejected. For untrusted input the recommended
  path is `SourceRegistry.from_untrusted(data)` which raises
  `CredentialInUrlError("source_url")` **before** the raw URL reaches
  Pydantic. Fixed-message exception, no `errors()` payload, no
  implicit chaining (`from None`), clears locals before raise.
  `hide_input_in_errors=True` is on, documented as covering only
  `str()`/`repr()` and NOT `errors()`/`json()`. The direct-constructor
  path still leaks the raw URL in `.errors()[*]["input"]`; this is a
  documented residual limitation of Pydantic v2 and is anchored by
  `test_direct_constructor_leak_in_structured_errors_is_documented_limitation`,
  which fails if the leak ever disappears so the README note gets
  retired on purpose.
- **LabelTaxonomy** (`label_taxonomy.py`):
  `task_name` restricted to `TaxonomyTask` (strict subset of annotation
  tasks). `supersedes` must be a well-formed `lbl_...` ID; a
  `@model_validator` rejects self-supersession
  (`supersedes == label_id`).

Chunk 2 implementation and tests landed in a single commit with 16
files (9 schema modules + README + 7 tests). A privacy blocker was
caught in review (a draft used the owner's real email as a bad-value
test case); it was replaced with `test.user@example.org` before
commit.

### VERIFIED — Chunk 3: draft taxonomies + loader (`feat: ship draft primary and domain taxonomies with YAML loader`, commit `93a83ef`)

- `hybrid_dataset/labels/primary_taxonomy.yaml`: 14 primary-type
  entries, all `status: draft`. Label IDs: `lbl_hackathon`,
  `lbl_competition`, `lbl_research_pub`, `lbl_patent`, `lbl_internship`,
  `lbl_certification`, `lbl_project`, `lbl_workshop`, `lbl_conference`,
  `lbl_leadership`, `lbl_sports`, `lbl_cultural`, `lbl_volunteering`,
  `lbl_other`. Each entry has `display_name`, `definition`,
  `inclusion_rules`, `exclusion_rules`, `examples`.
- `hybrid_dataset/labels/domain_tags.yaml`: 10 domain-tag entries,
  all `status: draft`. Label IDs: `lbl_domain_ai`, `lbl_domain_ml`,
  `lbl_domain_nlp`, `lbl_domain_cv`, `lbl_domain_security`,
  `lbl_domain_systems`, `lbl_domain_web`, `lbl_domain_data`,
  `lbl_domain_hardware`, `lbl_domain_other`.
- `src/nlp_semantic/schema/loader.py`: `load_taxonomy(path)` reads a
  YAML list and validates each entry through `LabelTaxonomy`;
  `validate_taxonomy(entries)` enforces file-local invariants (single
  task, unique IDs, `supersedes` references point into the same
  file, acyclic `supersedes` graph); `load_and_validate_taxonomy`
  convenience; `TaxonomyError(ValueError)` for file-level problems
  (per-entry failures surface as `pydantic.ValidationError`).
- `src/nlp_semantic/schema/__init__.py`: public API now re-exports
  `load_taxonomy`, `validate_taxonomy`, `load_and_validate_taxonomy`,
  `TaxonomyError`.
- `src/nlp_semantic/schema/README.md`: added `## Taxonomy` section
  covering loader API, review workflow
  (`draft → under_review → approved`), rules for adding, renaming
  (via `supersedes`), and deprecating labels, and the current
  `draft`-only state of every label.
- `tests/schema/test_loader.py`: 25 tests (shipped-file loads,
  empty / null YAML, non-list top level, non-mapping entry, unknown
  field, bad `label_id`, duplicate ID, mixed task, missing
  `supersedes` reference, 2-cycle, 3-cycle, linear chain allowed,
  convenience).

### VERIFIED — Key cross-chunk design decisions

- **Record IDs are full UUID4 hex (32 chars)**, prefix-tagged. Reviewers
  prefer prefixed IDs over bare UUID.
- **Label IDs are human-readable snake-case**, stable; renames go
  through `supersedes` and keep the old row.
- **FK existence checks are deferred** to a future dataset-level
  validator. Pydantic validates only format.
- **`UNKNOWN` licence allowed, grants no permission.** Downstream
  dataset validator makes eligibility calls.
- **Pseudonym contract for annotators**; the mapping from pseudonym to
  real identity must not be stored in this repo.
- **Timezone-aware `created_at`** required for `Annotation`.
- **Hybrid `extracted_text_ref` XOR `extracted_text_inline`** on
  Evidence; inline capped at 2 kB.
- **Taxonomy stays `draft`.** Nothing is approved. Ground truth
  requires both `annotation_status.<task> == VERIFIED` AND the
  referenced label's `status == approved`.
- **No `git add .`**, no silent sanitisation (credential URLs are
  rejected, not stripped), no cross-record checks inside Pydantic.

---

## 5. Repository state

### VERIFIED — Remote

- URL: `https://github.com/Aryan2080/AI-Powered-Student-Achievement-Intelligence-Platform`
- Active branch: `feature/nlp-semantic`
- Tip commit: `93a83efc62930afbfc1a96c51199f3ca6a115a1a`
- Commit history on this branch (newest first):
  ```
  93a83ef feat: ship draft primary and domain taxonomies with YAML loader
  d603b82 feat: add achievement data contract schemas
  1fbd8ad chore: scaffold hybrid dataset pipeline
  e4a7f42 Add project development document
  dbcfd06 Initial commit: set up project repository
  ```

### VERIFIED — Local (cloud container) vs remote

At the time this document was written, the cloud container's local
HEAD matches `origin/feature/nlp-semantic` at `93a83ef`. The only
uncommitted change at this moment is **this handoff file**
(`PROJECT_HANDOFF.md`).

### Owner's Windows clone — handoff instructions

```powershell
# in C:\Users\Balaji\OneDrive\Desktop\SUPERVISED PROJECT\AI-Powered-Student-Achievement-Intelligence-Platform
git fetch origin
git checkout feature/nlp-semantic                    # if not already on it
git pull --ff-only origin feature/nlp-semantic
```

After `git pull`, the Windows clone should hold the same three Member-1
commits (`1fbd8ad`, `d603b82`, `93a83ef`). This document (`PROJECT_HANDOFF.md`)
is intentionally **not** pushed yet — a new Claude Code session should
review it on the Windows clone before deciding whether to commit it to
the repo.

---

## 6. File structure and roles

### VERIFIED — Tree (files only; `.git/`, `.venv/`, `__pycache__/`
excluded)

```
AI-Powered-Student-Achievement-Intelligence-Platform/
├── .gitignore
├── AI_Powered_Student_Achievement_Intelligence_Project_Development_Document.docx
├── PROJECT_HANDOFF.md                                 ← this file (NEW, uncommitted)
├── README.md
├── pyproject.toml
├── requirements.txt
├── hybrid_dataset/
│   ├── README.md
│   ├── labels/
│   │   ├── .gitkeep
│   │   ├── domain_tags.yaml                           ← 10 draft tags
│   │   └── primary_taxonomy.yaml                      ← 14 draft classes
│   ├── metadata/.gitkeep
│   ├── notebooks/.gitkeep
│   ├── processed/.gitkeep
│   └── raw/.gitkeep                                   ← raw contents gitignored
├── src/nlp_semantic/
│   ├── __init__.py
│   └── schema/
│       ├── README.md
│       ├── __init__.py                                ← public API
│       ├── achievement.py
│       ├── annotation.py
│       ├── enums.py
│       ├── evidence.py
│       ├── identifiers.py
│       ├── label_taxonomy.py
│       ├── loader.py
│       └── source_registry.py
└── tests/
    ├── test_smoke.py
    └── schema/
        ├── test_achievement.py
        ├── test_annotation.py
        ├── test_evidence.py
        ├── test_identifiers.py
        ├── test_label_taxonomy.py
        ├── test_loader.py
        ├── test_roundtrip.py
        └── test_source_registry.py
```

### VERIFIED — Role of each important file

- `README.md` — project README; the authoritative short description.
  Mentions status, setup, test, data-safety principles.
- `pyproject.toml` — pytest configuration only (no build backend yet).
  `testpaths = ["tests"]`, `pythonpath = ["src"]`, `minversion = "7.0"`.
- `requirements.txt` — minimum deps. **No OCR / transformer / embedding
  deps.**
- `.gitignore` — path-scoped ignores for `hybrid_dataset/raw/*`,
  `hybrid_dataset/processed/*`, `hybrid_dataset/metadata/ocr_output/`,
  `hybrid_dataset/metadata/embeddings/`, plus Python / env / editor
  / cache / model artefact globs. Keeps schema, taxonomy YAML, and
  small test fixtures trackable.
- `hybrid_dataset/README.md` — layout and data-safety rules for the
  dataset tree.
- `hybrid_dataset/labels/primary_taxonomy.yaml` and `domain_tags.yaml`
  — see §4 Chunk 3.
- `src/nlp_semantic/schema/README.md` — data dictionary, missing-value
  conventions, safe-ingestion rule for SourceRegistry, taxonomy
  review workflow, residual limitations.
- `src/nlp_semantic/schema/__init__.py` — public API surface. Member 2
  / Member 3 import from `nlp_semantic.schema`.
- `tests/test_smoke.py` + `tests/schema/*` — pytest suite; 210 tests
  as of commit `93a83ef`.

---

## 7. Dataset strategy, taxonomy, privacy

### VERIFIED — Dataset strategy

- Hybrid approach: public datasets (with licences and provenance)
  + manually labelled own records + PDF/image evidence + a skills
  reference such as ESCO.
- Public datasets are used only for tasks their original labels
  actually support; original labels and provenance are preserved
  verbatim in `SourceRegistry.original_labels`.
- Dataset artefacts live in `hybrid_dataset/`; raw inputs stay out of
  Git by default.

### VERIFIED — Provenance and licensing

- Every source we rely on must be registered via a `SourceRegistry`
  entry with `source_url`, `license`, `collection_date`,
  `original_labels`, `intended_use`, and `review_status`.
- `UNKNOWN` licence is accepted by the schema but conveys no permission
  to train, redistribute, or publish; eligibility is a dataset-level
  decision.
- No source registry entries exist yet. Chunk 4 (PROPOSED) adds the
  first manifest.

### VERIFIED — Privacy

- No raw student records in Git.
- No credentials, API keys, `.env` files in Git.
- Annotator identifiers are pseudonyms; the mapping to real identities
  is not stored in the repo.
- URL credentials captured in `SourceRegistry.source_url` are rejected
  by the schema; the safe `SourceRegistry.from_untrusted` factory
  prevents the raw URL from reaching Pydantic error representations.
- The owner's own email (`<redacted>@…`) was removed from a draft
  test parameter before Chunk 2 was committed; the Chunk 2 commit
  does not contain it. The handoff file explicitly does not restate
  the raw email either.

### VERIFIED — Taxonomy

- 14 primary types + 10 domain tags shipped in Chunk 3, all
  `status: draft`.
- Promotion workflow: `draft → under_review → approved` (human-reviewed
  PR edits). `approved` is required for use as training ground truth.
- Renames go through `supersedes`; both rows kept. The loader rejects
  self-supersession, cycles, and references outside the file.

### VERIFIED — Annotation workflow decisions

- `primary_type` and `domain_tags` statuses are tracked independently
  via `Achievement.annotation_status`.
- `[]` + `NOT_STARTED` = unannotated; `[]` + `VERIFIED` = reviewed,
  no tags apply.
- `conflicted` is a valid annotation review status.
- An `Annotation` record itself cannot be `NOT_STARTED` (absence is
  modelled by having no row).

---

## 8. Testing, verified results, limitations, risks

### VERIFIED — Testing setup

- Tests under `tests/`, discovered by pytest via `pyproject.toml`.
- Package import path handled by `pythonpath = ["src"]`.
- Developers run `pytest` from the repo root inside a project venv.

### VERIFIED — Latest test results

Under the cloud container's `.venv/` (gitignored):

```
tool             version
pytest           9.1.1
pydantic         2.14.1
pandas           3.0.6
pyyaml           6.0.3
Python           3.13.16

============================= 210 passed in 0.44s ==============================
```

Breakdown (from the pytest trace, verified at commit `93a83ef`):
`tests/test_smoke.py` 3, `tests/schema/test_identifiers.py` 32,
`tests/schema/test_achievement.py` 23, `tests/schema/test_evidence.py` 25,
`tests/schema/test_annotation.py` 32, `tests/schema/test_source_registry.py` 36,
`tests/schema/test_label_taxonomy.py` 20, `tests/schema/test_roundtrip.py` 5,
`tests/schema/test_loader.py` 25 — total **210**.

### VERIFIED — Known limitations

- **Direct-construction credential leak in Pydantic errors.**
  `SourceRegistry(**data)` with a credential-bearing URL raises
  `pydantic.ValidationError` whose `.errors()[*]["input"]` and
  `.json()` carry the raw URL. `hide_input_in_errors=True` hides it
  from `str()`/`repr()` only. Documented in `src/nlp_semantic/schema/README.md`;
  mitigated by requiring `SourceRegistry.from_untrusted(data)` for
  untrusted input. Anchored by a test (named with
  "documented_limitation") that fails if the gap ever closes so the
  warning gets retired.
- **No cross-record FK existence check.** A referenced `label_id`,
  `source_id`, or `evidence_id` may be well-formed but non-existent;
  this is a dataset-validator concern (Chunk 5 or later).
- **No filesystem existence check** for `Evidence.relative_path` or
  `extracted_text_ref`.
- **No OCR, no embeddings, no ingestion** yet.
- **Taxonomy is `draft`.** No labels are approved for training.
- **URL hygiene gaps** on `source_url` (non-ASCII hosts, control
  characters in path, very long URLs are not rejected). Non-blocking
  for Chunk 2 scope; flag for later if the dataset reveals them.

### VERIFIED — Outstanding risks

- **Member 2 and Member 3 modules do not exist yet.** Integration can
  only be rehearsed once at least `src/ml/` is scaffolded.
- **Dataset content not collected.** No public datasets have been
  registered or inspected.
- **No annotation of own records.** No real-world examples have been
  annotated under the schema.
- **No evidence-pipeline tooling.** PyMuPDF and OCR deps are not
  installed.
- **One tech-debt note** — `.venv/` was created in the cloud container
  to run pytest; it is gitignored and does not land on origin. The
  Windows clone will need its own venv.

---

## 9. Decisions made, items deferred, pitfalls

### VERIFIED — Decisions already made (do not re-litigate)

- Pydantic v2, Python 3.10+.
- Package layout: `src/nlp_semantic/`, `tests/`, `hybrid_dataset/`.
- Full UUID4-hex record IDs; human-readable `lbl_` IDs.
- Modular schema package (one file per entity).
- All taxonomy labels start `draft`; promotion is a human PR edit.
- `UNKNOWN` licence allowed; grants no permission.
- Pseudonym contract for annotators; emails rejected.
- Timezone-aware `created_at`.
- `extracted_text_ref` XOR `extracted_text_inline` (≤2 kB inline).
- `SourceRegistry.from_untrusted` is the safe boundary for untrusted
  URLs.
- Taxonomy loader validates file-local invariants only.
- Six-file Chunk 3 structure (two YAMLs, loader, loader tests,
  `__init__.py` re-export, README update).

### VERIFIED — Explicitly deferred

- OCR, PyMuPDF, pytesseract, sentence-transformers, transformers,
  deep-learning deps.
- Cross-record / dataset-wide validator.
- Filesystem existence checks for evidence paths.
- License eligibility promotion (`UNKNOWN` cannot become permission).
- Finalised taxonomy (`approved` status).
- Teammate modules.
- Annotator-identity-mapping storage (never in this repo).

### VERIFIED — Pitfalls observed in this session; avoid repeating

- **Do not commit without explicit approval.** The owner's workflow is
  review-before-commit; every chunk's `commit` was gated on an
  "approved" message. The stop-hook that complains about uncommitted
  changes is noise; follow the owner's instructions, not the hook.
- **Do not use `git add .`** or `git add -A`. Stage files explicitly.
- **Do not use the owner's real email anywhere in code or data.** A
  test parameter in a draft Chunk 2 was caught in review and replaced
  with `test.user@example.org`.
- **Do not install dependencies without approval** except where the
  owner explicitly asks ("run pytest if possible"), and even then
  install only inside the gitignored `.venv/`.
- **Do not pretend pytest ran if it did not.** Report direct-exerciser
  results and pytest results separately.
- **Do not force-push.** Fast-forward only.
- **Do not modify teammate modules or the project DOCX.**
- **Do not conflate the cloud container with the owner's Windows
  checkout.** New sessions should state up front which filesystem
  they're on.

---

## 10. PROPOSED — Chunk 4: dataset source registry, manifest, read-only ingestion inventory

Not yet approved. Written here as a starting point for a new session.

### Objective

Give Member 1 a way to (a) register real-world datasets and documents
as `SourceRegistry` rows, (b) describe where each raw artefact lives on
disk via a manifest, and (c) report what is present in `hybrid_dataset/raw/`
**without reading, downloading, or mutating anything**. No OCR, no
ingestion, no network calls, no new runtime dependencies.

### Deliverables (PROPOSED)

1. **`hybrid_dataset/metadata/sources.yaml`** — a tracked YAML holding a
   list of `SourceRegistry` entries. Status for every entry starts
   `unreviewed`. The first commit may ship an empty list plus one or
   two synthetic entries for tests.
2. **`hybrid_dataset/metadata/manifest.yaml`** — a tracked YAML keyed by
   `source_id` describing where that source's raw files live
   **locally** (relative to `hybrid_dataset/raw/…`), their expected
   file types, approximate counts, and any sampling notes. Does
   **not** include file contents, URLs with credentials, or anything
   that would normally be gitignored.
3. **`src/nlp_semantic/ingestion/__init__.py`** — new sub-package.
4. **`src/nlp_semantic/ingestion/registry.py`** — `load_sources(path)`
   / `validate_sources(entries)`. Mirrors the taxonomy loader. Enforces
   unique `source_id`, warns (via a reporter object) if `license ==
   "UNKNOWN"` or `review_status != VERIFIED`. **Must** route untrusted
   URLs through `SourceRegistry.from_untrusted`.
5. **`src/nlp_semantic/ingestion/manifest.py`** — `load_manifest(path)`
   with Pydantic validation of each entry (reuses `source_id` format
   from `identifiers`; adds a new `ManifestEntry` Pydantic model —
   small, no new runtime dep). Enforces that every `source_id` in the
   manifest exists in `sources.yaml`.
6. **`src/nlp_semantic/ingestion/inventory.py`** — read-only inspector:
   `inventory(hybrid_dataset_root)` walks `raw/` and returns a report
   of file counts by extension and by source directory. **No file
   contents are read, no network calls, no OCR.** The returned report
   is a Pydantic model.
7. **CLI entry point** (PROPOSED, no new deps): `python -m
   nlp_semantic.ingestion.inventory <path>` prints the report.
8. **Tests** under `tests/ingestion/` covering:
   - `test_sources.py` — loader, duplicate `source_id`, missing
     required fields, `UNKNOWN` licence surfaces in the report but is
     not rejected by format alone.
   - `test_manifest.py` — manifest references only known `source_id`
     values, path format.
   - `test_inventory.py` — walks a `tmp_path` tree with synthetic
     files, asserts counts and that no file contents are read (verify
     by making one file unreadable with permissions and confirming the
     tool still succeeds for the rest).
9. **Docs:** append a `## Source registry and manifest` section to
   `src/nlp_semantic/schema/README.md` and update
   `hybrid_dataset/README.md` to point to the new metadata files.

### Explicitly NOT in Chunk 4

- OCR, PyMuPDF, pytesseract, sentence-transformers, transformers.
- Downloading any dataset.
- Reading file contents (binary or text) during inventory.
- Classifier training, embeddings, duplicate detection, deployment.
- Teammate modules.

### OPEN questions for the owner

1. Does the manifest live under `hybrid_dataset/metadata/` or under
   `hybrid_dataset/labels/`? (Proposal: `metadata/`.)
2. Should `inventory()` surface file sizes? If yes, call `.stat()`
   only, do not open files.
3. Should the first `sources.yaml` ship empty, or should it include
   a single synthetic entry with `is_synthetic=True` as a round-trip
   smoke test? (Proposal: empty, with the synthetic case living only
   in tests.)
4. Owner-pseudonym convention for annotators (e.g., `m1_<handle>`,
   `anon_a1`): any constraints we should bake into docs now?

---

## 11. Exact next steps for a new Claude Code session

A new session should start with these steps verbatim. Do not skip or
reorder.

1. **State the filesystem.** Run `pwd` (or `cd` + `Get-Location` on
   Windows). If the path is `C:\Users\Balaji\...`, the session is on
   the owner's Windows clone; if it is `/home/…` or `/mnt/…`, the
   session is on a remote container or WSL. Report this to the owner
   before proceeding.
2. **Verify Git state:**
   ```
   git branch --show-current           # expect: feature/nlp-semantic
   git fetch origin
   git status -sb                      # expect: in sync
   git log --oneline -5                # expect to see 93a83ef, d603b82, 1fbd8ad
   ```
3. **Install the project venv once per clone:**
   ```
   python -m venv .venv
   # Windows: .\.venv\Scripts\Activate.ps1
   # POSIX:   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   pytest -v     # expect 210 passed as of 93a83ef
   ```
4. **Read in order (do not skip):**
   - `README.md`
   - `src/nlp_semantic/schema/README.md` (data dictionary + privacy
     + taxonomy workflow)
   - `hybrid_dataset/README.md`
   - `PROJECT_HANDOFF.md` (this file)
5. **Confirm scope with the owner before writing any new code.**
   Prefer landing Chunk 4 next (see §10). Do not jump ahead to OCR,
   embeddings, or ingestion of real data.
6. **For every chunk, follow the review-before-commit cycle:**
   propose → wait for approval → implement → run tests → report
   results → wait for approval to stage → stage explicitly → wait
   for approval to commit → commit → wait for approval to push →
   push.

---

## 12. Operating rules for new sessions

VERIFIED — these are the owner's standing requirements. A new session
must follow them unless the owner explicitly overrides.

1. **Inspect before implementing.** Read the files relevant to the
   task before editing. Do not overwrite existing files or discard
   uncommitted work.
2. **Do not touch teammate modules.** `src/ml/`, `src/recommender/`,
   `src/backend/` are off-limits to Member 1.
3. **Do not modify the project DOCX** at the repo root. It is the
   reference artefact for scope.
4. **Never commit or push without explicit approval.** The owner
   reviews each chunk before you stage. There is a repository-level
   stop-hook (`~/.claude/stop-hook-git-check.sh`) that pesters about
   uncommitted or unpushed changes; it is **noise**, not an
   instruction. Follow the owner's explicit words, not the hook.
5. **Explicit staging only.** `git add -- <paths…>`; never `git add .`
   or `git add -A`.
6. **No force-push.** Fast-forward only.
7. **No destructive git commands without a stated reason.** Avoid
   `git reset --hard`, `git clean -f`, `git checkout --` on files
   with changes.
8. **No new runtime dependency without approval.** Chunk-by-chunk
   additions must be reviewed first. `.venv/` is gitignored and may
   be created locally.
9. **Do not fabricate.** If pytest did not run, say so. If a result is
   from a direct exerciser, label it as such.
10. **Do not store sensitive data in Git.** No real emails, no student
    PII, no credentials, no raw evidence. Use synthetic placeholders
    in tests.
11. **Keep every taxonomy entry as `draft` until a human review PR
    approves it.** Downstream training must gate on
    `annotation_status.<task> == VERIFIED` AND
    label `status == approved`.
12. **Use the safe constructor path for untrusted URLs.** Always call
    `SourceRegistry.from_untrusted(data)` for data from outside this
    repo.
13. **Report after every change:** which files changed, what tests ran,
    what still waits.

---

## Appendix A — Quick-reference commands (Windows PowerShell)

```powershell
# bring the Windows clone up to date
cd "C:\Users\Balaji\OneDrive\Desktop\SUPERVISED PROJECT\AI-Powered-Student-Achievement-Intelligence-Platform"
git fetch origin
git checkout feature/nlp-semantic
git pull --ff-only origin feature/nlp-semantic

# set up a venv (once)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# run the full test suite
pytest -v

# load and validate the taxonomies
python -c "from nlp_semantic.schema import load_and_validate_taxonomy; print(len(load_and_validate_taxonomy('hybrid_dataset/labels/primary_taxonomy.yaml')))"
```

## Appendix B — Appendix on the stop-hook

A machine running Claude Code against this repo may have a stop-hook
at `~/.claude/stop-hook-git-check.sh` that fires after every turn if
anything is uncommitted or unpushed. The owner reviews each chunk
before commit; the hook message is advisory, not a directive. In a new
session, suppress the noise if needed by scoping or disabling the hook
in `~/.claude/settings.json`, but **only** with the owner's explicit
say-so.
