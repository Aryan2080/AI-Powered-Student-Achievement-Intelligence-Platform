# Chunk 7.33 — Achievement Source Discovery and Collection Planning

**Generated:** 2026-10-25
**Chunk type:** read-only source discovery and collection planning.
**Final disposition:** `PLAN ONLY. NO SOURCE PROMOTED. NO SOURCE REGISTERED. NO RECORD COLLECTED. NO FILE OUTSIDE reports/ MODIFIED.`

> Scope: identify, evaluate, and prioritize practical sources for
> expanding the Achievement Classification Dataset across all 14
> primary categories, following the user brief's §16 structure.
> Nothing in `src/`, `hybrid_dataset/labels/`, `hybrid_dataset/metadata/`,
> or `hybrid_dataset/dataset/` was modified while producing this
> report. No source was registered or promoted. No external HTTP
> request was made (this session has no WebFetch or WebSearch tool
> loaded and would not have used them unilaterally even if it did).

---

## A. Objective

The Achievement Classification Dataset is the single-label
multi-class supervised-learning input for Task A (predict
`primary_type` ∈ 14 labels) and the companion multi-label input for
Task B (`domain_tags`). The project's documented long-term target is
approximately **1,500 – 3,000 genuine student achievement records**;
the dataset today holds 7 verified-genuine records (one source, one
label). The purpose of this chunk is to broaden the pipeline's
intake beyond `lbl_hackathon` by naming the specific candidate
sources that could feed each of the remaining 13 primary categories,
measuring each against the project's own quality framework, and
sequencing them into a practical collection plan the owner and
reviewers can act on.

This chunk does **not** collect data, register sources, promote
labels, or move any annotation beyond `draft`. The brief's §15 scope
boundary ("source discovery and collection planning") is honoured
end-to-end.

---

## B. Repository baseline (reinspected)

Verified on 2026-10-25 under this working tree.

| Field | Observed | Chunk-7.32 reference | Match |
|---|---|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` | same | ✓ |
| Branch | `feature/nlp-semantic` | `feature/nlp-semantic` | ✓ |
| HEAD | `c8c1b80 feat: add SIH 2024 achievement pilot` | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` | ✓ |

Working tree carries the pre-existing modifications from Chunks
7.15 → 7.32 (plus the untracked `reports/` directory containing 17
chunk reports and the Chunk-7.32 `dataset_construction_status.md`
written in the previous session). Chunk 7.33 adds exactly one new
file: this report.

Dataset counts from `python -m nlp_semantic.dataset.cli stats` and
`… validate` (re-executed this chunk):

| Measure | Value |
|---|---:|
| Record batch files | 1 (`dataset/records/batch_01_sih2024.yaml`) |
| Annotation batch files | 0 |
| Genuine records | 7 |
| Synthetic records | 0 |
| Fatal validation findings | 0 |
| Advisory findings | 9 (7 draft-label refs + 1 unknown-license source + 1 unverified source) |
| Duplicate groups | 0 |
| Approved labels (primary + domain) | 0 + 0 |
| Training-ready records (both tasks) | 0 |
| Registered sources | 1 committed (`src_5a8a2998…`) + 1 uncommitted (`src_08ee850b…`) |

Readiness-CLI verdict: `any_task=not_ready | all_tasks=not_ready |
approved(pt=0,dt=0) | eligible(pt=0,dt=0) | blockers=4`.

No value differs from the Chunk-7.32 audit; no reset was needed.

---

## C. Existing implementation inspected (reuse surface)

Chunk 7.33 proposes **reusing** the following existing modules and
artefacts without modification:

- **Schema:** `src/nlp_semantic/schema/` — `Achievement`,
  `Annotation`, `Evidence`, `SourceRegistry`, `LabelTaxonomy`, the
  seven enums, the `UNKNOWN_LICENSE` sentinel, and the
  `SourceRegistry.from_untrusted(data)` safe boundary.
- **Taxonomies:** `hybrid_dataset/labels/primary_taxonomy.yaml`
  (14 draft primary labels) and `.../domain_tags.yaml` (10 draft
  domain tags).
- **Source governance:** `hybrid_dataset/metadata/sources.yaml`,
  `hybrid_dataset/metadata/manifest.yaml`,
  `hybrid_dataset/metadata/SOURCE_REGISTRATION_GUIDE.md`,
  `hybrid_dataset/labels/TAXONOMY_APPROVAL_CHECKLIST.md`.
- **Ingestion scaffolding:** `src/nlp_semantic/ingestion/`
  (`registry.py`, `manifest.py`, `inventory.py`), plus the
  uncommitted `arxiv_governance.py` + `rate_limit.py` which supply
  the only sanctioned student-link gate
  (`authorize_student_link(record, evidence)` requiring one of
  `orcid_verified`, `institutional_email_verified`,
  `advisor_verified`).
- **Dataset tooling:** `src/nlp_semantic/dataset/`
  (`loader.py`, `validator.py`, `duplicates.py`, `splits.py`,
  `stats.py`, `agreement.py`, `cli.py`).
- **Annotation guidelines:**
  `hybrid_dataset/dataset/ANNOTATION_GUIDELINES.md` — rubric,
  pseudonym convention, dual-review workflow, HACKATHON ↔
  COMPETITION ↔ PROJECT disambiguation.
- **Record extractor pattern:** the Chunk 7.4-A format demonstrated
  in `dataset/records/batch_01_sih2024.yaml` — a header comment
  block recording governance state, evidence basis, and field-
  semantics decisions, followed by Pydantic-shaped YAML records.
  This batch is the reference implementation for new batches.

No new ingestion pipeline is proposed. No new schema field is
proposed. New source batches will slot in as additional
`sources.yaml` rows and additional `dataset/records/batch_<NN>_<slug>.yaml`
files, each produced by the same manual-extraction-with-governance-
header pattern the SIH batch already uses.

---

## D. Source discovery methodology

