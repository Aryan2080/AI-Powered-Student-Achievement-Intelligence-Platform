# Taxonomy Approval Checklist

**Audience:** project reviewers of taxonomy YAML changes
(`primary_taxonomy.yaml`, `domain_tags.yaml`).
**Scope:** promoting individual `LabelTaxonomy` entries from `draft`
through `under_review` to `approved`.

This checklist is advisory and shipped with Chunk 6. The authoritative
status machine lives in `TaxonomyStatus`
(`src/nlp_semantic/schema/enums.py`). Chunk 6 ships no automated
promotion; `approved` is a human decision captured in a YAML edit via
PR.

---

## What `approved` means to the code

`nlp_semantic.dataset.eligible_ground_truth` and
`nlp_semantic.dataset.training_ready_subset` require every referenced
`label_id` to have `status: approved`. All taxonomy labels currently
ship with `status: draft`, so the eligible/training-ready set is empty
by design until approvals happen.

Code treats `approved` as a human assertion that this checklist was
followed. Setting `approved` without the checklist breaks the
convention.

---

## Per-label checklist (fill in on the PR)

Every label promotion is a one-label-at-a-time PR. Do not bulk-promote.
A reviewer checking the box must have personally confirmed the item.

### Definition

- [ ] The `definition` field is complete, specific, and self-contained
      (a reader who has never seen this project should know what the
      label means from the definition alone).
- [ ] The definition is distinct from every other label at the same
      `task_name`. If two labels could plausibly refer to the same
      record, the definitions must spell out the boundary.
- [ ] Edge cases that would otherwise be ambiguous are addressed in the
      `inclusion_rules` or `exclusion_rules`.

### Inclusion / exclusion rules

- [ ] At least one `inclusion_rule` is present.
- [ ] At least one `exclusion_rule` is present, naming the adjacent
      label(s) that a tempted-but-wrong record would be assigned to.
- [ ] Rules are stated in observable terms (what the record says),
      not in reviewer intuition.

### Examples

- [ ] At least three realistic examples are present.
- [ ] Examples span the plausible variety of records the label will
      actually see (short / long, winner / participant, local / national,
      different domains).
- [ ] No example is a copy from a specific private source. If drawn
      from a real public source, attribution is noted; otherwise it is
      synthetic.

### Overlap check

- [ ] A reviewer different from the proposer has read all adjacent
      label definitions and confirmed no overlap exists for a realistic
      record.
- [ ] Two annotators would independently classify a representative
      sample (3–5 records) into the same label.

### Workflow

- [ ] The PR touches **one** label's `status` field. Multi-label
      promotions require separate PRs.
- [ ] The PR notes two reviewer sign-offs in the description (name /
      pseudonym + date).
- [ ] `supersedes` (if present) points at an existing label in the
      same file. The label being superseded is marked `deprecated` in
      the same PR.

---

## Reviewer independence

The two required reviewers must reach their initial decisions
independently so a second opinion is actually a second opinion.

1. Each of the two reviewers independently reads the label's
   `definition`, `inclusion_rules`, `exclusion_rules`, and
   `examples`, together with the adjacent-label definitions and the
   relevant boundary guidance in
   `hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md`.
2. Each reviewer posts their own `approve` or `revise` decision with a
   rationale **before** discussing the decision with the proposer or
   with the other reviewer.
3. Discussion may follow once both initial decisions are posted.
4. These rules describe the intended review process. They are
   procedural, not technically enforced — GitHub does not prevent
   reviewers from reading the PR together or chatting before posting.
   The proposer and reviewers are responsible for respecting the
   intent.

The proposer cannot count as either of the two required reviewers.
If the proposer is also the author of the label definition being
revised, the two sign-offs must come from two other team members.

---

## Sign-off record template

Each reviewer posts **one PR comment per decision** using exactly this
template. A thumbs-up emoji, a GitHub "Approve" review with no body,
or a free-form "lgtm" is **not** a complete sign-off under this
checklist.

```
label_id: lbl_<name>
reviewer: labeler_<NNN>
date:     YYYY-MM-DD
decision: approve   # or: revise
rationale: >
  Two or three sentences identifying the evidence you weighed
  (definition clarity, overlap boundary, examples) and any remaining
  issue. If the decision is `revise`, state what must change before
  you would approve.
```

Both required reviewers submit a separate comment matching this
template. The proposer does not post a decision comment, even in
support — the proposer's position is the YAML change itself.

A comment that omits any field, uses a different structure, or bundles
two reviewers' decisions into one message is not a complete sign-off
and does not count toward the two-sign-off requirement.

---

## Reviewer-disagreement workflow

Both reviewers' most recent decision comments are the current
decisions. Rules for the four possible states:

- **Both current decisions are `approve`.** If every box in the
  per-label checklist above is also checked, the proposer may prepare
  the status-changing promotion commit (or follow-up PR) per the
  one-label-per-promotion-PR rule in `### Workflow`.
- **Either current decision is `revise`.** The label **must not** be
  promoted. The proposer revises the definition, inclusion rules,
  exclusion rules, or examples per the reviewer's rationale. After
  revision, both reviewers must review the revised version and append
  a new decision comment matching the sign-off template.
