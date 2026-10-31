# Step 11: Independent Evaluation and Label-Quality Audit

**Project:** AI-Powered Student Achievement Intelligence Platform  
**Author:** Member 1 — NLP & Semantic Intelligence Engineer  
**Branch:** `feature/nlp-semantic`  
**Git HEAD:** `c8c1b80 feat: add SIH 2024 achievement pilot`  
**Dataset Release:** `achievement_dataset_v1.0.1` (**FROZEN**, 1,540 master records)  
**Date:** October 27, 2026  

---

## 1. Executive Summary & Objective

This report provides a rigorous, evidence-based audit of the multi-label domain categorization subsystem developed in Step 10. The primary objective is to investigate whether reported model metrics measure genuine domain-tagging generalization or primarily reflect the automated pseudo-label generation heuristics, and to evaluate the model on truly held-out, human-verified data without information leakage.

### Key Audit Findings:
1. **Reviewed Reference Subset Contamination:**
   The 45-record "reviewed reference subset" ([`data/annotations/categorization_reviewed_reference_samples.jsonl`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/categorization_reviewed_reference_samples.jsonl)) is **not an independent test set**. Of the 45 samples, **32 (71.1%) were drawn from the training split** and **6 (13.3%) from the validation split**. Only **7 samples (15.6%)** originated from the held-out test split.
2. **Invalid Improvement Claim:**
   The previously reported claim that Hamming loss "improved by 30.6% on the reviewed subset (0.1333 vs 0.1922)" is **statistically and methodologically invalid**. It compared a 231-sample test split against a 45-sample mixed dataset dominated by training samples. When evaluated exclusively on genuinely held-out, human-reviewed test records ($N=7$), Hamming loss degrades to **0.2857** (48.6% worse than on the pseudo-labeled test set).
3. **Information Leakage in Heuristic Pseudo-Labels:**
   Across the 1,540 master records, significant proportions of positive labels were assigned strictly via `source_domain` metadata (e.g., 100% of `lbl_domain_other`, 27.5% of `lbl_domain_ai`, 31.0% of `lbl_domain_hardware`). Because `source_domain` is not provided to the model during inference, the classifier cannot access the information that generated the target label.
4. **Circularity & Rule Memorization:**
   Analysis of TF-IDF feature weights demonstrates that the Logistic Regression classifiers primarily memorize the exact lexical keywords used in the derivation rules (e.g., `computer vision`, `opencv`, `cybersecurity`, `spacy`), effectively acting as an approximation of the rule engine rather than learning broader semantic concepts.
5. **Over-Prediction on Held-Out Text:**
   On held-out reviewed test data, validation-tuned decision thresholds ($T_k \approx 0.40–0.425$) cause severe over-prediction, resulting in a low micro precision of **0.3600** (only 36% of predicted tags are correct) and an exact match rate of only **14.3%** (1 out of 7).

---

## 2. Preservation & Cryptographic Hash Integrity Audit

The repository working tree was inspected prior to analysis. All core datasets, splits, and models remain strictly unaltered:

| File Path | SHA-256 Checksum | File Size | Status |
| :--- | :--- | :---: | :---: |
| `data/processed/achievement_classification_dataset.csv` | `1a62b8d8b56bd94df27d8c40ff86ef892b7d50e0c6bb92ff4f69882596b27ddc` | 1,413,407 B | **VERIFIED (Frozen)** |
| `data/processed/achievement_categorization_dataset.csv` | `d1d1c4b96dbcf5a1aea92d1b0134d41aefff65643c11b1ef18cb4e7e69daa0d9` | 880,298 B | **VERIFIED** |
| `data/processed/achievement_categorization_dataset.jsonl` | `d204d8f8223c4bbbdf92a1c83e1242891246327ca5700aa524b398c7a1ab2ab5` | 1,512,818 B | **VERIFIED** |
| `data/splits/train.csv` | `c5dc7c224cd98f17760f391cfb096867f50110860c8cf7341c5780eab371b635` | 989,410 B | **VERIFIED** |
| `data/splits/validation.csv` | `2b1afd584020ab234a4d3794ca99585ffdd640999fe188ccde73969216c337c9` | 211,843 B | **VERIFIED** |
| `data/splits/test.csv` | `88445ea36d71223d8943e14aa96c30818f0682db5c9b32a82aa6ddba53120ac5` | 212,824 B | **VERIFIED** |
| `data/splits/categorization_train.csv` | `dc44f3ff304c432a6b4d0ee5cfb961e54245495a214e115fe25c8b3fbfb551b1` | 618,135 B | **VERIFIED** |
| `data/splits/categorization_validation.csv` | `25fa2e533d0bf9ee523d5170611aabf2c1e42b6511724ec069a68fd1ffb00396` | 131,933 B | **VERIFIED** |
| `data/splits/categorization_test.csv` | `7cb2c0ac1cb00f6367fbd47c88a87ddce7dfb5ee4674d2ab7790e658c8ece859` | 130,938 B | **VERIFIED** |
| `data/annotations/categorization_reviewed_reference_samples.jsonl` | `2ce86c6540b7c65c7f5f13b8869fee7fbb4dbe402b0e4758a055f71ce8ce9fcf` | 29,046 B | **VERIFIED** |
| `models/achievement_categorizer_v1.0.1.joblib` | `e0f514a4286752948c069c43dda6626af9e4ace926ab899334d12af77353ddb3` | 296,149 B | **VERIFIED** |
| `models/achievement_classifier_v1.0.1.joblib` | `1359534562ced43eca0309c33a25cc630ad1eef95f1a94a8e7ffdc9fc7eed2cd` | 443,429 B | **VERIFIED** |

*Working tree status: No modifications to frozen splits or model bundles. No commits or pushes performed.*

---

## 3. Audit of the Reviewed Reference Subset

An audit of [`data/annotations/categorization_reviewed_reference_samples.jsonl`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/data/annotations/categorization_reviewed_reference_samples.jsonl) revealed the following properties:

### 3.1 Sample Counts & ID Integrity
- **Total records:** 45
- **Unique achievement IDs:** 45 (0 duplicates)
- **Annotation Status:** All 45 records are marked `annotation_status: "VERIFIED"` with specific audit notes by Member 1.
- **Zero-Tag Inclusions:** 5 records (11.1%) are zero-tag achievements representing non-technical domains (e.g., debating, alumni fellowship, community service).

### 3.2 Split Partition Breakdown
| Partition Source | Number of Samples | Percentage of Reviewed Subset | Used in Training / Tuning? |
| :--- | :---: | :---: | :---: |
| **Train Split (`train`)** | **32** | **71.1%** | **YES — Directly trained model weights** |
| **Validation Split (`val`)** | **6** | **13.3%** | **YES — Used to select decision thresholds ($T_k$)** |
| **Held-Out Test Split (`test`)** | **7** | **15.6%** | **NO — Genuinely held-out** |
| **Total** | **45** | **100.0%** | |

> **CRITICAL AUDIT CONCLUSION:**  
> The 45-sample reviewed reference subset cannot be represented as an independent test set. 84.4% of its records (38 of 45) directly influenced model training or validation threshold selection. It serves as a **development diagnostic subset**, while only the 7 test-split records represent an independent evaluation.

### 3.3 Positive Support per Tag across Partitions
| Domain Tag | Train Reviewed ($N=32$) | Val Reviewed ($N=6$) | Test Reviewed ($N=7$) | Total Reviewed ($N=45$) |
| :--- | :---: | :---: | :---: | :---: |
| `lbl_domain_ai` | 14 | 3 | 3 | 20 |
| `lbl_domain_ml` | 9 | 1 | 1 | 11 |
| `lbl_domain_nlp` | 4 | 1 | 1 | 6 |
| `lbl_domain_cv` | 4 | 2 | **0** | 6 |
| `lbl_domain_security` | 5 | 2 | 1 | 8 |
| `lbl_domain_systems` | 11 | 4 | 3 | 18 |
| `lbl_domain_web` | 11 | 2 | 1 | 14 |
| `lbl_domain_data` | 10 | 1 | 1 | 12 |
| `lbl_domain_hardware` | 11 | 3 | 2 | 16 |
| `lbl_domain_other` | 3 | 1 | **0** | 4 |
| **Zero-Tag Records** | 2 | 1 | 2 | 5 |

