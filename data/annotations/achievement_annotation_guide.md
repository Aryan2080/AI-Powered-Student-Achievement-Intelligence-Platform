# Achievement Classification Annotation & Boundary Resolution Guide
**AI-Powered Student Achievement Intelligence Platform**  
**Role:** Member 1 — NLP & Semantic Intelligence Engineer  
**Version:** 1.0.0  

---

## 1. Dataset Purpose & Foundational Principles

The primary objective of this dataset is to provide a clean, standardized, and diverse ground-truth corpus for training supervised NLP classifiers, semantic embedding representations, and duplicate detection pipelines within the platform.

### 1.1 The One-Record-Per-Achievement Rule
Each entry in the dataset represents exactly **one instance of an achievement claim**.
- If a student builds an application during a hackathon, and subsequently commercializes it as a long-term startup, the initial 48-hour event placement is recorded under `HACKATHON`, while substantive follow-on software engineering may be captured as a distinct `PROJECT` only if independently verified by new deliverables.
- Multiple awards from the exact same event must not be duplicated into multiple redundant records unless they represent materially distinct problem-statement submissions.

---

## 2. Taxonomy Boundary & Disambiguation Rules

### 2.1 Hackathon vs. Competition
- **`HACKATHON` Rule:** Must be a bounded, time-limited build event (typically $\le 7$ calendar days, e.g. 24, 36, 48, or 60 hours) where the primary deliverable is a **demonstrable prototype or MVP** (software or hardware).
- **`COMPETITION` Rule:** Involves judged submissions scored against benchmarks, test cases, algorithmic complexity, or debate/case criteria (e.g., ACM-ICPC, Kaggle challenges, debate championships).
- *Boundary Case:* An algorithmic coding sprint with automated unit tests is labeled `COMPETITION`, even if marketed as a "hack". Conversely, a 36-hour "Data Hackathon" where participants pitch a working dashboard to judges is labeled `HACKATHON`.

### 2.2 Project vs. Research Publication
- **`RESEARCH_PUBLICATION` Rule:** Requires formal acceptance, publication, or archival indexing in a peer-reviewed venue (journal, conference proceedings, or verified archival preprint repository like arXiv).
- **`PROJECT` Rule:** Classifies the artifact itself (software system, robotics hardware, capstone design, open-source library). An unsubmitted or rejected research prototype remains a `PROJECT`.
- *Boundary Case:* A student writing an undergraduate honors thesis that is later accepted at IEEE Access: the thesis report deliverable is a `PROJECT`, while the peer-reviewed conference/journal paper is `RESEARCH_PUBLICATION`.

### 2.3 Conference vs. Research Publication
- **`CONFERENCE` Rule:** Classifies event attendance, oral presentations without published proceedings, poster displays in non-archival student tracks, panel participation, or student volunteer coordination.
- **`RESEARCH_PUBLICATION` Rule:** Applies when the record specifically claims the peer-reviewed archival paper accepted into the conference proceedings.

### 2.4 Internship vs. Certification
- **`INTERNSHIP` Rule:** A time-bounded professional work engagement involving real-world production deliverables, software maintenance, or organizational responsibilities at a company, lab, or institution.
- **`CERTIFICATION` Rule:** A proctored, credentialed examination or curriculum validation issued by an authorized cloud provider or professional institute (e.g. AWS, GCP, Cisco, CKA).
- *Boundary Case:* An internship completion certificate is labeled `INTERNSHIP`, not `CERTIFICATION`. A Coursera specialization certificate completed during an internship remains `CERTIFICATION`.

### 2.5 Patent Status Rules
- **`PATENT` Rule:** Pertains strictly to formal intellectual property filings with recognized national/international patent offices (e.g. IPO, USPTO, EPO, WIPO).
- *Status Distinction:* Ensure that a *patent application filed* or *provisional specification* is tagged with `outcome: FILED`, whereas an issued patent carries `outcome: GRANTED`.

---

## 3. Controlled Vocabulary Guidelines

### 3.1 Achievement Level (`level`)
Annotators must use the following standard levels:
- `COLLEGE`: Intramural or intra-departmental activities within the student's college.
- `UNIVERSITY`: Campus-wide or inter-departmental university competitions.
- `LOCAL`: City or municipal community activities.
- `DISTRICT`: Inter-collegiate district-level activities.
- `STATE`: State-wide championships or inter-university meets.
- `NATIONAL`: Country-wide events (e.g. Smart India Hackathon, ACM-ICPC Regionals).
- `INTERNATIONAL`: Global challenges, IEEE international conferences, or worldwide olympiads.
- `ORGANIZATIONAL`: Corporate-internal or society-specific events.
- `PROFESSIONAL`: Standard industry certifications or company internships.
- `UNKNOWN`: Insufficient evidence to establish level.

### 3.2 Achievement Outcome (`outcome`)
- `WINNER` / `FIRST_PLACE`: Ranked 1st overall.
- `SECOND_PLACE`: Runner-up or 2nd place.
- `THIRD_PLACE`: 2nd runner-up or bronze placement.
- `FINALIST`: Advanced to final round without a top-3 podium finish.
- `PARTICIPATION`: Verified attendance or standard participation.
- `COMPLETION`: Completed a course, internship, or project milestone.
- `PRESENTED`: Oral, poster, or demo presentation.
- `PUBLISHED`: Archival peer-reviewed paper or book chapter.
- `GRANTED`: Formally issued patent.
- `FILED`: Published or provisional patent application.
- `LEADERSHIP`: Tenure in an officer or coordinator capacity.
- `RECOGNITION`: Honorable mention, special jury award, or dean's list.

---

## 4. Difficult Examples & Edge Cases

| Example Achievement Description | Correct Category | Disambiguation Rationale |
|---|---|---|
| *"Built an end-to-end solar tracking inverter prototype during the 48-hour CleanTech Sprint and won 2nd place."* | `HACKATHON` | Time-boxed sprint ($\le 7$ days) producing a demonstrable prototype, despite the engineering artifact. |
| *"Submitted an optimized gradient boosting pipeline to Kaggle Healthcare Challenge, finishing 4th out of 600 teams."* | `COMPETITION` | Algorithmic benchmark challenge scored against held-out private test set. |
| *"Undergraduate capstone project on transformer-based low-resource Indic OCR, code open-sourced on GitHub."* | `PROJECT` | Focus is on the completed software artifact and codebase; not submitted to a peer-reviewed venue. |
| *"Accepted and presented our Indic OCR study as a 6-page paper at ACL Findings 2024."* | `RESEARCH_PUBLICATION` | Formal peer-reviewed archival publication. |
| *"Delivered an invited demo of our Indic OCR tool at the IEEE Student Tech Summit without an archival paper."* | `CONFERENCE` | Conference presentation/demo without an archival publication entry. |
| *"Completed 12-week software engineering internship at Siemens and earned AWS Solutions Architect certification."* | Split or `INTERNSHIP` | If single record focuses on work term, label `INTERNSHIP`. Certification should ideally be a separate `CERTIFICATION` record. |
| *"Awarded University Gold Medal at annual convocation for securing Rank 1 across all semesters of B.Tech."* | `OTHER` | Legitimate academic scholastic recognition not fitting the first 13 event/artifact categories. |
| *"Volunteered 60 hours teaching basic programming to rural students at an NGO weekend camp."* | `VOLUNTEERING` | Unpaid civic community service without career-track employment deliverable. |

---
*Guide archived under `data/annotations/achievement_annotation_guide.md`.*
