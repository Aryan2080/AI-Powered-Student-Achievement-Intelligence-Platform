# Annotation Guidelines

**Audience:** project team members (Members 1 / 2 / 3) acting as
annotators. **Scope:** curating `hybrid_dataset/dataset/records/*.yaml`
and the optional `hybrid_dataset/dataset/annotations/*.yaml`.

This document is advisory and shipped with Chunk 5 code so annotation
work can begin after the code is merged. It does **not** add any
runtime enforcement; the Achievement / Annotation / LabelTaxonomy
Pydantic models and the dataset validator remain the authoritative
rulesets.

---

## Pseudonym convention

- Each annotator picks a stable pseudonym of the form `labeler_<NNN>`
  (e.g. `labeler_001`, `labeler_017`). Ordinals are assigned on first
  use and never reused.
- The pseudonym → real-identity mapping is **never** stored in this
  repository. If you need one, keep it in a separate private store.
- The annotator regex accepts other patterns too; `labeler_<NNN>` is
  the convention, not a runtime enforcement.

---

## Record workflow — single review

For an unambiguous record (one annotator sees it, no disagreement
expected):

1. Collect source material — public, aggregated, or impersonal.
2. Register the source in `hybrid_dataset/metadata/sources.yaml` if
   it is not already there. Verify license, provenance, collection
   date, and `original_labels` before committing the source entry.
3. Create a new YAML list file `records/batch_<NN>.yaml` or append
   to the current open batch.
4. Fill minimum fields: `achievement_id` (fresh UUID4 hex),
   `source_id`, `source_record_id`, `achievement_text`,
   `is_synthetic: false`.
5. Apply classification labels when ready:
   - Set `primary_type` to one `lbl_<...>` from
     `primary_taxonomy.yaml`.
   - Set `domain_tags` to zero or more `lbl_domain_<...>` from
     `domain_tags.yaml`.
   - Move `annotation_status.primary_type` and
     `.domain_tags` to `draft`, then to `verified` once a reviewer
     signs off.
6. Fill extraction fields (`event_name`, `organization`,
   `achievement_date`, `rank`, `skills`, `level`, `outcome`) when
   extractable. Missing fields stay `null` or `[]` — absence is
   never a negative signal.
7. Commit the batch file in a PR; another team member reviews the
   label choices on PR diff.

---

## Record workflow — dual review (for inter-annotator agreement)

Pick ~20% of the seed to dual-review. For each dual-reviewed record:

1. Both annotators independently apply labels. Each stores an
   `Annotation` row in `annotations/batch_<NN>.yaml` with their own
   pseudonym and `review_status: draft`.
2. If labels agree, promote the Achievement's
   `annotation_status.<task>` to `verified`. Both Annotation rows
   stay in history.
3. If labels disagree, mark both Annotation rows `conflicted` and
   schedule a resolution meeting (see "Dispute resolution" below).

---

## Choosing `primary_type`

Each record has **exactly one** `primary_type`. Pick the label whose
`definition` and `inclusion_rules` most tightly fit the record. Use
`exclusion_rules` as a disqualifier.

Quick guide to the 14 draft primary types:

| Record describes… | Likely primary_type |
|---|---|
| Time-boxed building competition (24-72 h) | `lbl_hackathon` |
| Non-hackathon judged contest (algorithmic, case, debate) | `lbl_competition` |
| Peer-reviewed paper or venue publication | `lbl_research_pub` |
| Granted or filed patent | `lbl_patent` |
| Industry / lab internship | `lbl_internship` |
| Certification exam / credential | `lbl_certification` |
| Standalone build with no contest | `lbl_project` |
| Attendance-oriented workshop | `lbl_workshop` |
| Conference talk / poster | `lbl_conference` |
| Student-body or club leadership role | `lbl_leadership` |
| Sports placement / selection | `lbl_sports` |
| Cultural performance / art placement | `lbl_cultural` |
| Volunteering / community service | `lbl_volunteering` |
| Doesn't fit any of the above (use sparingly) | `lbl_other` |

If a record fits two labels (e.g. a hackathon that was also published
as a research paper), pick the one that best describes the *primary*
achievement; capture the secondary aspect via `domain_tags` or
extraction fields. Err toward the narrower label.

---

## Choosing `domain_tags`

`domain_tags` is **multi-label**; a record can have zero or more. Pick
every tag whose `definition` applies. The 10 draft domain tags:

| Tag | Covers |
|---|---|
| `lbl_domain_ai` | Broad AI work not specifically ML / NLP / CV |
| `lbl_domain_ml` | Supervised / unsupervised classical ML |
| `lbl_domain_nlp` | Text, language, speech |
| `lbl_domain_cv` | Vision, images, video |
| `lbl_domain_security` | Infosec, cryptography, red-team |
| `lbl_domain_systems` | OS, distributed, infra, databases |
| `lbl_domain_web` | Front-end, back-end web, APIs |
| `lbl_domain_data` | Data engineering, pipelines, analytics |
| `lbl_domain_hardware` | Embedded, IoT, FPGA, robotics |
| `lbl_domain_other` | None of the above apply (use sparingly) |

Guidelines:

- Multiple tags are expected on cross-domain work (e.g. ML + NLP, or
  Web + Security).
- Empty list is OK when the record is intrinsically non-technical
  (sports, cultural, leadership) — set
  `annotation_status.domain_tags: verified` in that case, so empty
  means "reviewer confirms none apply" rather than "not yet
  annotated".

---

## Extraction fields (not labels)

