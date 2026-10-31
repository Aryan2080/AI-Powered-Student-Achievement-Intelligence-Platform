# Chunk 7.37 — `lbl_hackathon` Taxonomy Promotion Packet

**Generated:** 2026-10-25
**Chunk type:** taxonomy review preparation (packet only).
**Final disposition:** `PACKET READY FOR REVIEW`

> Scope: compile the evidence a reviewer needs to decide whether
> `lbl_hackathon` should move from `status: draft` through
> `under_review` to `approved` in
> `hybrid_dataset/labels/primary_taxonomy.yaml`. The packet does
> **not** itself approve the label, does **not** modify the taxonomy,
> does **not** change any annotation / source / review status, and
> does **not** open a promotion PR. The packet is this report; the
> promotion PR, the two independent reviewer sign-off comments, and
> the status-flip commit are reviewer actions that happen outside
> this chunk.

---

## 1. Chunk objective

Walk the official `TAXONOMY_APPROVAL_CHECKLIST.md` end-to-end
against the current `lbl_hackathon` YAML row and the seven
existing SIH 2024 Winners'-List records, surface every reviewer-
answerable question in one place, and give the reviewers an
unambiguous starting point for the Chunk-7.2 two-independent-
sign-off workflow.

The approval of `lbl_hackathon` is the first of the three
blockers that must flip for the existing seven records to clear
`training_ready_subset` (see Chunk 7.36 §12.3 for the full
critical path). This chunk is `Alternative Chunk 7.37 — AI-driven
work that is not source-ingestion` from Chunk 7.35 §O.3 and the
`Recommended next chunk` from Chunk 7.36 §14.

---

## 2. Repository precondition results

Verified on 2026-10-25 under this working tree.

| Field | Observed | Expected baseline | Match |
|---|---|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` | same | ✓ |
| Branch | `feature/nlp-semantic` | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` | ✓ |

Working tree carries the pre-existing modifications and untracked
artefacts from Chunks 7.15 → 7.36; nothing is staged, committed,
pushed, or branch-switched. This chunk's only new file is this
report. **Precondition: pass.** Not `REPOSITORY PRECONDITION
MISMATCH`.

### 2.1 Files consulted (read-only)

- `hybrid_dataset/labels/primary_taxonomy.yaml` — the
  `lbl_hackathon` row (lines 12-40) plus the thirteen adjacent
  labels.
- `hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md` — the
  per-label checklist, sign-off template, reviewer-independence
  rule, disagreement workflow, preliminary-agreement-exercise
  procedure, promotion sequence.
- `hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md` — the
  HACKATHON ↔ COMPETITION ↔ PROJECT boundary rubric (§73-174)
  and the per-label quick guide (§178-206).
- `hybrid_dataset/dataset/records/batch_01_sih2024.yaml` — the
  seven existing records that any overlap-check exercise can be
  run against.
- `hybrid_dataset/metadata/sources.yaml` — current source status
  for the seven records' upstream source.
- `reports/chunk_7_36_sih_pilot_record_quality_and_annotation_preparation.md` —
  the per-record audit this packet builds on.
- `src/nlp_semantic/schema/enums.py` — `TaxonomyStatus` values.
- `src/nlp_semantic/schema/label_taxonomy.py` — the
  `LabelTaxonomy` Pydantic model.
- `src/nlp_semantic/schema/loader.py` — file-level invariants
  that the taxonomy YAML must satisfy.
- `src/nlp_semantic/dataset/validator.py` — how
  `training_ready_subset` consumes `status: approved`.

No file was modified.

---

## 3. Actual taxonomy definition under review

Verbatim excerpt from `hybrid_dataset/labels/primary_taxonomy.yaml`
lines 12-40:

```yaml
- label_id: lbl_hackathon
  task_name: primary_type
  display_name: Hackathon
  definition: >
    Event-centric achievement: participation, placement, or team role in
    a competitive, bounded build event with a defined build window of up
    to seven calendar days, in which participants work toward a
    demonstrable software or hardware prototype, implementation, or
    minimum viable product. The record classifies the student's
    event-centric achievement (participation / role / placement), not
    the long-term evolution of any artifact built during the event.
  inclusion_rules:
    - In-person or virtual hackathons organized by universities, companies, or communities, with a defined build window of up to seven calendar days
    - Role-based participation (developer, designer, team lead) and placement (winner, runner-up, finalist) both qualify when the event meets the definition
    - Judged participation is sufficient; a documented placement is not required when competitive or formal judging is supported by evidence
    - The deliverable at the end of the build window must be a demonstrable software or hardware prototype, implementation, or MVP
  exclusion_rules:
    - Events whose defined build window exceeds seven calendar days do not qualify as HACKATHON even if organizers market them that way; evaluate PROJECT, COMPETITION, or OTHER instead
    - Multi-week asynchronous programs with periodic submissions and no single bounded build window do not automatically qualify as HACKATHON; evaluate PROJECT or COMPETITION where applicable
    - Hackathon-shaped workshops with no competitive judging belong to WORKSHOP
    - Algorithmic contests primarily judged through scored solutions or benchmark performance belong to COMPETITION, not HACKATHON
    - A certificate of participation alone does not establish that an event meets this definition; evaluate the underlying event and its evidence
    - Course-assigned project work with no bounded competitive build window is PROJECT, not HACKATHON
    - Materially distinct productization or further independent development after a hackathon may be recorded separately as PROJECT; do not duplicate the same underlying claim
  examples:
    - Won first place at HackMIT 2024 — 36-hour judged build event with a working prototype
    - Team captain at Smart India Hackathon 2023 — built a traffic-prediction prototype in a 48-hour build window
    - Participant at ETHGlobal Online 2024 — bare judged participation at a bounded build event
  status: draft
```

