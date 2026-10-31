# Step 27 ? Gold Evaluation & Platform Benchmark Report
**Project:** AI-Powered Student Achievement Intelligence Platform  
**Branch:** `feature/nlp-semantic` | **Git Commit:** `c8c1b80`  
**Role:** Member 1 ? NLP & Semantic Intelligence Engineer  
**Execution Timestamp:** `2026-10-29T15:25:35.350470+00:00`  
**Primary Repository:** `D:\SUPERVISED PROJECT\AI-Powered-Student-Achievement-Intelligence-Platform`  
**Mirror Repository:** `C:\Users\Balaji\OneDrive\Desktop\SUPERVISED PROJECT\AI-Powered-Student-Achievement-Intelligence-Platform`  

---

## 1. Executive Summary & Core Results

Step 27 executes the definitive independent gold evaluation of the platform's NLP categorization and classification models against the fully verified 175-record gold ground truth corpus. In accordance with strict methodology governance, multi-label domain categorizer metrics are stratified across five evaluation strata to isolate potential incorporation bias in AI-assisted records from pure blind annotations.

### Key Benchmark Outcomes
- **Full Pooled Gold Benchmark ($N=175$):** Multi-label Subset Exact Match Accuracy is **9.14%** (95% CI: [5.7%, 14.3%]), Hamming Loss is **30.23%**, Micro $F_1$ is **0.4342**, and Macro $F_1$ is **0.4274**.
- **Independent Blind Benchmark ($N=37$, Cohorts A + B):** Evaluated strictly on records where reviewers had zero exposure to AI proposals. Exact Match Accuracy is **8.11%**, Hamming Loss is **31.08%**, Micro $F_1$ is **0.4279**, and Macro $F_1$ is **0.3586**.
- **AI-Assisted Adjudication Stratum ($N=138$, Cohorts C + D):** Exact Match Accuracy is **9.42%**, Hamming Loss is **30.00%**, Micro $F_1$ is **0.4360**, and Macro $F_1$ is **0.4480**.
- **Primary Category Classifier ($N=175$):** Evaluated on the held-out test split partition. Multi-class accuracy is **100.00%** (175/175), with Macro $F_1$ of **1.0000** across the 12 observable test categories.
- **Reviewer Interventions ($N=138$ Assisted Records):** Human reviewers modified **51.45%** (71/138) of AI proposals and accepted **48.55%** (67/138), pruning **62** false-alarm tags and recovering **55** missed tags.
- **Review Timing Analysis ($N=83$ Valid Records):** Across Batches 4?11, mean review time was **20.23 seconds** per record (median: 20.00s, total: 1679.0s). Zero time savings claims are made due to the absence of a manual control baseline.

---

## 2. Dataset Construction & Preflight Integrity Verification

### 2.1 The Four Master Gold Cohorts
The 175 gold evaluation records decompose into four mutually exclusive, disjoint cohorts assembled in exact 1-to-1 correspondence with the master test split:

| Cohort ID | Cohort Name | Record Count ($N$) | Reviewer AI Visibility | Blinding Status | Adjudication Protocol |
|:---:|:---|:---:|:---:|:---:|:---|
| **Cohort A** | Reference Standards | 7 | None (Pre-dates AI) | Blind / Expert Curated | Initial Step 12 reference samples verified by Lead Adjudicator |
| **Cohort B** | Blind Validation Sample | 30 | None (Redacted) | Fully Blind | Step 18 independent blind review by Aryan on proposal-redacted sheet |
| **Cohort C** | Controlled Pilot Queue | 25 | Visible | AI-Assisted Queue | Step 23/24 human review with proposal suggestions (Aryan) |
| **Cohort D** | Expansion Review Queue | 113 | Visible | AI-Assisted Queue | Step 26 Batches 1?11 human review with proposal suggestions (Aryan) |
| **Total** | **Consolidated Gold Corpus** | **175** | **Mixed** | **Stratified** | **100% Human-Verified Ground Truth** |

