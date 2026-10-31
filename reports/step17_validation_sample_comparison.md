# Step 17 — Stratified Validation Sample Comparison & Evaluation Framework

**Project:** AI-Powered Student Achievement Intelligence Platform  
**Subsystem:** NLP & Semantic Intelligence (Member 1)  
**Branch:** `feature/nlp-semantic`  
**Target Sample Size:** 30 records (Stratified across 11 Primary Categories)  
**Random Seed:** 42 (Reproducible)  
**Blind CSV:** [`data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv)  
**Key JSONL:** [`data/annotations/ai_assisted/domain_categorization_validation_sample_key.jsonl`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/ai_assisted/domain_categorization_validation_sample_key.jsonl)  

---

## 1. Executive Summary & Protocol Design

This document establishes the independent evaluation and comparison framework for validating AI-proposed domain categorizations against human ground truth. To eliminate cognitive anchor bias, human annotators must complete the validation sample using the **strictly blind spreadsheet** where all AI predictions, rationales, and model hints have been completely omitted.

### Key Protocols Enforced
1. **Complete Blindness:** The human annotator receives only `achievement_id`, `achievement_text`, `primary_category`, and `split`. The fields `validator_name`, `validator_tags`, `validator_notes`, `validator_uncertain`, and `validator_status` are blank.
2. **Zero-Tag Protocol:** For non-technical or administrative records, human annotators enter `"NONE"`, which translates to an empty tag set (`[]`). AI proposals record empty tag sets as `[]` in JSONL and `"[]"` in CSV.
3. **Mutual Exclusion:** `lbl_domain_other` must never be co-assigned with any technical computing tag.
4. **Stratification Across 11 Categories:**
   - 3 samples each: `CERTIFICATION`, `COMPETITION`, `CONFERENCE`, `HACKATHON`, `INTERNSHIP`, `LEADERSHIP`, `PROJECT`, `RESEARCH_PUBLICATION`, `WORKSHOP` (27 records)
   - 2 samples: `PATENT`
   - 1 sample: `SPORTS`
   - **Total:** Exactly 30 records.

---

## 2. Evaluation Metrics Definition

Once human annotations are recorded in the validation CSV, the automated evaluation engine computes the following standard multi-label metrics:

| Metric | Formula / Definition | Target Threshold | Purpose |
|---|---|---|---|
| **Exact Match Ratio (Subset Accuracy)** | \(\frac{1}{N} \sum_{i=1}^N I(Y_i = \hat{Y}_i)\) | \(\ge 75\%\) | Measures percentage of records where predicted tag set matches ground truth exactly. |
| **Hamming Loss** | \(\frac{1}{N \cdot L} \sum_{i=1}^N |Y_i \Delta \hat{Y}_i|\) | \(\le 0.08\) | Measures fraction of incorrect label decisions across all record-label pairs. |
| **Macro-Averaged F1** | \(\frac{1}{L} \sum_{l=1}^L F1_l\) | \(\ge 0.80\) | Unweighted mean of tag-level F1 scores; gives equal weight to rare tags (e.g., CV, NLP). |
| **Micro-Averaged F1** | Global true positives, false positives, false negatives | \(\ge 0.85\) | Aggregate performance across all label assignments. |
| **Zero-Tag Precision / Recall** | Precision & recall on records with empty tag sets | \(\ge 90\%\) | Verifies fidelity of the Zero-Tag Policy on non-technical claims. |
| **Uncertainty Calibration** | Discrepancy rate on flagged vs unflagged records | Monotonic correlation | Verifies whether records flagged uncertain actually have higher human disagreement. |

---

## 3. Stratified 30-Record Sample Inventory & AI Baseline

Below is the baseline inventory of the 30 sampled records, showing the verbatim achievement text, the AI-proposed domain tags, extracted evidence snippets, and baseline uncertainty status. Downstream human comparisons will fill the remaining columns.

| # | Achievement ID | Category | Text Excerpt | AI Proposed Tags | Evidence Snippets | Uncertain? | Human Validated Tags | Match Status |
|---|---|---|---|---|---|---|---|---|
| 1 | `ACH000587` | CERTIFICATION | Completed verified credential program for Meta Back-End Developer... | lbl_domain_web | Back-End, RESTful | NO | *Pending Review* | *Pending* |
| 2 | `ACH000588` | CERTIFICATION | Earned industry certification Certified Kubernetes Administrator ... | lbl_domain_systems | Kubernetes | NO | *Pending Review* | *Pending* |
| 3 | `ACH000602` | CERTIFICATION | Completed verified credential program for TensorFlow Developer Ce... | lbl_domain_ai, lbl_domain_ml | model training architecture (inferred from ML), TensorFlow | NO | *Pending Review* | *Pending* |
| 4 | `ACH000125` | COMPETITION | Qualified as a National Finalist in the State-Level Algorithmic P... | lbl_domain_systems | Rust | NO | *Pending Review* | *Pending* |
| 5 | `ACH000155` | COMPETITION | Qualified as a National Finalist in the University Model United N... | lbl_domain_security | Security | NO | *Pending Review* | *Pending* |
| 6 | `ACH000162` | COMPETITION | Finished in the top 5th percentile at State Engineering Mathemati... | *[Zero-Tag]* | *None* | NO | *Pending Review* | *Pending* |
| 7 | `ACH000888` | CONFERENCE | Conferred the Best Student Poster Award at National Symposium on ... | lbl_domain_systems, lbl_domain_hardware | Systems, Embedded | NO | *Pending Review* | *Pending* |
| 8 | `ACH000926` | CONFERENCE | Presented an interactive research poster at the National Symposiu... | lbl_domain_systems, lbl_domain_hardware | Systems, Embedded | NO | *Pending Review* | *Pending* |
| 9 | `ACH000975` | CONFERENCE | Delivered an oral presentation at All-India Conference on Sustain... | lbl_domain_systems | systems | NO | *Pending Review* | *Pending* |
| 10 | `ACH000007` | HACKATHON | Awarded First Runner-Up (2nd position) at CleanTech Innovation Ja... | lbl_domain_systems, lbl_domain_data | Rust, Flink | NO | *Pending Review* | *Pending* |
| 11 | `ACH000017` | HACKATHON | Received Special Jury Recognition at the CodeGenesis Grand Finale... | lbl_domain_systems, lbl_domain_web, lbl_domain_data | fault-tolerant, system | NO | *Pending Review* | *Pending* |
| 12 | `ACH000025` | HACKATHON | Awarded First Runner-Up (2nd position) at InnovateAI Buildathon 2... | lbl_domain_systems, lbl_domain_data | System, dbt | NO | *Pending Review* | *Pending* |
| 13 | `ACH000486` | INTERNSHIP | Earned Outstanding Intern Performance Rating during my 4 months s... | lbl_domain_systems | Cloud, AWS | NO | *Pending Review* | *Pending* |
| 14 | `ACH000513` | INTERNSHIP | Successfully concluded a 4 months research-oriented internship at... | lbl_domain_systems | system | NO | *Pending Review* | *Pending* |
| 15 | `ACH000537` | INTERNSHIP | Served as Firmware Engineering Intern at NVIDIA AI Technology Cen... | lbl_domain_systems, lbl_domain_web, lbl_domain_hardware | fault-tolerant, backend | NO | *Pending Review* | *Pending* |
| 16 | `ACH001038` | LEADERSHIP | Elected as Chief Coordinator of University Innovation and Entrepr... | *[Zero-Tag]* | *None* | NO | *Pending Review* | *Pending* |
| 17 | `ACH001041` | LEADERSHIP | Held the post of Lead Organizer in Annual National Collegiate Tec... | *[Zero-Tag]* | *None* | NO | *Pending Review* | *Pending* |
| 18 | `ACH001060` | LEADERSHIP | Spearheaded operations as President for ACM Student Chapter acros... | *[Zero-Tag]* | *None* | NO | *Pending Review* | *Pending* |
| 19 | `ACH000344` | PATENT | Patent application published by European Patent Office (EPO) (App... | lbl_domain_hardware | Circuit, Sensor | NO | *Pending Review* | *Pending* |
| 20 | `ACH000438` | PATENT | Co-inventor on patent application #2024499941 filed with the Indi... | lbl_domain_systems, lbl_domain_data, lbl_domain_hardware | Fault-Tolerant, Apache Spark | NO | *Pending Review* | *Pending* |
| 21 | `ACH000684` | PROJECT | Fabricated an autonomous agricultural drone survey platform for o... | lbl_domain_ai, lbl_domain_ml | model training architecture (inferred from ML), scikit-learn | NO | *Pending Review* | *Pending* |
| 22 | `ACH000686` | PROJECT | Awarded Best Departmental Capstone Project for developing an auto... | lbl_domain_cv, lbl_domain_systems | OpenCV, Azure | NO | *Pending Review* | *Pending* |
| 23 | `ACH000687` | PROJECT | Developed and open-sourced an dual-axis solar tracking inverter w... | lbl_domain_ai, lbl_domain_hardware | Reinforcement Learning, IoT | YES | *Pending Review* | *Pending* |
| 24 | `ACH000237` | RESEARCH_PUBLICATION | Co-authored research paper in IEEE Internet of Things Journal foc... | lbl_domain_ai, lbl_domain_ml, lbl_domain_cv, lbl_domain_data | model training architecture (inferred from ML), cross-validation | NO | *Pending Review* | *Pending* |
| 25 | `ACH000297` | RESEARCH_PUBLICATION | Co-authored research paper in IEEE Transactions on Artificial Int... | lbl_domain_ai, lbl_domain_ml, lbl_domain_systems | Artificial Intelligence, cross-validation | NO | *Pending Review* | *Pending* |
| 26 | `ACH000326` | RESEARCH_PUBLICATION | First author on peer-reviewed study 'Automated EEG Anomaly Detect... | lbl_domain_hardware | PCB | NO | *Pending Review* | *Pending* |
| 27 | `ACH001139` | SPORTS | Won the Gold Medal (1st place) in Chess at the District Collegiat... | lbl_domain_other | Chess | NO | *Pending Review* | *Pending* |
| 28 | `ACH000776` | WORKSHOP | Awarded Certificate of Completion for the 'Big Data Stream Analyt... | lbl_domain_data | Analytics, Apache Kafka | YES | *Pending Review* | *Pending* |
| 29 | `ACH000863` | WORKSHOP | Participated in the week-long advanced training program on 'FPGA ... | lbl_domain_systems, lbl_domain_hardware | system, Systems | NO | *Pending Review* | *Pending* |
| 30 | `ACH000866` | WORKSHOP | Completed the intensive week-long technical workshop on 'Embedded... | lbl_domain_hardware | Embedded, Firmware | NO | *Pending Review* | *Pending* |

---

## 4. Analysis of AI Baseline on the 30-Record Sample

- **Total Sample Size:** 30 records
- **Zero-Tag Proposals in Sample:** 4 (13.3%)
- **Uncertain Proposals in Sample:** 2 (6.7%)
- **Tag Frequency in Sample:**
  - `lbl_domain_systems`: 15 occurrences
  - `lbl_domain_hardware`: 9 occurrences
  - `lbl_domain_data`: 6 occurrences
  - `lbl_domain_ai`: 5 occurrences
  - `lbl_domain_ml`: 4 occurrences
  - `lbl_domain_web`: 3 occurrences
  - `lbl_domain_cv`: 2 occurrences
  - `lbl_domain_security`: 1 occurrences
  - `lbl_domain_other`: 1 occurrences

---

## 5. Next Steps for Completing Validation

1. **Deliver Blind CSV to Human Reviewer:**
   - Provide [`domain_categorization_validation_sample_blind.csv`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/ai_assisted/domain_categorization_validation_sample_blind.csv) to the human annotator.
   - Annotator references [`domain_categorization_annotation_guide.md`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/domain_categorization_annotation_guide.md).
2. **Ingest Completed Validation CSV:**
   - Ingest reviewed rows into the evaluation script.
   - Execute automated comparison against [`domain_categorization_validation_sample_key.jsonl`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/ai_assisted/domain_categorization_validation_sample_key.jsonl).
3. **Generate Final Agreement & Reliability Scorecard:**
   - Update this report with human labels, agreement percentage, and failure mode analysis.
   - If agreement exceeds \(85\%\) without systematic drift, proceed to Phase 2 of human adjudication on the remaining 138 records.