- **Never edit or delete a previous sign-off comment** to hide a
  change of position. Each decision is appended as a new comment; the
  thread's history is the audit trail. The latest explicit decision
  from each reviewer is the current decision; earlier decisions remain
  visible.
- **Persistent disagreement.** If the pair has gone through two full
  review-and-revision cycles without converging, request an
  independent third reviewer to adjudicate. The third reviewer posts
  one sign-off comment matching the template; a majority of three
  `approve` decisions resolves the deadlock, otherwise the label stays
  in `draft` or `under_review` and a decision is deferred.

The label must not be promoted while any reviewer's current decision
is `revise`, or while a disagreement remains unresolved.

Automated tests passing is not evidence that a reviewer has approved.
Code review tooling and CI do not count as either sign-off.

---

## Refinement PRs versus promotion PRs

The one-label-per-PR rule in `### Workflow` applies specifically to
PRs that change a label's `status` field. Two kinds of PR are
expected:

- **Refinement PR.** Updates `definition`, `inclusion_rules`,
  `exclusion_rules`, or `examples` for one or more labels while
  leaving every `status` field unchanged. May touch multiple related
  labels in a single PR (e.g. a boundary clarification between
  HACKATHON, COMPETITION, and PROJECT). Needs ordinary PR review, not
  the two-sign-off approval procedure in this checklist. Refinement
  is not approval.
- **Promotion PR.** Changes exactly one label's `status` field
  (typically `draft` → `under_review` → `approved`, or `approved` →
  `deprecated` paired with a `supersedes` entry on the replacement).
  Must satisfy every box in this checklist and must carry two
  independent sign-off comments using the template above.

A refinement that passes the structural tests in
`tests/schema/test_primary_taxonomy_refinements.py` has demonstrated
that it preserves the YAML's shape and the operational distinctions
Chunk 7.1 pinned down. It has **not** demonstrated that the label is
ready to be used as training ground truth; that is what the
promotion-PR sign-off procedure establishes.

---

## Illustrative examples when real records are unavailable

The dataset currently has no curated records. The "two annotators
would independently classify a representative sample of 3–5 records
into the same label" box in `### Overlap check` cannot be exercised
against real data until a pilot batch exists.

In the interim, reviewers may run a **preliminary agreement
exercise** using the illustrative material already in the repository:

1. The three canonical `examples` in each affected label's YAML row.
2. The adjacent cases from the boundary matrix in
   `hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md` under
   "Deciding between `HACKATHON`, `COMPETITION`, and `PROJECT`".

Record the exercise on the promotion PR using this shape (one block
per reviewer):

```
reviewer: labeler_<NNN>
date:     YYYY-MM-DD
exercise: preliminary (illustrative examples, not real records)
cases_evaluated:
  - "<example or boundary-matrix row>"
  - "<example or boundary-matrix row>"
  - "<example or boundary-matrix row>"
classifications:
  - "<label the reviewer picked>"
  - "<label the reviewer picked>"
  - "<label the reviewer picked>"
disagreements_and_resolutions: >
  Two or three sentences. If every classification matched the other
  reviewer, say so explicitly.
```

Important limitations:

- A preliminary exercise on illustrative examples **does not** satisfy
  the representative-sample box in `### Overlap check`. It is a
  heuristic sanity check, not evidence of inter-annotator agreement on
  a production dataset.
- When real records become available, the representative-sample box
  must still be addressed per the existing checklist — the
  preliminary exercise does not substitute for it.
- Record this limitation explicitly on the PR so a future reviewer
  understands that the box remains to be addressed when real records
  arrive.

---

## Promotion sequence

Per the Chunk 6 approval, the suggested first-review order for the
primary taxonomy is:

1. `lbl_hackathon`
2. `lbl_competition`
3. `lbl_project`

This is a review order, not a promotion decision. Each label still
goes through this checklist individually. If a reviewer finds that
the overlap check fails (`lbl_project` vs `lbl_hackathon` boundary not
sharp enough for a specific example), the label stays `draft` and the
definitions get revised first.

Domain tags should be reviewed after the first three primary labels so
primary-vs-domain interactions are understood. No fixed order is
mandated.

---

## What this checklist does NOT establish

- **Not representativeness.** An `approved` label does not imply that
  the dataset will contain records for it. Rare labels (patent,
  cultural) may remain approved-but-empty for the pilot.
- **Not immutability.** An approved label can be moved to `deprecated`
  later via a new entry's `supersedes`. The deprecated row stays in
  place for historical traceability.
- **Not automatic.** Chunk 6 ships no code that promotes labels.
- **Not a model-quality claim.** Approval says the label is
  well-defined; it does not say a classifier will achieve any
  particular accuracy on it.

---

## Related files

- `src/nlp_semantic/schema/enums.py` — `TaxonomyStatus` values.
- `src/nlp_semantic/schema/label_taxonomy.py` — the `LabelTaxonomy`
  model.
- `src/nlp_semantic/schema/loader.py` — file-level invariants on
  taxonomy YAML.
- `src/nlp_semantic/dataset/validator.py` — `eligible_ground_truth`
  and `training_ready_subset` consume `status == approved`.
- `hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md` — the per-label
  rubric annotators follow.