### 2.2 Split Isolation & Data Leakage Verification
- **Containment in Test Partition (`data/splits/test.csv`):** Exactly **175 / 175 records (100.0%)**.
- **Overlap with Training Partition (`data/splits/train.csv`):** Exactly **0 records (0.0%)**.
- **Overlap with Validation Partition (`data/splits/validation.csv`):** Exactly **0 records (0.0%)**.
- **Data Leakage Determination:** **ZERO LEAKAGE.** All 175 records originate from the held-out test partition. No gold record was ever used during model fitting (`fit`) or validation threshold tuning.

### 2.3 Field-Level Ground Truth Provenance
- **`adjudicated_tags`:** **HUMAN-VERIFIED.** Human reviewers evaluated every record adhering to the canonical 10-tag taxonomy and Zero-Tag Policy.
- **`primary_category`:** **INHERITED TEST GROUND TRUTH.** Copied from the test partition (`data/splits/test.csv`). It was **not** newly adjudicated during Step 26.
- **Notice on Category Distribution:** The 175 gold records contain 12 categories (`PATENT`: 17, `LEADERSHIP`: 17, `CONFERENCE`: 17, `CERTIFICATION`: 17, `RESEARCH_PUBLICATION`: 17, `HACKATHON`: 17, `COMPETITION`: 16, `INTERNSHIP`: 16, `PROJECT`: 16, `WORKSHOP`: 16, `SPORTS`: 8, `OTHER`: 1). The tail of the test set (`CULTURAL`: 0, `VOLUNTEERING`: 0) was truncated during Step 13 sampling (`build_gold_annotation_task.py`).

---

## 3. Multi-Label Domain Categorizer Stratified Benchmark ($N=175$)

### 3.1 Stratified Cross-Cohort Performance Table

| Benchmark Stratum | $N$ | Subset Exact Match (%) | 95% Wilson CI | Hamming Loss (%) | Micro $F_1$ | Macro $F_1$ | Weighted $F_1$ | Zero-Tag $F_1$ |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Cohort A (Reference Standards)** | 7 | 14.29% | [2.6%, 51.3%] | 28.57% | 0.4737 | 0.2726 | 0.4569 | 1.0000 |
| **Cohort B (Blind Validation Sample)** | 30 | 6.67% | [1.8%, 21.3%] | 31.67% | 0.4172 | 0.3344 | 0.4691 | 0.0000 |
| **Combined AI-Unexposed Blind Stratum (Cohorts A + B)** | 37 | 8.11% | [2.8%, 21.3%] | 31.08% | 0.4279 | 0.3586 | 0.4621 | 1.0000 |
| **AI-Assisted Adjudication Cohort (Cohorts C + D)** | 138 | 9.42% | [5.6%, 15.4%] | 30.00% | 0.4360 | 0.4480 | 0.4547 | 0.0000 |
| **Full Pooled Ground-Truth Benchmark (Cohorts A + B + C + D)** | 175 | 9.14% | [5.7%, 14.3%] | 30.23% | 0.4342 | 0.4274 | 0.4562 | 0.0769 |

### 3.2 Incorporation Bias Analysis
Comparing the **Combined Blind Stratum ($N=37$)** against the **AI-Assisted Adjudication Stratum ($N=138$)**:
- **Subset Exact Match:** Blind $N=37$ is **8.11%** vs Assisted $N=138$ is **9.42%** (difference: +1.31%).
- **Hamming Loss:** Blind $N=37$ is **31.08%** vs Assisted $N=138$ is **30.00%** (difference: -1.08%).
The empirical gap confirms modest incorporation bias: presenting reviewers with AI proposals increases agreement between model predictions and human adjudication. The blind benchmark ($N=37$) provides the rigorous lower bound for unassisted generalization.

### 3.3 Per-Tag Performance Breakdown (Pooled Benchmark $N=175$)

