# Controlled AI-Assisted Domain Annotation Pilot Protocol (Step 23)

**Project:** AI-Powered Student Achievement Intelligence Platform  
**Subsystem:** NLP & Semantic Intelligence (Member 1)  
**Target Queue:** `data/annotations/ai_assisted/pilot/domain_categorization_pilot_queue.csv`  
**Manifest:** `data/annotations/ai_assisted/pilot/domain_categorization_pilot_manifest.json`  
**Protocol Version:** 1.0.0  
**Effective Date:** 2026-10-28  

---

## 1. Pilot Context & Purpose

Following the formal Step 22 evaluation of the 30-record blind validation sample (which demonstrated an active-class Macro F1 of 67.87% and a Hamming Loss of 9.33%), the project governance ruled that **AI proposals must not be autonomously accepted into gold ground truth**, but are sufficiently reliable to serve as **reviewer assistance suggestions**.

This pilot evaluates a controlled sample of **25 held-out records** drawn from the 138 remaining pending records to measure:
1. Reviewer agreement and modification patterns with AI suggestions.
2. Review velocity (measured in seconds per record).
3. The operational feasibility of assisted review prior to rolling out the remaining 113 records.

---

## 2. Reviewer Instructions & Decision Taxonomy

Reviewers must inspect each row in `domain_categorization_pilot_queue.csv` using the columns:
- `achievement_id`: Unique identifier (e.g. `ACH000019`).
- `achievement_text`: Verbatim student claim (the sole authoritative evidence source).
- `primary_category`: High-level form (e.g. `HACKATHON`, `INTERNSHIP`).
- `ai_proposed_tags`: The suggestion produced by the rule-based AI annotator.
- `ai_evidence_snippets`: Verbatim keywords extracted by the AI engine.
- `ai_uncertainty_flag`: `TRUE` if the AI engine flagged low confidence or ambiguous triggers.

### The Four Reviewer Decision Codes

For each row, the reviewer must assign exactly one decision code in `reviewer_decision`:

| Decision Code | When to Use | Action Required in `reviewer_final_tags` |
|:---:|---|---|
| **`ACCEPT`** | The AI-proposed tags are completely accurate, comprehensive, and adhere strictly to the annotation guide. | Copy `ai_proposed_tags` into `reviewer_final_tags`. |
| **`MODIFY`** | The AI-proposed tags are partially correct, but either missed a substantive domain or included an unsupported tag. | Enter the corrected list of canonical tags in `reviewer_final_tags` (e.g. `lbl_domain_systems\|lbl_domain_data`). |
| **`REJECT`** | The AI-proposed tags are fundamentally incorrect (e.g. assigned technical tags to a non-technical claim, or completely wrong domain). | Enter the entirely corrected tag list, or `NONE` if zero technical domains apply. |
| **`UNRESOLVED`** | The verbatim text is contradictory, vague, or lacks sufficient evidence to reach a defensible decision. | Leave `reviewer_final_tags` blank and provide an explanation in `reviewer_rationale`. |

---

## 3. Taxonomy Rules & Critical Boundaries

Reviewers must strictly adhere to the [Domain Categorization Annotation Guide](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/domain_categorization_annotation_guide.md):

### 3.1 The Canonical 10 Tags
- `lbl_domain_ai`: Artificial Intelligence (high-level AI, heuristics, agents, search).
- `lbl_domain_ml`: Machine Learning (empirical model training, statistical learning, PyTorch/TensorFlow).
- `lbl_domain_nlp`: Natural Language Processing (computational linguistics, NER, transformers).
- `lbl_domain_cv`: Computer Vision (image/video processing, object detection, OpenCV).
- `lbl_domain_security`: Cybersecurity & Privacy (cryptography, CTFs, IAM, network security).
- `lbl_domain_systems`: Systems, Cloud & Architecture (operating systems, distributed systems, backend modules, Docker, AWS).
- `lbl_domain_web`: Web Development & APIs (REST APIs, full-stack, React, Node.js, FastAPI).
- `lbl_domain_data`: Data Engineering & Analytics (ETL, databases, Kafka, SQL, Spark).
- `lbl_domain_hardware`: Hardware & IoT (microcontrollers, FPGA, embedded C, PCB design).
- `lbl_domain_other`: Non-Computing Domain (debate/MUN, sports, music, arts, business).

### 3.2 Critical Boundary Rules
1. **`NONE` vs. `lbl_domain_other`:**
   - Use **`NONE`** for generic academic administration claims with no technical computing or non-computing domain (e.g. general scholarships, attendance).
   - Use **`lbl_domain_other`** for substantive non-computing activities (athletics, debate tournaments, cultural competitions).
2. **Mutual Exclusion Rule (§2.10):**
   - `lbl_domain_other` must **never** be co-assigned with any of the 9 technical computing tags. If a technical tag is present, `lbl_domain_other` is strictly suppressed.
3. **Delimiter Syntax:**
   - When entering multiple tags in `reviewer_final_tags`, separate them with a single literal pipe `|` with no spaces (e.g. `lbl_domain_systems|lbl_domain_data`). Never use escaped `\|` or trailing pipes.

---

## 4. Review Velocity Tracking

To empirically evaluate productivity gains over manual blind tagging:
1. Reviewers are instructed to measure active review time per record in seconds and enter it in `review_time_seconds`.
2. Do not include external interruption time; record the net cognitive evaluation duration.
3. If timing cannot be tracked accurately for an individual row, leave the cell blank rather than guessing.

---

## 5. Pilot Evaluation Metrics (Post-Review Plan)

Upon completion of the 25 reviews, the following quantitative metrics will be calculated:
1. **Proposal Acceptance Rate:** $\frac{\sum \mathbb{I}(\text{decision} == \text{'ACCEPT'})}{25} \times 100\%$
2. **Proposal Modification Rate:** $\frac{\sum \mathbb{I}(\text{decision} == \text{'MODIFY'})}{25} \times 100\%$
3. **Proposal Rejection Rate:** $\frac{\sum \mathbb{I}(\text{decision} == \text{'REJECT'})}{25} \times 100\%$
4. **Unresolved Rate:** $\frac{\sum \mathbb{I}(\text{decision} == \text{'UNRESOLVED'})}{25} \times 100\%$
5. **Per-Tag Discrepancy Breakdown:** Frequency of additions (false negatives of AI) and deletions (false positives of AI) per domain tag.
6. **Average Time per Record:** Mean and median seconds recorded in `review_time_seconds` compared against the unassisted baseline (historical average: ~75–90 seconds per record).
