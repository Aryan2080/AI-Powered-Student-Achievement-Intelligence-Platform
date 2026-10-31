# Dataset Construction Status — Student Achievement Classification

**Generated:** 2026-10-25
**Audience:** Member 1 (NLP & Semantic Intelligence) and downstream reviewers.
**Scope:** read-only audit of the Student Achievement Classification
dataset as it exists in this working tree. No file in `src/`,
`hybrid_dataset/metadata/`, `hybrid_dataset/labels/`, or
`hybrid_dataset/dataset/` was modified while producing this report.
No source was promoted. No teammate directory was touched. Nothing was
staged, committed, pushed, or branch-switched. No records were
generated or imported.

This report is written for the brief in the user prompt ("§20 — Required
Dataset Report"), re-grounded in the actual repository state verified
by git, by Pydantic model loads, and by the project's own dataset
CLI commands.

---

## A. Project objective

The AI-Powered Student Achievement Intelligence Platform ingests
heterogeneous student achievement evidence (certificates, letters,
publications, project write-ups), extracts structured fields and
skills, classifies achievements by **primary type** (single-label,
multi-class), tags them with multi-label **domain tags**, and feeds
downstream recommendation and ML modules. The dataset constructed in
this report is the **supervised-learning input** for Task A
(multi-class classification over `primary_type`) and Task B
(multi-label categorisation over `domain_tags`).

The documented long-term dataset-size target is approximately
**1,500 – 3,000 genuine achievement records**. This is a corpus
aspiration, not a current chunk deliverable. The repository's
chunk-by-chunk workflow explicitly requires human source review,
license approval, and taxonomy promotion before any record becomes
training-eligible — the dataset will grow only as fast as that
review process allows.

---

## B. Existing implementation audit

### B.1 Branch and HEAD
- Working tree root: `AI-Powered-Student-Achievement-Intelligence-Platform/`
- Nested git repository on branch `feature/nlp-semantic`
- HEAD: `c8c1b80 feat: add SIH 2024 achievement pilot`
- Outer wrapping repo (SUPERVISED PROJECT) is on
  `feature/recommendation-platform` and tracks the inner platform repo
  only as an untracked directory. The outer repo was **not** touched.

### B.2 Data contract — `src/nlp_semantic/schema/` (committed)
Pydantic v2 models with `extra="forbid"`:
- `Achievement` — the record. Fields: `achievement_id`, `source_id`,
  `source_record_id`, `achievement_text`, `primary_type`,
  `domain_tags`, `level`, `outcome`, `event_name`, `organization`,
  `achievement_date`, `rank`, `skills`, `evidence_id`,
  `annotation_status` (`AnnotationStatusMap` with per-task
  `AnnotationStatus`), `is_synthetic`.
- `Annotation` — one labeler's position on one task of one record.
  Fields: `annotation_id`, `achievement_id`, `task`, `label_ids`,
  `annotator` (pseudonym), `review_status`, `notes`, `created_at`
  (timezone-aware required), `is_synthetic`.
- `Evidence` — evidence document pointer; strict path-safety under
  `hybrid_dataset/raw/evidence_documents/` and
  `hybrid_dataset/processed/`.
- `SourceRegistry` — source provenance. Enforces http/https URL with
  no embedded credentials; safe `.from_untrusted(data)` boundary.
- `LabelTaxonomy` — one label row (primary or domain). `supersedes`
  for renames; self-supersession and cycles rejected.
- Enums: `AnnotationStatus`, `ReviewStatus`, `AnnotationTask`,
  `TaxonomyTask`, `TaxonomyStatus`, `DocumentFileType`,
  `ExtractionMethod`.
- `UNKNOWN_LICENSE` sentinel.

### B.3 Dataset tooling — `src/nlp_semantic/dataset/` (committed)
- `loader.load_dataset(root)` — walks
  `<root>/dataset/records/batch_*.yaml` and (optional)
  `<root>/dataset/annotations/batch_*.yaml`; enforces unique
  `achievement_id` / `annotation_id`; file-level errors raise
  `DatasetError`; per-entry format problems surface as
  `pydantic.ValidationError`.
- `validator.validate_dataset(...)` — cross-record FK + taxonomy
  checks. Fatal set: unknown source ref, unknown primary/domain
  label ref, deprecated label ref, duplicate
  `(source_id, source_record_id)` pair, orphan annotation,
  annotation referencing unknown label. Advisory set:
  draft/under_review label refs, `UNKNOWN`-license sources,
  non-`VERIFIED` sources.
- `validator.eligible_ground_truth(records, task=…)` — training
  eligibility rule 1 (both `annotation_status.<task> == VERIFIED`
  **and** every referenced label `status == APPROVED`).
- `validator.training_ready_subset(records, sources=…, task=…)` —
  training eligibility rule 2 (adds `review_status == VERIFIED`
  **and** `license != UNKNOWN` on the record's source). Case-
  insensitive license comparison.
- `duplicates.find_duplicates(records)` — deterministic duplicate
  detector with four rules: `exact_text`, `normalized_text` (NFKC +
  whitespace collapse + casefold), `source_record_pair`,
  `date_org_event_triple`. Reports groups; does **not** merge or
  delete. Semantic duplicate detection (embeddings) is deferred —
  this is explicitly noted in the module docstring.
- `splits.generate_splits(records, seed=…, ratios=…,
  exclude_synthetic=…)` — reproducible source-grouped
  train/val/test splits. Hard guarantee: every record carrying a
  given `source_id` lands in exactly one split (no `source_id`
  crosses splits). Surfaces infeasibility (empty splits,
  fewer sources than non-zero splits) as `warnings`. Writes JSONL
  + SHA-256 manifest to `processed/splits/`.
- `stats.compute_stats(records)` — class-distribution, synthetic
  counts, per-source counts, primary↔domain cooccurrence. Pure
  stdlib `Counter`.
- `agreement.compute_agreement(annotations, task=…)` — IAA.
  Collapses same-annotator rows by latest `created_at`; excludes
  rejected rows; reports Cohen's κ (primary) and mean Jaccard
  (domain); κ is `None` when mathematically undefined; empty-vs-
  empty Jaccard is `1.0` by documented convention.
- `cli.main(argv)` — `validate | stats | split | readiness`
  subcommands; JSON to stdout, one-line human summary to stderr;
  exit codes `0` success / `1` dataset or build error / `2`
  argparse.

### B.4 Ingestion scaffolding — `src/nlp_semantic/ingestion/`
Committed: `registry.py` (loads `sources.yaml`), `manifest.py`
(loads `manifest.yaml`, enforces manifest-only references to known
`source_id` values), `inventory.py` (read-only `raw/` walker; the
docstring and tests confirm no file contents are read, no network
calls, no OCR).

**Uncommitted (working-tree) ingestion work:**
- `src/nlp_semantic/ingestion/arxiv_governance.py` and
  `src/nlp_semantic/ingestion/rate_limit.py` — policy surface for
  future arXiv metadata collection (CC0 scope, endpoint allowlist,
  rate-limit coordinator). **No arXiv ingestion has occurred.**
- `tests/ingestion/test_arxiv_governance.py`,
  `tests/ingestion/test_rate_limit.py`,
  `tests/ingestion/test_redis_rate_limit.py` — tests for the
  above (`fakeredis` test gracefully skips when the dep is absent).
- `hybrid_dataset/metadata/arxiv_governance_decisions.md` —
  governance decisions companion document.
- `requirements.txt` — adds `redis>=5,<6` and `fakeredis[lua]>=2,<3`.
- `pyproject.toml` — adds `.` to `pythonpath` so a top-level
  `tests/__init__.py` resolves ahead of a site-packages orphan.
- `hybrid_dataset/metadata/sources.yaml` — adds a second
  `SourceRegistry` entry for arXiv (`CC0-1.0` metadata only,
  `review_status: unreviewed`).

### B.5 Taxonomies — `hybrid_dataset/labels/` (committed)
- `primary_taxonomy.yaml` — the 14 primary classes, exactly matching
  the user brief's §4 list (ids are
  `lbl_hackathon`, `lbl_competition`, `lbl_research_pub`,
  `lbl_patent`, `lbl_internship`, `lbl_certification`, `lbl_project`,
  `lbl_workshop`, `lbl_conference`, `lbl_leadership`, `lbl_sports`,
  `lbl_cultural`, `lbl_volunteering`, `lbl_other`). Every entry
  carries `status: draft` with full `definition`, `inclusion_rules`,
  `exclusion_rules`, and `examples`.
- `domain_tags.yaml` — 10 draft domain tags
  (`lbl_domain_ai`, `lbl_domain_ml`, `lbl_domain_nlp`,
  `lbl_domain_cv`, `lbl_domain_security`, `lbl_domain_systems`,
  `lbl_domain_web`, `lbl_domain_data`, `lbl_domain_hardware`,
  `lbl_domain_other`).
- `TAXONOMY_APPROVAL_CHECKLIST.md` — the formal promotion workflow
  (draft → under_review → approved) is documented and gated.

### B.6 Records and sources — `hybrid_dataset/`
- `dataset/ANNOTATION_GUIDELINES.md` — full annotator rubric,
  pseudonym convention, single-review and dual-review workflows,
  HACKATHON ↔ COMPETITION ↔ PROJECT disambiguation procedure,
  class-balance targets, worked examples (unambiguous hackathon,
  ambiguous hackathon-or-research, synthetic fixture).
- `metadata/SOURCE_REGISTRATION_GUIDE.md` — source registration /
  review workflow.
- `metadata/sources.yaml` — one committed source + one uncommitted
  source (see §F).
- `metadata/manifest.yaml` — empty list; no raw files expected on
  disk yet.
- `dataset/records/batch_01_sih2024.yaml` — the one and only record
  batch (7 Smart India Hackathon 2024 Winners' List team records,
  derived from PIB press release PRID 2085000).
- `dataset/annotations/` — empty (no annotation history rows yet).
- `raw/`, `processed/` — empty on disk; inventory reports 0 files.

### B.7 Reports
`reports/` holds 17 pre-existing chunk reports covering arXiv
governance design (7.16 – 7.23), test-collection remediation (7.24),
source-review packet preparation (7.25 – 7.27A), and three recent
readiness audits (7.29 – 7.32). The present report is **net-new**
and additive; it does not revise or displace any of them.

---

## C. Dataset inventory

Verified by `python -m nlp_semantic.dataset.cli validate hybrid_dataset`
and `… stats hybrid_dataset` on 2026-10-25.

| Measure | Value |
|---|---|
| Record batch files | 1 (`dataset/records/batch_01_sih2024.yaml`) |
| Annotation batch files | 0 |
| Total records loaded | 7 |
| Genuine records (`is_synthetic: false`) | 7 |
| Synthetic records | 0 |
| Pydantic-valid records | 7 (loader completed without `ValidationError`) |
| Fatal cross-record validation findings | 0 |
| Advisory cross-record validation findings | 9 |
| Duplicate detector groups flagged | 0 |
| Unique achievement identities (post-dedup) | 7 |
| Records requiring human review | 7 (all `annotation_status.primary_type: draft`) |

Every record is a genuine, team-level Smart India Hackathon 2024
hardware-grand-finale Winners' List entry derived from a public PIB
press release. There are no fabricated records.

---

## D. Category distribution

All 14 primary labels reported, zero-count labels included (per the
brief's "do not hide zero-count categories" rule):

| Primary label | Count | Share |
|---|---:|---:|
| `lbl_hackathon` | 7 | 100.0% |
| `lbl_competition` | 0 | 0.0% |
| `lbl_research_pub` | 0 | 0.0% |
| `lbl_patent` | 0 | 0.0% |
| `lbl_internship` | 0 | 0.0% |
| `lbl_certification` | 0 | 0.0% |
| `lbl_project` | 0 | 0.0% |
| `lbl_workshop` | 0 | 0.0% |
| `lbl_conference` | 0 | 0.0% |
| `lbl_leadership` | 0 | 0.0% |
| `lbl_sports` | 0 | 0.0% |
| `lbl_cultural` | 0 | 0.0% |
| `lbl_volunteering` | 0 | 0.0% |
| `lbl_other` | 0 | 0.0% |
| **Total** | **7** | **100%** |

Primary-type annotation-status distribution (over the 7 records):
- `draft`: 7
- `pending`: 0
- `verified`: 0
- `rejected`: 0
- `conflicted`: 0
- `not_started`: 0

Domain-tags annotation-status distribution:
- `not_started`: 7
- All 10 domain tags have 0 occurrences across the dataset.

---

## E. Field completeness

Per the current `Achievement` schema (which is the project's
authoritative shape; the brief's §5 field list is honoured by this
mapping — the schema does not have standalone `category`, `domain`,
`normalized_text`, `source_type`, `labeler_id`, or `quality_status`
columns because those concepts live on the `AnnotationStatusMap`,
the `domain_tags[]` list, the dataset tooling, the `SourceRegistry`,
the `Annotation` rows, and the validator reports respectively).

| Field | Populated | Missing | Missing % | Validation issues |
|---|---:|---:|---:|---|
| `achievement_id` | 7 | 0 | 0% | all `ach_` + 32-hex, all unique |
| `source_id` | 7 | 0 | 0% | all `src_` + 32-hex; FK → `sources.yaml` resolves |
| `source_record_id` | 7 | 0 | 0% | all unique; validator detects no duplicate pairs |
| `achievement_text` | 7 | 0 | 0% | all within 1–4000 chars |
| `primary_type` | 7 | 0 | 0% | all `lbl_hackathon`; label is **still `draft`** (advisory) |
| `domain_tags` | 0 of 7 populated | 7 | 100% | `not_started` is schema-legal; "no tags" is not a negative label |
| `level` | 7 | 0 | 0% | all `national` |
| `outcome` | 7 | 0 | 0% | all `winner` |
| `event_name` | 7 | 0 | 0% | all `Smart India Hackathon 2024 (Hardware Grand Finale)` |
| `organization` | 7 | 0 | 0% | all team-affiliated institutions |
| `achievement_date` | 0 of 7 | 7 | 100% | **intentionally `null`** per Chunk 7.4-A.2 — source does not establish an unambiguous start-of-build-window date |
| `rank` | 0 of 7 | 7 | 100% | Winners' List does not publish numeric rank beyond "winner" |
| `skills` | 0 of 7 | 7 | 100% | no project titles / abstracts in the source; inference would violate the "no fabricated skills" rule |
| `evidence_id` | 0 of 7 | 7 | 100% | no evidence documents ingested; text-only pilot |

Absence here is schema-legal, not a defect. The project's
"missing-field is never a negative label" rule is honoured.

---

## F. Source coverage

Verified against `hybrid_dataset/metadata/sources.yaml` (committed +
uncommitted entries).

### F.1 Committed source
| Attribute | Value |
|---|---|
| `source_id` | `src_5a8a2998d6f44055a42dcfd8991e4d12` |
| `source_name` | Smart India Hackathon 2024 Concludes with Innovative Solutions — PIB Release ID 2085000 |
| `source_url` | `https://www.pib.gov.in/PressReleasePage.aspx?PRID=2085000&lang=2&reg=48` |
| `license` | `UNKNOWN` (holding registration pending two-reviewer sign-off on PIB copyright policy applicability) |
| `collection_date` | 2026-10-23 |
| `intended_use` | `primary_type_training_lbl_hackathon` |
| `review_status` | **`unreviewed`** |
| Record count citing this source | 7 |
| Evidence files ingested | 0 (text-only extraction; PIB third-party-material carve-out excludes photographs) |

### F.2 Uncommitted source
| Attribute | Value |
|---|---|
| `source_id` | `src_08ee850ba4b54d1b81cdbd652809b613` |
| `source_name` | arXiv |
| `source_url` | `https://arxiv.org/` |
| `license` | `CC0-1.0` (metadata only; full-text not authorised; separate registration required for any future full-text use) |
| `collection_date` | 2026-10-23 |
| `intended_use` | `primary_type_training_lbl_research_pub_metadata_only` |
| `review_status` | **`unreviewed`** |
| Record count citing this source | 0 (no arXiv records ingested — governance surface only) |

### F.3 Validator advisory summary (verbatim from the CLI)
- `unknown_license_source_ids`: `["src_5a8a2998d6f44055a42dcfd8991e4d12"]`
- `unverified_source_ids`: both ids above.
- `draft_label_refs`: 7 tuples, one per record × `lbl_hackathon`.

### F.4 Provenance completeness
Every one of the 7 records satisfies the project's provenance
contract: `(source_id, source_record_id)` is unique, the
`source_record_id` encodes the PIB press-release identifier plus the
ministry category plus the team slug (e.g.
`pib-prid-2085000-mohua-the-olympians`), and the raw-source
screenshot evidence that grounds the ingestion is retained in the
companion Chunk 7.3-A.4 chunk report. No record relies on inferred
provenance.

### F.5 Collection gaps
- Only one real source has been ingested from (`src_5a8a2998…`), and
  it is confined to a single event (SIH 2024 hardware grand finale)
  with 7 team records.
- The arXiv entry is governance surface only — no record flows
  through it yet, and promotion to `verified` requires two
  independent reviewer sign-offs plus a review of the Chunk 7.18
  revisions.
- Thirteen of the fourteen primary categories have **zero sources**
  registered as the entry point for their records.

---

## G. Label quality

### G.1 Verified vs unreviewed
No label on any record is at `annotation_status.<task> == verified`.
All 7 records are at `annotation_status.primary_type: draft` and
`annotation_status.domain_tags: not_started`. No dual review has
been performed; there are 0 `Annotation` rows and 0 pairs for
inter-annotator agreement.

### G.2 Readiness-command summary (verbatim)
`python -m nlp_semantic.dataset.cli readiness hybrid_dataset`:

```
assessment_status           = completed
structurally_valid          = true
approved_label_count        = {primary_type: 0, domain_tags: 0}
eligible_record_count       = {primary_type: 0, domain_tags: 0}
is_training_ready           = {primary_type: false, domain_tags: false}
any_task_training_ready     = false
all_tasks_training_ready    = false
blockers                    = 4
warnings                    = 2
```

The four blockers are: `no_approved_labels` × 2 (one per task) and
`no_eligible_records` × 2 (one per task). The two warnings are
`unknown_license` and `unverified_source`.

### G.3 Ambiguity and `lbl_other`
Zero records are classified `lbl_other`. The project's own
annotation guidelines prohibit defaulting to `lbl_other` to work
around missing information; `batch_01_sih2024.yaml` honours that
rule by keeping all 7 records at `annotation_status.primary_type:
draft` under `lbl_hackathon`, backed by event-level evidence (five-
day bounded build window, formal competitive judging, Winners'
List) that satisfies the Chunk 7.1 event-centric hackathon definition.

### G.4 Human-review requirements
Before any training can begin, each of the following humans-in-the-
loop requirements must be met:

1. Promote `lbl_hackathon` from `draft` to `approved` in
   `primary_taxonomy.yaml` via the Chunk 7.2 two-independent-reviewer
   workflow.
2. Promote `src_5a8a2998d6f44055a42dcfd8991e4d12` from `unreviewed`
   to `verified` AND populate its `license` with a reviewer-signed
   verbatim summary of the PIB copyright policy applicability.
3. Promote each record's `annotation_status.primary_type` from
   `draft` to `verified` through single or dual review per
   `ANNOTATION_GUIDELINES.md`.
4. If domain tagging is desired, promote
   `annotation_status.domain_tags` from `not_started` after a
   reviewer has deliberately marked it (empty is legitimate once
   deliberately set to `verified`).
5. Repeat (1)–(4) for every additional label and source as the
   dataset grows.

---

## H. Duplicate and leakage analysis

### H.1 Deterministic duplicate detection (Chunk 5 scope)
`python -m nlp_semantic.dataset.cli validate hybrid_dataset`:

| Rule | Groups |
|---|---:|
| `exact_text` | 0 |
| `normalized_text` | 0 |
| `source_record_pair` | 0 |
| `date_org_event_triple` | 0 |

The seven records all share the same `event_name`, `organization
category` (institution), and `source_id`, but differ in `team name`
and `source_record_id`; `achievement_date` is deliberately `null`
(see §E), so the `date_org_event_triple` rule does not fire. They
are **distinct achievements by distinct teams at the same event** —
exactly the "different students / teams receiving the same event's
awards" case the user brief flags as `DIFFERENT_STUDENTS_SAME_AWARD`,
which must not be collapsed.

### H.2 Semantic / near-duplicate detection (deferred)
Not implemented. The duplicate module's docstring states
semantic (embedding-based) duplicate detection is a later chunk and
requires sentence-transformer or equivalent dependencies that are
not yet approved. No cross-source corroboration pass has run
because there is only one record source.

### H.3 Achievement identity resolution
Each record is identified by `achievement_id` (UUID4 hex, prefixed
`ach_`) and anchored by `(source_id, source_record_id)` where the
latter encodes the PIB PRID, ministry category, and team slug. No
student-level identifiers are stored (per the project's privacy
rule); the records are team-level only. There is no
"canonical achievement" aliasing table yet; it is not needed while
every record maps to exactly one source and one team.

### H.4 Leakage-safe splitting
The split module enforces **source-group integrity**: all records
sharing a `source_id` land in exactly one split, so the two-splits-
of-the-same-event-record leakage case cannot occur. With 7 records
across 1 source, the current data cannot be split into
train/val/test; `generate_splits` would surface
`source_group_count_below_nonzero_split_count` as a warning. No
split has been written to disk in this report; `processed/splits/`
is empty.

Student-level grouping (grouping by individual student across
achievements) is **not** currently enforced because the records are
team-level and the schema does not carry a `student_id`. If future
records introduce per-student records, a `student_id` field
addition should be audited for its leakage implications.

---

## I. Dataset size assessment

| Measure | Value |
|---|---:|
| Documented long-term target (approximate) | 1,500 – 3,000 |
| Current genuine records | 7 |
| Current unique achievement identities | 7 |
| Current training-eligible records (`training_ready_subset`) | 0 |
| Nominal gap to lower target bound | 1,493 |
| Nominal gap to upper target bound | 2,993 |

Category-specific shortages, measured against the annotation
guideline's planning floor of ≥ 5 records per primary label
(≥ 10 preferred):

| Label | Current | Floor (≥ 5) | Gap-to-floor |
|---|---:|---:|---:|
| `lbl_hackathon` | 7 | 5 | met |
| `lbl_competition` | 0 | 5 | 5 |
| `lbl_research_pub` | 0 | 5 | 5 |
| `lbl_patent` | 0 | 5 | 5 |
| `lbl_internship` | 0 | 5 | 5 |
| `lbl_certification` | 0 | 5 | 5 |
| `lbl_project` | 0 | 5 | 5 |
| `lbl_workshop` | 0 | 5 | 5 |
| `lbl_conference` | 0 | 5 | 5 |
| `lbl_leadership` | 0 | 5 | 5 |
| `lbl_sports` | 0 | 5 | 5 |
| `lbl_cultural` | 0 | 5 | 5 |
| `lbl_volunteering` | 0 | 5 | 5 |
| `lbl_other` | 0 | — (capped as a dumping-ground label) | — |

The dataset is **not** ready for training in either Task A or Task
B. Zero records satisfy the two-condition
`training_ready_subset` rule (`annotation_status.<task> == VERIFIED`
AND label `status == APPROVED` AND source `review_status == VERIFIED`
AND source `license != UNKNOWN`). The remaining collection and
review requirements are summarised in §L.

Per the user brief's explicit instruction, **no records have been
generated or imported to close the gap**. Fabrication is prohibited;
closing this gap requires registering more real sources, running the
Chunk 7.4-style extraction workflow against them, and completing
label/source review for each.

---

## J. Implemented changes

| File | Change | Reason |
|---|---|---|
| `reports/dataset_construction_status.md` | **Created** (this file). | Deliver the user brief's §20 required status report. Additive; replaces no existing report. |

No other file was created or modified in this session. Specifically:
- `src/nlp_semantic/`, `hybrid_dataset/labels/`,
  `hybrid_dataset/metadata/sources.yaml`,
  `hybrid_dataset/dataset/records/batch_01_sih2024.yaml`,
  taxonomy YAMLs, `pyproject.toml`, `requirements.txt`,
  `ANNOTATION_GUIDELINES.md`, `README.md`, and `PROJECT_HANDOFF.md`
  were all left exactly as they were on entry.
- The teammate directories `src/ml/`, `src/recommender/`,
  `src/backend/` do not exist (empty on `feature/nlp-semantic`) and
  were not created.
- No `git add`, `git commit`, `git push`, or `git checkout` was
  performed. The branch is still `feature/nlp-semantic`.

---

## K. Testing

Run on 2026-10-25 under the project venv
`C:\Users\Balaji\OneDrive\Desktop\SUPERVISED PROJECT\AI-Powered-Student-Achievement-Intelligence-Platform\.venv\`.

### K.1 Full test suite
Command:
```
.\.venv\Scripts\python.exe -m pytest -q --tb=short
```
Result:
```
579 passed, 5 skipped in 14.88s
```

Skip reasons (verified with `-rs`):
- 4 × `tests/ingestion/test_inventory.py` — "symlink creation
  unavailable (Windows without developer mode)". Platform-conditional,
  not a defect; symlink tests validate inventory behaviour that is
  itself tested on POSIX CI.
- 1 × `tests/ingestion/test_redis_rate_limit.py` — "could not import
  `fakeredis`: No module named `fakeredis`". The requirements.txt
  change that adds `fakeredis[lua]` is uncommitted and not installed
  into this venv; the test gracefully skips rather than fail.

### K.2 Dataset CLI exercises
`python -m nlp_semantic.dataset.cli validate hybrid_dataset`
→ `dataset: ok | records=7 | fatal=0 | advisory=9 | duplicates_flagged=0`
(exit 0).

`python -m nlp_semantic.dataset.cli stats hybrid_dataset`
→ `dataset: stats | records=7 | synthetic=0 | real=7 | primary_classes=1`
(exit 0).

`python -m nlp_semantic.dataset.cli readiness hybrid_dataset`
→ `dataset: readiness | any_task=not_ready | all_tasks=not_ready | approved(pt=0,dt=0) | eligible(pt=0,dt=0) | blockers=4 | strict=off`
(exit 0 under default mode; `--strict` would exit 1).

`python -m nlp_semantic.ingestion.inventory hybrid_dataset`
→ `0 files | 0 warnings`.

### K.3 No new tests added
No test was added or modified in this session, consistent with the
report-only scope. The verification above was performed against the
existing test suite as of HEAD `c8c1b80`.

---

## L. Outstanding work

The dataset is **not** complete. Precise, enumerated blockers:

1. **Taxonomy promotion.** All 14 primary labels and 10 domain
   tags are `draft`. No label is `approved`; without that, the
   `training_ready_subset` filter returns `[]` for both tasks by
   design.
2. **Source review (SIH 2024 PIB).** `src_5a8a2998…` is still
   `unreviewed` with `license: UNKNOWN`. Chunk 7.2 workflow requires
   two independent reviewer sign-off PR comments and population of
   `license` with a verbatim summary of the applicable PIB copyright
   policy.
3. **Source review (arXiv).** `src_08ee850b…` is also `unreviewed`
   and the governance code that would gate its ingestion
   (`arxiv_governance.py`, `rate_limit.py`) is itself uncommitted.
   Promotion requires a review of the Chunk 7.18 revisions.
4. **Annotation review of the 7 SIH records.** All 7 have
   `annotation_status.primary_type: draft` and need either single
   or dual review per the guidelines.
5. **Domain tagging.** No record carries any domain tag. The seven
   SIH records lack per-team project titles in the public source,
   so domain tags cannot be assigned without inference — this is
   working-as-intended; the fix is to collect sources with evidence
   of per-team deliverables (official project titles, press
   releases that describe the actual builds), not to guess.
6. **Breadth of sources.** The dataset today spans one event and
   one primary label. Thirteen other primary labels have **zero
   records**. Candidate sources must be registered, source-reviewed,
   and ingested through the existing Chunk 7.4-style extractor
   workflow:
   - `lbl_competition`: Kaggle, ACM-ICPC regional pages, published
     case-competition results.
   - `lbl_research_pub`: arXiv (once review completes), DBLP, ACL
     Anthology.
   - `lbl_patent`: USPTO Patent Trial & Appeal Board, Indian Patent
     Office search, Google Patents.
   - `lbl_internship`, `lbl_project`, `lbl_leadership`,
     `lbl_sports`, `lbl_cultural`, `lbl_volunteering`,
     `lbl_workshop`, `lbl_conference`, `lbl_certification`,
     `lbl_other`: candidate sources to be identified by the team.
   Candidate sources above are flagged for human source-governance
   evaluation; this report is **not** proposing to collect from any
   of them unilaterally.
7. **Volume to target.** Even with the above resolved, growing to
   the aspirational 1,500 – 3,000 record range implies
   approximately 100 – 215 records per primary label. The current
   per-source ingest cadence is 7 records per fully reviewed source;
   the gap is as much a review-capacity question as a collection
   question.
8. **Document OCR + evidence pipeline.** The brief's "Document
   processing → OCR → text extraction → NLP preprocessing" stages
   are deliberately deferred until approved. OCR, PyMuPDF,
   pytesseract, sentence-transformers, and transformers are not in
   `requirements.txt` and are explicitly listed as not-yet-approved
   dependencies in `PROJECT_HANDOFF.md`.
9. **Semantic duplicate detection.** `duplicates.py` ships only
   deterministic rules; sentence-transformer-based near-duplicate
   detection is deferred alongside item 8.

### L.1 What this session recommends be done next
This report does **not** execute any of the following; it names
them so the owner can decide the next chunk:

- Complete the Chunk 7.2 PIB-source two-reviewer sign-off packet
  (`chunk_7_26A_independent_reviewer_sign_off_packet.md` is
  prepared).
- Promote `lbl_hackathon` to `approved` via the taxonomy approval
  checklist, after reviewers confirm the Chunk 7.1 event-centric
  definition.
- With both of those gates cleared, flip the 7 SIH records to
  `annotation_status.primary_type: verified` and re-run the
  readiness CLI; `training_ready_subset` should return the 7
  records.
- Identify, register, and review two or three additional sources
  spanning different primary labels (candidate domains above) so
  the second batch exercises the pipeline end-to-end for a label
  other than `lbl_hackathon`.
- Only after a second label has at least one approved end-to-end
  record, assess whether the OCR / embeddings dependencies are
  worth adding, and under which chunk.

---

## M. Completion verdict

Measured against the user brief's §21 "Final completion conditions":

| Condition | Status |
|---|---|
| 1. Required dataset structure implemented | ✓ (schemas, loader, validator, duplicates, splits, stats, agreement, CLI). |
| 2. Genuine achievement records collected or reused | **Partial** — 7 genuine records; 1,493 – 2,993 short of target. |
| 3. Original achievement descriptions preserved | ✓ (`achievement_text` is unmodified source prose). |
| 4. Primary categories follow existing taxonomy | ✓ (all 7 records use `lbl_hackathon`). |
| 5. Structured attributes extracted where supported | ✓ (`level`, `outcome`, `event_name`, `organization`); explicit nulls where unsupported. |
| 6. Provenance preserved | ✓ (every record cites `source_id` + `source_record_id`). |
| 7. Duplicate detection performed | ✓ (deterministic; 0 groups). |
| 8. Achievement identity resolved for intended task | ✓ (team-level; schema has no `student_id` and does not require one). |
| 9. Leakage-safe preparation implemented | ✓ (source-grouped splits; semantic dedup deferred). |
| 10. Required validation passes | ✓ (0 fatal findings; 9 advisories, all expected). |
| 11. Human-review requirements satisfied | ✗ — 0 of 7 records verified; 0 of 14 labels approved; 0 of 2 sources reviewed. |
| 12. Dataset size and category distribution reported | ✓ (§C, §D above). |
| 13. Dataset is reproducible | ✓ (deterministic loader + split; no manual edits). |
| 14. Remaining limitations clearly documented | ✓ (§L above). |

**Verdict:** The dataset is **not complete.** The scaffolding is in
place and healthy; the dataset itself is a 7-record single-label
pilot that is still awaiting human source review, label promotion,
and annotation verification before any record becomes training-
eligible. The user brief's cap target of 1,500 – 3,000 records is
feasible under the existing workflow but is **chunk-by-chunk work
gated on human review**, not something this report could or should
have attempted to short-circuit.