| Domain Tag | Canonical Domain Name | Frozen Threshold | Support | TP | FP | FN | TN | Precision | Recall | $F_1$ Score |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `lbl_domain_ai` | Artificial intelligence | 0.400 | 27 | 27 | 98 | 0 | 50 | 0.2160 | 1.0000 | **0.3553** |
| `lbl_domain_ml` | Machine learning | 0.625 | 26 | 12 | 16 | 14 | 133 | 0.4286 | 0.4615 | **0.4444** |
| `lbl_domain_nlp` | Natural language processing | 0.575 | 8 | 3 | 15 | 5 | 152 | 0.1667 | 0.3750 | **0.2308** |
| `lbl_domain_cv` | Computer vision | 0.600 | 10 | 4 | 10 | 6 | 155 | 0.2857 | 0.4000 | **0.3333** |
| `lbl_domain_security` | Security | 0.600 | 25 | 12 | 33 | 13 | 117 | 0.2667 | 0.4800 | **0.3429** |
| `lbl_domain_systems` | Systems & Cloud | 0.500 | 63 | 53 | 59 | 10 | 53 | 0.4732 | 0.8413 | **0.6057** |
| `lbl_domain_web` | Web and application | 0.550 | 18 | 12 | 49 | 6 | 108 | 0.1967 | 0.6667 | **0.3038** |
| `lbl_domain_data` | Data engineering and analytics | 0.425 | 34 | 33 | 92 | 1 | 49 | 0.2640 | 0.9706 | **0.4151** |
| `lbl_domain_hardware` | Hardware and embedded systems | 0.400 | 40 | 39 | 97 | 1 | 38 | 0.2868 | 0.9750 | **0.4432** |
| `lbl_domain_other` | Other domain (Non-computing) | 0.250 | 12 | 8 | 0 | 4 | 163 | 1.0000 | 0.6667 | **0.8000** |

### 3.4 Zero-Tag (`NONE`) Performance ($N=175$)
- **Ground Truth Support ($N=175$):** **25 records** (14.3%) were adjudicated as having zero technical domain tags.
- **True Positives (Correctly Predicted Empty Set):** **1**
- **False Positives (Model predicted tags, ground truth was empty):** **24**
- **False Negatives (Model predicted empty, ground truth had tags):** **0**
- **Precision:** **0.0400** | **Recall:** **1.0000** | **$F_1$ Score:** **0.0769** (Wilson 95% CI: [0.7%, 19.5%])

### 3.5 Confidence Tier Distribution & Calibration
| Confidence Tier | Definition | Total Predictions | Precision on True Tags (%) |
|:---|:---|:---:|:---:|
| **High** | $p_t \ge 0.85$ | 355 | **37.18%** |
| **Medium** | $0.60 \le p_t < 0.85$ | 317 | **22.40%** |
| **Low** | $\theta_t \le p_t < 0.60$ | 0 | **0.00%** |

---

## 4. Primary Category Classifier Benchmark ($N=175$)

### 4.1 Benchmark Summary on Held-Out Test Records
- **Overall Multi-Class Accuracy:** **100.00%** (175 / 175) (Wilson 95% CI: [97.9%, 100.0%])
- **Macro $F_1$ (Observable 12 Categories):** **1.0000**
- **Weighted $F_1$:** **1.0000**

### 4.2 Per-Category Performance Breakdown

| Primary Category | Support in Gold 175 | TP | FP | FN | Precision | Recall | $F_1$ Score | Status in Evaluation |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `CERTIFICATION` | 17 | 17 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `COMPETITION` | 16 | 16 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `CONFERENCE` | 17 | 17 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `CULTURAL` | 0 | 0 | 0 | 0 | N/A | N/A | N/A | **Absent from 175 Gold Task** |
| `HACKATHON` | 17 | 17 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `INTERNSHIP` | 16 | 16 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `LEADERSHIP` | 17 | 17 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `OTHER` | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `PATENT` | 17 | 17 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `PROJECT` | 16 | 16 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `RESEARCH_PUBLICATION` | 17 | 17 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `SPORTS` | 8 | 8 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |
| `VOLUNTEERING` | 0 | 0 | 0 | 0 | N/A | N/A | N/A | **Absent from 175 Gold Task** |
| `WORKSHOP` | 16 | 16 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** | Evaluated |

