# Technical Handoff Document: Member 1 to Member 2
## Primary Achievement Classification Dataset & Baseline Readiness
**From:** Member 1 — NLP & Semantic Intelligence Engineer  
**To:** Member 2 — Machine Learning & Classification Engineer  
**Dataset Release Version:** `achievement_dataset_v1.0.1` (Frozen Release)  
**Date:** 2026-10-26  

---

## 1. Executive Summary & Readiness Certification

Member 1 has completed the dataset construction, quality audit, template investigation, and baseline readiness evaluation for the **Primary Achievement Classification Dataset**.

The dataset release `achievement_dataset_v1.0.1` is **CERTIFIED READY** for supervised classification experiments, model architecture exploration, and Sentence Transformer duplicate detection.

### Key Facts:
- **Total Validated Records:** **1,540** (100% schema and semantic integrity compliant).
- **Taxonomy Categories:** **14** (Balanced — exactly **110 records per category**).
- **Dataset Partitions:** Pre-split **1,078 Train (70.00%) / 231 Validation (15.00%) / 231 Test (15.00%)** with zero partition leakage.
- **Duplicate Detection Benchmark:** **300 pairs** (150 positive, 150 hard negative) strictly split-isolated (210 train, 46 val, 44 test).
- **Skill Annotations:** **2,105 annotations** across **116 canonical skills** (100% character slice match).
- **Classification Baseline:** TF-IDF + Linear Classifiers established in `src/data/run_classification_baseline.py`.
- **Sentence Transformer Status:** **`PENDING EMBEDDING EVALUATION`** (Evaluation script and benchmark dataset ready for Member 2 execution).

---

## 2. Dataset Locations & File Artifacts

| Component | File Path | Format / Size | Description |
|---|---|---|---|
| **Primary CSV Dataset** | `data/processed/achievement_classification_dataset.csv` | CSV (1,540 rows, 1.41 MB) | Complete master dataset (26 columns). |
| **Primary JSONL Dataset** | `data/processed/achievement_classification_dataset.jsonl` | JSONL (1,540 lines, 2.17 MB) | Streaming JSON format for Hugging Face datasets. |
| **Training Partition (70%)** | `data/splits/train.csv` | CSV (1,078 rows) | Exclusively for model training and fitting. |
| **Validation Partition (15%)**| `data/splits/validation.csv` | CSV (231 rows) | For model selection, hyperparameter search, and threshold tuning. |
| **Held-Out Test Partition (15%)** | `data/splits/test.csv` | CSV (231 rows) | **FROZEN.** Final unbiased generalization evaluation only. |
| **Duplicate Pairs Benchmark** | `data/annotations/achievement_duplicate_pairs.csv` | CSV (300 pairs) | Split-isolated pairs for duplicate detector evaluation. |
| **Skill Annotations** | `data/annotations/achievement_skill_annotations.csv` | CSV (2,105 rows) | Character offset spans (`start_offset`, `end_offset`). |
| **Canonical Skill Catalog** | `data/annotations/canonical_skill_vocabulary.csv` | CSV (116 skills) | Controlled vocabulary across 10 skill domains. |
| **Extraction Evaluation** | `data/annotations/extraction_evaluation_samples.jsonl` | JSONL (75 samples) | Gold-standard structured attribute extraction targets. |
| **Cryptographic Manifest** | `data/manifests/achievement_classification_manifest.json` | JSON | SHA-256 release checksums for all artifacts. |

---

## 3. Modeling Specifications & Leakage Warnings

### 3.1 Primary Classification Target
- **Target Column:** `category`
- **Classes (14):** `HACKATHON`, `COMPETITION`, `RESEARCH_PUBLICATION`, `PATENT`, `INTERNSHIP`, `CERTIFICATION`, `PROJECT`, `WORKSHOP`, `CONFERENCE`, `LEADERSHIP`, `SPORTS`, `CULTURAL`, `VOLUNTEERING`, `OTHER`.

### 3.2 Recommended Model Input
- **Primary Text Column:** `normalized_text` (Cleaned Unicode NFC representation of `achievement_text`).
- **NEVER EXPOSE ADMINISTRATIVE OR TARGET-DERIVED COLUMNS:**
  > [!WARNING]
  > Under no circumstances may the following columns be used as model features:
  > - `achievement_id`, `source_id`, `generation_id`, `generation_method`
  > - `synthetic_status`, `record_origin`, `quality_status`, `annotation_status`, `validation_flags`
  > - `outcome` (Contains 100% shortcuts: `FILED`/`GRANTED` $\rightarrow$ `PATENT`, `PUBLISHED` $\rightarrow$ `RESEARCH_PUBLICATION`).

---

## 4. Findings from Template Quality Audit (Member 2 Notice)

An audit of 105 near-duplicate candidate pairs revealed:
1. **Template Clustering in `CERTIFICATION` and `OTHER`:**
   - 84 records in `CERTIFICATION` and 44 records in `OTHER` share boilerplate synthetic sentence structures.
   - 40 pairs cross between Train and Validation/Test (17 train-val, 23 train-test).
2. **Impact on Evaluation:**
   - Linear models (TF-IDF) achieve 100% accuracy on validation partly because synthetic phrasing is clean and grammatical.
   - Member 2 should not assume 100% accuracy will transfer to messy real-world student submissions.

---

## 5. Duplicate Detection & Sentence Transformer Instructions

The duplicate detection benchmark (`data/annotations/achievement_duplicate_pairs.csv`) is partitioned strictly to match the dataset splits:
- **Validation Partition (46 pairs):** Use exclusively to tune the cosine similarity threshold $\tau^*$ (typically $0.78 - 0.86$).
- **Test Partition (44 pairs):** Evaluate at $\tau^*$ to report unbiased test metrics.

### Reproducibility Command for Member 2:
```bash
# 1. Run baseline classification experiments:
python src/data/run_classification_baseline.py

# 2. Once torch and sentence-transformers are installed:
python src/data/evaluate_similarity_thresholds.py
```

---

## 6. Critical Governance Limitations

1. **Synthetic Nature:** 100% of records in `achievement_dataset_v1.0.1` are explicitly synthetic (`record_origin = SYNTHETIC`). No real student private data is included.
2. **Generalization Caveat:** High validation performance on synthetic records does not guarantee production reliability on unconstrained, noisy, or OCR-transcribed student documents.
3. **Partition Discipline:** Never train models on `validation.csv` or `test.csv`. Never tune thresholds using `test.csv`.

---
*Technical handoff successfully delivered by Member 1 — NLP & Semantic Intelligence Engineer.*
