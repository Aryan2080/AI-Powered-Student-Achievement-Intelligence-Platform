# Source Registration Guide

**Audience:** project team members registering a data source for use
by the AI-Powered Student Achievement Intelligence Platform.
**Scope:** curating entries in `hybrid_dataset/metadata/sources.yaml`
and promoting them to `review_status: verified`.

This guide is advisory; the authoritative rule set lives in the
`SourceRegistry` Pydantic model (`src/nlp_semantic/schema/source_registry.py`).
Chunk 6 ships no automated license-approval check — code treats
`review_status: verified` as the human's assertion that this document's
checklist was followed.

---

## When to register a source

Before any record from a source is added to
`hybrid_dataset/dataset/records/*.yaml`, the source must appear as a
`SourceRegistry` entry in `sources.yaml`.

Chunk 6 code (`training_ready_subset`) treats a record as training-ready
only when its source has `review_status: verified` **and**
`license != "UNKNOWN"`. The flag is set by a human after review; code
does not set it.

---

## Pre-registration checklist (what the reviewer must confirm)

Before adding an entry **and** before promoting it from `unreviewed` to
`verified`, the reviewer must confirm all of the following in writing on
the PR. If any item is unclear, keep `review_status: unreviewed` and
request a second reviewer.

### Provenance

- [ ] The `source_url` is a stable canonical URL (not a session-scoped,
      personalized, or rate-limited link).
- [ ] The URL resolves without authentication for anyone with public
      access.
- [ ] The content described in `source_name` is actually present at the
      URL.
- [ ] `collection_date` reflects the date the content was observed, not
      an arbitrary date.

### License and reuse terms

- [ ] A written license, Terms of Service, or usage statement is
      visible at the source. "I think it's open" is not a license;
      keep `review_status: unreviewed` in that case.
- [ ] The license text has been read in full. Note the exact license
      identifier (e.g. `CC-BY-4.0`, `MIT`, `Apache-2.0`, `arXiv.org
      submission license v1`) in the `license` field.
- [ ] The license permits the intended uses described in
      `intended_use` (e.g. "primary_type_training",
      "domain_tag_training", "example_extraction"). Non-commercial
      academic research usually qualifies — but check.
- [ ] Attribution requirements (if any) are captured in
      `usage_restrictions`.
- [ ] Share-alike / derivative restrictions (if any) are captured in
      `usage_restrictions`.
- [ ] If the license is unknown or ambiguous, use the canonical
      upper-case sentinel `license: "UNKNOWN"` and
      `review_status: unreviewed`. `training_ready_subset` compares the
      sentinel **case-insensitively** (`UNKNOWN`, `Unknown`, and
      `unknown` are all treated as unknown and reject the record),
      but the canonical upper-case form is strongly preferred so a
      reader scanning the YAML sees the sentinel at a glance. Code
      treats any case-variant of UNKNOWN as "no permission".

### Privacy and PII

- [ ] The content you intend to ingest does not include student personal
      data (names, email addresses, phone numbers, roll numbers, scanned
      IDs) that cannot be rephrased or removed before storage.
- [ ] If the source carries personal names only as public bylines
      (e.g. patent inventor, paper author), downstream records will
      either preserve the attribution with the public byline or rephrase
      impersonally. Decide which, and note the policy in
      `mapping_notes`.
- [ ] No credentials (API keys, tokens, user:password URLs) are embedded
      in `source_url`. The Chunk 4 safe-ingestion boundary
      (`SourceRegistry.from_untrusted`) rejects these at load time.

### Original labels

- [ ] If the source carries its own labels, record them verbatim in
      `original_labels`. Do not silently remap to the project's
      taxonomy; mapping decisions live in a separate column
      downstream.

---

## Workflow

1. **Draft entry.** Open a PR adding one new source entry to
   `sources.yaml` with `review_status: unreviewed`,
   `is_synthetic: false`, and the pre-registration checklist filled in
   on the PR description. Include a `make_id("src")` generated
   `source_id`.
2. **First reviewer.** A different team member walks through this
   checklist against the source itself. They either request changes
   or approve.
3. **Second reviewer.** A second team member re-verifies the license
   and provenance claims (two sign-offs required for `verified`).
4. **Promote.** The author updates `review_status: verified` in a
   follow-up commit on the same PR, referencing both reviewers'
   sign-offs.
5. **Merge.** Only merge after both sign-offs and the Chunk 4 ingestion
   loader validates the entry (`python -m nlp_semantic.ingestion.inventory`
   runs clean; the Chunk 5 CLI validates downstream).

Chunk 6's `readiness` CLI will show the entry's advisory status until
it is `verified`. Setting `verified` without the two human sign-offs
breaks the convention this guide depends on.

---

## When to NOT register a source

- The license is unknown and cannot be verified → stop; do not add the
  entry.
- The source contains obvious PII that cannot be stripped →
  stop; it is not usable.
- The source URL is unstable (behind a login, rate-limited, redirects
  to a search page) → stop; find a canonical mirror or drop the
  source.
- The reuse terms require commercial-license negotiation that the team
  cannot complete → stop; do not treat as `verified`.

---

## What this guide does NOT establish

- **Not legal advice.** This checklist helps the team be careful. A
  reviewer's `verified` flag is their assertion of good-faith
  compliance. If a license is ambiguous, consult a university library
  or legal office; do not promote the entry.
- **Not an automated check.** Chunk 6 ships no code that reads license
  text and decides compatibility. The reviewer does that work.
- **Not representativeness.** A `verified` source does not imply that
  the data is representative of the problem domain. Separate human
  review of the dataset's class distribution is required.
- **Not permission to publish.** Downstream publication of derivatives
  may require additional checks beyond those listed here.

---

## Related files

- `src/nlp_semantic/schema/source_registry.py` — the `SourceRegistry`
  Pydantic model.
- `src/nlp_semantic/ingestion/registry.py` — the YAML loader + advisory
  warnings.
- `src/nlp_semantic/dataset/validator.py` — `training_ready_subset`
  consumes this field.
- `hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md` — parallel
  checklist for taxonomy labels.
- `hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md` — annotation
  workflow using the sources this file governs.