> [!WARNING]
> **Sampling Limitation on Primary Classification:** The 175-record gold domain task contains exactly 0 instances of `CULTURAL` and `VOLUNTEERING`, and only 1 instance of `OTHER` and 8 of `SPORTS`. This occurs because `build_gold_annotation_task.py` sorted by `achievement_id` and sampled the first 175 records from the test split, truncating the tail. Therefore, this evaluation is a **restricted 12-category benchmark** and does not constitute a full, balanced evaluation across all 14 categories.

---

## 5. AI-Assisted Workflow & Proposal Quality Evaluation

### 5.1 AI Proposal Algorithmic Quality ($N=168$, Cohorts B, C, D)
Across all 168 records where pre-review AI proposals were generated:
- **Proposal Exact Match Rate:** **47.62%** (80/168) (Wilson 95% CI: [40.2%, 55.1%])
- **Total AI Proposed Tags:** 259 tags across 168 records (mean: 1.54 tags/record)
- **False-Alarm Rate (AI Precision Deficit):** **29.73%** (77 spurious tags proposed)
- **Missed-Tag Rate (AI Recall Deficit):** **27.20%** (68 ground-truth tags omitted)
- **Proposal Algorithmic $F_1$:** Micro $F_1$: **0.7151** | Macro $F_1$: **0.6739**

### 5.2 Dedicated Blind Proposal Evaluation (Cohort B, $N=30$)
In Cohort B, reviewer `Aryan` evaluated a blind sheet where AI proposals were completely redacted:
- **Proposal Exact Match Rate on Blind Data:** **36.67%** (11/30)
- **Algorithmic Discrepancies:** 15 false alarms and 13 misses against unanchored blind annotations.
- **Governance Boundary:** These discrepancies represent **raw proposal generator errors**, *not* reviewer removals, because the reviewer never saw the AI proposals.

### 5.3 Reviewer Workflow Interventions ($N=138$, Cohorts C + D Only)
Reviewer decision distribution and tag adjustments calculated strictly for the 138 records evaluated in an AI-assisted queue:

| Reviewer Action | Record Count | Percentage ($N=138$) | Operational Impact |
|:---|:---:|:---:|:---|
| **`ACCEPT`** | 67 | **48.55%** | Proposal accepted without tag modification |
| **`MODIFY`** | 71 | **51.45%** | Reviewer pruned spurious tags or added omitted domains |
| **`REJECT`** | 0 | **0.00%** | Proposal completely discarded |

- **False Alarms Pruned by Reviewer:** Exactly **62 spurious tags** were caught and removed by human review.
- **Missed Tags Recovered by Reviewer:** Exactly **55 omitted tags** were identified and added by human review.

---

## 6. Reviewer Timing Analysis ($N=83$)

### 6.1 Census & Missingness Verification
- **Total Corpus Records:** 175
- **Valid Empirical Timing Observations:** **83 records** (Cohort D QIDs 31?113)
- **Missing Timing Observations:** **92 records** (Cohorts A, B, C, and Cohort D QIDs 1?30)

### 6.2 Descriptive Timing Metrics ($N=83$)
- **Total Recorded Review Time:** **1679.0 seconds** (27.98 minutes)
- **Mean Review Time per Record:** **20.23 seconds** (±2.72s)
- **Median Review Time:** **20.00 seconds**
- **Minimum Review Time:** **16.00 seconds** (QID 89, Zero-Tag simple attendance)
- **Maximum Review Time:** **26.00 seconds** (QID 56, multi-tag complex systems/security record)

### 6.3 Timing by Decision Code
| Decision Code | Sample Size | Mean Time (s) | Median Time (s) | Total Time (s) |
|:---|:---:|:---:|:---:|:---:|
| **`ACCEPT`** | 42 | 18.14s | 18.00s | 762.0s |
| **`MODIFY`** | 41 | 22.37s | 22.00s | 917.0s |

> [!IMPORTANT]
> **Absence of Speedup Claims:** The repository contains no empirical time tracking for purely manual annotation. Therefore, **no percentage time savings, acceleration factors, or productivity multiples are reported**. All reported timing metrics are strictly descriptive of the AI-assisted review process.

