# Chunk 7.41 — Reviewer Evidence Storage Setup

**Generated:** 2026-10-25
**Chunk type:** storage infrastructure (new directory + README + minimal `.gitignore` change).
**Final disposition:** `REVIEW EVIDENCE STORAGE IMPLEMENTED`

> Owner selected the dedicated `reviews/` directory approach
> (Chunk 7.31 §4.1 Option A). This chunk ships: the directory
> itself, a `.gitkeep` structural marker, a comprehensive
> `reviews/README.md` documenting policy and the reviewer capture
> workflow, and a two-line additive change to the top-level
> `.gitignore` mirroring the existing `hybrid_dataset/raw/*`
> pattern. No code changes to the intake pipeline were required —
> the Chunk 7.39 CLI already accepts any local path. No evidence
> was fabricated; the storage location is ready to receive
> genuine reviewer-captured evidence later. Dataset state is
> byte-identical to pre-chunk.

---

## 1. Final disposition

**`REVIEW EVIDENCE STORAGE IMPLEMENTED`.**

The storage convention is actually implemented and usable:

- The `reviews/` directory exists on disk.
- `reviews/README.md` documents the policy, naming convention,
  Git tracking rules, and a nine-step reviewer capture workflow.
- `.gitignore` is updated to exclude `reviews/evidence/*` while
  tracking the `.gitkeep` structural marker (mirroring the
  existing `hybrid_dataset/raw/*` pattern).
- No change to the Chunk 7.39 intake pipeline was needed; the
  pipeline's `ingest` subcommand already accepts any local path.
