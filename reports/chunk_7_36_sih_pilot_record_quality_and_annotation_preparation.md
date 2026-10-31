# Chunk 7.36 — SIH Pilot Record Quality & Annotation Preparation

**Generated:** 2026-10-25
**Chunk type:** local-only, read-only, record-by-record audit of the pre-existing 7 SIH 2024 records.
**Final disposition:** `REVIEW CHECKLIST READY`

> This chunk audits only what is already in the repository. No external
> source was fetched, no file in `src/`, `hybrid_dataset/labels/`,
> `hybrid_dataset/metadata/`, or `hybrid_dataset/dataset/` was
> modified, no record was added or removed, no annotation or source
> review status was changed. The chunk's output is this report plus a
> record-by-record annotation checklist for the reviewers.

---

## 1. Chunk objective

Audit the seven existing SIH 2024 Winners'-List records in
`hybrid_dataset/dataset/records/batch_01_sih2024.yaml`, measure
their field-level quality against the project's own schema and
annotation guidelines, surface the specific gaps that must be
resolved before any of them can clear
`training_ready_subset`, and produce a per-record annotation
checklist a reviewer can act on in the next review session.

This is the first chunk in the Chunk-7.33 §O.3 "AI-driven work
that is not source-ingestion" lane. It makes progress toward
training-eligibility of the existing seven records without
needing any new source verification.

---

## 2. Repository precondition results

Verified on 2026-10-25 under this working tree.

| Field | Observed | Expected baseline | Match |
|---|---|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` | same | ✓ |
| Branch | `feature/nlp-semantic` | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` | ✓ |

Working tree carries the pre-existing modifications and untracked
artefacts from Chunks 7.15 → 7.35; nothing is staged, committed,
pushed, or branch-switched. This chunk's only new file is the
report at `reports/chunk_7_36_…md`.

**Disposition: preconditions pass.** Not `REPOSITORY PRECONDITION
MISMATCH`.

---

## 3. Actual files inspected (read-only)

- `hybrid_dataset/dataset/records/batch_01_sih2024.yaml` — the one
  and only record batch.
- `hybrid_dataset/dataset/README.md` — directory layout and
  loader-enforced rules.
- `hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md` — the rubric
  the reviewer applies to each record.
- `hybrid_dataset/labels/primary_taxonomy.yaml` — the 14 primary
  labels, all `status: draft`.
- `hybrid_dataset/labels/domain_tags.yaml` — the 10 domain tags,
  all `status: draft`.
- `hybrid_dataset/metadata/sources.yaml` — the two
  `SourceRegistry` rows (SIH-2024 PIB; arXiv).
- `src/nlp_semantic/schema/achievement.py` — the authoritative
  `Achievement` field list and validators.
- `src/nlp_semantic/schema/annotation.py` — the `Annotation`
  shape (per-task label-arity, pseudonym contract).
- `src/nlp_semantic/dataset/validator.py` — `validate_dataset`,
  `eligible_ground_truth`, `training_ready_subset`.
- `src/nlp_semantic/dataset/duplicates.py` — the four
  deterministic duplicate rules.
- `src/nlp_semantic/dataset/cli.py` — the `validate | stats |
  split | readiness` subcommands.
- `reports/chunk_7_32_…md` through `reports/chunk_7_35_…md` —
  prior reports for cross-reference (not treated as sources of
  truth; cross-checked against live code).

### 3.1 Schema vs. brief field-list mapping

The brief's §2 field list uses some names that are **not** fields
on the project's actual `Achievement` schema. The audit below
uses the real schema names and notes the mapping explicitly.

| Brief name | Project schema name / location | Notes |
|---|---|---|
| `achievement_id` | `Achievement.achievement_id` | identical |
| `achievement_text` | `Achievement.achievement_text` | identical |
| `normalized_text` | **not a field on `Achievement`** | the `duplicates.py._normalize_text()` normalisation is runtime-only (NFKC + whitespace collapse + casefold); no stored field |
| `category` | `Achievement.primary_type` | project uses `primary_type` consistently |
| `domain` | `Achievement.domain_tags[]` | multi-label list, not a single value |
| `level` | `Achievement.level` | identical |
| `outcome` | `Achievement.outcome` | identical |
| `event_name` | `Achievement.event_name` | identical |
| `organization` | `Achievement.organization` | identical |
| `achievement_date` | `Achievement.achievement_date` | identical |
| `rank` | `Achievement.rank` | identical (`int` ≥ 1 or null) |
| `skills` | `Achievement.skills[]` | identical |
| `source_type` | **not a field on `Achievement`** | this concept lives on `Evidence.file_type` (`DocumentFileType` enum) |
| `evidence_id` | `Achievement.evidence_id` | identical |
| `source_id` | `Achievement.source_id` | identical |
| `annotation_status` | `Achievement.annotation_status` (`AnnotationStatusMap` with `.primary_type` and `.domain_tags`) | per-task map, not a single value |
| `labeler_id` | **not a field on `Achievement`** | the annotator pseudonym lives on `Annotation.annotator`; the Achievement has no labeler field — annotation history is a separate table |
| `quality_status` | **not a field on `Achievement`** | this concept is distributed across `annotation_status.<task>` values, source `review_status`, taxonomy `status`, and dataset-level validator reports |