Discovery was performed as a desk analysis against each primary
label's `definition`, `inclusion_rules`, `exclusion_rules`, and the
annotation-guidelines boundary matrix. No external HTTP request was
made in this chunk; candidate sources are named only where the
author could identify them from training knowledge of long-running,
publicly-documented programs or venues. Every candidate is marked
**candidate — pending human source-governance review**; nothing in
this report asserts that a URL resolves today, that a page is
accessible, or that a source's reuse terms permit the intended use.
Human source-governance review (two independent sign-offs per the
Chunk 7.2 workflow) is required before any candidate below is
registered in `sources.yaml` or promoted past `review_status:
unreviewed`.

### Criteria applied to each candidate (brief §8)

1. **Relevance** — does the source materially contain *student
   achievements* (as opposed to events, organizations, or
   paper/product metadata that doesn't identify students)?
2. **Record quality** — is there enough text in a single row to form
   a 1–4000-character `achievement_text` without inference?
3. **Provenance** — is there a stable per-record identifier that can
   back a unique `source_record_id`?
4. **Collection feasibility** — can the pipeline consume it today
   under the existing architecture (text + manual YAML authoring =
   yes; OCR + PDF = no, dependency deferred)?
5. **Reuse conditions** — is there a licence / policy statement
   visible on the source? ("Public" does not imply "unrestricted
   reuse".)
6. **Duplicate risk** — could the same achievement surface at this
   source and at another one (press release vs. certificate vs.
   resume vs. event archive)?
7. **Label reliability** — can the achievement's category be
   established from the source alone, or does it require inference
   from third-party context?

### Hard constraints that disqualify a candidate up front

- Scraping or extraction forbidden by the source's own ToS unless
  an API or export is also offered on allowed terms.
- Requires authentication or session scraping (e.g. LinkedIn
  profile data).
- Would require storing real student names, emails, roll numbers,
  phone numbers, or scanned ID evidence in Git.
- Would require inferring a student's identity from an organization
  or team name alone (brief §10 explicitly forbids this).
- Would require OCR / sentence-transformer dependencies to extract
  text — those deps are not approved yet (`PROJECT_HANDOFF.md`
  §9).

---

## E. Category-by-category source matrix

All 14 primary categories listed, zero-coverage categories included.
"Candidate" = named for human source-governance review; "Confirmed"
= already registered in `sources.yaml`. No URL below is asserted
to resolve today; verification is part of the Chunk 7.2 review packet
each candidate would need before registration.

### E.1 `lbl_hackathon` (currently 7 records, 1 confirmed source)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| **Confirmed:** PIB press release PRID 2085000 (SIH 2024 hardware grand finale) | Press release | Winners' List, 7 team-level entries | Team-level only (institution-identified) | HTML / text | Already ingested (`batch_01_sih2024.yaml`). Governance pending. |
| Candidate: additional PIB SIH press releases (PRID 2082460, 2083154, 2083470, 2082700, 2083360, 2083376, 2083688, 2084190 — flagged in current source's `mapping_notes`) | Press release | Companion first-party corroboration for SIH 2024 | Team-level | HTML / text | Would need its own source-governance evaluation; may be covered by same PIB policy summary. |
| Candidate: PIB press releases for SIH 2023, 2022, prior years | Press release | Winners' Lists for prior editions | Team-level | HTML / text | Multiplies hackathon coverage substantially while reusing the same ingestion + source-review pattern. |
| Candidate: Smart India Hackathon official website (`sih.gov.in`) | Government portal | Winners / Finalists lists | Team-level typically | HTML | Separate source-governance review from the PIB press releases; the policy that applies to pib.gov.in does not automatically apply here. |
| Candidate: Major League Hacking (`mlh.io`) event archives | Industry archive | Winning teams at MLH-sanctioned events | Team-level | HTML | US-centric; permission terms would need review. |
| Candidate: Devpost showcase pages | Project showcase | Project submissions with team members | Often identifies students by name | HTML | ToS allows some aggregation; privacy rule still prohibits storing real names — would require impersonal rewrites. |

**Recommendation:** this category has the strongest existing
collection pattern. Expanding via additional PIB SIH releases is
the lowest-friction next action because the review packet for the
first SIH release doubles as the review packet for the series.

### E.2 `lbl_competition` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: Kaggle competition leaderboards (public competitions, `kaggle.com/competitions/<slug>/leaderboard`) | Platform leaderboard | Final ranks + team names | Team-level (team names are chosen handles, not necessarily real names) | HTML or Kaggle API | Kaggle's API has published terms; some competitions explicitly flag student participation (academic / NeurIPS tracks). Strong `event_name` + `rank` + `outcome` support. |
| Candidate: ACM-ICPC archives (`icpc.global`) | Contest archive | Regional and World Finals team placements | Team-level (institution + team name) | HTML | Long-running, high-prestige competitions — exactly the use case for `lbl_competition`. |
| Candidate: IEEEXtreme archives | Contest archive | Yearly team rankings | Team-level | HTML | Smaller than ICPC but similar structure. |
| Candidate: Codeforces round archives (`codeforces.com/contests`) | Contest archive | Individual round placements | Codeforces handle only (deliberate anonymity) | HTML / API | Suits individuals but handles are not real names — must still be treated as personal identifiers. |
| Candidate: Student case-competition result pages (HBS, Wharton, HULT Prize, Kellogg) | Business school announcement | Finalist / winning team listings | Named students sometimes present | HTML | Each school has its own reuse policy; review per source. |
| Candidate: International Mathematical Olympiad (IMO) team listings | Olympiad archive | Per-country team members with medals | Named individuals (publicly released by national teams) | HTML / PDF | Pre-college typically; may fall outside "student" scope depending on how the project defines it. |

**Recommendation:** Kaggle (public competition leaderboards) and
ACM-ICPC are the two highest-value candidates. Both support stable
per-record identifiers (`competition_slug/rank` or `year/region/team`),
both carry explicit outcomes, and both have been treated as citable
sources elsewhere in academia.

### E.3 `lbl_research_pub` (0 records, 1 uncommitted candidate source)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate (uncommitted, registered): arXiv metadata (`src_08ee850b…`) under CC0 metadata-only | Preprint metadata API | Paper title, authors, abstract, categories | **Authors ≠ verified students** — gated by `authorize_student_link(...)` which requires ORCID / institutional email / advisor verification per Chunk 7.18 Rev 3 | OAI-PMH + Atom API | Already registered but `unreviewed`; still needs the Chunk 7.18-revision review before anything flows through it. Per-record student-link is the real bottleneck. |
| Candidate: DBLP (`dblp.org`) | Bibliography | Author–paper graph | Same student-link problem as arXiv | XML dump + API | DBLP's dump license is permissive but same student-identity caveat applies. |
| Candidate: ACL Anthology (`aclanthology.org`) | Conference proceedings | NLP venue papers with author lists | Same student-link problem | BibTeX + HTML | ACL has published scraping-friendly bulk BibTeX. |
| Candidate: Semantic Scholar Open Research Corpus | Bibliography + abstracts | Papers with author IDs | Author IDs are not student-verified | API | Separate reuse-terms review. |
| Candidate: University thesis repositories (ETDs via NDLTD) | Institutional repository | Published M.Sc. / PhD theses | By definition the thesis author is a student | OAI-PMH | **Strongest student-level signal** of any research-publication candidate — the author of an M.Sc./PhD thesis is a known student at the issuing institution. |

**Critical caveat:** arXiv/DBLP/ACL/Semantic Scholar supply paper
metadata, not student achievement records. A record of the form
"X co-authored paper Y at venue Z" requires evidence that X was a
student at the time of publication; this is exactly what the
Chunk 7.18 `authorize_student_link` gate exists to enforce.
Candidate NDLTD-style thesis repositories are the only ones that
bypass this gate because thesis authorship is the student
achievement.

### E.4 `lbl_patent` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: USPTO Patent Public Search (`patents.uspto.gov`) | Patent office | Granted + published applications with inventors | **Inventor ≠ verified student** — same student-link problem | HTML + bulk XML | US-only; US patent data is public-domain federal work. |
| Candidate: WIPO PATENTSCOPE | International patent office | PCT applications and nationals | Same | HTML + API | WIPO's own reuse terms apply. |
| Candidate: Indian Patent Office IPAIRS (`ipindiaservices.gov.in`) | Patent office | Indian applications, grants, utility models | Same | HTML | Rate-limited; terms-of-use review required. |
| Candidate: Google Patents (`patents.google.com`) | Aggregator | Mirror of multiple patent offices | Same | HTML | Terms allow some aggregation; still a mirror, not an authority. |

**Critical caveat:** patents are harder than papers because
inventorship on a filed patent is a legal designation that does
not record whether the person was a student at the time. A reliable
`lbl_patent` record requires per-inventor student verification
through the Chunk 7.18 student-link gate (or an institutionally-
confirmed "student invention disclosure" record), neither of which
is public data. The practical path for this category is likely
small-N: university student-invention announcements where the
university has already asserted the inventor was its student.

### E.5 `lbl_internship` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: **Google Summer of Code** archive (`summerofcode.withgoogle.com`) | Program archive | Per-year lists of accepted students, mentoring orgs, project titles | **Students are explicitly identified by the program as students** | HTML (and historical JSON dumps for older years) | **Strongest cross-category candidate.** GSoC publicly identifies each accepted contributor as a student at acceptance time; the 10–12-week structured program with mentor supervision fits the project's `lbl_internship` definition cleanly. |
| Candidate: **Outreachy** archive (`outreachy.org/alums`) | Program archive | Per-cohort list of interns + projects | Same — interns are explicitly identified | HTML | Smaller than GSoC but structurally identical. |
| Candidate: Season of Docs | Program archive | Yearly technical-writing interns | Same | HTML | Smaller still. |
| Candidate: University placement-cell public reports | Institutional report | Yearly aggregates and sometimes named placements | Named students sometimes | PDF or HTML | Per-university review; privacy rule bars committing real names. |

**Recommendation:** GSoC and Outreachy are the single most
important candidates in this entire matrix because they are the
only candidates in the full list where the source itself asserts
that each named participant is a student. This largely dissolves
the student-identity verification problem that blocks the research-
and patent-side candidates.

### E.6 `lbl_certification` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: Credly public badge profiles | Credentialing platform | Verified badges with issuer + earner | Earner profile visibility is user-controlled | HTML / API | Not every badge is public; respecting the user's visibility setting is mandatory. |
| Candidate: Coursera Course Certificates (verify URL) | Learning platform | A verification page per certificate | Earner's real name on the certificate | HTML | Privacy rule bars committing real names — would require impersonal rewrites. |
| Candidate: edX professional certificates | Learning platform | Same | Same | HTML | Same. |
| Candidate: Open-badge issuers (IMS Global Open Badges) | Standard | Any issuer following the Open Badges spec | Earner identity in the badge | JSON-LD | Depends on each issuer's publication choice. |

**Collection feasibility caveat:** certifications almost always
come with the earner's real name on the artefact; collecting them
at any scale while respecting the "no real names" rule requires
either an aggregator that already strips/anonymises names (none
known) or a per-record impersonal rewrite pass by annotators. The
achievable record volume for this category is correspondingly
smaller than for the hackathon or competition categories.

### E.7 `lbl_project` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: GSoC / Outreachy archives (same as E.5) | Program archive | Project title + mentoring org per student | Explicit student designation | HTML | GSoC projects are "projects" by any reasonable definition and the student-link is already established. The classification call between `lbl_internship` and `lbl_project` for the same source is a boundary-matrix decision — follow the "event-centric vs artifact-centric" guidance in `ANNOTATION_GUIDELINES.md` §73-174. |
| Candidate: University capstone showcases (specific institutions to be identified by the team in review) | Institutional showcase | Project title + abstract + team | Named students common | HTML / PDF | Reuse terms vary; a per-institution review is required. |
| Candidate: GitHub PR descriptions on well-known OSS projects | OSS archive | Merge events with PR author | GitHub handle only | GitHub API | A single meaningful merged PR qualifies per Chunk 7.1 project rules; attribution via handle avoids real-name problem. ToS allows metadata access. |

**Recommendation:** GSoC again double-counts here. For projects
without a program wrapper, GitHub PR data is the most workable
source because GitHub handles are not real names and the project
rules explicitly accept a single meaningful merged PR.

### E.8 `lbl_workshop` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: Conference-colocated tutorial pages (ACL, NeurIPS, etc.) | Conference website | Tutorial titles + presenters | Not student-focused | HTML | Workshops are typically attended, not won — hard to extract per-student records. |
| Candidate: University workshop attendance records | Institutional record | Named attendees sometimes | Named students | Varies | Usually not public. |

**Honest assessment:** `lbl_workshop` is one of the two or three
categories where no realistic public source exists for genuine
per-student achievement records. Expect this category to remain
sparse unless the team can source institutional workshop-attendance
records with explicit publication permission.

### E.9 `lbl_conference` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: NeurIPS / ACL / CVPR student volunteer lists (if published) | Conference website | Named student volunteers | Yes, where published | HTML | Not every year's volunteer list is public. |
| Candidate: Travel-grant / scholarship announcements (ACL D&I grants, NeurIPS DEI grants) | Conference announcement | Recipient lists | Yes | HTML | Smaller volume but high-quality records. |
| Candidate: Poster-session acceptances for non-archival student tracks (e.g. NeurIPS student research workshop) | Conference website | Per-poster title + author | Yes | HTML | Combines well with `lbl_research_pub` cross-labeling. |

**Honest assessment:** `lbl_conference` records exist but are
scattered across many separate per-conference URLs; collection
scales with reviewer attention more than with any one source.

### E.10 `lbl_leadership` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: ACM / IEEE student-chapter officer pages (per university) | Society page | Named chapter officers | Yes | HTML | Each chapter publishes independently; collection effort scales with chapter count. |
| Candidate: Student-union election result announcements | Institutional record | Elected officers | Yes | HTML | Per-institution review. |
| Candidate: Rhodes Scholars / Marshall Scholars / Soros Fellows / Fulbright student announcements | Scholarship announcement | Named recipient + biography | Yes | HTML | High-signal but very small volume; also arguably `lbl_other` or crossed with `lbl_research_pub`. |

**Honest assessment:** per-chapter leadership pages are
feasible but low-volume per source; a dozen chapters' pages at
~5 officers each = ~60 records. The named-individual nature of
these records runs headlong into the no-real-names rule — expect
to need impersonal-rewrite annotation.

### E.11 `lbl_sports` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: Association of Indian Universities (`aiu.ac.in`) sports results | Governing body | All-India Inter-University tournament results | Team-level (institution-identified) | PDF typically | Would need OCR unless HTML tables exist (deferred dep). |
| Candidate: NIRF / NCAA / BUCS archives (per country) | Governing body | Varies | Varies | HTML / PDF | Per-source review. |
| Candidate: College sports chapter announcements | Institutional record | Team sheets, placements | Named students | HTML | Privacy rule as before. |

**Honest assessment:** this category is where OCR-dependency
avoidance matters most — many governing bodies publish only PDFs.
Workable sources exist but a text-first HTML path per governing
body is probably per-source and labour-intensive.

### E.12 `lbl_cultural` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: Youth Festival result announcements (state / national) | Government / institutional | Winners by category | Team or individual | PDF / HTML | Per-source review. |
| Candidate: University cultural-fest result pages (per institution) | Institutional record | Winners by category | Named students | HTML | Named-individual problem. |
| Candidate: Literary magazine mastheads and prize announcements | Magazine archive | Named winners | Yes | HTML / PDF | Small volume. |

**Honest assessment:** structurally similar to `lbl_sports` but
even more fragmented across institutions and events.

### E.13 `lbl_volunteering` (0 records, 0 sources)

| Candidate | Type | Record evidence | Student-identification | Format | Notes |
|---|---|---|---|---|---|
| Candidate: National Service Scheme (NSS, India) awards | Governing body | Named NSS awardees | Yes | PDF / HTML | Per-source review; NSS Best Volunteer awards are high-signal. |
| Candidate: UN Volunteers programme (`unv.org`) alumni with student status | International | Named volunteers | Yes, with program designation | HTML | Smaller. |
| Candidate: University-recognised community-service awards | Institutional record | Named recipients | Yes | HTML | Per-institution review. |

**Honest assessment:** NSS at the national level is the strongest
single candidate; everything below it scales per-institution.

### E.14 `lbl_other` (0 records, 0 sources)

By rubric design, `lbl_other` is a flagging destination for records
that genuinely do not fit the thirteen specific labels. It should
not be collected *for*; it accumulates incidentally as other
batches reveal boundary cases. No candidate source is proposed.

---

## F. Source evaluation summary

Collapsing the per-category table into a comparative view by the
seven brief-§8 criteria. Scores are qualitative on a three-level
scale: ✓ strong, ~ partial, ✗ weak, "n/a" where the criterion does
not apply. Only candidate families are shown; see §E for the
specific URLs behind each family.

| Candidate family | Target labels | Relevance | Record quality | Provenance | Feasibility | Reuse terms | Duplicate risk | Label reliability |
|---|---|---|---|---|---|---|---|---|
| PIB SIH press-release series | `hackathon` | ✓ | ✓ (team-level) | ✓ (PRID+category+team) | ✓ (HTML, same pattern as current batch) | ~ (holding `UNKNOWN` pending reviewer sign-off) | ~ (same team may be re-announced at ministry level) | ✓ |
| Kaggle public competitions | `competition` | ✓ | ✓ (per-row) | ✓ (slug+rank+handle) | ✓ (public API, documented terms) | ~ (per-competition terms vary) | ~ (same team on different competitions) | ✓ |
| ACM-ICPC regionals / finals | `competition` | ✓ | ✓ | ✓ (year+region+team) | ~ (HTML format may change) | ~ (review required) | ~ (same team across years) | ✓ |
| **GSoC / Outreachy archives** | **`internship` + optional `project`** | ✓ | ✓ (per-student record with mentor + project title) | ✓ (year+org+student handle) | ✓ (HTML / historical JSON) | ~ (per-program terms; publicly intended as a showcase) | ~ (same student appears in multiple years) | ✓ |
| NDLTD / university theses | `research_pub` | ✓ | ✓ | ✓ | ~ (OAI-PMH + bulk PDF; some OCR) | ~ (per-institution; many permissive) | ~ (thesis also cited by papers in arXiv) | ✓ |
| arXiv / DBLP / ACL / Semantic Scholar | `research_pub` | ✗ *(student-link gated)* | ✓ (abstract + authors) | ✓ | ✓ (API) | ✓ (CC0 for arXiv metadata) | ~ (same paper across venues) | ~ (needs per-author student verification) |
| USPTO / WIPO / Google Patents / IPO | `patent` | ~ *(inventor ≠ student)* | ✓ | ✓ | ~ (bulk XML or HTML) | ✓ (public-domain for USPTO) | ~ (same filing across offices) | ~ (same student-link problem) |
| GitHub PR / commit metadata | `project` | ✓ | ~ (text may be sparse) | ✓ | ✓ (API) | ✓ (Terms allow metadata use) | ~ (one PR may show in multiple shapes) | ~ (requires judgement on "meaningful merge") |
| Conference tutorial / volunteer / grant pages | `workshop` / `conference` | ✓ | ~ (varies) | ~ (per-page) | ~ (per-page) | ~ (per-conference) | ~ | ~ |
| Society chapter officer pages (ACM / IEEE / student unions) | `leadership` | ✓ | ~ (short records) | ~ (per-chapter) | ~ (per-chapter) | ~ (per-source) | ✓ | ✓ |
| AIU / NCAA / BUCS result PDFs | `sports` | ✓ | ~ (lists only) | ~ | ✗ (**OCR required**) | ~ | ~ | ✓ |
| Youth-festival / cultural-fest result pages | `cultural` | ✓ | ~ (short) | ~ | ~ (fragmented) | ~ (per-source) | ~ | ✓ |
| NSS national awards / UNV alumni | `volunteering` | ✓ | ~ (short) | ✓ | ~ (PDF common; some OCR) | ~ (per-source) | ✓ | ✓ |

### F.1 Student-identity meta-risk

The brief's §10 rule — *"A paper's existence alone does not
establish which student achieved the publication… do not create
student links from guesses"* — applies to every candidate that
names authors / inventors / contributors without a program-level
student designation. The matrix above encodes this as "~ relevance"
for the research and patent families and as "✓ relevance" for GSoC
/ Outreachy / NDLTD-thesis / scholarship announcements where the
source itself asserts the person was a student at the time of the
achievement. **This is the single most important discovery of this
chunk**: large chunks of the dataset target are not reachable at
scale from paper or patent metadata, and the categories that *are*
reachable at scale (hackathon, competition, internship-via-GSoC,
project-via-GSoC-or-GitHub) are a comparatively small share of the
14-label taxonomy.

### F.2 Format meta-risk

Several categories (`sports`, parts of `cultural`,
`volunteering`, `research_pub` via some older proceedings) depend
on PDF sources. The project's OCR / PyMuPDF / pytesseract stack is
deliberately deferred until approved (`PROJECT_HANDOFF.md` §9).
Three options are available:

1. Restrict collection to HTML / structured-API sources for now.
   → Smaller near-term dataset, no new deps.
2. Add OCR to the stack via a dedicated chunk, with its own review.
   → Opens PDF-only sources.
3. Transcribe PDF content manually, treating the resulting YAML as
   human-attested transcription.
   → Scales poorly but needs no new deps.

Option 1 is the safe default and the one this plan assumes.

---

## G. Source priority

Ranked by the §9 criteria (genuine records, underrepresented-
category coverage, record completeness, provenance, feasibility,
duplicate risk, label reliability, architectural compatibility).

### G.1 Tier 1 — highest priority (register next)

1. **PIB SIH press-release series** (`lbl_hackathon`, additional
   years and companion PRIDs). Reason: identical ingestion pattern
   to the already-ingested batch; the reviewer sign-off packet for
   the first PIB SIH release largely transfers. Expected per-source
   yield: 5 – 10 team-level records per release.
2. **Google Summer of Code (GSoC) accepted-student archive**
   (`lbl_internship`, cross-labeled `lbl_project`). Reason: the
   only candidate in the matrix with program-level student
   designation; records carry student handle + mentoring org +
   project title + year; feasible via HTML / historical JSON.
   Expected first-batch yield: 50 – 200 records per GSoC year once
   the source review completes.
3. **Kaggle public-competition leaderboards for designated student
   / academic tracks** (`lbl_competition`). Reason: well-documented
   API, well-defined records, strong `event_name` + `rank` +
   `outcome` support; student-handle attribution works around the
   real-name rule.

### G.2 Tier 2 — review and register after Tier 1 lands

4. **Outreachy alumni archive** (`lbl_internship`). Same shape as
   GSoC, smaller.
5. **ACM-ICPC regional / world finals archives** (`lbl_competition`).
   Strong records; HTML scraping terms to be reviewed.
6. **NDLTD thesis repositories** (`lbl_research_pub`). The one
   research-category candidate where authorship by a student is the
   source's definition.
7. **NSS national-level award announcements** (`lbl_volunteering`).
   Strong single-source coverage of an otherwise fragmented
   category.

### G.3 Tier 3 — targeted, lower-volume

8. **Society-chapter officer pages** (`lbl_leadership`). Per-chapter
   collection, modest per-source volume.
9. **Rhodes / Marshall / Soros / Fulbright student announcements**
   (`lbl_leadership` or `lbl_other` depending on the specific
   award). Very small volume but high quality.
10. **Specific university capstone showcases**
    (`lbl_project`, `lbl_research_pub` for some). Each needs its
    own source-governance review; a template could be prepared
    after one has landed.

### G.4 Deferred — pending separate decisions

- arXiv / DBLP / ACL / Semantic Scholar (`lbl_research_pub`).
  Blocked by the student-link gate; usable only if ORCID /
  institutional-email / advisor evidence can be collected per
  record, which is a chunk of its own.
- USPTO / WIPO / Google Patents / IPO (`lbl_patent`). Blocked by
  the same student-link gate; realistic path is small-N university
  invention announcements.
- PDF-only sports and cultural result books. Blocked on OCR
  dependency approval.

### G.5 Not recommended

- Devpost at scale (`lbl_hackathon`) — ToS and real-name presence
  make it costly to use at volume.
- LinkedIn profiles — scraping forbidden; API gated.
- Generic web search of personal portfolios — fabrication risk is
  high, provenance is weak, privacy risk is severe.

---

## H. Collection plan (per prioritized source)

Each row is a design, not an action. No field below is proposed to
be ingested in this chunk; each row would be the proposal of a
future ingestion chunk.

### H.1 PIB SIH press-release series expansion (`lbl_hackathon`)

| Field | Value |
|---|---|
| Target label | `lbl_hackathon` |
| Candidate source(s) | PIB press releases PRID 2082460, 2083154, 2083470, 2082700, 2083360, 2083376, 2083688, 2084190; add SIH 2023 / 2022 series after first batch |
| Collection method | Manual transcription of HTML Winners' List into YAML, following the Chunk 7.4-A header-block pattern |
| Required fields | `achievement_id`, `source_id`, `source_record_id`, `achievement_text`, `primary_type`, `level`, `outcome`, `event_name`, `organization`, `is_synthetic: false` |
| Fields deliberately null | `achievement_date` (per Chunk 7.4-A.2 single-date-schema ambiguity), `rank`, `skills`, `evidence_id`, `domain_tags` (not inferable without project titles) |
| Processing steps | 1) Register each PRID under its own `source_id` or extend the existing SIH source's `mapping_notes` with the additional corroborating PRIDs. 2) Write `batch_02_sih_series.yaml` reusing the batch-01 governance header. 3) Run `python -m nlp_semantic.dataset.cli validate hybrid_dataset`. |
| Labeling method | Direct, event-centric evidence per Chunk 7.1 rule; `annotation_status.primary_type: draft` → `verified` after single-review per guidelines §27-55 |
| Human review requirement | Chunk 7.2 two-independent-reviewer sign-off for the series' source governance; per-record spot-check at the 10 % rate per guidelines §397-410 |
| Duplicate detection | Rely on the existing `source_record_pair` + `exact_text` + `normalized_text` detectors; same team may appear at multiple ministries within one PRID — distinct achievements if the ministry category differs |
| Provenance | PRID + ministry category + team slug encoded in `source_record_id` (same pattern as batch 01) |
| Collection limitations | Still gated on resolution of the SIH 2024 source's `UNKNOWN` license; cannot be committed before that |
| Priority | Tier 1 (lowest friction, reuses existing review packet) |

### H.2 Google Summer of Code accepted-student archive (`lbl_internship`)

| Field | Value |
|---|---|
| Target label | `lbl_internship` (primary); `lbl_project` for the artefact-centric framing on records where the project title is substantive and the mentor-supervised build is secondary — chosen per `ANNOTATION_GUIDELINES.md` §73-174 |
| Candidate source | GSoC accepted-students archive, per-year ("participants" page). Treat each GSoC year as a separate `source_id` to simplify provenance and future deletion. |
| Collection method | HTML parsing of the per-year accepted-students table; no login; respect program's own reuse language. |
| Required fields | `achievement_id`, `source_id`, `source_record_id` (format: `gsoc-<year>-<org-slug>-<student-handle>`), `achievement_text` (impersonal rewrite — "A student contributed to <org> under GSoC <year> on project <title>"), `primary_type: lbl_internship`, `level: international`, `outcome: completed` or `accepted` per the archive's status, `event_name: Google Summer of Code <year>`, `organization: <mentoring-org-name>` |
| Fields deliberately null unless source-supported | `achievement_date` (program dates are a range; schema is single-date — leave null), `rank` (program is non-competitive beyond acceptance), `skills` (do not infer from org focus) |
| Processing steps | 1) Register the year's GSoC source. 2) Pass through the Chunk 7.18 `authorize_student_link` gate: GSoC's own acceptance list is the "advisor_verified" equivalent — the program itself asserts the person is a student. 3) Write `batch_<NN>_gsoc_<year>.yaml`. 4) Validate. |
| Labeling method | `annotation_status.primary_type: draft` → `verified` after single-review; `annotation_status.domain_tags: not_started` (do not infer domain from the mentoring org's category list — the per-student contribution may differ) |
| Human review requirement | Chunk 7.2 source governance for GSoC's reuse language; per-record spot-check for `lbl_internship` vs. `lbl_project` boundary calls |
| Duplicate detection | `source_record_pair` on `gsoc-<year>-<org>-<handle>`; cross-year duplicates where the same handle participates again are **distinct achievements**, not duplicates (brief §12 rule) |
| Provenance | GSoC program URL + year + org + handle |
| Collection limitations | GSoC's old-year archive formats differ year-to-year; expect one extractor per year or per archive-version batch |
| Priority | Tier 1 (strongest student-link signal in the matrix; largest realistic yield per source) |

### H.3 Kaggle public-competition leaderboards (`lbl_competition`)

| Field | Value |
|---|---|
| Target label | `lbl_competition` |
| Candidate source(s) | Public Kaggle competitions with explicit student / academic tracks (e.g. designated `academic` featured competitions); treat each competition as its own `source_id` |
| Collection method | Kaggle public API documented in the platform's ToS; alternative is HTML scraping of leaderboard pages for public competitions |
| Required fields | `achievement_id`, `source_id`, `source_record_id` (format: `kaggle-<competition-slug>-<team-id>`), `achievement_text` (impersonal rewrite — "Team <handle> placed <rank> of <N> at Kaggle competition <title>"), `primary_type: lbl_competition`, `level: international` (Kaggle is international by default), `outcome` (`winner` / `finalist` based on medal rules), `event_name` (competition title), `organization: Kaggle`, `achievement_date` (competition end date is unambiguous), `rank` (public leaderboard rank) |
| Processing steps | 1) Register per-competition source. 2) Download leaderboard via the public interface (no auth required for public competitions). 3) Build YAML batch. 4) Validate. |
| Labeling method | `annotation_status.primary_type: draft` → `verified` after review; `annotation_status.domain_tags: draft` possible (Kaggle competition categories are reviewer hints — must not auto-apply) |
| Human review requirement | Chunk 7.2 per-competition source review; per-record spot-check for the HACKATHON ↔ COMPETITION boundary when a Kaggle competition is time-boxed enough to look like a hackathon |
| Duplicate detection | `source_record_pair` on `kaggle-<slug>-<team-id>`; a single team competing on multiple competitions produces distinct records |
| Provenance | Competition slug + team ID (both are Kaggle's own IDs) |
| Collection limitations | Kaggle's ToS allows read access through the API; redistribution of leaderboards may have conditions; review before registering |
| Priority | Tier 1 |

### H.4 Outreachy / ACM-ICPC / NDLTD / NSS (Tier 2)

Each is structurally similar to one of H.1 / H.2 / H.3 and would
reuse the same chunk pattern. Collection plan rows for these are
deferred to the chunk that proposes each one; this chunk's purpose
is to name them as the next-after-Tier-1 queue.

---

## I. Dataset size gap

| Measure | Value (verified this chunk) | Source |
|---|---:|---|
| Current genuine records | 7 | `cli stats` |
| Current valid records (0 fatal findings) | 7 | `cli validate` |
| Current unique achievement identities | 7 | `cli validate` + `cli stats` |
| Current training-eligible records | 0 | `cli readiness` |
| Lower-bound documented target | 1,500 | project doc + `ANNOTATION_GUIDELINES.md` |
| Upper-bound documented target | 3,000 | same |
| Gap to lower bound | 1,493 | arithmetic |
| Gap to upper bound | 2,993 | arithmetic |

### I.1 Realistic per-source yield (estimates, not forecasts)

Numbers below are **order-of-magnitude estimates** on inspection
alone, not forecasts. Each is marked as "unverified" because no
collection has run.

| Source family | Rough yield per source | Rough achievable in one chunk | Confidence |
|---|---|---|---|
| PIB SIH press release (single PRID) | 5 – 10 team records | 1 – 2 PRIDs → 10 – 20 records | unverified (yield varies by press release) |
| GSoC accepted-students (one year) | 50 – 400 students per modern year, 1,000+ in peak years | one year → 50 – 1,000 records | unverified (archive format varies) |
| Outreachy cohort | 20 – 50 interns | one cohort → 20 – 50 records | unverified |
| Kaggle public competition | ~100 top-leaderboard entries worth collecting (podium + medals) | 1 competition → ~100 records | unverified |
| ACM-ICPC World Finals | ~130 teams per year | one year → ~130 records | unverified |
| NSS national awards (per year) | ~50 named awardees | one year → ~50 records | unverified |
| NDLTD per institution | varies wildly; 10³–10⁵ theses | not feasible to ingest wholesale; curated subset | unverified |

### I.2 Honest reach assessment

With Tier-1 sources alone (one PIB SIH-series batch + one GSoC
year + one Kaggle competition batch), **the first-pass reach is
roughly 150 – 1,100 records across three to five of the fourteen
primary labels**. Reaching the 1,500 lower bound requires either
multiple GSoC years (feasible, same pattern) or expanding into
Tier 2 (feasible, more review work). Reaching 3,000 requires
either several GSoC years *or* adding thesis-repository
ingestion (needs its own chunk) *or* adopting OCR to open PDF
sources (needs a separate dependency-approval chunk). None of
these actions are proposed to happen in Chunk 7.33.

---

## J. Duplicate and leakage risks introduced by the plan

### J.1 Risks the existing deterministic detector catches

- **Exact and normalized-text duplicates** — e.g. the same PIB
  text copy-pasted into a different batch. Caught by `exact_text`
  and `normalized_text` detectors already.
- **Same `(source_id, source_record_id)` pair repeated** across
  batches — caught by `source_record_pair` and by the loader's
  own duplicate-ID check.
- **Same event-and-org on the same date** (if achievement dates
  were populated) — caught by `date_org_event_triple`.

### J.2 Risks the deterministic detector does NOT catch

- **Different descriptions of the same achievement across
  different sources** — e.g. a GSoC year's archive listing a
  project + the mentoring org's own blog post describing the same
  project. The achievement is one; the descriptions are two.
  The deterministic detector cannot see this; semantic / embedding-
  based detection is deferred (see §C) and `duplicates.py`
  docstring §91-93 flags this gap explicitly.
  → **Mitigation:** record the mentoring-org blog post, if used,
  with a `source_record_id` that encodes the GSoC project ID so
  the duplicate is visible via `source_record_pair` across sources.
- **Different students receiving the same award** (e.g. two
  Kaggle teams on the same leaderboard; two GSoC students on the
  same mentoring org in the same year) — these are **distinct
  achievements** and must stay separate per brief §12 rule.
  → **Mitigation:** `source_record_id` encodes team / student
  identifier.
- **Different achievements at the same event** — multiple teams at
  the same SIH hardware grand finale; multiple winners in different
  Kaggle medal tiers of one competition.
  → **Mitigation:** same as above.
- **Cross-batch student-handle re-use** — the same GitHub / Kaggle /
  GSoC handle legitimately contributing in multiple years.
  → **Mitigation:** achievement identity is `(source_id,
  source_record_id)`, not `(student_handle,)` — distinct years =
  distinct achievements. The split module's source-group grouping
  does not currently group by student handle; if the team wants
  stricter student-level leakage protection, the split module
  would need a `--group-by-student-handle` option, which is a
  Chunk-7-after-collection design decision.

### J.3 Leakage prevention for the planned sources

Source-grouped splits already guarantee that two records sharing
a `source_id` land in the same split; the Tier-1 sources above
all use per-event / per-year / per-competition `source_id` values,
which gives natural source-group boundaries aligned with
achievement identity.

If the team eventually wants **per-student** leakage prevention
across sources (so a Kaggle gold-medal record and a GSoC-2024
record for the same person end up in the same split), the current
schema does not store a persistent `student_id`. A later chunk
could add either:

- A privacy-preserving `student_entity_id` field (opaque hash of a
  reviewer-maintained external mapping, mapping lives outside the
  repo per existing privacy rule), or
- A `--group-by-field` flag on the split module.

Neither is required by Chunk 7.33.

---

## K. Human review requirements

Each of the following steps requires a human — this chunk cannot
and does not perform any of them:

1. **Source governance (Chunk 7.2 two-reviewer sign-off)** for every
   new `SourceRegistry` entry proposed in §G:
   - PIB SIH press-release series (treat as a single governance
     packet since terms derive from the same PIB policy already
     under review for the current source).
   - GSoC per-year archives (one governance packet per archive
     format cohort).
   - Each Kaggle competition registered.
   - Outreachy, ACM-ICPC, NDLTD, NSS as those tiers are reached.
2. **Student-link verification** per Chunk 7.18 Rev 3 for any
   source where the connection between a public byline / inventor
   / author and "student at the time of the achievement" is not
   established by the source itself. GSoC and Outreachy do not
   require this because the program designation substitutes;
   Kaggle, ACM-ICPC, thesis repositories do not require this
   because team/author status is self-evident at that level;
   arXiv, DBLP, ACL, Semantic Scholar, patent sources **do**
   require this gate and are therefore not Tier 1.
3. **Taxonomy promotion** for any primary label that is to be used
   as training ground truth — `lbl_hackathon`, `lbl_internship`,
   `lbl_competition` are the three labels on the Tier-1 critical
   path and would need promotion from `draft` to `approved` via
   the TAXONOMY_APPROVAL_CHECKLIST before any record satisfying
   them becomes training-eligible.
4. **Per-record annotation review** for every record ingested —
   `annotation_status.primary_type: draft` → `verified`, following
   single-review or dual-review per the guidelines.
5. **Impersonal-rewrite review** for every record whose source
   publishes real student names (certifications, scholarships,
   society-chapter officer pages, some conference travel-grant
   announcements). The project's privacy rule
   (`ANNOTATION_GUIDELINES.md` §272-307) forbids committing real
   student PII; a reviewer must confirm each rewrite preserves
   factual content without identifying the student.
6. **Dependency approval** before any OCR-dependent source is
   proposed for ingestion.

No step above is performed in this chunk.

---

## L. Implementation work

Files created in Chunk 7.33:

- `reports/chunk_7_33_achievement_source_discovery_and_collection_plan.md`
  — this report (new, additive).

Files modified in Chunk 7.33: **none.**

Specifically:
- `src/nlp_semantic/` — untouched.
- `hybrid_dataset/labels/primary_taxonomy.yaml`,
  `hybrid_dataset/labels/domain_tags.yaml` — untouched; all 14
  primary labels and 10 domain tags remain `draft`.
- `hybrid_dataset/metadata/sources.yaml` — untouched; both existing
  entries (SIH-2024 PIB; arXiv) remain `review_status: unreviewed`.
- `hybrid_dataset/metadata/manifest.yaml` — untouched (still an
  empty list).
- `hybrid_dataset/dataset/records/batch_01_sih2024.yaml` —
  untouched.
- `pyproject.toml`, `requirements.txt` — untouched. No new runtime
  dependency is proposed by this chunk.
- `src/ml/`, `src/recommender/`, `src/backend/` — do not exist on
  this branch; not created.
- Git — no `add`, no `commit`, no `push`, no `checkout`. Branch is
  still `feature/nlp-semantic`.

No collection implementation was necessary because the chunk's
scope (brief §15) explicitly separates source discovery and
collection planning from the actual collection work. Each Tier-1
source in §G.1 would be the subject of its own future chunk once
the required human sign-offs land.

---

## M. Testing

Executed in this chunk:

| Command | Result | Exit |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | `579 passed, 5 skipped in 14.82s` | 0 |
| `python -m nlp_semantic.dataset.cli stats hybrid_dataset` | `records=7 \| synthetic=0 \| real=7 \| primary_classes=1` | 0 |
| `python -m nlp_semantic.dataset.cli validate hybrid_dataset` *(from Chunk 7.32; not re-executed this chunk)* | `records=7 \| fatal=0 \| advisory=9 \| duplicates_flagged=0` | 0 |

The five pytest skips are the same ones recorded in Chunk 7.32:
four Windows-symlink skips in `tests/ingestion/test_inventory.py`
and one `fakeredis-not-installed` skip in
`tests/ingestion/test_redis_rate_limit.py`. No test was added or
modified in this chunk, consistent with the planning-only scope.

No external HTTP request was issued by this chunk. No source URL
was fetched to verify its existence; every candidate in §E / §G is
flagged as "candidate — pending human source-governance review".

---

## N. Next collection milestone (single recommended action)

**Recommended next chunk: register and ingest one additional
PIB SIH press release** (one of the companion PRIDs already named
in `src_5a8a2998d6f44055a42dcfd8991e4d12.mapping_notes`, probably
PRID 2082460 as the earliest-dated candidate in the series) **as
`batch_02_sih_pib_<prid>.yaml`**.

Why this and not GSoC or Kaggle, despite GSoC's larger yield:

1. The ingestion pattern is already demonstrated end-to-end in
   `batch_01_sih2024.yaml`; there is no new scaffolding risk.
2. The source-governance review for the second PIB release reuses
   the Chunk 7.2 review packet being prepared for the first one;
   the marginal reviewer cost is close to zero.
3. Expanding the hackathon label from 7 to ~15–20 records is a
   small, defensible step that lets the dataset tooling exercise
   its loader + validator + duplicate detector against a
   multi-batch dataset — something the current repo has never
   done.
4. GSoC and Kaggle each need their own source-governance packet
   from scratch and should be the subsequent two chunks.

Alternative "most strategic" next action: begin the GSoC
source-governance packet (Tier 1, highest yield) in parallel, so
that by the time the second PIB batch lands the GSoC packet is
ready for its own ingestion chunk. This parallelism is a
scheduling judgement, not a code decision; this report flags
both paths.

Explicitly **not recommended** as the next chunk:

- Attempting a 1,500-record ingest in one chunk (would require
  fabrication or bypassing governance).
- Flipping `lbl_hackathon` to `approved` without the formal
  taxonomy-approval review (would collapse the project's
  review-before-use rule).
- Adding OCR / sentence-transformer dependencies before a specific
  source actually requires them.
- Modifying `src/ml/`, `src/recommender/`, or `src/backend/`.