The excerpt is quoted here so the reviewer does not have to
cross-reference the YAML file to run the Chunk-7.2 workflow.

---

## 4. Current taxonomy status

| Field | Value |
|---|---|
| `label_id` | `lbl_hackathon` |
| `task_name` | `primary_type` |
| `display_name` | Hackathon |
| `status` | `draft` |
| `supersedes` | (not set — this is the original definition, not a renamed label) |
| Position in `primary_taxonomy.yaml` | first entry (lines 12-40) |

Status machine (from `src/nlp_semantic/schema/enums.py`):
`draft → under_review → approved → deprecated`. This chunk does
not transition the status; a Chunk-7.2 promotion PR does.

Promotion-sequence position (from checklist §252-268):
`lbl_hackathon` is **label #1** of the suggested first-review
order (`lbl_hackathon` → `lbl_competition` → `lbl_project`), so
it is the appropriate first label to review.

---

## 5. Existing SIH evidence summary

Seven genuine records in `batch_01_sih2024.yaml`, all currently
labeled `lbl_hackathon`. From the Chunk 7.36 audit:

- All seven are at `annotation_status.primary_type: draft`.
- All seven cite source `src_5a8a2998d6f44055a42dcfd8991e4d12`
  (SIH 2024 PIB press release PRID 2085000).
- The source is `review_status: unreviewed`, `license: UNKNOWN`
  (pending Chunk 7.2 two-reviewer sign-off on PIB-policy
  applicability).
- The seven records are team-level only; no individual student
  identifiers.
- All seven describe the same event (SIH 2024 hardware grand
  finale, Dec 12-16, 2024 at MIT-ADT University, Pune).
- Six are MoHUA-category winners; one is Ministry-of-Coal winner.
- No duplicates detected across the four deterministic rules.

**What the SIH records demonstrate about `lbl_hackathon`:**

