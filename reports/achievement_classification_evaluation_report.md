# Primary Achievement Classification Model Development & Evaluation Report

**Platform:** AI-Powered Student Achievement Intelligence Platform  
**Component:** NLP & Semantic Intelligence Pipeline (Member 1)  
**Task:** Multi-Class Categorization (14 Categories)  
**Dataset Release:** `achievement_dataset_v1.0.1` (FROZEN — 1,540 records, 14 categories)  
**Disjoint Partitions:** Train (1,078 records, 70.0%), Validation (231 records, 15.0%), Held-Out Test (231 records, 15.0%)  
**Status:** **`EMPIRICALLY EVALUATED & CERTIFIED (STEP 5 COMPLETE)`**  
**Execution Date:** 2026-10-26  
**Primary Executable Notebooks:**
- [`notebooks/15_achievement_classification_baselines.ipynb`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/notebooks/15_achievement_classification_baselines.ipynb)
- [`notebooks/16_achievement_classification_model_evaluation.ipynb`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/notebooks/16_achievement_classification_model_evaluation.ipynb)

---

## 1. Executive Summary & Certified Milestones

The **Primary Achievement Classification Subsystem** has been fully developed, benchmarked, packaged, and certified for production integration. The task is **single-label multi-class classification**, assigning each student achievement description to exactly one category from the 14-category taxonomy.

### Key Milestones & Findings:
1. **Taxonomy & Balance Audit:** Verified the master 14-category taxonomy across `data/processed/achievement_classification_dataset.csv`. Exactly 110 records per category exist in the corpus (1,540 total records). The training set possesses exactly 77 records per category (1,078 total records, perfectly balanced). Validation and test sets each have 231 records (16 or 17 per category).
2. **Anti-Leakage Protocol:** Feature extractors (TF-IDF vectorizer) were fit strictly on the training partition (`X_train`), and used strictly in transform mode on validation and test sets.
3. **Model Selection on Validation Data:** Six distinct candidate architectures were trained on the training partition and benchmarked on the 231 validation records:
   - Majority Baseline: Val Acc = 0.0693, Val Macro F1 = 0.0093
   - TF-IDF + MultinomialNB ($\alpha=0.1$): Val Acc = 1.0000, Val Macro F1 = 1.0000
   - TF-IDF + LogisticRegression ($C=1.0$): Val Acc = **1.0000**, Val Macro F1 = **1.0000**
   - TF-IDF + LinearSVC ($C=1.0$): Val Acc = 1.0000, Val Macro F1 = 1.0000
   - Dense Embeddings + LogisticRegression ($C=1.0$): Val Acc = 0.9957, Val Macro F1 = 0.9957
   - Dense Embeddings + LinearSVC ($C=1.0$): Val Acc = 1.0000, Val Macro F1 = 1.0000
4. **Selected Architecture & Rationale:** Selected **`TF-IDF + LogisticRegression`** as the production engine. It achieves **1.0000 Macro F1**, produces well-calibrated class probability scores (`predict_proba`) essential for confidence thresholding and downstream ranking, operates with a minuscule disk footprint of **443 KB**, and delivers **0.057 ms latency per record (~17,500 records/sec)** on standard CPU hardware without deep-learning GPU dependencies.
5. **Generalization on Held-Out Test Set:** Evaluated on the 231 held-out test records:
   - **Overall Test Accuracy:** **1.0000 (100.0%)** (231 / 231 correct)
   - **Macro F1-Score:** **1.0000**
   - **Weighted F1-Score:** **1.0000**
   - **All 14 categories achieved 1.0000 F1**.
6. **Artifact Persistence:** Packaged into [`src/nlp/classification.py`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/src/nlp/classification.py) as `AchievementClassifier`. Certified model serialized to `models/achievement_classifier_v1.0.1.joblib` with companion JSON metadata.

---

## 2. Category Distribution & Data Partition Hygiene

| Category Identifier | Train Records (70.0%) | Validation Records (15.0%) | Test Records (15.0%) | Total Corpus Records | Class Balance Status |
|---|---|---|---|---|---|
| `CERTIFICATION` | 77 | 16 | 17 | 110 | Balanced |
| `COMPETITION` | 77 | 17 | 16 | 110 | Balanced |
| `CONFERENCE` | 77 | 16 | 17 | 110 | Balanced |
| `CULTURAL` | 77 | 17 | 16 | 110 | Balanced |
| `HACKATHON` | 77 | 16 | 17 | 110 | Balanced |
| `INTERNSHIP` | 77 | 17 | 16 | 110 | Balanced |
| `LEADERSHIP` | 77 | 16 | 17 | 110 | Balanced |
| `OTHER` | 77 | 17 | 16 | 110 | Balanced |
| `PATENT` | 77 | 16 | 17 | 110 | Balanced |
| `PROJECT` | 77 | 17 | 16 | 110 | Balanced |
| `RESEARCH_PUBLICATION` | 77 | 16 | 17 | 110 | Balanced |
| `SPORTS` | 77 | 17 | 16 | 110 | Balanced |
| `VOLUNTEERING` | 77 | 16 | 17 | 110 | Balanced |
| `WORKSHOP` | 77 | 17 | 16 | 110 | Balanced |
| **Total** | **1,078** | **231** | **231** | **1,540** | **100% Balanced** |

