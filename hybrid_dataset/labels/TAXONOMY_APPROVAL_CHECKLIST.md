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