- An event with a defined 5-day build window (within the ≤ 7-day
  bound of the definition's inclusion rule 1).
- Formal competitive judging (ministry-level Winners' List).
- A hardware prototype as the primary deliverable (within the
  "software or hardware prototype … or minimum viable product"
  scope).
- Winner outcome supported by evidence (not inferred from
  participation).
- Team-level identification (not individual, not conflated with
  the broader institution).

**What they do NOT demonstrate about `lbl_hackathon`:**

- Software hackathons.
- Shorter events (24-36 hour build windows).
- Online / virtual events.
- Non-winning participants.
- Judged-participation-without-placement cases.
- International-level events.
- Non-governmental hackathons.
- Per-team deliverable-level evidence.

The second list is the empirical narrowness the reviewer must
weigh against the breadth of the definition itself.

---

## 6. Record-by-record taxonomy applicability

For each of the seven records (per Chunk 7.36 §5), run the Chunk 7.1
HACKATHON four-condition test. Record IDs are repeated here for the
reviewer's convenience.

| Record | Build window ≤ 7 days? | Competitive judging? | Primary deliverable is demonstrable prototype / MVP? | Primary story is event-centric? | HACKATHON applies? | Residual reviewer question |
|---|---|---|---|---|---|---|
| R1 `ach_766cc3af…` Jagarama007 (Coal) | ✓ 5-day (source §67-70) | ✓ (source "Winners' List") | ✓ event-level (SIH hardware grand finale); ⚠ per-team deliverable not published | ✓ (team winner of the event's ministry category) | ✓ under event-level evidence | Is event-level evidence sufficient, or does the reviewer want per-team deliverable confirmation? |
| R2 `ach_e4b1879e…` VoltAces (MoHUA) | ✓ | ✓ | ✓/⚠ | ✓ | ✓ | same |
| R3 `ach_89125470…` Mavericks (MoHUA) | ✓ | ✓ | ✓/⚠ | ✓ | ✓ | same |
| R4 `ach_0d791e5b…` The Olympians (MoHUA) | ✓ | ✓ | ✓/⚠ | ✓ | ✓ | same |
| R5 `ach_9e2fc52c…` Paradox Innovator (MoHUA) | ✓ | ✓ | ✓/⚠ | ✓ | ✓ | same |
| R6 `ach_483f29b3…` Rail Manics (MoHUA) | ✓ | ✓ | ✓/⚠ | ✓ | ✓ | same |
| R7 `ach_ebb1dce6…` Nidaan 7.0 (MoHUA) | ✓ | ✓ | ✓/⚠ | ✓ | ✓ | same |

The ⚠ in the deliverable column is the gap flagged in Chunk 7.4-A.1
and reaffirmed in Chunk 7.36 §5.9 and §7.1: the PIB source
establishes the *event's* primary deliverable (demonstrable
hardware prototype) and the *team's* winner status, but does **not**
publish per-team project titles or technical descriptions. The
extraction decision (quoted verbatim in `batch_01_sih2024.yaml`
lines 36-47) is that event-level evidence suffices for the
event-centric label; the reviewer's acceptance of that reasoning
is the per-record promotion gate.

**Potential ambiguity with `lbl_competition`:** none for the SIH
records. The event is a bounded build (not a scored-submission
contest), the deliverable is a prototype (not an algorithmic
submission), and the Chunk 7.1 Step 2 test resolves it to
HACKATHON on all four criteria. The exclusion rule 4
("Algorithmic contests primarily judged through scored solutions
or benchmark performance belong to COMPETITION") does not apply —
SIH is not an algorithmic benchmark contest.

---

## 7. Hackathon vs Competition boundary analysis

**Current rule (definition + inclusion/exclusion):** HACKATHON is
an event-centric ≤ 7-day bounded build whose primary deliverable
is a *demonstrable prototype / implementation / MVP*. COMPETITION
is an event-centric judged event whose primary deliverable is a
*scored, ranked, or formally judged submission or result* — e.g.
algorithmic contests scored against test cases, Kaggle leaderboard
submissions scored against a held-out benchmark, case competitions
adjudicated by panel, debates, Model UN.

**Supporting guidance:** `ANNOTATION_GUIDELINES.md` §100-134 Step 2
gives the four-condition test for HACKATHON and a parallel
definition for COMPETITION; the boundary-matrix table at
§137-152 handles the common edge cases (3-day prototype → HACKATHON;
seven-day prototype → HACKATHON; multi-week async → not HACKATHON;
Kaggle-style scored → COMPETITION; algorithmic contest → COMPETITION;
case competition → COMPETITION; competition-submission-without-
placement → COMPETITION when judged).

**Potential ambiguity (not currently in dataset):**
- A time-boxed Kaggle-adjacent challenge that includes a required
  prototype demo at the end. The deliverable determines the label:
  if the demo is the primary deliverable, HACKATHON; if the
  leaderboard rank is the primary deliverable, COMPETITION. The
  exclusion rule 4 and the boundary matrix row for "Kaggle-style
  scored data-science challenge" between them cover this.
- "Innovation Challenge" events marketed as hackathons but running
  over multiple weeks. Exclusion rule 1 handles this: the ≤ 7-day
  bound is the arbiter, not the marketing name.

**Recommended clarification:** none required for approval of
`lbl_hackathon`. The boundary is sharp and the exclusion rules
name COMPETITION explicitly. Any later refinement would be a
Refinement PR (per checklist §173-197), not a blocker on this
promotion.

**Supported by existing guidelines?** Yes.
**Reviewer approval required?** Only the standard two sign-offs
for the promotion itself — no additional revision needed to
address this boundary.

---

## 8. Other category boundary analyses

### 8.1 Hackathon vs Project

**Current rule:** HACKATHON event-centric; PROJECT artefact-centric.
Follow-on development after a hackathon can be a separate PROJECT
record only when materially distinct per Chunk 7.1 Step 4.

**Potential ambiguity:** none for the SIH records (no follow-on
work claimed). For future records: a hackathon prototype that
later becomes a long-running project should produce **two**
records if-and-only-if the follow-on is a materially distinct
achievement with its own evidence. The guidelines'
§125-134 Step 4 and §146-152 boundary-matrix row ("Hackathon
participation followed by materially distinct product development")
cover this.

**Clarification needed?** No.

### 8.2 Hackathon vs Workshop

**Current rule:** HACKATHON requires competitive formal judging;
WORKSHOP is skills-transfer with no competitive component.
Exclusion rule 3 names WORKSHOP as the adjacent target for
"hackathon-shaped workshops with no competitive judging".

**Potential ambiguity:** boundary is clean.

**Clarification needed?** No.

### 8.3 Hackathon vs Internship

**Current rule:** none *explicitly* — the two labels have different
shapes (HACKATHON is a ≤ 7-day event; INTERNSHIP is a time-bounded
professional engagement under enrolment, defined in
`primary_taxonomy.yaml` lines 113-135 to typically run multiple
weeks). GSoC was discussed in Chunk 7.35 as an `lbl_internship`
candidate, not a hackathon candidate; the shape of the two labels
makes the boundary self-evident.

**Potential ambiguity:** a reviewer might ask whether a 7-day
company "hackathon" that is actually an internship-recruiting
event should be HACKATHON or INTERNSHIP. The current wording
resolves it: if there is a defined build window ≤ 7 days with
competitive judging and prototype deliverable, HACKATHON;
otherwise INTERNSHIP.

**Clarification needed?** No. Could be added later as a minor
refinement with a one-line boundary note in both labels'
exclusion_rules, but not a promotion blocker.

### 8.4 Hackathon vs Research Publication

**Current rule:** `ANNOTATION_GUIDELINES.md` Example B (lines
356-378) handles a NeurIPS workshop paper based on a 48-hour
hackathon prototype: pick RESEARCH_PUBLICATION when the published
paper is the primary story. The exclusion rule 7 for HACKATHON
and the explicit guidance in RESEARCH_PUBLICATION's own
inclusion_rules together prevent double-counting.

**Potential ambiguity:** low. The reviewer picks the perspective
the primary story supports; they do not duplicate.

**Clarification needed?** No.

### 8.5 Hackathon vs Participation (participation-only records)

**Current rule:** inclusion rule 3 says "Judged participation is
sufficient; a documented placement is not required when
competitive or formal judging is supported by evidence". Exclusion
rule 5 says "A certificate of participation alone does not
establish that an event meets this definition". The two together
mean: participation + evidence that the event was judged = HACKATHON;
participation certificate alone (no event-level evidence of
judging) = not enough.

**Potential ambiguity:** a reviewer could reasonably ask whether
"was judged" refers to the event-as-a-whole being a judged
competition, or the specific record being personally judged. Rule
3's "when competitive or formal judging is supported by evidence"
seems to point at event-level judging; combined with rule 2
("role-based participation … both qualify when the event meets
the definition"), the natural reading is: event has judging →
any participation at that event qualifies as HACKATHON. **One of
the seven existing records (and most future records) will depend
on this reading;** the reviewer should confirm it is the intended
reading or request a refinement.

**Clarification needed?** Reviewer judgement. If the reviewer
reads this ambiguity differently, a Refinement PR to one or both
of inclusion rules 2 and 3 would be needed before promotion.

### 8.6 Hackathon as category vs winner as outcome

**Current rule:** HACKATHON is the `primary_type` label; winner
status is the `outcome` field. The two are intentionally
independent per the schema and per `ANNOTATION_GUIDELINES.md`
§197-206's quick guide. Inclusion rule 2 reinforces: "Role-based
participation … and placement … both qualify".

**Potential ambiguity:** none.

**Clarification needed?** No.

### 8.7 Summary of boundary findings

| Boundary | Current rule clear? | Clarification required for promotion? |
|---|---|---|
| HACKATHON vs COMPETITION | ✓ | No |
| HACKATHON vs PROJECT | ✓ | No |
| HACKATHON vs WORKSHOP | ✓ | No |
| HACKATHON vs INTERNSHIP | ✓ (self-evident by shape) | No |
| HACKATHON vs RESEARCH_PUBLICATION | ✓ | No |
| HACKATHON for participation-only cases | ⚠ ("judged" readable two ways) | **Reviewer decision — may or may not require a refinement first** |
| HACKATHON as category vs winner as outcome | ✓ | No |

The participation-only reading (§8.5) is the one place a reviewer
might legitimately ask for a one-line clarification before
approving. All other boundaries are sharp enough that promotion
can proceed on the current wording.

---

## 9. Generalization analysis

Scenarios that `lbl_hackathon` should either clearly cover or
clearly exclude, per §5 of the brief. These are conceptual tests
of the definition — **not** proposed dataset entries, **not**
achievement claims about specific people.

| Scenario | Current definition covers? | Current definition excludes? | Ambiguous? | Reviewer decision needed? |
|---|---|---|---|---|
| Hardware hackathon (prototype at the end) | ✓ (definition names "software or hardware prototype"; SIH is the empirical case) | — | — | No |
| Software hackathon (24-48 hour build) | ✓ (inclusion rules 1, 4; examples 1-3) | — | — | No |
| University-only hackathon | ✓ (inclusion rule 1 names universities) | — | — | No |
| National-scale hackathon | ✓ (SIH is the empirical case; level is a separate schema field) | — | — | No |
| International hackathon | ✓ (same — level is schema-separate) | — | — | No |
| Online / virtual hackathon | ✓ (inclusion rule 1 names "In-person or virtual"; example 3 is online) | — | — | No |
| Team participation (role, not placement) | ✓ (inclusion rule 2) | — | — | No |
| Individual participation (role, not placement) | ✓ (inclusion rule 2 "Role-based participation") | — | — | No |
| Winner | ✓ (inclusion rule 2; `outcome` field) | — | — | No |
| Runner-up / finalist | ✓ (inclusion rule 2) | — | — | No |
| Non-winning participant at a judged event | ✓ (inclusion rule 3 "Judged participation is sufficient") | — | ⚠ §8.5 reading | Possibly — depends on §8.5 reviewer call |
| Participation certificate without evidence of event-level judging | — | ✓ (exclusion rule 5) | — | No |
| Hackathon that runs > 7 calendar days | — | ✓ (exclusion rule 1) | — | No |
| Multi-week async "hackathon" with periodic submissions | — | ✓ (exclusion rule 2) | — | No |
| Hackathon-shaped workshop with no judging | — | ✓ (exclusion rule 3 → WORKSHOP) | — | No |
| Algorithmic / benchmark contest | — | ✓ (exclusion rule 4 → COMPETITION) | — | No |
| Course-assigned project work | — | ✓ (exclusion rule 6 → PROJECT) | — | No |

**Note on example coverage:** all three canonical examples
(HackMIT 2024, Smart India Hackathon 2023, ETHGlobal Online 2024)
describe software-oriented events. A reviewer may reasonably
observe that a hardware-hackathon example would strengthen the
`examples` field, now that the SIH 2024 batch confirms the
definition's "software or hardware prototype" phrasing is used.
Adding such an example would be a Refinement PR (status
unchanged) rather than a blocker on the promotion PR.

---

## 10. Taxonomy risks

The brief's §6 asks that actual problems be distinguished from
hypothetical future risks.

### 10.1 Actual problems supported by the repository state

1. **Pilot narrowness.** Seven records, one source, one event,
   one year. The checklist §64-70 overlap-check box asks for
   "Two annotators would independently classify a representative
   sample (3-5 records) into the same label." The sample is
   available (3-5 of the 7 SIH records can be used), but it does
   not span the plausible variety the label will see (software
   vs. hardware; winners vs. participants; short vs. long events;
   national vs. international). The reviewer should either (a)
   accept the narrow sample for the preliminary pass and note the
   limitation on the promotion PR, or (b) require the overlap
   check to run against a broader future sample before approval.
2. **Upstream source still `unreviewed` with `license: UNKNOWN`.**
   The seven records that an overlap-check reviewer would exercise
   the label against cite a source whose own review packet (Chunk
   7.26A) is still open. Running the overlap check against those
   records is **procedurally permissible** (the checklist's §201-247
   explicitly allows preliminary agreement exercises using
   illustrative or draft-grade material), but the reviewer should
   note that any "two annotators classified these the same way"
   claim is being made against records whose source is not yet
   verified.
3. **§8.5 participation-only reading** of inclusion rules 2 and 3.
   Reviewer-answerable; see §8.7.

### 10.2 Non-blocking opportunities

4. **Hardware-hackathon canonical example absent.** All three
   examples are software-oriented. A reviewer may propose adding
   a hardware-hackathon canonical example in a subsequent
   Refinement PR — this is not a promotion blocker because the
   definition itself names "software or hardware prototype"
   explicitly.
5. **Attribution on examples.** The checklist §61 asks "No example
   is a copy from a specific private source. If drawn from a real
   public source, attribution is noted; otherwise it is
   synthetic." The current three examples name real public events
   (HackMIT, SIH, ETHGlobal) but do not formally mark attribution
   or synthetic status. This is a minor refinement candidate; not
   a blocker.
6. **Chunk 7.1 provenance.** The ≤ 7-calendar-day bound derives
   from Chunk 7.1 and is baked into inclusion rule 1 and exclusion
   rule 1. The reviewer should confirm they agree with that bound
   as the arbiter; if they disagree, the whole series of SIH
   records (and the label's generalization) shifts. The current
   bound appears supported by the common understanding of
   "hackathon" and by the batch 01 records fitting cleanly inside
   it, but it is a reviewer policy call that the promotion sign-off
   implicitly ratifies.

### 10.3 Hypothetical future risks (not present today)

7. If the project ever decides to broaden HACKATHON to include
   multi-week "innovation challenges", exclusion rules 1 and 2
   and inclusion rule 1 would all need rewording. This is not a
   current proposal; mentioned only because the current wording
   is written tightly.
8. If a future source publishes individual-student hackathon
   evidence (not team-level), the schema does not store a
   `student_id` and the records would need to use the same
   impersonal-rewrite pattern. This is a schema-and-privacy
   question, not a HACKATHON definition question.

### 10.4 Risks checklist did NOT identify in the current wording

Of the possible issues the brief §6 names:

- **Definition too broad:** no — four conjunctive conditions tighten it.
- **Definition too narrow:** possibly for very-long "innovation challenges" that the project may want to include later; see §10.3-7. Not a current problem.
- **Inclusion rules overlap with competition:** no — exclusion rule 4 explicitly separates algorithmic / benchmark contests.
- **Outcome embedded in category:** no — `outcome` is schema-separate; inclusion rule 2 reinforces.
- **Event duration as unsupported universal condition:** the ≤ 7-day bound is a Chunk 7.1 project policy, not a legal fact about hackathons; see §10.2-6 — the reviewer sign-off ratifies the policy.
- **Deliverable requirements unclear:** definition and inclusion rule 4 together specify "demonstrable software or hardware prototype, implementation, or MVP". Clear.
- **Team vs individual achievement ambiguity:** inclusion rule 2 handles both.
- **Participation treated as achievement:** inclusion rule 3's phrasing is the §8.5 reviewer question.
- **Examples too narrowly based on SIH:** no — none of the three examples is SIH-2024 (SIH 2023 appears in one, HackMIT and ETHGlobal in the others). Narrower risk: all three are software; see §10.2-4.
- **Label relying on one source's wording:** no — the definition is phrased in observable terms, not quotations.
- **Insufficient negative examples:** three positive examples; the exclusion_rules carry seven negative cases implicitly. The checklist does not require explicit negative examples beyond the exclusion rules.

---

## 11. Proposed clarifications (optional, not required for promotion)

Each proposal below is tagged ⟳ **refinement** (status unchanged,
not a promotion blocker) or ⇧ **promotion-conditional** (the
reviewer may require this before approving).

### 11.1 (⟳) Add a hardware-hackathon canonical example

**Why:** rounds out §10.2-4. **Supported by current evidence?**
Yes — the SIH 2024 records fit the "hardware prototype in a
bounded build window" pattern; a synthetic example in the YAML
would describe that generically.

**Draft (if approved by a reviewer as a Refinement PR after
promotion lands):**

```yaml
examples:
  - Won first place at HackMIT 2024 — 36-hour judged build event with a working prototype
  - Team captain at Smart India Hackathon 2023 — built a traffic-prediction prototype in a 48-hour build window
  - Participant at ETHGlobal Online 2024 — bare judged participation at a bounded build event
  - Winning team at a national hardware hackathon — built a demonstrable hardware prototype in a five-day bounded build window at a judged ministry-category finale
```

Marked explicitly as synthetic / illustrative on the Refinement
PR, per checklist §61.

**Status:** proposal only; not applied to the YAML in this chunk.

### 11.2 (⇧) Clarify "judged participation" wording in inclusion rules 2-3

**Why:** addresses §8.5 potential ambiguity. **Supported by
current evidence?** Yes — the SIH records rely on the "event-level
judging implies the event is a HACKATHON for any judged
participant" reading, and the current wording is readable both
ways.

**Options for the reviewer:**

- *Option A (keep current wording).* Rely on
  `ANNOTATION_GUIDELINES.md` §100-134 Step 2 to carry the
  event-level reading; no YAML change.
- *Option B (refinement before promotion).* Rephrase inclusion
  rule 3 to pin the reading explicitly. Draft:
  "Judged participation at an event that itself meets the
  definition is sufficient; a documented individual placement is
  not required. The event-level judging must be supported by
  evidence."

**Status:** proposal only; not applied. Reviewer picks A or B.
If B, the reviewer opens a Refinement PR first, then opens the
promotion PR against the revised wording.

### 11.3 (⟳) Note attribution for the three canonical examples

**Why:** addresses checklist §61 and §10.2-5. **Supported by
current evidence?** Yes — the three events are real and public;
noting that explicitly is procedural hygiene.

**Status:** proposal only; not applied.

### 11.4 Nothing else is being proposed

The remainder of the definition, inclusion rules, and exclusion
rules is left unchanged. No proposal is made to modify the ≤ 7-day
bound, the deliverable requirement, the event-centric framing,
or the exclusion rules — each is already observable and distinct
from adjacent labels.

---

## 12. Exact reviewer questions

The two reviewers assigned to the promotion PR must answer the
following, independently and before discussion (checklist §84-107):

1. **Definition clarity.** Is the current `definition` field
   complete, specific, and self-contained? Could a reader with no
   prior exposure to this project understand what HACKATHON means
   from reading only this entry's definition?
2. **HACKATHON vs COMPETITION boundary.** Is the current wording
   sufficient to distinguish HACKATHON from COMPETITION for the
   realistic range of records the label will see? (If no, propose
   the specific sentence that would resolve your concern — this
   is a Refinement PR, not a promotion blocker you resolve
   silently.)
3. **Event-centric classification for the SIH records.** The seven
   SIH records are labeled HACKATHON on event-level evidence
   (five-day build window + ministry-level Winners' List) with
   the per-team deliverable gap (no project titles / technical
   descriptions in the source). Is this acceptable for `lbl_hackathon`
   promotion to `verified` on those records, or must per-team
   deliverable evidence be collected before any of the seven
   can clear `annotation_status.primary_type: verified`?
4. **Demonstrable prototype requirement.** Should a demonstrable
   software or hardware prototype be required for every HACKATHON
   achievement (as the current inclusion rule 4 says), or is
   event-level demonstration of competitive judging + a bounded
   build window sufficient when the per-record deliverable
   evidence is absent?
5. **Participation without placement.** Should judged participation
   without a documented placement qualify as HACKATHON (current
   inclusion rule 3), or does the project want a stricter rule?
   See §8.5 and §11.2 Option B.
6. **Category vs outcome independence.** The schema keeps `primary_type`
   and `outcome` independent. Do you agree that the HACKATHON
   label represents event type and not placement, with winner /
   finalist / participant living on `outcome`?
7. **Clarity for new annotators.** Reading only this YAML row plus
   `ANNOTATION_GUIDELINES.md` §73-174, would a new annotator
   classify a Kaggle gold-medal record (benchmark leaderboard,
   30-day window) correctly as COMPETITION rather than HACKATHON?
   A 48-hour corporate hack jam correctly as HACKATHON? A
   semester-long capstone correctly as PROJECT?
8. **Software and hardware coverage.** Is the current definition
   general enough to cover both software and hardware hackathons?
   Would you require a hardware-hackathon canonical example in
   the `examples` field (as §11.1 proposes) before approving, or
   is the SIH 2024 pilot sufficient evidence?
9. **Pilot narrowness disclosure.** Do you accept the SIH-only
   overlap-check sample as sufficient for the preliminary
   agreement exercise, with the explicit note on the promotion PR
   that the representative-sample box
   (checklist §64-70) remains open until a second, substantively
   different source lands? (See checklist §201-247 for the
   preliminary-exercise option.)
10. **Decision.** `approve`, `revise`, or `reject` — using the
    sign-off template at checklist §110-131.

**AI did not answer these.** Each reviewer must answer them
independently. The packet's job is to list them.

---

## 13. Required approval evidence

Per the checklist's §30-70 per-label boxes, the promotion PR must
carry **all** of the following in its description:

| Box | Status today | What the reviewer must do |
|---|---|---|
| Definition complete and self-contained | ✓ Appears to meet the bar; §3 excerpt available for reviewer inspection | Confirm per Q12-1 above |
| Definition distinct from every other label at task=primary_type | ✓ For 12 of 13 adjacent labels; participation-only reading (§8.5) is the one spot a reviewer may want tightened | Confirm per Q12-2 and Q12-5 |
| Edge cases addressed in inclusion / exclusion rules | ✓ Seven exclusion rules cover the common edge cases | Confirm per Q12-7 |
| ≥ 1 inclusion_rule present | ✓ Four | — |
| ≥ 1 exclusion_rule naming adjacent label(s) | ✓ Seven, naming COMPETITION / PROJECT / WORKSHOP | — |
| Rules in observable terms | ✓ Build-window length, judging presence, deliverable kind — all observable | — |
| ≥ 3 examples | ✓ Three | Reviewer may propose a 4th (§11.1); not required |
| Examples span plausible variety | ⚠ Three are software-oriented; variety across short/long/winner/participant/local/national is partial | Reviewer judgement call per Q12-8 |
| Attribution on examples | ⚠ Not explicitly noted | §11.3 refinement candidate; not a promotion blocker |
| Overlap check by a reviewer different from proposer | pending reviewer action | Each reviewer runs the §8 boundary analysis themselves |
| Two annotators independently classify 3-5 records into same label | pending reviewer action; 7 SIH records available but narrow | Reviewer runs the exercise against the SIH records OR runs the §201-247 preliminary-exercise option using the three YAML examples + the boundary-matrix rows; both must be documented on the promotion PR |
| PR touches ONE label's status field | pending — promotion PR not yet opened | Opened as a separate PR; this chunk prepares the packet, not the PR |
| PR notes two reviewer sign-offs | pending reviewer action | Both reviewers post sign-off comments using the §110-131 template |
| `supersedes` consistency | n/a — `lbl_hackathon` has no `supersedes` (original definition) | — |

Legend: ✓ met; ⚠ reviewer judgement call; `pending` = reviewer
action during the Chunk-7.2 promotion PR, not pre-packet.

---

## 14. Promotion readiness assessment

**Outcome: `PACKET READY FOR REVIEW`.**

Rationale:

- The current `lbl_hackathon` definition is structurally
  well-formed (passes `tests/schema/test_primary_taxonomy_refinements.py`
  and the loader's file-level invariants — see §16 commands).
- All non-overlap checklist boxes are either met or are explicit
  reviewer judgement calls listed in §12-13.
- The boundary analyses in §7-8 identify one spot (§8.5
  participation-only wording) where a reviewer may legitimately
  want a Refinement PR before approving. That is a reviewer
  decision, not a packet-level block — a packet is "ready for
  review" even when some of the review questions have `revise`
  as a plausible answer.
- The checklist's overlap-check box (§64-70) can be exercised in
  one of two documented ways: against the 7 SIH records
  (narrow sample, but exercisable) or via the preliminary
  illustrative-examples exercise (§201-247). Either option is
  available to the reviewer at PR time.

**Alternative outcomes considered and rejected:**

- `REVISION REQUIRED BEFORE REVIEW` — would be correct if §8.5
  ambiguity were a hard problem rather than a reviewer judgement
  call. The audit treats it as reviewer-answerable; §11.2 Option
  A keeps current wording and relies on `ANNOTATION_GUIDELINES.md`
  to carry the reading, which is a defensible position.
- `OWNER DECISION REQUIRED` — would be correct if the ≤ 7-day
  bound or the deliverable requirement were outside reviewer
  scope. They are not — the Chunk 7.1 project policy is on-record
  and the two reviewers' sign-off ratifies it.
- `REPOSITORY PRECONDITION MISMATCH` — not applicable; §2 passes.

### 14.1 What `PACKET READY FOR REVIEW` means operationally

- A reviewer may open the promotion PR immediately against the
  current YAML (status: `draft` → `under_review`) — no refinement
  is required first.
- The reviewer-independence rule (checklist §84-107) requires
  that both reviewers read the definition, inclusion rules,
  exclusion rules, examples, adjacent-label definitions, and the
  relevant ANNOTATION_GUIDELINES.md sections before posting. This
  packet is a convenience, not a substitute for that reading.
- A reviewer whose decision is `revise` should state what must
  change before they would approve; the §11.1 / §11.2 / §11.3
  proposals here are candidate wording, not mandates.
- The seven SIH records can be used as the overlap-check sample;
  the reviewer should note the narrowness on the PR.

---

## 15. Recommended next step

**Immediate next action (reviewer-driven, outside AI session
scope):** open the `lbl_hackathon` promotion PR. The PR should:

1. Set `status: draft` → `status: under_review` on the YAML row.
   (Alternatively, if the project convention is to go directly
   from `draft` to `approved` with two sign-offs, that is a
   project-policy call — the TaxonomyStatus enum allows the
   `under_review` intermediate state but the checklist §252-268
   does not mandate it.)
2. Link this packet as the review context.
3. Note on the PR description that the SIH overlap-check sample
   is narrow (one source, one event) and that the preliminary-
   illustrative-exercise option is available.
4. Call out §8.5 / §11.2 Option B explicitly so each reviewer can
   decide independently whether a Refinement PR is required
   first.

**Alternative AI-session next chunk (if reviewer time is short):**
pick one of:

- **Chunk 7.38A — `lbl_competition` taxonomy promotion packet.**
  The checklist §252-268 names `lbl_competition` as label #2 of
  the first-review order; preparing its packet now puts it on the
  critical path for the next ingestion-chunk candidate (Kaggle
  or ACM-ICPC from Chunk 7.33 §G.1 Tier 1).
- **Chunk 7.38B — reviewer-evidence-bundle validator.** Still
  valid from Chunk 7.35 §O.3 and Chunk 7.36 §14.
- **Chunk 7.38C — `src/nlp_semantic/dataset/duplicates_semantic.py`
  design chunk.** Also still valid from the same prior reports.

**Explicitly not recommended:** flipping `status: approved` from
inside this chunk, modifying the YAML to adopt §11 proposals
without the reviewer-driven refinement PR, or opening a
promotion PR in a shared repository as an AI session (the
proposer must be a human per checklist §104-106 implicit
intent).

---

## 16. Validation (actual commands, actual results)

Executed in this chunk:

| Command | Result | Exit |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | `579 passed, 5 skipped in 13.14s` | 0 |

Prior chunks also recorded the dataset-CLI counts (`cli stats`,
`cli validate`, `cli readiness`) — their outputs are a pure
function of the dataset state, which is unchanged, so they were
not re-run this chunk.

The five pytest skips are the same ones recorded in prior chunks:
four Windows-symlink skips in `tests/ingestion/test_inventory.py`
and one `fakeredis-not-installed` skip in
`tests/ingestion/test_redis_rate_limit.py`.

### 16.1 Taxonomy unchanged

- `hybrid_dataset/labels/primary_taxonomy.yaml` — not modified.
  Verified by `git status --short`: file does not appear in the
  modified-files list.
- `hybrid_dataset/labels/domain_tags.yaml` — not modified. Same.
- All 14 primary + 10 domain labels remain `status: draft`.

### 16.2 Dataset unchanged

- `hybrid_dataset/dataset/records/batch_01_sih2024.yaml` — not
  modified. Verified by `git status --short`.
- `hybrid_dataset/metadata/sources.yaml` — pre-existing
  modifications unchanged; no new modification in this chunk.
- `hybrid_dataset/metadata/manifest.yaml` — still an empty list.
- No new `batch_<NN>_*.yaml` created.
- No `Annotation` row added.

### 16.3 No external HTTP request

No WebFetch, no WebSearch, no scraping tool used. No source URL
fetched. No external evidence introduced into the packet.

### 16.4 Modules unchanged

- `src/nlp_semantic/` — untouched.
- `src/ml/`, `src/recommender/`, `src/backend/` — do not exist on
  this branch; not created.
- `pyproject.toml`, `requirements.txt` — pre-existing
  modifications unchanged.

---

## 17. Files created or modified

Files **created** in Chunk 7.37:

- `reports/chunk_7_37_lbl_hackathon_taxonomy_promotion_packet.md`
  — this report. New, additive, inside the Member-1 scope.

Files **modified** in Chunk 7.37: **none.**

Git: no `add`, no `commit`, no `push`, no `checkout`, no `reset`,
no `stash`, no `clean`.

---

## 18. Scope compliance summary

| Rule from brief §Repository-Safety and §Strictly-Forbidden | Honoured? |
|---|---|
| Not switch branches / reset / clean / stash / stage / commit / push | ✓ |
| Not modify `src/ml`, `src/recommender`, `src/backend` | ✓ |
| Not modify existing achievement records | ✓ |
| Not modify source registry | ✓ |
| Not modify taxonomy files | ✓ (`primary_taxonomy.yaml` untouched; §11 proposals are proposals, not edits) |
| Not change annotation statuses | ✓ |
| Not change source review statuses | ✓ |
| Not fabricate examples / achievements / reviewer decisions / approvals | ✓ (§11 proposals are explicitly reviewer-pending; §12 questions are explicitly left unanswered) |
| Not fetch external sources or URLs | ✓ |
| Not treat the SIH records as sufficient evidence for all hackathon types | ✓ (§5, §10.1-1, §13 overlap-check row all surface the narrowness) |
| Not change `lbl_hackathon` from `draft` to `approved` | ✓ (`status: draft` remains) |
| Report-only chunk | ✓ |
| Not approve `lbl_hackathon` | ✓ |
| Not create reviewer signatures / fabricated approval evidence | ✓ |
| Not add synthetic examples to the dataset | ✓ (§11.1 is a proposal, not an edit) |
| Not add achievement records | ✓ |
| Not modify training-ready subset / weaken eligibility gate | ✓ |

---

## 19. Final response fields

- **Branch:** `feature/nlp-semantic`
- **HEAD:** `c8c1b80 feat: add SIH 2024 achievement pilot`
- **Working-tree preservation:** confirmed; same three modified
  files and same untracked artefact set as entry; no new
  modification outside this report file.
- **Exact report path:**
  `reports/chunk_7_37_lbl_hackathon_taxonomy_promotion_packet.md`
- **Current `lbl_hackathon` status:** `draft` (unchanged).
- **Final disposition:** **`PACKET READY FOR REVIEW`.**
- **Required-approval evidence summary:** §13 table — most boxes
  met; two boxes (overlap-check sample run; two sign-off comments)
  are reviewer actions at promotion-PR time, not pre-packet
  prerequisites.
- **Validation:** `pytest -q` → 579 passed, 5 skipped (§16).
  Taxonomy and dataset unchanged (§16.1-2).
- **Recommended next step:** open the `lbl_hackathon` promotion
  PR against the current YAML, with the explicit note that §8.5
  / §11.2 Option B is a reviewer judgement call that may require
  a prior Refinement PR (§15).