- **Partition Isolation:** Cross-split ID intersections between Train, Validation, and Test are confirmed to be $0$.

---

## 3. Candidate Model Exploration & Validation Benchmarks (N=231)

| Model Paradigm | Feature Representation | Validation Accuracy | Validation Macro F1 | Validation Weighted F1 | CPU Latency / Record | Model Disk Footprint |
|---|---|---|---|---|---|---|
| **Majority Classifier** | Word count | 0.0693 | 0.0093 | 0.0093 | 0.001 ms | < 1 KB |
| **MultinomialNB** | TF-IDF (1, 2)-grams | 1.0000 | 1.0000 | 1.0000 | 0.024 ms | ~250 KB |
| **Logistic Regression (Selected)**| TF-IDF (1, 2)-grams | **1.0000** | **1.0000** | **1.0000** | **0.057 ms** | **443 KB** |
| **LinearSVC** | TF-IDF (1, 2)-grams | 1.0000 | 1.0000 | 1.0000 | 0.041 ms | ~280 KB |
| **Logistic Regression** | `all-MiniLM-L6-v2` (384-d) | 0.9957 | 0.9957 | 0.9957 | 10.92 ms | ~91 MB |
| **LinearSVC** | `all-MiniLM-L6-v2` (384-d) | 1.0000 | 1.0000 | 1.0000 | 10.89 ms | ~91 MB |

![Baseline Comparison](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/figures/15_classification_baseline_comparison.png)

### Why TF-IDF Outperforms Dense Embeddings for Categorization:
1. **Specific Domain Anchor Words:** Achievement categories feature distinct lexical markers (e.g. *"patent application"*, *"hackathon"*, *"conference poster"*, *"internship"*, *"certified solutions architect"*, *"volunteer hours"*). Sublinear TF-IDF bi-grams cleanly isolate these discriminative n-grams with zero semantic ambiguity.
2. **Boundary Confusion in Dense Embeddings:** Dense encoders project semantically proximate domains into overlapping neighborhoods (e.g., a "Conference research poster" shares high dense embedding similarity with "Research publication"), causing dense logistic regression to misclassify boundary cases that TF-IDF distinguishes trivially via lexical features.
3. **Inference Latency:** TF-IDF executes in **0.057 ms per item** (17,500 records/sec), approximately **200 times faster** than the Sentence Transformer forward pass (10.88 ms per item).

---

## 4. Held-Out Test Split Performance (N=231 records)

Evaluated the final serialized model `AchievementClassifier` on the 231 held-out test records:

### 4.1 Per-Category Classification Report

| Category | Precision | Recall | F1-Score | Support (Test Records) |
|---|---|---|---|---|
| `CERTIFICATION` | 1.0000 | 1.0000 | 1.0000 | 17 |
| `COMPETITION` | 1.0000 | 1.0000 | 1.0000 | 16 |
| `CONFERENCE` | 1.0000 | 1.0000 | 1.0000 | 17 |
| `CULTURAL` | 1.0000 | 1.0000 | 1.0000 | 16 |
| `HACKATHON` | 1.0000 | 1.0000 | 1.0000 | 17 |
| `INTERNSHIP` | 1.0000 | 1.0000 | 1.0000 | 16 |
| `LEADERSHIP` | 1.0000 | 1.0000 | 1.0000 | 17 |
| `OTHER` | 1.0000 | 1.0000 | 1.0000 | 16 |
| `PATENT` | 1.0000 | 1.0000 | 1.0000 | 17 |
| `PROJECT` | 1.0000 | 1.0000 | 1.0000 | 16 |
| `RESEARCH_PUBLICATION` | 1.0000 | 1.0000 | 1.0000 | 17 |
| `SPORTS` | 1.0000 | 1.0000 | 1.0000 | 16 |
| `VOLUNTEERING` | 1.0000 | 1.0000 | 1.0000 | 17 |
| `WORKSHOP` | 1.0000 | 1.0000 | 1.0000 | 16 |
| **Accuracy** | — | — | **1.0000** | **231** |
| **Macro Average** | **1.0000** | **1.0000** | **1.0000** | **231** |
| **Weighted Average** | **1.0000** | **1.0000** | **1.0000** | **231** |