Notice that in the held-out test subset ($N=7$), `lbl_domain_cv` and `lbl_domain_other` have **zero positive support**, and five tags have only **1 positive example**. This sample size is too small to compute statistically meaningful individual tag metrics.

---

## 4. Audit of Label-Generation Provenance & Leakage

In Step 10, pseudo-labels for the 1,540 master records were synthesized via [`derive_record_tags()`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/src/nlp/categorization_dataset.py#L95) using three evidence streams:
1. `source_domain`: High-level scenario domain string.
2. `skills`: Pipe-separated canonical skill annotations from the frozen dataset.
3. `text_cues`: Regular expression keyword patterns in the raw achievement text.

### 4.1 Provenance Source Distribution (1,540 Master Records)
| Domain Tag | Total Positives | `source_domain` Present | `skill` Present | `text_cue` Present | `source_domain` ONLY | % Solely from `source_domain` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `lbl_domain_hardware` | 532 | 262 | 367 | 74 | 165 | **31.0%** |
| `lbl_domain_systems` | 643 | 239 | 502 | 138 | 101 | **15.7%** |
| `lbl_domain_other` | 220 | 220 | 0 | 0 | 220 | **100.0%** |
| `lbl_domain_ai` | 637 | 365 | 437 | 57 | 175 | **27.5%** |
| `lbl_domain_nlp` | 133 | 44 | 95 | 25 | 27 | **20.3%** |
| `lbl_domain_security` | 192 | 114 | 106 | 85 | 51 | **26.6%** |
| `lbl_domain_cv` | 93 | 42 | 64 | 37 | 26 | **28.0%** |
| `lbl_domain_ml` | 265 | 57 | 223 | 38 | 30 | **11.3%** |
| `lbl_domain_web` | 350 | 58 | 303 | 51 | 22 | **6.3%** |
| `lbl_domain_data` | 560 | 59 | 544 | 19 | 16 | **2.9%** |

### 4.2 Critical Provenance Findings:
1. **External Information Leakage:**  
   `source_domain` is a metadata column created during synthetic scenario generation. It is **never provided to the categorizer at inference time** (`AchievementCategorizer.predict_record(achievement_text)` only consumes text). Yet, for tags like `lbl_domain_other` (100%), `lbl_domain_hardware` (31.0%), `lbl_domain_cv` (28.0%), and `lbl_domain_ai` (27.5%), the pseudo-label was generated solely from `source_domain` without any accompanying skill or text cue. When an achievement text does not explicitly state its domain, the model is penalized for failing to predict a label that was assigned from hidden metadata.
2. **Circularity & Tautological Memorization:**  
   For tags derived via `text_cues`, the TF-IDF Logistic Regression model learns almost verbatim the keywords of the derivation rule:
   - `lbl_domain_cv` text cue: `computer vision`, `opencv`, `yolo`.  
     *Top model features:* `computer vision` (+3.02), `vision` (+3.02), `computer` (+2.42), `opencv` (+2.24).
   - `lbl_domain_security` text cue: `cybersecurity`, `security`, `cryptography`, `penetration testing`.  
     *Top model features:* `cybersecurity` (+3.29), `security` (+1.87), `cryptography` (+1.65), `penetration testing` (+1.35).
   - `lbl_domain_nlp` text cue: `natural language`, `nlp`, `speech synthesis`.  
     *Top model features:* `spacy` (+2.69), `language` (+2.43), `natural` (+2.04), `natural language` (+2.04).  
   *Implication:* The classifier is not discovering latent domain semantic representations; it is learning a smoothed approximation of the keyword rules.

---

## 5. Independent Model Evaluation without Leakage

The existing production model ([`models/achievement_categorizer_v1.0.1.joblib`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/models/achievement_categorizer_v1.0.1.joblib)) was evaluated across multiple partitions using its fixed validation-selected thresholds ($T_k \in [0.25, 0.625]$).

### 5.1 Multi-Subset Overall Metrics Comparison
| Evaluation Partition | Sample Count ($N$) | Hamming Loss (Lower is better) | Exact Match Ratio | Micro Precision | Micro Recall | Micro F1 | Macro F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Auto-Derived Test Split** | 231 | 0.1922 | 0.3333 | 0.5687 | 0.7551 | **0.6487** | **0.5640** |
| **Reviewed Reference Subset (All)** | 45 | 0.1333 | 0.4000 | 0.6897 | 0.8696 | 0.7692 | 0.7942 |
| **Reviewed Train Split Only** | 32 | **0.0969** | **0.4688** | **0.7629** | **0.9024** | **0.8268** | **0.8502** |
| **Reviewed Val Split Only** | 6 | 0.1500 | 0.3333 | 0.7391 | 0.8500 | 0.7907 | 0.7524 |
| **Reviewed Test Split Only (Held-Out)** | **7** | **0.2857** | **0.1429** | **0.3600** | **0.6923** | **0.4737** | **0.2726** |

### 5.2 Analysis of Discrepancies
- **In-Sample Train Inflation:** On the 32 reviewed training records, the model achieves a high Micro F1 of **0.8268** and Hamming Loss of **0.0969** because its TF-IDF weights were fitted directly on these texts.
- **True Held-Out Generalization ($N=7$):** On the 7 human-audited records from the test split, Micro F1 drops to **0.4737** and Hamming Loss increases to **0.2857**.
- **Over-Prediction Pattern:** Across the 7 test records, the model generated **9 True Positives and 16 False Positives** (Micro Precision = 0.3600). The validation-tuned thresholds ($T_{ai}=0.40$, $T_{hw}=0.40$, $T_{data}=0.425$) were optimized on auto-derived labels and are too aggressive, causing technical keywords to trigger false positive domain tags.

### 5.3 Per-Tag Performance on Held-Out Reviewed Test Records ($N=7$)
| Domain Tag | Support (Pos / Neg) | TP | FP | FN | TN | Precision | Recall | F1 Score | Threshold ($T_k$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `lbl_domain_ai` | 3 / 4 | 3 | 2 | 0 | 2 | 0.6000 | 1.0000 | **0.7500** | 0.400 |
| `lbl_domain_ml` | 1 / 6 | 0 | 0 | 1 | 6 | 0.0000 | 0.0000 | **0.0000** | 0.625 |
| `lbl_domain_nlp` | 1 / 6 | 0 | 1 | 1 | 5 | 0.0000 | 0.0000 | **0.0000** | 0.575 |
| `lbl_domain_cv` | 0 / 7 | 0 | 0 | 0 | 7 | 0.0000 | 0.0000 | **0.0000** | 0.600 |
| `lbl_domain_security` | 1 / 6 | 1 | 2 | 0 | 4 | 0.3333 | 1.0000 | **0.5000** | 0.600 |
| `lbl_domain_systems` | 3 / 4 | 2 | 2 | 1 | 2 | 0.5000 | 0.6667 | **0.5714** | 0.500 |
| `lbl_domain_web` | 1 / 6 | 0 | 2 | 1 | 4 | 0.0000 | 0.0000 | **0.0000** | 0.550 |
| `lbl_domain_data` | 1 / 6 | 1 | 4 | 0 | 2 | 0.2000 | 1.0000 | **0.3333** | 0.425 |
| `lbl_domain_hardware` | 2 / 5 | 2 | 3 | 0 | 2 | 0.4000 | 1.0000 | **0.5714** | 0.400 |
| `lbl_domain_other` | 0 / 7 | 0 | 0 | 0 | 7 | 0.0000 | 0.0000 | **0.0000** | 0.250 |

---

## 6. Sample-Level Dissection of Held-Out Test Records

The 7 genuinely held-out, human-verified test samples illustrate specific model behaviors:

1. **`ACH000891` (Conference Poster on Sustainable Engineering):**
   - *Text snippet:* *"Presented an interactive research poster at the All-India Conference on Sustainable Engineering Innovations (2023)..."*
   - *Gold Tags:* `[lbl_domain_ai, lbl_domain_hardware, lbl_domain_ml]`
   - *Predicted Tags:* `[lbl_domain_ai, lbl_domain_data, lbl_domain_hardware, lbl_domain_security]`
   - *Errors:* FP on `data` (score 0.651 vs thresh 0.425) and `security` (score 0.711 vs thresh 0.600). FN on `ml` (score 0.572 fell below threshold 0.625).
2. **`ACH000376` (WIPO Patent Application):**
   - *Text snippet:* *"Patent application published by World Intellectual Property Organization (WIPO - PCT) (App No. 2021333049)..."*
   - *Gold Tags:* `[lbl_domain_ai, lbl_domain_nlp]`
   - *Predicted Tags:* `[lbl_domain_ai, lbl_domain_data, lbl_domain_hardware, lbl_domain_systems, lbl_domain_web]`
   - *Errors:* FP on 4 unmentioned technical domains (`data`, `hardware`, `systems`, `web`) because general patent vocabulary triggers multiple classifiers. FN on `nlp`.
3. **`ACH000645` (CISSP Associate Credential):**
   - *Text snippet:* *"Achieved professional industry credential: Certified Information Systems Security Professional Associate (CISSP)..."*
   - *Gold Tags:* `[lbl_domain_security]`
   - *Predicted Tags:* `[lbl_domain_security, lbl_domain_systems]`
   - *Errors:* Correctly identified `security` (0.729); FP on `systems` (0.519 vs thresh 0.500).
4. **`ACH000364` (Fault-Tolerant Distributed Architecture Patent):**
   - *Text snippet:* *"Patent application published by World Intellectual Property Organization... 'A Fault-Tolerant Distributed Architecture'..."*
   - *Gold Tags:* `[lbl_domain_systems]`
   - *Predicted Tags:* `[lbl_domain_ai, lbl_domain_data, lbl_domain_hardware, lbl_domain_systems, lbl_domain_web]`
   - *Errors:* Correctly identified `systems` (0.620); FP on `ai`, `data`, `hardware`, and `web`.
5. **`ACH001075` (Journal Editor-in-Chief & Mentorship):**
   - *Text snippet:* *"Served as Editor-in-Chief of Faculty of Engineering Annual Technical Journal. Mentored junior engineering students in Electronics..."*
   - *Gold Tags:* `[lbl_domain_data, lbl_domain_systems]`
   - *Predicted Tags:* `[lbl_domain_ai, lbl_domain_data, lbl_domain_hardware]`
   - *Errors:* Correctly identified `data` (0.610); FP on `ai` (0.767) and `hardware` (0.428); FN on `systems`.
6. **`ACH000230` (Federated Differential Privacy in Edge IoT):**
   - *Text snippet:* *"Published a peer-reviewed research paper titled 'Federated Differential Privacy in Edge IoT' in ACM International Conference..."*
   - *Gold Tags:* `[lbl_domain_ai, lbl_domain_hardware, lbl_domain_systems, lbl_domain_web]`
   - *Predicted Tags:* `[lbl_domain_ai, lbl_domain_data, lbl_domain_hardware, lbl_domain_nlp, lbl_domain_security, lbl_domain_systems]`
   - *Errors:* Correctly identified `ai`, `hardware`, `systems`. FP on `data`, `nlp`, `security`. FN on `web`.
7. **`ACH001538` (Alumni Endowment Fellowship - Academic Integrity & Resilience):**
   - *Text snippet:* *"Recognized with the Alumni Endowment Fellowship Award for exceptional overall academic integrity, resilience, and scholastic merit..."*
   - *Gold Tags:* `[]` (Non-technical achievement)
   - *Predicted Tags:* `[]`
   - *Match:* **Exact True Match**. All technical tag scores remained below 0.20, verifying zero false positives on generic academic honors.

---

## 7. Audit of Previous Evaluation Claims

### 7.1 Refutation of the 30.6% Improvement Claim
The Step 10 report stated:
> *"Hamming Loss: 0.1333 (30.6% error reduction compared to raw heuristic test set)"*

**Audit Finding:** This claim is methodologically flawed:
1. **Sample Incomparability:** The 0.1922 figure was measured on the 231 records of `categorization_test.csv`. The 0.1333 figure was measured on the 45 records of `categorization_reviewed_reference_samples.jsonl`. This was not a paired comparison on the same data.
2. **Training Set Leakage:** 32 of the 45 records in the reviewed set (71.1%) were present in the model's training set, where the model achieved a 0.0969 Hamming loss. The apparent "improvement" was driven primarily by training set memorization.
3. **True Held-Out Metric:** When the human-verified labels are evaluated exclusively on the held-out test split records ($N=7$), the Hamming loss is **0.2857**—which is a **48.6% degradation** compared to the auto-labeled test set.

### 7.2 Why Auto-Derived Metrics Differ from Human-Audited Metrics
- The auto-derived test set labels were produced by the same rules that generated the training labels. The model acts as a surrogate for those rules; hence, it achieves moderate agreement (Micro F1 ~0.65).
- Human auditors evaluate semantic meaning and technical context rather than superficial keywords. When an achievement says "Patent application published by WIPO," humans recognize that this denotes administrative form, whereas the model predicts technical domains (`data`, `hardware`, `systems`) based on generic engineering terms.

---

## 8. Recommended Independent Validation Plan

To establish production-grade reliability, the platform requires an independent, human-annotated gold evaluation set.

### 8.1 Proposed Annotation Plan
1. **Target Sample Size:**
   - **150–200 held-out achievement records** drawn exclusively from the held-out test partition (`data/splits/test.csv`).
   - None of these records may be used in model training, threshold tuning, or heuristic rule development.
2. **Stratified Sampling Strategy:**
   - Sample to ensure **minimum 15 positive examples** for every domain tag, particularly rare categories:
     - `lbl_domain_cv` (target: 15–20 samples)
     - `lbl_domain_nlp` (target: 15–20 samples)
     - `lbl_domain_other` (target: 20–25 non-technical achievements)
   - Include 25–30 multi-domain achievements (spanning $\ge 3$ tags).
   - Include 15–20 zero-tag achievements (purely non-technical awards, cultural activities, sports).
3. **Multi-Annotator Protocol & Adjudication:**
   - Each sample annotated independently by two domain reviewers (Member 1 and Member 2).
   - Compute inter-annotator agreement using Fleiss' Kappa / Multi-label Krippendorff's Alpha.
   - Discrepancies adjudicated by platform lead against explicit guideline criteria.

---

## 9. Prioritized Remediation Plan

| Priority | Remediation Action | Technical Implementation | Target Milestone |
| :---: | :--- | :--- | :---: |
| **P1** | **Threshold Recalibration to Control Over-Prediction** | Raise conservative thresholds ($T_k$) on technical tags (e.g., raise `lbl_domain_ai`, `lbl_domain_data`, `lbl_domain_hardware` from 0.40 to 0.55–0.60) to suppress false positives on general engineering text. | Step 12 |
| **P1** | **Decouple Heuristics from Hidden Metadata** | Refactor [`categorization_dataset.py`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/src/nlp/categorization_dataset.py) so that pseudo-labels are derived strictly from text content, eliminating labels that rely exclusively on `source_domain`. | Step 12 |
| **P2** | **Execute Gold Annotation Campaign** | Author the 150-sample independent gold test set adhering to the Section 8 protocol. | Step 12 |
| **P2** | **Dense Semantic Feature Exploration** | Incorporate Sentence Transformer embeddings (`all-MiniLM-L6-v2`) into categorization feature vectors alongside TF-IDF to capture context beyond exact keyword matches. | Step 13 |
| **P3** | **Administrative Review Routing for Low Margin Predictions** | If an achievement has predicted tag probabilities hovering near threshold ($|P(y) - T_k| < 0.08$), route to administrative review (`review_required = True`). | Step 13 |

---

## 10. Operational Readiness Assessment

- **Autonomous Production Deployment:** **NOT RECOMMENDED** at this stage. The model exhibits high false-positive rates on held-out text and requires threshold tuning against human-reviewed data.
- **Assisted Review / Human-in-the-Loop Pilot:** **RECOMMENDED WITH SAFEGUARDS**. The model accurately surfaces candidate tags and cleanly identifies zero-tag non-technical achievements (e.g., `ACH001538`), but predicted domain tags must be presented to administrators as recommendations rather than finalized records.
- **Handoff Status:** All findings and machine-readable data are preserved in [`reports/step11_per_tag_metrics.json`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/step11_per_tag_metrics.json) and [`reports/step11_per_tag_metrics.csv`](file:///D:/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/step11_per_tag_metrics.csv) for backend integration.