- `event_name`, `organization`, `achievement_date`, `rank`,
  `outcome`, `level`, `skills` — these are information-extraction
  outputs, not classification targets.
- Fill them when the source makes them unambiguous. Leave them `null`
  or `[]` otherwise.
- Do not infer values. "He probably used Python" is not grounds for
  adding Python to `skills`.
- `achievement_date` is ISO `YYYY-MM-DD`. If only the year is known,
  leave it `null` and note the gap in `notes` (on an Annotation row
  if you are opening one).

---

## Dispute resolution

- If two annotators disagree on `primary_type`, both Annotation rows
  are flipped to `review_status: conflicted`. Neither is promoted.
- The team discusses the record at the next sync. One of:
  1. Convinces the other → the losing annotator updates their row to
     `rejected` and the winner's row stays `verified`. The Achievement
     advances to `verified`.
  2. No agreement → the Achievement's
     `annotation_status.<task>` stays below `verified`; the record is
     set aside and does not enter any ground-truth set.
- Document the discussion in the winning Annotation's `notes` field so
  reviewers understand the final decision.

---

## Privacy and sourcing

**Never commit to Git:**

- Real student names, email addresses, phone numbers, roll numbers.
- Scanned ID cards, certificates, or private evidence documents.
- Credentials, API keys, tokens, `.env` files.
- Direct quotes that re-identify a student (unless the source is a
  public byline the student authored).

**Prefer:**

- Impersonal rewrites: "A student built a traffic prediction app at a
  48-hour hackathon" rather than naming the student.
- Synthetic records (`is_synthetic: true`) for development, test
  fixtures, and tutorial examples. Keep them clearly separated from
  the training set.
- Public sources with clear licenses: conference proceedings, patent
  databases, public hackathon leaderboards, news articles with
  attribution. Register each one in `sources.yaml` with its license,
  URL, collection date, and `review_status`.

**Verify before registering a source:**

- Canonical URL resolves and is not a login-gated or
  rate-limited scrape target.
- License is written down somewhere stable (the source page, a
  LICENSE file, Terms of Service). "I think it's open" is not a
  license.
- No obvious PII in the fields you intend to copy.
- `collection_date` reflects when you actually read the data, not an
  arbitrary date.

Registration is NOT approval. A `SourceRegistry` entry with
`review_status: verified` plus a human-approved license decision is
required before any downstream model consumes records from that
source.

---

## Class balance targets

The 14 primary types are not uniformly represented in real-world
achievement data. Guidance for the seed:

- **Target each `primary_type` with ≥ 5 records** (plan floor;
  ≥ 10 is preferred).
- **Cap `lbl_other` and `lbl_project`** at the sum of the next three
  largest classes — these labels are dumping grounds without balance.
- **Rare types** (`lbl_patent`, `lbl_cultural`) may need synthesized
  realistic examples; mark `is_synthetic: true`.
- The split generator's `stratification` report will tell you where
  balance has broken; iterate annotation until the report is
  acceptable.

---

## Worked examples

### Example A — unambiguous hackathon

```yaml
- achievement_id: ach_<32 hex>
  source_id:      src_<32 hex>              # must be registered
  source_record_id: "devpost/hackmit-2024/traffic-forecaster"
  achievement_text: >
    First place at HackMIT 2024 for a traffic-forecasting prototype
    built in 48 hours using Python, PyTorch, and public open-data
    APIs.
  primary_type: lbl_hackathon
  domain_tags:  [lbl_domain_ml]
  level:        national
  outcome:      winner
  event_name:   HackMIT
  organization: MIT
  achievement_date: 2024-09-15
  rank:         1
  skills:       [python, pytorch, data_pipelines]
  annotation_status:
    primary_type: verified
    domain_tags:  verified
  is_synthetic: false
```

### Example B — ambiguous (hackathon or research?)

```yaml
- achievement_id: ach_<32 hex>
  source_id:      src_<32 hex>
  source_record_id: "arxiv/2403.12345"
  achievement_text: >
    Co-authored a NeurIPS workshop paper based on a prototype built
    during a 48-hour hackathon.
  # Reviewer call: the published paper is the primary record;
  # hackathon context goes in notes on the Annotation row.
  primary_type: lbl_research_pub
  domain_tags:  [lbl_domain_ml]
  level:        international
  outcome:      accepted
  event_name:   "NeurIPS 2024 workshop"
  organization: NeurIPS
  achievement_date: 2024-12-14
  skills:       [python, pytorch]
  annotation_status:
    primary_type: verified
    domain_tags:  verified
  is_synthetic: false
```

### Example C — synthetic test fixture

```yaml
- achievement_id: ach_<32 hex>
  source_id:      src_<32 hex>                 # a synthetic source
  source_record_id: "synthetic/test-fixture-01"
  achievement_text: "Won a university-level coding competition."
  primary_type: lbl_competition
  domain_tags:  []
  annotation_status:
    primary_type: verified
    domain_tags:  verified
  is_synthetic: true          # excluded from real-data splits by default
```

---

## Quality-review procedure

Before merging an annotation batch PR:

1. CI runs the full test suite plus `python -m
   nlp_semantic.dataset.cli validate --dataset-root hybrid_dataset`.
   The validator must report zero fatal errors.
2. A second team member reads the batch diff and spot-checks ~10% of
   records against their source material.
3. The split generator's draft output is checked for class-balance
   regressions.
4. Only after sign-off, merge the PR. No in-place edits to a
   previously-merged batch — open a new batch file or a correction
   PR that references the record IDs being revised.