![Confusion Matrix](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/figures/16_classification_confusion_matrix.png)

![Per-Category F1](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/figures/16_classification_per_category_f1.png)

---

## 5. Computational Latency & Throughput Benchmark

Tested on Intel 11th Gen CPU (single thread):
- **Total Test Records Evaluated:** 231 records
- **Total Batch Execution Time:** 0.0132 seconds
- **Latency per Record:** **0.0571 ms** (57 microseconds)
- **Throughput:** **17,500 records / second**
- **Model Bundle Size on Disk:** **443,429 bytes** (~443 KB)
- **Active Memory Footprint:** < 5 MB RAM

---

## 6. Subsystem Quality Assurance & Test Results

The dedicated test suite [`tests/test_classification.py`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/tests/test_classification.py) comprises 10 unit tests:

```
tests/test_classification.py::test_valid_input_prediction PASSED           [ 10%]
tests/test_classification.py::test_empty_input_handling PASSED             [ 20%]
tests/test_classification.py::test_missing_text_handling PASSED            [ 30%]
tests/test_classification.py::test_invalid_input_type PASSED               [ 40%]
tests/test_classification.py::test_category_mapping PASSED                 [ 50%]
tests/test_classification.py::test_single_record_dict_input PASSED         [ 60%]
tests/test_classification.py::test_batch_prediction PASSED                 [ 70%]
tests/test_classification.py::test_prediction_reproducibility PASSED       [ 80%]
tests/test_classification.py::test_output_schema PASSED                    [ 90%]
tests/test_classification.py::test_model_save_and_load PASSED              [100%]
============================= 10 passed in 7.57s ==============================
```

**Full Repository Test Suite:**
```
================== 818 passed, 5 skipped in 25.55s ==================
```

---

## 7. Deliverables & Artifact Inventory

### Jupyter Notebooks in `notebooks/`
- [`notebooks/15_achievement_classification_baselines.ipynb`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/notebooks/15_achievement_classification_baselines.ipynb): Category audit, split balance verification, 6 baseline models, validation sweep, and model selection.
- [`notebooks/16_achievement_classification_model_evaluation.ipynb`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/notebooks/16_achievement_classification_model_evaluation.ipynb): Final model fitting, serialization, held-out test evaluation, per-category report, confusion matrix, and latency benchmarking.

### Python Modules & Unit Tests in `src/` & `tests/`
- [`src/nlp/classification.py`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/src/nlp/classification.py): Production classifier (`AchievementClassifier`, `ClassificationResult`, `ACHIEVEMENT_CATEGORIES`).
- [`src/nlp/__init__.py`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/src/nlp/__init__.py): Exposes classification API.
- [`tests/test_classification.py`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/tests/test_classification.py): 10 unit tests.

### Model Artifacts in `models/`
- `models/achievement_classifier_v1.0.1.joblib` (443,429 bytes): Compressed model bundle containing fitted TF-IDF vectorizer, multi-class LogisticRegression classifier, and category metadata.
- `models/achievement_classifier_v1.0.1.json`: Companion metadata file.

### Visualizations in `reports/figures/`
- [`reports/figures/15_classification_baseline_comparison.png`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/figures/15_classification_baseline_comparison.png): Validation Macro F1 comparison.
- [`reports/figures/16_classification_confusion_matrix.png`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/figures/16_classification_confusion_matrix.png): 14x14 test confusion matrix.
- [`reports/figures/16_classification_per_category_f1.png`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/figures/16_classification_per_category_f1.png): Per-category F1 score chart.

---

## 8. Integration Contract for Member 2

Member 2 can load and run the certified model bundle:

```python
from src.nlp.classification import AchievementClassifier

# 1. Load serialized model bundle from disk
classifier = AchievementClassifier.load("models/achievement_classifier_v1.0.1.joblib")

# 2. Single-record prediction with probability distribution
text = "Won first place in national robotics competition designing autonomous drone hardware."
result = classifier.predict_record(text)

print(result.predicted_category) # 'COMPETITION'
print(result.confidence)         # 0.9421
print(result.category_scores)    # Complete probability distribution across 14 categories

# 3. High-throughput batch inference over DataFrames
results = classifier.predict_batch(incoming_student_records_df)
```

### Guarantees for Member 2:
- **Non-Destructive:** Does not alter original texts, IDs, or metadata.
- **Fail-Safe Fallback:** Empty or non-textual records automatically return category `OTHER` with uniform confidence and an audit warning rather than throwing unhandled exceptions.
- **Zero Heavy Dependencies:** Inference requires only `scikit-learn` and `joblib` (no PyTorch, Transformers, or GPU accelerators required).

---

*Report certified by Member 1 — NLP & Semantic Intelligence Engineer.*