- Full pytest suite passes without regression (667 passed, 5
  skipped, same as Chunk 7.39's end state).

Alternatives considered and rejected:

- `REVIEW EVIDENCE STORAGE DOCUMENTED — OWNER DECISION REMAINS` —
  would be correct if the storage decision had been left
  unresolved. The owner has explicitly selected Option A, so
  this chunk implements it.
- `STORAGE IMPLEMENTATION BLOCKED BY REPOSITORY POLICY` —
  would be correct if `.gitignore` or project policy forbade the
  layout. It doesn't; the `hybrid_dataset/raw/*` precedent
  directly supports it.
- `REPOSITORY PRECONDITION MISMATCH` — not applicable; §2 passes.
- `IMPLEMENTATION FAILED` — not applicable; everything landed
  cleanly.

---

## 2. Branch and HEAD

| Field | Observed | Expected baseline | Match |
|---|---|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` | same | ✓ |
| Branch | `feature/nlp-semantic` | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` | ✓ |

Preconditions pass. No `REPOSITORY PRECONDITION MISMATCH`.

---

## 3. Working-tree preservation

Verified by `git status --short` after implementation:

```
M .gitignore                                            (new modification by this chunk)
 M hybrid_dataset/metadata/sources.yaml                  (pre-existing; unchanged)
 M pyproject.toml                                        (pre-existing; unchanged)
 M requirements.txt                                      (pre-existing; unchanged)
?? PROJECT_HANDOFF.md                                    (pre-existing untracked; unchanged)
?? hybrid_dataset/metadata/arxiv_governance_decisions.md (pre-existing untracked; unchanged)
?? reports/                                              (pre-existing untracked; unchanged, plus 1 new report added here)
?? reviews/                                              (NEW this chunk)
?? src/nlp_semantic/ingestion/arxiv_governance.py        (pre-existing untracked; unchanged)
?? src/nlp_semantic/ingestion/rate_limit.py              (pre-existing untracked; unchanged)
?? src/nlp_semantic/intake/                              (pre-existing untracked; unchanged)
?? src/nlp_semantic/review/                              (pre-existing untracked; unchanged)
?? tests/__init__.py                                     (pre-existing untracked; unchanged)
?? tests/ingestion/test_arxiv_governance.py              (pre-existing untracked; unchanged)
?? tests/ingestion/test_rate_limit.py                    (pre-existing untracked; unchanged)
?? tests/ingestion/test_redis_rate_limit.py              (pre-existing untracked; unchanged)
?? tests/intake/                                         (pre-existing untracked; unchanged)
?? tests/review/                                         (pre-existing untracked; unchanged)
?? tests/schema/__init__.py                              (pre-existing untracked; unchanged)
```

- **Pre-existing modified files** (`sources.yaml`, `pyproject.toml`,
  `requirements.txt`) — byte-identical to their pre-chunk state.
  Verified: `git diff --stat` on each shows no new changes.
- **Pre-existing untracked files/directories** — all byte-identical.
- **`.gitignore`** — now in `M` status with exactly one additive
  hunk (six lines added, zero changed, zero removed). This is the
  owner-selected policy change for this chunk; it is not a
  modification of any pre-existing modification.
- **`reviews/`** — new, untracked.
- **This report** — added under `reports/`.

Teammate directories (`src/ml/`, `src/recommender/`,
`src/backend/`) do not exist on this branch; not created.

No git stage / commit / push / branch-switch / reset / clean /
stash.

---

## 4. Owner-selected storage approach

**Chunk 7.31 §4.1 Option A — dedicated repository `reviews/`
directory.** The owner has explicitly selected this approach per
the Chunk 7.41 brief's opening statement.

Chunk 7.31's own §4 side-by-side comparison (lines 105-116)
scored Option A against ten criteria. Highlights relevant to this
chunk:

- **Reviewer attribution:** ✓ strong (git commit author binds a
  committed file to the reviewer, when the reviewer commits their
  own file via `git add -f`).
- **Scope identification:** ✓ (directory layout can encode source
  id and reviewer slot).
- **Independent submission:** ✓ (each reviewer commits their own
  file; commits visible in `git log` with ordered timestamps —
  applies only when `git add -f` is used).
- **Posting-order evidence:** ✓ (via `git log --format=%ai` for
  committed files; capture-notes timestamps for uncommitted
  files).
- **Supported by the existing repository:** ⚠ requires a new
  top-level directory + convention. Implemented in this chunk.
- **Requires new architecture or workflow:** ⚠ minor new workflow
  only. Implemented as documentation in `reviews/README.md` §6.

The chunk also noted (§4.5) that Option A requires "reviewer
commits (reviewers must have repo write access + git
familiarity)." This chunk documents that requirement in
`reviews/README.md` §5 and in §15 below (Remaining owner
decisions).

---

## 5. Implemented directory layout

```
reviews/
├── README.md                   # policy + workflow + capture template (TRACKED)
└── evidence/
    └── .gitkeep                # structural marker (TRACKED)
    # evidence file contents stay LOCAL; .gitignore excludes them
```

**What was NOT implemented** (and why):

- A `reviews/manifests/` subdirectory. The Chunk 7.41 brief §2
  "Proposed structure" suggests a `manifests/` subdirectory, but
  the brief also says the structure is "a proposal, not a
  requirement" and explicitly directs: "Do not introduce a second
  evidence-management system." The Chunk 7.39 intake pipeline
  already writes manifests to `hybrid_dataset/intake/manifests/`.
  Adding `reviews/manifests/` would duplicate that store and
  introduce ambiguity about which manifest is authoritative. The
  implementation instead documents (in `reviews/README.md` §4)
  that reviewer-authored *capture notes* can live as
  `reviews/evidence/<filename>.notes.yaml` sidecar files when the
  reviewer wants to record capture-time context the pipeline does
  not record.
- A pre-populated set of per-source subdirectories. The brief
  §2 warns against "a `reviews/` directory merely containing
  placeholders if the implementation cannot establish a useful,
  documented workflow." Per-source subdirectories can be added
  on demand by future chunks when they are known to be useful;
  speculating now would create unused placeholders.
- An automated indexing / linking file. The reviewer may append
  the pipeline-assigned `intake_id` to their notes file manually
  (§6.8 of the README); automation is deliberately out of scope
  for this chunk.

---

## 6. Evidence naming convention

Documented in `reviews/README.md` §6 (reviewer capture workflow).
Key rules:

1. **Original filename preserved verbatim** in `reviews/evidence/<name>.<ext>`
   and in the Chunk 7.39 intake manifest's `original_filename`
   field. No silent renaming.
2. **Filename collisions** are rejected by the Chunk 7.39
   pipeline's existing per-intake-id directory structure
   (`<evidence_root>/intk_<hex>/<filename>`), which guarantees
   two files with the same name but different content get
   distinct storage directories.
3. **Content hashing** (SHA-256) is calculated by the Chunk 7.39
   pipeline on ingest; the pipeline's existing
   `DUPLICATE_HASH` finding fires when the same bytes have been
   ingested before.
4. **Path traversal** is rejected by the Chunk 7.39 pipeline's
   existing `IntakeEntry.original_filename` validator (no
   `/`, `\`, `.`, `..`, or NUL in filenames) and by the Pydantic
   model's `relative_path` validator (reusing the shared
   `reject_unsafe_relative_path`).
5. **Repository-relative references** in all committed metadata.
   The reviewer workflow prescribes `reviews/evidence/<name>.<ext>`
   as the input to the CLI; the pipeline's manifests record
   repository-relative paths rooted at `INTAKE_ROOT_PREFIX`.
6. **Capture notes sidecar convention** (optional):
   `reviews/evidence/<name>.<ext>.notes.yaml`. Documented in
   README §4 with a complete template.

None of these required code changes — all were already enforced
by the Chunk 7.39 pipeline. The Chunk 7.41 README documents how
to use them from the reviewer side.

---

## 7. Provenance policy

Documented in `reviews/README.md` §2-§4. Summary:

**What belongs** (per README §2): reviewer-captured browser
screenshots of a primary source page; original source documents
the reviewer downloaded with a stable reference; reviewer-authored
YAML sidecar notes.

**What does not belong** (per README §2): search-result
screenshots that are not of the primary source; AI-generated
screenshots; synthetic evidence; reconstructed documents;
unverified web captures; achievement records; model-generated
summaries presented as original evidence; private student PII that
wasn't already in the source; credentials.

**Per-artifact provenance fields** (per README §4 template, filled
by the reviewer in the sidecar notes file): `original_filename`,
`capture_date_utc` (ISO 8601, timezone-aware), `reviewer`
(pseudonym — never an email), `source_url` and
`source_url_verified_at_capture` flag, `source_identifier`,
`intended_source_id`, `intended_batch`, `capture_method`,
`browser`, `operating_system`, `reviewer_notes` (free-text, 2-3
sentences).

**Explicitly forbidden** (per README §2): inferring reviewer
identity from Windows usernames, Git author names, file ownership,
browser profiles, or email addresses in unrelated files.
Fabricating reviewer identities or signatures. The convention
preserves the project's "pseudonym only; mapping stored
externally" rule from `ANNOTATION_GUIDELINES.md`.

**Authenticity caveats** (per README §7): a stored file is NOT
proof of source approval, taxonomy promotion, annotation
verification, or reviewer authentication. The Chunk 7.38B
authentication limitation and the Chunk 7.39 pipeline's
unconditional `AUTHENTICATION_NOT_ESTABLISHED` finding both apply
unchanged.

---

## 8. Git tracking and privacy policy

Documented in `reviews/README.md` §5. Implemented by the
two-line additive change to `.gitignore`:

```
# Reviewer-supplied evidence (Chunk 7.41). Contents stay LOCAL;
# only the structural marker is tracked. Mirrors the
# hybrid_dataset/raw/* policy. Reviewers may override on a
# per-file basis with `git add -f` for files they confirm are
# PII-free; see reviews/README.md §5 for the policy.
reviews/evidence/*
!reviews/evidence/.gitkeep
```

### 8.1 Why this policy

Three reasons derived from the existing project rules
(detailed in `reviews/README.md` §5.2):

1. **PII in raw evidence.** `hybrid_dataset/README.md` §Data
   safety rules already excludes "names, roll numbers, emails,
   phone numbers, scanned IDs, and document images" from Git.
   The same reasoning applies: a screenshot may incidentally
   capture reviewer-identifying metadata (bookmark bar, open
   tabs, window chrome).
2. **Repository size.** Screenshots and PDFs are binary and
   grow fast. `.gitignore` already excludes model checkpoints,
   embeddings, and raw datasets for size reasons.
3. **Reviewer identity.** The project forbids storing a
   pseudonym-to-real-identity mapping in this repository
   (`ANNOTATION_GUIDELINES.md` §Pseudonym convention). A
   screenshot can leak identity details that a pseudonym
   deliberately hides.

### 8.2 Why this is NOT inventing policy

The owner's EXISTING documented policy
(`hybrid_dataset/README.md` §Data safety rules) already requires
raw evidence files to stay local. This chunk applies that
established policy to the new `reviews/` directory by analogy,
with the two-line `.gitignore` entry explicitly annotated as
"Mirrors the hybrid_dataset/raw/* policy."

Per the brief §8 ("Do not silently choose a privacy-sensitive
policy"), this chunk documents the choice loudly:

- `reviews/README.md` §5 names the decision, the three reasons,
  and the override mechanism (`git add -f`).
- `.gitignore` includes a six-line comment block above the two
  rules explaining the policy and pointing at the README.
- This report's §15 "Remaining owner decisions" lists the two
  specific sub-decisions this chunk did NOT make.

---

## 9. Reviewer capture instructions

Documented in `reviews/README.md` §6 as a nine-step workflow,
reproduced here in summary:

| Step | Action |
|---|---|
| 1 | Verify the intended source in a browser against `sources.yaml` |
| 2 | Capture the full page (screenshot or Print-to-PDF) |
| 3 | Save to `reviews/evidence/<descriptive_name>.<ext>` |
| 4 | Create the sibling `.notes.yaml` capture-context file (optional but recommended) |
| 5 | Compute SHA-256 for sanity check (optional) |
| 6 | Run `python -m nlp_semantic.intake.cli ingest ...` |
| 7 | Validate with `python -m nlp_semantic.intake.cli validate ...` |
| 8 | Record the pipeline-assigned `intake_id` back into the notes file (optional) |
| 9 | Preserve the original (the pipeline copies, does not move) |

**Chunk 7.41 did not perform these steps.** The brief §6 is
explicit:

- "Do not actually fetch the PIB URL."
- "Do not open the website."
- "Do not generate or reconstruct the screenshot."
- "Do not create a placeholder intake entry."
- "Do not claim that the reviewer completed these steps."
- "The workflow is documentation and infrastructure only."

The nine-step workflow is the handoff spec a human reviewer will
run in a future session.

---

## 10. Intake pipeline compatibility

**Full compatibility achieved with zero code changes.**

The Chunk 7.39 CLI's `ingest` subcommand already accepts
arbitrary local paths via its `source_file` positional argument.
Passing `reviews/evidence/<filename>.<ext>` requires no new flag,
no new validator, and no modification to
`src/nlp_semantic/intake/pipeline.py` or
`src/nlp_semantic/intake/cli.py`.

Specifically:

- `ingest_evidence(source_file=...)` reads bytes from any local
  path reachable to the Python process.
- `classify_file_type(filename)` uses the extension on
  `source_file.name`, independent of the parent directory.
- `make_intake_id()` is independent of the input path.
- The copy destination is `<evidence_root>/<intake_id>/<filename>`,
  which uses the FILENAME from `source_file.name` and the configured
  `--evidence-root` flag. The intake pipeline's `evidence_root`
  default (`hybrid_dataset/raw/evidence_intake`) is unchanged
  and distinct from `reviews/evidence/` — the reviewer stores
  the original in `reviews/`, and the pipeline makes a copy in
  `hybrid_dataset/`.

**Behavioural guarantee preserved from Chunk 7.39:** no existing
intake behaviour is modified. The two directories play distinct
roles:

| Path | Role | Written by |
|---|---|---|
| `reviews/evidence/<file>` | Reviewer-saved ORIGINAL | Human reviewer |
| `hybrid_dataset/raw/evidence_intake/<intake_id>/<file>` | Pipeline-generated COPY | `ingest_evidence()` |
| `hybrid_dataset/intake/manifests/<intake_id>.yaml` | Pipeline manifest | `ingest_evidence()` |
| `reviews/evidence/<file>.notes.yaml` | Reviewer capture-context notes (optional) | Human reviewer |

The pipeline makes a copy because the reviewer should always be
able to inspect their original without worrying that a downstream
process has mutated it.

---

## 11. Files created

| Path | Purpose |
|---|---|
| `reviews/README.md` | Policy + layout + supported file types + reviewer-authored capture-notes template + Git tracking policy + 9-step reviewer capture workflow + list of what the pipeline does NOT change. 300+ lines. |
| `reviews/evidence/.gitkeep` | Structural marker so the directory exists after a fresh clone. Empty file. |
| `reports/chunk_7_41_reviewer_evidence_storage_setup.md` | This report. |

Total: **3 files created**.

---

## 12. Files modified

| Path | Change |
|---|---|
| `.gitignore` | **Six lines added** (one blank + four comment + two rules): a comment block explaining the policy and the pair `reviews/evidence/*` + `!reviews/evidence/.gitkeep`. Zero lines removed. Zero existing lines modified. |

Total: **1 file modified** (`.gitignore`).

### 12.1 Explicit confirmation of what was NOT modified

- `src/nlp_semantic/` — no file touched. Verified by `git status`:
  the only path with a leading `M` outside `hybrid_dataset/`,
  `pyproject.toml`, `requirements.txt`, and `.gitignore` is this
  chunk's own `.gitignore` edit.
- `src/nlp_semantic/intake/pipeline.py` and
  `src/nlp_semantic/intake/cli.py` — untouched. Confirmed by their
  continued presence in the "untracked" set and by the full test
  suite passing without change.
- `hybrid_dataset/` — no file in this directory tree was touched.
  The pre-existing modified `sources.yaml` is byte-identical to
  its pre-chunk state. `batch_01_sih2024.yaml` is byte-identical.
  All taxonomy YAML files are byte-identical.
- Teammate directories — do not exist; not created.
- Pre-existing untracked files — all byte-identical to their
  pre-chunk state.

Git: no `add`, no `commit`, no `push`, no `checkout`, no `reset`,
no `clean`, no `stash`, no branch switch.

---

## 13. Tests actually executed

Executed in this chunk:

| Command | Result | Exit |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | `667 passed, 5 skipped in 23.85s` | 0 |
| `python -m nlp_semantic.dataset.cli readiness hybrid_dataset` | `dataset: readiness \| any_task=not_ready \| all_tasks=not_ready \| approved(pt=0,dt=0) \| eligible(pt=0,dt=0) \| blockers=4 \| strict=off` | 0 |

Full-suite result is unchanged from Chunk 7.39 (`667 passed, 5
skipped`) — the `.gitignore` edit does not affect test discovery
or any test's behaviour because no test depends on the committed
state of `reviews/`. The five skips are the same four
Windows-symlink skips + one `fakeredis-not-installed` skip
reported in every chunk since Chunk 7.32.

### 13.1 Why no new tests were added

The brief §9 is explicit: "If the chunk is documentation-only,
do not create tests merely to increase test counts." This chunk's
only non-documentation change is a two-rule `.gitignore` addition,
which Python code does not consume. The intake pipeline's
compatibility with `reviews/evidence/` paths is already covered
by Chunk 7.39's `test_pipeline.py` and `test_cli.py` (which use
`tmp_path` for isolated fixtures). The pipeline's behaviour does
not change with input-directory location, so there is no new
behaviour to test.

### 13.2 Dependencies

No new runtime dependency was added. `requirements.txt` is
byte-identical. The `fakeredis-not-installed` skip persists for
the same reason as prior chunks.

---

## 14. Dataset before/after comparison

Baseline per brief §10.

| Measure | Before | After | Changed? |
|---|---:|---:|---|
| Achievement record count | 7 | 7 | no |
| Record hashes (per-record `.model_dump()`) | all unchanged | all unchanged | no |
| Source count (committed + uncommitted) | 1 + 1 | 1 + 1 | no |
| Evidence count (approved `Evidence` rows) | 0 | 0 | no |
| Intake-manifest count | 0 | 0 | no |
| Primary-taxonomy label statuses (14 labels) | all `draft` | all `draft` | no |
| Domain-tag label statuses (10 labels) | all `draft` | all `draft` | no |
| Annotation status of 7 SIH records (primary_type) | all `draft` | all `draft` | no |
| Annotation status of 7 SIH records (domain_tags) | all `not_started` | all `not_started` | no |
| Source review status for `src_5a8a2998…` | `unreviewed` | `unreviewed` | no |
| Source license for `src_5a8a2998…` | `UNKNOWN` | `UNKNOWN` | no |
| Source review status for `src_08ee850b…` | `unreviewed` | `unreviewed` | no |
| Training-ready records (primary_type) | 0 | 0 | no |
| Training-ready records (domain_tags) | 0 | 0 | no |

No field of `batch_01_sih2024.yaml`, `sources.yaml`,
`manifest.yaml`, `primary_taxonomy.yaml`, `domain_tags.yaml`, or
any `Annotation` row was modified. No new record created. No
synthetic data added. The brief §10 "Expected result" bullet list
is honoured verbatim.

---

## 15. Training-readiness before/after

| State | Before | After |
|---|---|---|
| `any_task_training_ready` | `false` | `false` |
| `all_tasks_training_ready` | `false` | `false` |
| `approved_label_count.primary_type` | 0 | 0 |
| `approved_label_count.domain_tags` | 0 | 0 |
| `eligible_record_count.primary_type` | 0 | 0 |
| `eligible_record_count.domain_tags` | 0 | 0 |
| `blockers` count | 4 | 4 |
| `warnings` count | 2 | 2 |

Verbatim stderr CLI summary (byte-identical both before and
after):

```
dataset: readiness | any_task=not_ready | all_tasks=not_ready |
approved(pt=0,dt=0) | eligible(pt=0,dt=0) | blockers=4 | strict=off
```

The readiness output is a pure function of taxonomy status +
annotation status + source review status + record contents.
None of those four changed, so the output cannot change.

---

## 16. Remaining owner decisions

Listed in `reviews/README.md` §5.3; summarized here with the
reviewer / owner action each requires:

1. **Per-file override policy for `.notes.yaml` sidecars.** The
   default-ignore + `git add -f` approach lets reviewers
   explicitly commit a sidecar file they have confirmed is
   PII-free. The owner may prefer the inverse default (track by
   default, review a staging area). Not implemented in this
   chunk; left as an owner decision. If the owner picks the
   inverse default, a one-line `.gitignore` change plus a
   per-sidecar PR-review step would implement it.
2. **Whether a tracked evidence-hash index should exist.** The
   pipeline already produces manifests under
   `hybrid_dataset/intake/manifests/` that carry the hash and
   provenance. A second tracked index
   (e.g. `reviews/EVIDENCE_INDEX.yaml`) would duplicate that
   record and introduce ambiguity about which is authoritative.
   Not implemented; left as an owner decision.
3. **Whether redacted versions of a screenshot should be
   committed.** The current policy permits per-file override
   with `git add -f`. The owner may prefer a formal redacted
   subdirectory with its own tracking policy. Not implemented.

None of these three is a blocker for the first real-evidence
intake exercise (Chunk 7.42-candidate). Each is a long-term
convention refinement.

---

## 17. Remaining reviewer actions

The three outstanding reviewer actions from Chunk 7.36 §13.1 are
unchanged by this chunk:

1. **PIB-policy applicability decision** — Chunk 7.26A packet.
   Not affected by Chunk 7.41 (storage ≠ approval).
2. **`lbl_hackathon` taxonomy promotion** — Chunk 7.37 packet
   ready; two reviewers must sign off.
3. **Per-record annotation review** for the seven SIH records.

Added by this chunk:

4. **Reviewer screenshot capture of the PIB SIH 2024 URL.** The
   `reviews/README.md` §6 nine-step workflow documents how. The
   target URL is
   `https://www.pib.gov.in/PressReleasePage.aspx?PRID=2085000&lang=2&reg=48`
   per `sources.yaml`. The reviewer must do this manually in
   their own browser; this chunk did NOT fetch the URL and did
   NOT generate a replacement screenshot.

Once (4) completes, Chunk 7.40 can be re-run (see §18) to achieve
its intended `REAL EVIDENCE INGESTED` disposition.

---

## 18. Recommended next action

### 18.1 Primary recommendation — reviewer-driven

**Chunk 7.42 — Re-run the first real-evidence intake exercise.**
The brief's closing sentence makes this the natural next chunk:

> The next chunk should rerun the first real-evidence intake
> exercise only after the actual reviewer-captured artifact is
> available.

Precondition for Chunk 7.42: a reviewer must execute steps 1-5
of the `reviews/README.md` §6 workflow (capture a screenshot or
PDF of the PIB SIH 2024 URL in their own browser and save it to
`reviews/evidence/`). Steps 6-8 (ingest + validate) are what
Chunk 7.42 verifies.

Expected Chunk 7.42 disposition (if the reviewer step precedes
it): `REAL EVIDENCE INGESTED`.

### 18.2 Alternative — AI-driven work that does not need real evidence

If reviewer time is short, Chunk 7.39 §14.2 listed candidates
that remain valid:

- **Chunk 7.42-alt — Candidate-to-Achievement reviewer workflow
  design.** Designs the explicit transition from
  `AchievementCandidate` (intake-side) to `Achievement`
  (dataset-side).
- **Chunk 7.38A — `lbl_competition` taxonomy promotion packet.**
  The second label in the `TAXONOMY_APPROVAL_CHECKLIST.md`
  §252-268 recommended review order (after `lbl_hackathon`).
- **Semantic duplicate design** — still valid from Chunk 7.35
  §O.3 / Chunk 7.38B §16.1.

### 18.3 Explicitly not recommended

- Any attempt by an AI session to fetch the PIB URL, generate a
  screenshot, or populate `reviews/evidence/` with a synthetic
  artifact. The brief §6 explicitly forbids each.
- Modifying the intake pipeline's default `evidence_root` to
  point at `reviews/evidence/` so the pipeline writes copies
  back on top of the originals. This would defeat the
  "reviewer can always inspect the original" guarantee that
  Chunk 7.41 §10 establishes.
- Adding per-source subdirectories under `reviews/evidence/`
  before any reviewer has actually captured evidence from more
  than one source. Speculative structure creates unused
  placeholders.

### 18.4 The stated project objective

The Chunk 7.41 brief's final paragraph:

> "The goal is to establish a real, documented reviewer evidence
> storage convention that can receive genuine evidence later. Do
> not fabricate evidence or approvals. The next chunk should
> rerun the first real-evidence intake exercise only after the
> actual reviewer-captured artifact is available."

Chunk 7.41 achieves the first part: the convention is real,
documented, and ready. Chunk 7.42 completes the second part
once a reviewer executes the capture steps.
