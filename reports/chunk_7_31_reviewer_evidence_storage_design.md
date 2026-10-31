# Chunk 7.31 — Reviewer Evidence Storage and Handoff Design (Read-Only)

**Report type:** read-only design recommendation.
**Generated:** 2026-10-24 (session date).
**Final disposition:** `DESIGN COMPLETE — OWNER DECISION REQUIRED. Three storage alternatives evaluated against ten criteria; one recommended with rationale; implementation deferred to Aryan.`

> This chunk designs a traceable, reviewer-independent storage + handoff process for the two current-scope sign-offs Chunk 7.30 confirmed are missing. **Nothing is implemented, no `reviews/` directory is created, no reviewer is contacted, no sign-off is filled in.** Final storage choice is explicitly Aryan's.

---

## 1. Repository, branch, HEAD

| Field | Observed | Expected per Chunk 7.31 §2 | Match |
|---|---|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` | same | ✓ |
| Branch | `feature/nlp-semantic` | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` | ✓ |
| Remote (verified in this chunk) | `https://github.com/Aryan2080/AI-Powered-Student-Achievement-Intelligence-Platform.git` | — | **PR workflow architecturally available** |
| Protected hash `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | — | ✓ |
| Protected hash `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | — | ✓ |

No branch switch. No file modified except the creation of this new report.

---

## 2. Existing evidence inventory

Inspected in this chunk (read-only):

| Artifact | Location | Nature | Contains an actual sign-off? |
|---|---|---|---|
| Chunk 7.26A packet (Ashok + Mohan templates in §7 and §8) | [`reports/chunk_7_26A_independent_reviewer_sign_off_packet.md`](chunk_7_26A_independent_reviewer_sign_off_packet.md) | **Templates** with angle-bracketed placeholders | **No** |
| Chunk 7.26A reviewer evidence checklist | [`reports/chunk_7_26A_reviewer_evidence_checklist.md`](chunk_7_26A_reviewer_evidence_checklist.md) | **Audit of evidence state** | **No** — §9.1 and §9.2 are explicitly BLANK placeholders |
| Chunk 7.30 current reviewer evidence audit | [`reports/chunk_7_30_current_reviewer_signoff_evidence_audit.md`](chunk_7_30_current_reviewer_signoff_evidence_audit.md) | **Evidence sweep report** — confirms zero populated sign-offs | **No** |
| Governance decisions (preserves historical outcomes) | [`hybrid_dataset/metadata/arxiv_governance_decisions.md`](../hybrid_dataset/metadata/arxiv_governance_decisions.md) line 6 | Historical fact record: Ashok APPROVE (pre-revision), Mohan REVISE (pre-revision) | **No current-scope sign-off**; only historical pre-revision decisions |
| Reviewer-independence protocol | `hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md` §Reviewer independence (lines 84-104) | Procedural rules | **n/a** — process document |
| Source-registration workflow | `hybrid_dataset/metadata/SOURCE_REGISTRATION_GUIDE.md` §Workflow | Procedural rules | **n/a** |
| Source-promotion gate | `reports/chunk_7_17_arxiv_source_promotion_review_preparation.md` §5.5 (sign-off template) + §5.8 (five-point promotion gate); Chunk 7.26A §6 (eight-condition promotion gate) | Procedural rules + evaluation checklist | **n/a** |
| Source registry (live) | `hybrid_dataset/metadata/sources.yaml` arXiv entry | Target of the review | `review_status: unreviewed` (not promoted) |

**Historical reviewer decisions preserved verbatim and NOT reinterpreted by this chunk:**
- Ashok: APPROVE, historical pre-revision scope.
- Mohan: REVISE, historical pre-revision scope.

Neither is a current-scope sign-off (Chunk 7.30 §4 and §5 confirmed).

---

## 3. Actual reviewer-independence requirements

Verbatim from `TAXONOMY_APPROVAL_CHECKLIST.md` §Reviewer independence (lines 84-104):