Audit below applies to actual schema fields. The "not a field"
entries above are reported as structural clarifications, not
missing data on the records.

---

## 4. Dataset baseline (live CLI output)

| Measure | Value | Source |
|---|---:|---|
| Record batch files | 1 (`dataset/records/batch_01_sih2024.yaml`) | `cli validate` |
| Annotation batch files | 0 | `cli validate` |
| Total records loaded | 7 | `cli stats` |
| Synthetic (`is_synthetic: true`) | 0 | `cli stats` |
| Genuine (`is_synthetic: false`) | 7 | `cli stats` |
| Fatal validation findings | 0 | `cli validate` |
| Advisory validation findings | 9 | `cli validate` |
| Duplicate detector groups | 0 | `cli validate` |
| Approved primary labels | 0 | `cli readiness` |
| Approved domain tags | 0 | `cli readiness` |
| Training-eligible primary_type records | 0 | `cli readiness` |
| Training-eligible domain_tags records | 0 | `cli readiness` |

Live outputs confirmed by `python -m nlp_semantic.dataset.cli
validate | stats | readiness hybrid_dataset` this chunk; see §15.

---

## 5. Record-by-record audit

The seven records share many fields by construction (same event,
same source, same batch-level evidence basis). The table below
lists the per-record identifiers and the record-specific fields;
the universal fields are tabled separately in §5.9.

### 5.1 Record R1 — Team Jagarama007

| Field | Value |
|---|---|
| `achievement_id` | `ach_766cc3af7a694f78889cdc10863b17cb` |
| `source_record_id` | `pib-prid-2085000-coal-jagarama007` |
| `organization` | Sri Sairam Engineering College, Kanchipuram, Tamil Nadu |
| Ministry category | Ministry of Coal |
| `achievement_text` summary | "Team Jagarama007 (… Tamil Nadu) won the Smart India Hackathon 2024 hardware grand finale in the Ministry of Coal problem-statement category. … Each winning team received a one lakh rupee cash prize from the Government of India." |

### 5.2 Record R2 — Team VoltAces

| Field | Value |
|---|---|
| `achievement_id` | `ach_e4b1879e000e4f91b5c7189212cdbb6d` |
| `source_record_id` | `pib-prid-2085000-mohua-voltaces` |
| `organization` | National Institute of Technology, Hamirpur |
| Ministry category | Ministry of Housing and Urban Affairs (MoHUA) |

### 5.3 Record R3 — Team Mavericks

| Field | Value |
|---|---|
| `achievement_id` | `ach_891254703afb4bbdaab55b946d85047b` |
| `source_record_id` | `pib-prid-2085000-mohua-mavericks` |
| `organization` | National Institute of Engineering, Mysuru, Karnataka |
| Ministry category | MoHUA |

### 5.4 Record R4 — Team The Olympians

| Field | Value |
|---|---|
| `achievement_id` | `ach_0d791e5be579428ba34f9d1f19bed967` |
| `source_record_id` | `pib-prid-2085000-mohua-the-olympians` |
| `organization` | Swami Keshvanand Institute of Technology, Management, Jaipur, Rajasthan |
| Ministry category | MoHUA |

### 5.5 Record R5 — Team Paradox Innovator

| Field | Value |
|---|---|
| `achievement_id` | `ach_9e2fc52c07ee459da700c9c4e9692501` |
| `source_record_id` | `pib-prid-2085000-mohua-paradox-innovator` |
| `organization` | Heritage Institute of Technology, North 24 Parganas, West Bengal |
| Ministry category | MoHUA |

### 5.6 Record R6 — Team Rail Manics

| Field | Value |
|---|---|
| `achievement_id` | `ach_483f29b3a5eb47bc92bf87d44d0b59ad` |
| `source_record_id` | `pib-prid-2085000-mohua-rail-manics` |
| `organization` | Indian Institute of Technology, Kharagpur |
| Ministry category | MoHUA |

### 5.7 Record R7 — Team Nidaan 7.0