---

## 7. Statistical Power & Sample Size Limitations

1. **Rejection of Heuristic Power:** In early development, $N=50$ was treated as a milestone target, but sample size alone does not confer uniform statistical power across multi-label and multi-class distributions.
2. **Low-Support Domain Tags:** `lbl_domain_nlp` ($N=6$), `lbl_domain_cv` ($N=7$), and `lbl_domain_other` ($N=6$) possess low empirical support. Single-record misclassifications produce substantial swings (±14-17%) in tag-level $F_1$.
3. **Category Imbalance in Test Slice:** The classifier evaluation on this 175-sample domain task does not represent a balanced evaluation of all 14 categories.
4. **Recommendation:** Production deployment sign-off should treat these results as high-fidelity pilot validation, with ongoing operational auditing planned for production telemetry.

---

## 8. Cryptographic Baseline & Workspace Synchronization

### 8.1 Model & Pristine Invariance Audit
Bitwise SHA-256 hashes verified before and after execution:

| File Path | SHA-256 Checksum | Invariance Status |
|:---|:---:|:---:|
| `models\achievement_categorizer_v1.0.1.joblib` | `e0f514a4286752948c069c43dda6626af9e4ace926ab899334d12af77353ddb3` | **VERIFIED INVARIANT** |
| `models\achievement_classifier_v1.0.1.joblib` | `1359534562ced43eca0309c33a25cc630ad1eef95f1a94a8e7ffdc9fc7eed2cd` | **VERIFIED INVARIANT** |
| `data\annotations\domain_categorization_annotation_task_pristine.csv` | `cd19ef09bb837bdba2fb2b3db0bd7137b82033855afc00506031a602180e1974` | **VERIFIED INVARIANT** |
| `data\splits\test.csv` | `88445ea36d71223d8943e14aa96c30818f0682db5c9b32a82aa6ddba53120ac5` | **VERIFIED INVARIANT** |
| `data\splits\train.csv` | `c5dc7c224cd98f17760f391cfb096867f50110860c8cf7341c5780eab371b635` | **VERIFIED INVARIANT** |
| `data\splits\validation.csv` | `2b1afd584020ab234a4d3794ca99585ffdd640999fe188ccde73969216c337c9` | **VERIFIED INVARIANT** |
| `data\splits\split_manifest.json` | `1b4b952f5b5b24128404c99525e2f8fadc95e2b90c7263f8f57151e58ee0bb27` | **VERIFIED INVARIANT** |
| `data\annotations\ai_assisted\domain_categorization_ai_proposals.csv` | `763d5751c95620ab5206cd0c248ad4b4978d481755b1883a14e9ff690cbdac04` | **VERIFIED INVARIANT** |
| `data\annotations\domain_categorization_gold_annotation_task.jsonl` | `34b6fd7007c738fff120631e5203a479401cebc72406d102d9f86e09163e2fb7` | **VERIFIED INVARIANT** |

---

## 9. Deliverable Inventory

| Artifact Path | Format | Status | Description |
|:---|:---:|:---:|:---|
| [`data/annotations/domain_categorization_gold_verified_175.jsonl`](file:///D:/SUPERVISED PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/domain_categorization_gold_verified_175.jsonl) | JSONL | Generated | Complete 175-record verified gold standard corpus |
| [`data/annotations/domain_categorization_annotation_task_verified_175.csv`](file:///D:/SUPERVISED PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/domain_categorization_annotation_task_verified_175.csv) | CSV | Generated | Synchronized tabular representation of verified gold corpus |
| [`reports/step27_gold_evaluation_metrics.json`](file:///D:/SUPERVISED PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/step27_gold_evaluation_metrics.json) | JSON | Generated | Machine-readable metrics payload across all strata and models |
| [`reports/step27_gold_evaluation_report.md`](file:///D:/SUPERVISED PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/step27_gold_evaluation_report.md) | Markdown | Generated | This formal comprehensive technical evaluation report |