> 1. Each of the two reviewers independently reads the label's `definition`, `inclusion_rules`, `exclusion_rules`, and `examples`, together with the adjacent-label definitions and the relevant boundary guidance…
> 2. Each reviewer posts their own `approve` or `revise` decision with a rationale **before** discussing the decision with the proposer or with the other reviewer.
> 3. Discussion may follow once both initial decisions are posted.
> 4. These rules describe the intended review process. They are procedural, not technically enforced — **GitHub does not prevent reviewers from reading the PR together or chatting before posting**. The proposer and reviewers are responsible for respecting the intent.
> …
> The proposer cannot count as either of the two required reviewers.

The protocol was authored for a GitHub-PR workflow. The explicit mention of "GitHub" and "PR" in the protocol is a project-maintained preference, not a technical requirement.

### 3.1 Requirements the storage mechanism must support

For each requirement below, the storage mechanism must either enforce or at minimum make easily auditable:

| # | Requirement | What the storage mechanism must preserve |
|---|---|---|
| R-1 | Reviewer identity and attribution | A verifiable identity bound to the sign-off (not just a pseudonym the proposer wrote). |
| R-2 | Reviewer independence from the proposer | The reviewer identity must not equal the proposer's identity. The proposer of the Chunk 7.15 arXiv registration commit is traceable from `git log`. |
| R-3 | Independent decision submission | Reviewer 1's decision posted BEFORE Reviewer 2 reads it, and before any discussion. |
| R-4 | Posting-order evidence | Timestamps that establish Reviewer 1 → Reviewer 2 order with sub-day resolution (or better). |
| R-5 | Current-scope decision | The decision explicitly addresses the current state (post-Chunk-7.18/7.20/7.22/7.27A), not a prior one. |
| R-6 | Explicit `approve` vs `revise` | A literal `approve` or `revise` string, not a pipe-template `approve \| revise`. |
| R-7 | Original reviewer response preserved | The reviewer's own wording, not paraphrased by the proposer or anyone else. |
| R-8 | Durability / tamper-evidence | The record cannot be silently rewritten after the fact. |
| R-9 | Auditability | A later chunk / reviewer / auditor can inspect the full history (both decisions + any discussion that followed). |
| R-10 | No AI-generated or owner-authored approval is mistakable for human approval | Any AI output must be clearly identifiable; owner-authored notes must not be interpreted as reviewer sign-offs. |

### 3.2 What the protocol does NOT require

- A specific hosting platform. "GitHub" is mentioned as the current project venue, but not mandated.
- A dedicated repository directory.
- Cryptographic signatures (the protocol is procedural).

---

## 4. Storage alternatives

Three options grounded in actual project workflow. Each is evaluated against ten criteria.

### 4.1 Option A — Dedicated repository `reviews/` directory

**Description.** A new top-level `reviews/` directory committed to the repository. Each reviewer posts their sign-off as a dedicated file: e.g. `reviews/src_08ee850ba4b54d1b81cdbd652809b613/reviewer_01_<pseudonym>.yaml`. The reviewer commits their own file (git author = reviewer).

### 4.2 Option B — Pull-request review comments (GitHub)

**Description.** Aryan pushes a `source-promotion/src_08ee850ba4b54d1b81cdbd652809b613` branch (or opens a PR off the current `feature/nlp-semantic` work) and attaches the Chunk 7.26A packet. Each reviewer posts their Chunk 7.26A §7 / §8 sign-off block as a GitHub PR comment (NOT a `Review` with a thumbs-up — the Chunk 7.17 §5.5 note "A thumbs-up emoji, a GitHub 'Approve' review with no body, or a free-form 'lgtm' is **not** a complete sign-off" rules that out). PR comment metadata (author, timestamp, immutable thread) provides the independence + attribution + posting-order evidence.

### 4.3 Option C — Existing governance documentation / report structure

**Description.** Append both reviewers' responses to `hybrid_dataset/metadata/arxiv_governance_decisions.md` (or into a new append-only section inside the existing `reports/` dir). The proposer (or someone) commits the appended text on behalf of each reviewer.

### 4.4 Side-by-side comparison