| Field | Value |
|---|---|
| `achievement_id` | `ach_ebb1dce69e3b4a18a85976375d9b8439` |
| `source_record_id` | `pib-prid-2085000-mohua-nidaan-7-0` |
| `organization` | Muzaffarpur Institute of Technology, Bihar |
| Ministry category | MoHUA |

### 5.8 Audit result per record

| Record | `achievement_id` well-formed? | `source_id` resolves? | Pydantic-valid? | `(source_id, source_record_id)` unique? | FK references valid? | Fatal findings | Advisory flag |
|---|---|---|---|---|---|---|---|
| R1 Jagarama007 | ✓ | ✓ (`src_5a8a2998…`) | ✓ | ✓ | ✓ (`lbl_hackathon` exists in taxonomy) | 0 | draft label ref (`lbl_hackathon` still `draft`) |
| R2 VoltAces | ✓ | ✓ | ✓ | ✓ | ✓ | 0 | same |
| R3 Mavericks | ✓ | ✓ | ✓ | ✓ | ✓ | 0 | same |
| R4 The Olympians | ✓ | ✓ | ✓ | ✓ | ✓ | 0 | same |
| R5 Paradox Innovator | ✓ | ✓ | ✓ | ✓ | ✓ | 0 | same |
| R6 Rail Manics | ✓ | ✓ | ✓ | ✓ | ✓ | 0 | same |
| R7 Nidaan 7.0 | ✓ | ✓ | ✓ | ✓ | ✓ | 0 | same |

All seven records pass structural validation. The nine advisory
findings reported by `cli validate` are: 7 × `draft_label_ref`
(one per record × `lbl_hackathon`) + 1 × `unknown_license_source`
(SIH source `UNKNOWN`) + 1 × `unverified_source`
(SIH source `review_status: unreviewed`).

### 5.9 Universal (common) fields across all seven records