| # | Criterion | A: `reviews/` dir | B: PR comments | C: existing docs |
|---|---|---|---|---|
| 1 | **Reviewer attribution** | ✓ Strong — git commit `Author:` field binds the file to the committer. Requires reviewer to commit their own file. | ✓ Strong — GitHub user identity on the comment. Not spoofable without compromising the reviewer's account. | ✗ Weak — the commit `Author:` is whoever appended the text, typically the proposer. Reviewer attribution reduces to "the proposer says this was the reviewer's words." |
| 2 | **Scope identification** | ✓ Directory path encodes the source id and reviewer slot. | ✓ PR title / description encodes the source id. The PR enumerates the Chunk 7.26A §3 D-A through D-J decisions. | ⚠ Depends on how the appended text is structured. Easy to lose scope if the file is edited piecewise. |
| 3 | **Independent submission** | ✓ Each reviewer commits their own file. The commits are visible in `git log` with ordered timestamps. | ✓ GitHub PR comments are timestamped and chronologically ordered. | ✗ If the proposer appends both reviewers' text, the "independent submission" guarantee is lost. |
| 4 | **Posting-order evidence** | ✓ Via `git log --format=%ai`. | ✓ Via comment timestamps on the PR. | ✗ Only one commit timestamp; posting order of the two reviewers is not recorded. |
| 5 | **Timestamp provenance** | ✓ Git-signed author timestamp (though trustable only up to clock-correctness; signed-off-by is a strong improvement). | ✓ GitHub-stamped server-side timestamp (independent of client clocks). | ⚠ Depends on commit discipline. |
| 6 | **Auditability** | ✓ `git log reviews/` + `git blame` shows the full history including any later changes. | ✓ GitHub PR UI preserves the entire thread including edits (edited comments show "edited" marker). | ⚠ Append-only documentation is auditable if the convention is strictly followed; weak if edits in place are allowed. |
| 7 | **Original reviewer wording preserved** | ✓ Reviewer commits their own file; nothing is paraphrased. | ✓ Reviewer posts their own comment; nothing is paraphrased. | ✗ If the proposer appends on behalf of the reviewer, there is no proof the words are the reviewer's. |
| 8 | **Risk of AI-generated or owner-authored approval being mistaken for human** | **Low** — the commit `Author:` must be the reviewer (requires reviewer's git identity). An AI-generated commit would show the AI/owner as author, visibly. | **Lowest** — GitHub account identity is bound to the comment. An AI cannot post as the reviewer without the reviewer's account. | **Highest** — anyone with repo write access can append text that *looks* like a reviewer sign-off. This is the Chunk 7.4-D reviewer-independence stop's biggest risk vector. |
| 9 | **Supported by the existing repository** | ⚠ Requires creating a new top-level directory + convention + maybe a schema + maybe a validator. All reasonable but all new. | ✓ Fully supported — the GitHub remote exists (verified in §1); no new repo file needed. | ✓ Already supported — the files exist. |
| 10 | **Requires new architecture or workflow** | ⚠ Minor new workflow: a schema or template for the sign-off files; a convention for who commits them. | ✓ No new architecture; standard PR comment workflow. The Chunk 7.17 §5.5 template already fits a PR-comment post. | ✗ Weakest on independence; would need a strict discipline convention (e.g. "only the reviewer may push the commit that appends their own text"). This replicates Option A on worse ground. |

### 4.5 Short summary

- **Option A** is attribution-strong and auditable but requires reviewer commits (reviewers must have repo write access + git familiarity).
- **Option B** is attribution-strongest, requires no new repo file, aligns with the Chunk 7.17 §5.5 template's "post a PR comment" wording, and uses platform-native independence / timestamping.
- **Option C** is weakest on independence and attribution — the proposer can easily edit text in place and the git author of the appending commit is typically the proposer, not the reviewer. Not recommended.

---

## 5. Proposed handoff workflow

Steps 1-8 describe what Aryan + the two reviewers would do. **Chunk 7.31 does not execute any of these.**

### Step 1 — Aryan selects + authorizes the storage location

Pick one of:

- **A** (recommended fallback): create `reviews/<source_id>/` with a committed schema template.
- **B** (strongly recommended if GitHub is the working platform): push a dedicated promotion PR; the Chunk 7.26A §7 / §8 sign-off blocks become PR comments.
- A hybrid where Aryan prefers one, as long as it satisfies R-1 through R-10 (§3.1).

Aryan authorizes the location in a project-visible way (slack / email / documented decision — explicitly outside Claude's scope).

### Step 2 — Provide the packet to each reviewer independently

- Give Ashok (independently of Mohan) the Chunk 7.26A packet + the Chunk 7.26A reviewer evidence checklist + this Chunk 7.31 design.
- Give Mohan (independently) the same materials.
- Aryan does NOT discuss the decisions with either reviewer before they post.

### Step 3 — Each reviewer submits their own response

- **Reviewer 1** (Ashok OR Mohan — the one who posts first) reads the materials, re-opens the two external evidence URLs (`https://info.arxiv.org/help/license/index.html`, `https://info.arxiv.org/help/api/tou.html`), fills every placeholder in their respective template block (Chunk 7.26A §7 for Ashok, §8 for Mohan), and posts it to the selected storage location.
- **Reviewer 2** posts their own block to the same storage location — WITHOUT reading Reviewer 1's block first.
- Each sign-off block must contain a literal `overall_decision: approve` or `overall_decision: revise` string (not the `|`-pipe template).

### Step 4 — Original responses preserved without rewriting

- No one edits either sign-off block after posting.
- If a reviewer changes their mind, they APPEND a new block; the original stays as history.
- Platform affordances: in Option B, GitHub shows "edited" markers; in Option A, `git log` + `git blame` preserve the history; in Option C, the no-edit discipline must be strictly followed (and auditing is weaker — hence not recommended).

### Step 5 — Scope and attribution check

A follow-up chunk (not Chunk 7.31) checks:
- Both block pseudonyms are populated and not placeholder.
- Neither pseudonym corresponds to the proposer (the git author of the Chunk 7.15 arXiv registration commit, which is on `feature/nlp-semantic` branch).
- Both blocks address the CURRENT scope (post-Chunk-7.27A implementation), not a prior one.

### Step 6 — Current approval conditions evaluated independently

Against the Chunk 7.26A §6 eight-condition checklist (§7 of this report):

- #1 Reviewer 1 `approve` → check against Reviewer 1's block.
- #2 Reviewer 2 `approve` → check against Reviewer 2's block.
- #3-#8 → check per Chunk 7.26A §6 wording.

Only if ALL 8 pass does the next chunk perform the single-field YAML edit (`review_status: unreviewed → verified`).

### Step 7 — Missing or ambiguous evidence stays blocked

- If either block reads `revise`: Chunk 7.17 §5.7 reviewer-disagreement workflow applies. Source stays `unreviewed`.
- If either block is missing: source stays `unreviewed`.
- If either block is ambiguous (e.g. not a literal `approve`): source stays `unreviewed`.
- If the Protocol conformance checks fail (e.g. the "proposer ≠ reviewer" check fails): source stays `unreviewed`.

### Step 8 — Source promotion is a SEPARATE authorized step

Chunk 7.26A §6 condition #8 restates the Chunk 7.17 §5.8 gate: the promotion commit is a single-field YAML edit on `sources.yaml`, bundled with nothing else, performed by the proposer AFTER both sign-offs are visible.

**This chunk does NOT perform or trigger the promotion. The promotion commit is a separate authorized chunk.**

---

## 6. Evidence-preservation requirements

Across all options, the chosen storage mechanism MUST preserve:

| # | Preservation requirement |
|---|---|
| E-1 | Each sign-off block is **immutable after posting** (silent edits are prevented or at minimum visibly flagged). |
| E-2 | The platform-recorded author (git `Author:` for Option A, GitHub user identity for Option B) matches the reviewer's known identity. |
| E-3 | Posting timestamps for Reviewer 1 and Reviewer 2 are visible and ordered. |
| E-4 | Any discussion between reviewers (Chunk 7.17 §Reviewer independence step 3: "Discussion may follow once both initial decisions are posted") is append-only and visually distinguished from the initial sign-off blocks. |
| E-5 | Previously posted historical decisions (Ashok APPROVE pre-revision, Mohan REVISE pre-revision) remain where they are in `arxiv_governance_decisions.md` and are explicitly labeled as pre-revision context, NOT merged into the current-scope responses. |
| E-6 | AI-generated text, if any Chunk-authored report cites a reviewer, must say "cites Ashok's historical APPROVE" rather than treating it as a current sign-off. |
| E-7 | On a `revise` decision, the full rationale is preserved for the proposer to address. |
| E-8 | After promotion, the sign-off blocks are not deleted — they are the audit trail. |

---

## 7. Eight-condition gate status (verbatim preservation; NOT modified)

Current status per Chunk 7.30 §6:

| # | Condition (verbatim) | Depends on current reviewer responses? | Assessable without those responses? | Current status |
|---|---|---|---|---|
| 1 | Reviewer 1 (Ashok) sign-off block present with `decision: approve` | **Yes** | No | **NO (missing)** |
| 2 | Reviewer 2 (Mohan) sign-off block present with `decision: approve` | **Yes** | No | **NO (missing)** |
| 3 | Both sign-off blocks posted independently (Chunk 7.17 §2.6) | **Yes** | No | NO (prerequisite not met) |
| 4 | Neither reviewer is the proposer (Aryan) | **Yes** | Partially — the proposer identity is already known, so this is checkable once #1 and #2 exist | NO (prerequisite not met) |
| 5 | Neither sign-off is AI-generated | **Yes** | Partially — AI-origin is checkable from authorship metadata | NO (prerequisite not met) |
| 6 | No reviewer decision is `revise` | **Yes** | No | NO (prerequisite not met) |
| 7 | Both `license_page_wording` and `tou_page_wording` are `match` (or both reviewers explicitly approved any change) | **Yes** | No | NO (prerequisite not met) |
| 8 | The Chunk 7.17 §5.8 five-point gate is satisfied | **Yes** (subsumes #1 and #2) | No | NO (subsumes #1 and #2) |

**No condition is satisfied. 0 of 8. Chunk 7.31 does NOT change this.**

**Chunk 7.31's design completion does NOT satisfy any of these conditions.** Design is a planning step, not a reviewer sign-off.

---

## 8. Recommended storage option

### 8.1 Recommendation

**Option B — GitHub PR review comments is the recommended primary storage mechanism.** Option A (dedicated `reviews/` directory) is the recommended fallback for environments where PR workflow is not available. Option C is explicitly NOT recommended.

### 8.2 Rationale

- The GitHub remote already exists (`https://github.com/Aryan2080/AI-Powered-Student-Achievement-Intelligence-Platform.git`), so no new infrastructure is required for Option B.
- The Chunk 7.17 §5.5 sign-off template is explicitly described in terms of "post a PR comment" — Option B uses the mechanism the template was authored for.
- GitHub-recorded account identity + server-side timestamping satisfies R-1, R-4, R-5, R-8, and most importantly R-10 (no AI-generated or owner-authored approval can be mistaken for human — the committer's GitHub account is not spoofable without compromising the reviewer's account).
- Reviewer independence (R-3) is auditable via the comment timestamps and the comment-thread order.
- Original reviewer wording (R-7) is preserved — the reviewer types their own comment.
- Edits leave a visible "edited" marker, protecting E-1.

### 8.3 Why NOT Option C

- Option C's attribution column (R-1 in §4.4) is marked "Weak" because the git commit author on an appended-text commit is typically the proposer, not the reviewer.
- Option C's "AI-generated or owner-authored approval mistaken for human" risk (R-10) is marked "Highest" because anyone with repo write access can append text that looks like a reviewer sign-off, and nothing in the file formatting itself distinguishes a genuine reviewer sign-off from a fabricated one.
- The Chunk 7.4-D reviewer-independence stop and the Chunk 7.17 §Reviewer independence protocol were authored specifically to prevent this failure mode.

### 8.4 Why Option A if Option B is unavailable

- If Aryan is unwilling to open a GitHub PR for the promotion (e.g. the branch has local-only work that is not yet pushable), Option A still provides reasonable attribution via git commit authorship — provided each reviewer commits THEIR OWN file.
- This requires each reviewer to have repo write access and git familiarity. If either reviewer prefers not to interact with the repo directly, Option B via PR comments is simpler for them.

### 8.5 The chunk does NOT make the decision

Per Chunk 7.31 §4: "Do not select or implement a storage location on Aryan's behalf." The recommendation above is advisory. **Aryan must authorize the actual choice** before any sign-off collection begins.

---

## 9. Decisions requiring Aryan's explicit authorization

Each row is a decision Chunk 7.31 does NOT make. These are listed for Aryan to pick.

| # | Decision | Options | Chunk's note |
|---|---|---|---|
| D-STORAGE | Which storage mechanism? | Option A (`reviews/` dir) / Option B (PR comments) / Option C (append to `arxiv_governance_decisions.md`) | Recommend B primary, A fallback. C discouraged. |
| D-REVIEWER-IDENT | Each reviewer's pseudonym for the sign-off (e.g. `labeler_001` for Ashok, `labeler_002` for Mohan) + the mapping of pseudonym to real identity (stored elsewhere, NEVER in the repo) | pseudonym + identity-store location | Project convention is `labeler_<NNN>` (Chunk 7.17 §5.5) |
| D-PR-TARGET | If Option B: which branch does the promotion PR target? (`main`, or a dedicated review branch) | Project workflow decision | — |
| D-PROPOSER-ID | Who is the Chunk 7.15 arXiv-registration proposer? Needed to verify Chunk 7.26A §6 condition #4 (reviewer ≠ proposer). | Confirm via `git log` on the Chunk 7.15 commit vs the pseudonyms Ashok and Mohan use | Likely Aryan from the commit history, but needs explicit confirmation |
| D-DEADLINE | Target deadline for both sign-offs to be posted | project-timing decision | Not needed for Chunk 7.31 completion |
| D-DISCUSSION-STORAGE | Where does the post-sign-off discussion happen? (Same PR? Separate thread? Dedicated discussion file?) | Project workflow decision | Must preserve the independence constraint (step 3 of Chunk 7.17 §Reviewer independence) |
| D-REVISE-WORKFLOW | If one or both reviewers return `revise`, how does the proposer address it? Chunk 7.17 §5.7 defines the workflow; Aryan should confirm the specific tracking location (same PR? new PR?). | Project workflow | — |
| D-WHO-COMMITS-PROMOTION | If both reviewers return `approve`, who commits the single-field YAML edit? Chunk 7.17 §5.8 says the proposer; confirmation required. | Confirm via Aryan | — |

---

## 10. Risks and unresolved gaps

| # | Risk / gap | Severity | Notes |
|---|---|---|---|
| G-1 | **Procedural, not technically enforced.** `TAXONOMY_APPROVAL_CHECKLIST.md` line 98-102: "They are procedural, not technically enforced — GitHub does not prevent reviewers from reading the PR together or chatting before posting." Independence is honor-system. | MEDIUM | Documented limitation; Options A and B provide stronger evidence than C but cannot technically prevent collusion. |
| G-2 | **Pseudonym-to-identity mapping is explicitly NOT stored in-repo** (per `TAXONOMY_APPROVAL_CHECKLIST.md` convention). This protects reviewer privacy but makes external verification of "which real human has which pseudonym" dependent on an out-of-band record. | LOW-MEDIUM | Project convention. |
| G-3 | **Both reviewers may need prior onboarding** to the Chunk 7.26A packet + Chunk 7.26A reviewer evidence checklist + this Chunk 7.31 design + the Chunk 7.17 §Reviewer independence rules. Onboarding is out of Chunk 7.31's scope. | LOW | Standard workflow. |
| G-4 | **GitHub PR comment edits leave a marker but can lose content** if a reviewer edits their comment to remove the original decision. The "edited" marker is visible but doesn't by itself preserve the original text. | LOW | Mitigated by E-1 convention. |
| G-5 | **If Option A chosen, the schema for the sign-off file is undefined.** Chunk 7.31 does not design a schema (would be scope expansion). A sibling future chunk would need to define the file format if Option A is adopted. | MEDIUM | Deferred decision. |
| G-6 | **Mohan's primary residual (D-D in Chunk 7.26A §4.2)** on real-Redis integration remains the hardest open question. The storage mechanism does not resolve it — only Mohan can decide. | HIGH | Explicit; not changed by this chunk. |
| G-7 | **Historical pre-revision decisions might be misread as current-scope sign-offs** by a less-careful reader. The storage mechanism must label historical vs current clearly. | MEDIUM | Mitigated by E-5 convention. |

---

## 11. Safety confirmations

Chunk 7.31 did NOT:

- Modify any file (except creating this new report).
- Create a `reviews/` directory.
- Create a sign-off artifact.
- Fill either Chunk 7.26A §7 or §8 template.
- Enter any reviewer decision.
- Contact Ashok, Mohan, or any other person.
- Open, modify, or close a GitHub PR.
- Push, fetch, or otherwise interact with the GitHub remote.
- Promote the arXiv source; `src_08ee850ba4b54d1b81cdbd652809b613` remains `review_status: unreviewed`.
- Change the SIH source; `src_5a8a2998d6f44055a42dcfd8991e4d12` remains `UNKNOWN` + `unreviewed`.
- Change any taxonomy status; all 14 primary-taxonomy labels remain `draft`.
- Implement a collector; collect metadata; call any external API; connect to Redis; provision infrastructure; run training.
- Touch `src/ml`, `src/recommender`, `src/backend` (do not exist).
- Stage, commit, push, or switch branches.
- Fabricate reviewer identities, dates, decisions, rationales, or signatures.
- Reinterpret Ashok's historical APPROVE as covering the current scope.
- Reinterpret Mohan's historical REVISE as approve.
- Re-audit or modify Chunk 7.27A (`coordinator=` injection).
- Weaken, delete, or modify any test.
- Modify `src/*`, `tests/*`, `pyproject.toml`, `requirements.txt`, `sources.yaml`, `arxiv_governance_decisions.md`, or `PROJECT_HANDOFF.md`.

Protected hashes verified at session start and end:
- `PROJECT_HANDOFF.md`: `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` ✓
- `hybrid_dataset/raw/.gitkeep`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` ✓

Chunk 7.4-D reviewer-independence stop preserved.

---

## 12. Final disposition

**DESIGN COMPLETE — OWNER DECISION REQUIRED.**

Three storage alternatives (A: `reviews/` directory; B: PR review comments; C: existing governance documentation) have been evaluated against ten criteria (§4.4). **Option B is recommended as primary; Option A as fallback; Option C is NOT recommended.** The actual choice is Aryan's.

The eight-condition promotion gate (§7) remains at **0 of 8 satisfied**. Chunk 7.31's design completion does NOT by itself satisfy any condition; the gate still requires two actual independent human sign-off blocks.

### 12.1 What this chunk does NOT authorize

- Reviewer sign-off (reviewers must post their own blocks externally).
- Source promotion (no `review_status` change performed).
- Collection, infrastructure, training (all explicitly out of scope).
- Any file modification beyond the creation of this report.

### 12.2 Next step (owner-driven, external to Claude)

1. Aryan decides D-STORAGE (and the related D-PR-TARGET / D-PROPOSER-ID / etc.).
2. Aryan hands the Chunk 7.26A packet + Chunk 7.26A reviewer evidence checklist + this Chunk 7.31 design to Ashok and Mohan independently.
3. Ashok and Mohan post their own sign-off blocks (Chunk 7.26A §7 and §8, every placeholder filled, every D-A through D-J answered, `overall_decision` literal `approve` or `revise`).
4. A FUTURE chunk re-checks the Chunk 7.26A §6 eight-condition gate against the new evidence. Only if all 8 pass does a separate narrowly scoped chunk perform the single-field `review_status: unreviewed → verified` YAML edit.