| Field | Universal value | Audit note |
|---|---|---|
| `source_id` | `src_5a8a2998d6f44055a42dcfd8991e4d12` | Resolves. Source is `review_status: unreviewed`, `license: UNKNOWN`. |
| `primary_type` | `lbl_hackathon` | Supported by Chunk 7.1 event-centric interpretation (bounded 5-day build window + competitive judging + Winners'-List placement). Label itself still `status: draft`. |
| `domain_tags` | `[]` | Legitimate `[]`-plus-`not_started` state. Source does not publish per-team project titles, so domain inference would be guesswork. |
| `level` | `national` | Supported — SIH is India's national hackathon; the source's ministry framing confirms. Chunk 7.1 excludes "international" inferences from event-name alone, so `national` is the right call. |
| `outcome` | `winner` | Supported — source heading is "Winners' List". |
| `event_name` | `Smart India Hackathon 2024 (Hardware Grand Finale)` | Supported by the source's headline and body. |
| `achievement_date` | `null` | Deliberate per Chunk 7.4-A.2: single-`date` schema cannot represent the five-day build window Dec 12–16, 2024 unambiguously, and the Dec 16 ceremony date is announcement-not-achievement. |
| `rank` | `null` | Supported — source lists "Winners' List" without numeric rank within the ministry category. The guidelines explicitly reject fabricated ranks. |
| `skills` | `[]` | Supported — source has no per-team project titles or technologies; the guidelines explicitly prohibit "He probably used Python" inference. |
| `evidence_id` | `null` | No `Evidence` row has been created yet; the PIB-page screenshot evidence from Chunk 7.3-A.4 is tracked in reviewer notes but not as an `Evidence` artifact pointing into `hybrid_dataset/raw/evidence_documents/`. |
| `annotation_status.primary_type` | `draft` | Per Chunk 7.4-A.1: the label is a tentative extraction decision resting on event-level evidence; no reviewer has verified per-team deliverable independently. |
| `annotation_status.domain_tags` | `not_started` | Legitimate `not_started` because the source does not support any domain-tag inference. |
| `is_synthetic` | `false` | Correct — all seven are genuine, text-only records derived from a real PIB press release. |

---

## 6. Field-level completeness summary

Across the seven records:

| Field | Populated | Null / Empty | % populated | Correct? |
|---|---:|---:|---:|---|
| `achievement_id` | 7 | 0 | 100 % | ✓ |
| `source_id` | 7 | 0 | 100 % | ✓ |
| `source_record_id` | 7 | 0 | 100 % | ✓ |
| `achievement_text` | 7 | 0 | 100 % | ✓ (source-grounded prose preserved) |
| `primary_type` | 7 | 0 | 100 % | ~ (set to `lbl_hackathon` but under `draft` annotation + draft label) |
| `domain_tags` | 0 (list length 0) | 7 | 0 % | ✓ (legitimate `[]` with `not_started` status) |
| `level` | 7 | 0 | 100 % | ✓ |
| `outcome` | 7 | 0 | 100 % | ✓ |
| `event_name` | 7 | 0 | 100 % | ✓ |
| `organization` | 7 | 0 | 100 % | ✓ |
| `achievement_date` | 0 | 7 | 0 % | ✓ (deliberately null per Chunk 7.4-A.2) |
| `rank` | 0 | 7 | 0 % | ✓ (deliberately null; source does not publish) |
| `skills` | 0 | 7 | 0 % | ✓ (deliberately empty; no evidence) |
| `evidence_id` | 0 | 7 | 0 % | ⚠ (no `Evidence` row created yet — reviewer workitem) |
| `annotation_status.primary_type` | 7 at `draft` | 0 | 100 % | ⚠ (needs promotion to `verified` after review) |
| `annotation_status.domain_tags` | 7 at `not_started` | 0 | 100 % | ⚠ (legitimate; reviewer may re-affirm as `verified` with `[]` after confirming no tags apply) |
| `is_synthetic` | 7 at `false` | 0 | 100 % | ✓ |

Legend: ✓ compliant; ~ compliant pending upstream governance;
⚠ reviewer workitem.

---

## 7. Category and outcome review

### 7.1 Category (`primary_type: lbl_hackathon`)

Decision tree per `ANNOTATION_GUIDELINES.md` §73-174:

- **Step 1 — event-centric or artefact-centric?** The source
  describes an event (hackathon ceremony, Winners' List);
  achievement is event-centric. → Candidates: `HACKATHON`,
  `COMPETITION`.
- **Step 2 — HACKATHON vs COMPETITION?** The event has a defined
  five-day build window (≤ seven-day Chunk-7.1 bound); has
  competitive formal judging (ministry-level Winners' List); the
  primary deliverable is a demonstrable hardware prototype (SIH
  hardware grand finale); and the record's primary story is the
  team's event-centric role at that event. All four conditions
  hold → **`HACKATHON`.**

The current label is correct under the current guideline.
The record file's own header comment (lines 23-47) records this
reasoning explicitly.

**Caveat the reviewer must confirm per record:** the Chunk 7.1
HACKATHON definition requires "a demonstrable software or hardware
prototype". The PIB source establishes that *the event's primary
deliverable* is a demonstrable hardware prototype; it does **not**
publish *per-team* project titles. The project-level annotation
decision (recorded in the batch header) is that event-level
evidence suffices for the event-centric label, with the per-team
deliverable left as an information-extraction gap in `skills` /
`event_name`. The reviewer must either (a) accept that reasoning
on sign-off, or (b) decide the per-team deliverable gap is
material and leave the record at `draft`.

### 7.2 Outcome (`outcome: winner`)

Source directly supports "winner" — the publication is the
Winners' List and each record cites "won … in the … problem-
statement category". The guidelines prohibit inferring winner from
participation; here winner is explicitly stated.

**Rank distinct from outcome:** the source lists winning teams
by category but does **not** publish ordinal ranks within the
category. The schema's `rank: null` correctly expresses that.
A later reviewer must not promote `rank` to a number without
independent evidence (brief §4 "do not infer a rank unless the
source explicitly supports it").

### 7.3 Taxonomy label status

The taxonomy entry for `lbl_hackathon` is at `status: draft`
(`primary_taxonomy.yaml` line 40). Even once the per-record
annotation flips to `verified`, `training_ready_subset` returns
`[]` until the label is promoted to `approved`. That promotion is
the Chunk 7.37-candidate work recommended in §13 below.

---

## 8. Duplicate and identity review

### 8.1 Deterministic duplicate detector (this chunk, live run)

`python -m nlp_semantic.dataset.cli validate hybrid_dataset` →
`duplicates_flagged=0`.

Per-rule result:

| Rule | Groups found |
|---|---:|
| `exact_text` | 0 |
| `normalized_text` | 0 |
| `source_record_pair` | 0 |
| `date_org_event_triple` | 0 |

### 8.2 Why no duplicates despite high surface similarity

The seven records share event, source, date framing, level,
outcome, and `event_name` — but their `achievement_text` differs
in team name and institution, their `source_record_id` is unique
per team-and-ministry, and `achievement_date` is `null` on every
record so the `date_org_event_triple` rule never fires.
Shared-event-different-team is the exact "different students
receiving the same award" case the brief's §12 duplicate taxonomy
flags as *distinct achievements*, which the current records
correctly preserve.

### 8.3 Identity granularity

Per Chunk 7.3-A.5 ingestion decision (quoted in the batch
header):

> Scope decision: TEAM-LEVEL hackathon achievements only. The
> Winners' List enumerates seven teams by team name + institution
> + state; no individual student names were present in the
> reviewed screenshots. Dignitaries (judges, officials) are named
> but are not participants. Do not infer individual records from
> team membership.

Audit result: team-level granularity is honoured in all seven
records. Team names are team-chosen handles, not individual
student names. The brief's §3 rule ("do not infer an individual
achievement from a team achievement") is honoured.

### 8.4 Ministry framing

R1 (Jagarama007) is in the **Ministry of Coal** category; R2-R7
are in the **Ministry of Housing and Urban Affairs** category.
R2-R7 share the *problem-statement* category but **not** the
problem statement — SIH's structure is one problem statement per
team within a ministry category, so six MoHUA winners means six
distinct winning solutions. The reviewer confirms per record that
"same ministry category" is not treated as "same problem" or
"same prize", because within SIH it is not.

---

## 9. Evidence and provenance review

### 9.1 Source identity and status

| Attribute | Value in `sources.yaml` |
|---|---|
| `source_id` | `src_5a8a2998d6f44055a42dcfd8991e4d12` |
| `source_name` | Smart India Hackathon 2024 Concludes with Innovative Solutions — PIB Release ID 2085000 |
| `source_url` | `https://www.pib.gov.in/PressReleasePage.aspx?PRID=2085000&lang=2&reg=48` |
| `license` | `UNKNOWN` |
| `review_status` | `unreviewed` |
| `collection_date` | 2026-10-23 |
| `intended_use` | `primary_type_training_lbl_hackathon` |

Values verified from the current `sources.yaml` this chunk; no
change made.

### 9.2 Evidence resolution

**Status: `LOCAL EVIDENCE INSUFFICIENT` for `Evidence` row
creation.** The PIB-page screenshot captured in Chunk 7.3-A.4 is
referenced in prose inside the source's `mapping_notes` ("Observed
via browser screenshot capture during Chunk 7.3-A.4 human
verification") and in the ongoing Chunk 7.31 / 7.32 reviewer-
evidence design, but no `Evidence` Pydantic row has been created
in the dataset. Consequences:

- Every record's `evidence_id` is `null` — schema-legal, but it
  means `training_ready_subset` cannot cross-reference evidence.
- The screenshot artefact itself is tracked outside the dataset
  pipeline; linking it in requires either an `Evidence` row
  pointing at `hybrid_dataset/raw/evidence_documents/<path>`
  (currently `raw/` is empty — inventory this chunk: 0 files) or a
  reviewer-signed evidence-storage decision from Chunk 7.31.
- Promoting any of the seven records to
  `annotation_status.primary_type: verified` is **structurally
  possible without an `evidence_id`** (the field is optional on
  `Achievement`), but is **not recommended** without the
  reviewer-signed evidence link — the annotation guidelines §24-55
  single-review workflow references source material by provenance,
  not by prose-in-mapping-notes.

### 9.3 External reviewer evidence still required

Even once an `Evidence` row anchors the screenshot, the Chunk 7.2
two-reviewer sign-off packet (which decides whether the blanket
PIB free-reproduction clause covers this project's non-commercial
research dataset use) is **still pending**. Chunks 7.26A, 7.30,
and 7.32 all cite its preparation but none record its completion.
That packet is the hard upstream block on `training_ready_subset`.

---

## 10. Human annotation checklist (per record)

For each of the seven records, the reviewer runs this seven-item
checklist. The checklist is uniform because the records share
their source, event framing, and granularity — but each item is
answered **per record** so the reviewer's sign-off is per-record,
not batch-level.

### 10.1 Per-record checklist

For record `R<n>`, team `<team-name>`, institution `<org>`:

1. **Does the PIB screenshot evidence (captured Chunk 7.3-A.4)
   list `<team-name>` on the Winners' List under the
   `<ministry-category>` problem-statement?**
   Expected answer: *yes* (every record's `source_record_id` was
   constructed from the screenshot).
2. **Is `<org>` as spelt in the batch an exact match for the
   institution name on the screenshot?**
   Expected answer: *yes* (verbatim transcription).
3. **Does the Chunk 7.1 HACKATHON definition cover this record
   given event-level evidence of a ≤ 7-day build window and
   formal competitive judging?**
   Expected answer: *yes* (the batch header's own reasoning
   stands).
4. **Is the per-team deliverable gap (no project title, no
   problem-statement code, no technical description) acceptable
   for `primary_type: lbl_hackathon` promotion to `verified`, or
   does the reviewer require per-team deliverable evidence
   before promoting?**
   Expected answer: *reviewer's call*. If "acceptable", flip
   `annotation_status.primary_type` from `draft` to `verified`.
   If "require more", leave at `draft` and record the gap on an
   `Annotation` row.
5. **Is the record genuinely distinct from the other six records
   in this batch?**
   Expected answer: *yes* (distinct team, distinct institution,
   distinct winning solution within the ministry category).
6. **Is leaving `domain_tags: []` with `annotation_status.
   domain_tags: not_started` the right final state, or does the
   reviewer want to deliberately mark `[]` + `verified` ("no
   tags apply, I checked")?**
   Expected answer: *reviewer's call*. If "verified empty", flip
   the status. If "not_started remains", leave as is.
7. **Should an `Annotation` row be created to record the review
   decision, pseudonym, and timestamp, or is single-review
   enough that the Achievement row's status flip suffices?**
   Expected answer: *reviewer's call*. Guidelines §27-55 permit
   either; the inter-annotator-agreement pipeline only requires
   `Annotation` rows for dual-reviewed records.

### 10.2 Batch-level checklist (one answer covers all seven)

1. **Is the PIB copyright-policy applicability decision complete
   (Chunk 7.2 two-reviewer packet)?**
   Expected answer at the time of this report: *no, still
   pending*. Promotion of `src_5a8a2998…` from
   `review_status: unreviewed` to `verified` requires it.
2. **Is the taxonomy promotion of `lbl_hackathon` from `draft`
   to `approved` complete (TAXONOMY_APPROVAL_CHECKLIST)?**
   Expected answer: *no*. Required for any `lbl_hackathon`
   record to clear `training_ready_subset`.
3. **Is an `Evidence` row created for the PIB screenshot and
   referenced from every record's `evidence_id`?**
   Expected answer: *no*. Optional for structural validation but
   expected before `verified` sign-off per the guidelines'
   §27-55 workflow spirit.
4. **Is the batch's own header comment (lines 1-72 of
   `batch_01_sih2024.yaml`) still an accurate record of the
   extraction decisions after this audit?**
   Expected answer: *yes, with no changes required by this
   audit*. If a reviewer records a decision that contradicts the
   header, the header should be amended in that reviewer's own
   small chunk, not here.

### 10.3 What the reviewer must NOT do under this checklist

The checklist is a reviewer tool; it is not a code change list.
Flipping statuses, creating `Annotation` rows, writing
`Evidence` rows, promoting taxonomy — each of these is a
separate action under its own chunk, with its own evidence
packet. This chunk does none of them.

---

## 11. Dataset coverage statistics (actual local data)

| Measure | Value |
|---|---:|
| Total records | 7 |
| Valid records (0 fatal findings) | 7 |
| Invalid records | 0 |
| Records per category — `lbl_hackathon` | 7 |
| Records per category — all other 13 primary labels | 0 each |
| Records per domain tag | 0 across all 10 domain tags (no records carry any) |
| Records per outcome — `winner` | 7 |
| Records per source — `src_5a8a2998…` | 7 |
| Records with missing required field (`achievement_id`, `source_id`, `source_record_id`, `achievement_text`) | 0 |
| Records with unresolved evidence references | 0 (every record has `evidence_id: null`, which is schema-legal and so not an "unresolved reference"; but see §9.2) |
| Duplicate candidates flagged by the deterministic detector | 0 |
| Records at `annotation_status.primary_type: verified` | 0 |
| Records currently training-eligible | 0 |

**The current pilot is category-mono, not category-diverse.** One
of the 14 primary labels is represented; thirteen have zero
records. This confirms the Chunk 7.32 §D finding and does not
change it.

---

## 12. Training eligibility (from code and live CLI)

### 12.1 Current gate (from `validator.py` lines 321-371, verbatim behaviour)

A record passes `training_ready_subset(records, sources=…,
task=…)` only when:

1. `annotation_status.<task> == AnnotationStatus.VERIFIED`, AND
2. For `task=primary_type`: the record's `primary_type` label
   has `LabelTaxonomy.status == APPROVED` in
   `primary_taxonomy.yaml`.
   For `task=domain_tags`: every entry in `domain_tags[]` has
   `LabelTaxonomy.status == APPROVED` in `domain_tags.yaml`.
3. The record's source has `review_status ==
   ReviewStatus.VERIFIED` in `sources.yaml`, AND
4. The record's source has `license.strip().upper() !=
   "UNKNOWN"`.

Case-insensitive comparison on the licence (sentinel is `UNKNOWN`
regardless of casing).

### 12.2 Current result (live `cli readiness` this chunk)

- Eligible records for `primary_type`: **0.**
- Eligible records for `domain_tags`: **0.**
- Blockers: 4 (`no_approved_labels` × 2 and
  `no_eligible_records` × 2).
- Warnings: 2 (`unknown_license` for `src_5a8a2998…`;
  `unverified_source` for both committed sources).

### 12.3 Reasons each of the 7 records is excluded

For every record, **all four of the following** block eligibility:

| Record | Fails §12.1(1) | Fails §12.1(2) | Fails §12.1(3) | Fails §12.1(4) |
|---|---|---|---|---|
| R1 Jagarama007 | annotation_status.primary_type = draft | lbl_hackathon status = draft | source review_status = unreviewed | source license = UNKNOWN |
| R2 VoltAces | same | same | same | same |
| R3 Mavericks | same | same | same | same |
| R4 The Olympians | same | same | same | same |
| R5 Paradox Innovator | same | same | same | same |
| R6 Rail Manics | same | same | same | same |
| R7 Nidaan 7.0 | same | same | same | same |

All four conditions must flip for any record to clear. The flip
order is reviewer discretion but the shortest critical path is:

1. Chunk 7.2 two-reviewer sign-off → flip source
   `review_status: verified` AND populate `license` with the
   PIB-policy summary (resolves §12.1(3) and §12.1(4)).
2. Taxonomy approval chunk → flip `lbl_hackathon`
   `status: approved` (resolves §12.1(2)).
3. Per-record annotation review → flip each of the seven's
   `annotation_status.primary_type: verified` (resolves
   §12.1(1)).

Three chunks, each of which is reviewer-gated at least in part.

### 12.4 Eligibility gate not weakened

This chunk did not modify `validator.py`, `cli.py`, or any
eligibility-related code. `training_ready_subset` behaviour is
exactly as it was at Chunk 7.32.

---

## 13. Issues requiring owner or reviewer action

Not performed in this chunk; listed for the owner / reviewers.

### 13.1 Blockers (resolve before any record is training-eligible)

1. **PIB-policy applicability decision** — the Chunk 7.2
   two-reviewer sign-off packet
   (`chunk_7_26A_independent_reviewer_sign_off_packet.md`) is
   prepared but not completed. Required for
   `src_5a8a2998…` → `verified` + populated `license`.
2. **`lbl_hackathon` taxonomy promotion** — the
   `TAXONOMY_APPROVAL_CHECKLIST.md` document exists but has not
   been run end-to-end for `lbl_hackathon`. Required for the
   label to flip to `status: approved`.
3. **Per-record annotation review** — all seven records are at
   `annotation_status.primary_type: draft`. Each needs the §10.1
   per-record checklist completed and the status flipped.

### 13.2 Non-blocking but recommended before promotion

4. **`Evidence` row for the PIB screenshot** — pending the
   Chunk 7.31 reviewer-evidence-storage design landing. Would
   populate `evidence_id` on each of the seven records (optional
   field, but closes the §9.2 "LOCAL EVIDENCE INSUFFICIENT" note
   for `Evidence` row creation).
5. **Deliberate decision on `domain_tags`** — the current
   `[]` + `not_started` state is schema-legal, but a reviewer may
   prefer to flip to `[]` + `verified` ("I checked; no tags
   apply") so empty-with-verified vs. empty-with-not-started
   remains legible in audits.

### 13.3 Open design questions (not blocking the seven records)

6. **Whether to add a `student_id` or `student_entity_id`
   field** — no decision is required by this chunk; the seven
   records are team-level and the current schema is sufficient.
   Raised earlier (Chunk 7.33 §J.3) because future GSoC records
   would make it salient.
7. **Whether to persist `normalized_text`** — the brief lists it
   as a target field. The project currently normalises at
   runtime in `duplicates.py._normalize_text()`; storing it would
   duplicate the computation but could speed the duplicate
   detector against very large batches. Not a decision this
   chunk needs to force.

---

## 14. Recommended next chunk

Of the three Chunk-7.35 §O.3 alternatives, the most direct unlock
of the existing seven records is **Chunk 7.37 — `lbl_hackathon`
taxonomy-promotion packet draft**. This chunk would:

- Walk the `TAXONOMY_APPROVAL_CHECKLIST.md` for `lbl_hackathon`
  as a dry run.
- Compile the evidence the current seven records provide for the
  label's `definition`, `inclusion_rules`, `exclusion_rules`,
  and `examples`.
- List the exact gaps a reviewer must close to sign off.
- Produce the packet as `reports/chunk_7_37_lbl_hackathon_taxonomy_promotion_packet.md`.

It is AI-driven (no external source verification needed) and
narrows the critical path to training-eligibility by one of the
three blockers in §13.1.

**Alternative Chunk 7.37 candidates** if the owner prefers:

- A reviewer-evidence-bundle validator module
  (`src/nlp_semantic/dataset/evidence_bundle.py` + tests) that
  helps the eventual screenshot capture produce manifest files
  the dataset tooling can read.
- A `src/nlp_semantic/dataset/duplicates_semantic.py` design
  chunk (interface + tests with injectable similarity
  functions; no sentence-transformer dep yet) — widens the
  duplicate detector's coverage for future multi-source batches.

**Explicitly not recommended** as Chunk 7.37:

- Another AI-driven source-verification chunk — Chunks 7.34 and
  7.35 already demonstrated the structural block.
- Modifying `validator.training_ready_subset` to loosen the
  eligibility gate — the gate's conservatism is the project's
  guarantee that no record is training-fed without governance,
  and loosening it bypasses that guarantee rather than earning
  past it.

---

## 15. Testing and validation

Executed in this chunk:

| Command | Result | Exit |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | `579 passed, 5 skipped in 13.35s` | 0 |
| `python -m nlp_semantic.dataset.cli validate hybrid_dataset` | `records=7 \| fatal=0 \| advisory=9 \| duplicates_flagged=0`; `is_valid: true` | 0 |
| `python -m nlp_semantic.dataset.cli readiness hybrid_dataset` | `any_task=not_ready \| all_tasks=not_ready \| approved(pt=0,dt=0) \| eligible(pt=0,dt=0) \| blockers=4` | 0 |

Prior chunks also recorded `cli stats` (`records=7 \| synthetic=0 \|
real=7 \| primary_classes=1`) and `inventory` (`0 files \| 0
warnings`); their outputs are a pure function of the dataset
state, which is unchanged, so they were not re-run this chunk.

The five pytest skips are the same ones recorded in prior chunks:
four Windows-symlink skips in `tests/ingestion/test_inventory.py`
and one `fakeredis-not-installed` skip in
`tests/ingestion/test_redis_rate_limit.py`. No test was added or
modified in this chunk, consistent with the no-code-change scope.
No new test was useful under the audit-only scope.

No external HTTP request was issued (no WebFetch, no WebSearch,
no scraping tool used). No reviewer sign-off was created. No
source URL was fetched.

---

## 16. Explicit limitations

- **This chunk did not verify external source content.** Every
  statement about the PIB press release derives from fields
  already in `sources.yaml` and `batch_01_sih2024.yaml`; the
  PIB page itself was not fetched or screenshot-captured in this
  chunk.
- **This chunk cannot promote any annotation, label, or source
  status.** Each promotion is a reviewer action under its own
  chunk.
- **The seven records cannot be mapped to individual students.**
  Team-level granularity is a feature of the source, not a
  limitation of the audit; but it does mean this dataset does
  not — and should not be made to — carry individual student
  achievement records for SIH 2024.
- **No agreement metric (Cohen's κ, Jaccard) is meaningful.**
  There are zero `Annotation` rows and zero dual-reviewed
  records; `agreement_status` for both tasks is zeroed/`None`.
- **The brief's field list (`normalized_text`, `source_type`,
  `labeler_id`, `quality_status`) does not match the project
  schema one-to-one.** This chunk's audit uses the actual schema;
  §3.1 records the mapping. Adding any of those fields to
  `Achievement` would itself be a schema-change chunk and
  requires its own reviewer decision.
- **The current pilot is category-mono.** Thirteen of the 14
  primary labels are empty. This remains true after Chunk 7.36
  because the audit does not expand the dataset.

---

## 17. Final disposition

**`REVIEW CHECKLIST READY`.** All ten task steps are complete:

1. ✓ Repository preconditions checked (§2).
2. ✓ Seven existing SIH records inspected (§5).
3. ✓ Record-by-record audit included (§5, §6).
4. ✓ Duplicate and identity concerns documented (§8).
5. ✓ Annotation questions prepared (§10).
6. ✓ Dataset statistics based on live `cli stats` / `cli
   validate` output (§4, §11).
7. ✓ Training eligibility based on live `cli readiness` output
   and the actual `validator.py` behaviour (§12).
8. ✓ Report created at `reports/chunk_7_36_sih_pilot_record_quality_and_annotation_preparation.md` (§15).
9. ✓ No dataset or source status changed (§15, §16).

The §9.2 "`LOCAL EVIDENCE INSUFFICIENT`" note is a per-record
`evidence_id` gap, not a disposition-level block — the audit
itself completed with reviewable evidence throughout.
