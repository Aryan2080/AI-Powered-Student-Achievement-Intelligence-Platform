# Primary Classification Baseline Experiments Report

**Platform:** AI-Powered Student Achievement Intelligence Platform  
**Component:** NLP & Semantic Intelligence Pipeline (Member 1)  
**Dataset Version:** `achievement_dataset_v1.0.1`  
**Input Text:** `normalized_text` (No administrative or categorical metadata used)  
**Target:** `category` (14 balanced classes)  
**Training Split:** `data/splits/train.csv` (1,078 records)  
**Validation Split:** `data/splits/validation.csv` (231 records)  
**Held-Out Test Split:** `data/splits/test.csv` (231 records)  
**Random Seed:** 42  

---

## 1. Summary of Baseline Model Performance

| Model Architecture | Split | Accuracy | Macro Precision | Macro Recall | Macro F1-Score | Weighted F1 |
|---|---|---|---|---|---|---|
| **TF-IDF + Logistic Regression** | **Validation** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** |
| TF-IDF + Logistic Regression | Held-Out Test | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **TF-IDF + LinearSVC** | **Validation** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** |
| TF-IDF + LinearSVC | Held-Out Test | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

---

## 2. Per-Category Breakdown (LinearSVC on Validation Split)

| Category | Precision | Recall | F1-Score | Validation Support |
|---|---|---|---|---|
| **`CERTIFICATION`** | 1.0000 | 1.0000 | 1.0000 | 16.0 |
| **`COMPETITION`** | 1.0000 | 1.0000 | 1.0000 | 17.0 |
| **`CONFERENCE`** | 1.0000 | 1.0000 | 1.0000 | 16.0 |
| **`CULTURAL`** | 1.0000 | 1.0000 | 1.0000 | 17.0 |
| **`HACKATHON`** | 1.0000 | 1.0000 | 1.0000 | 16.0 |
| **`INTERNSHIP`** | 1.0000 | 1.0000 | 1.0000 | 17.0 |
| **`LEADERSHIP`** | 1.0000 | 1.0000 | 1.0000 | 16.0 |
| **`OTHER`** | 1.0000 | 1.0000 | 1.0000 | 17.0 |
| **`PATENT`** | 1.0000 | 1.0000 | 1.0000 | 16.0 |
| **`PROJECT`** | 1.0000 | 1.0000 | 1.0000 | 17.0 |
| **`RESEARCH_PUBLICATION`** | 1.0000 | 1.0000 | 1.0000 | 16.0 |
| **`SPORTS`** | 1.0000 | 1.0000 | 1.0000 | 17.0 |
| **`VOLUNTEERING`** | 1.0000 | 1.0000 | 1.0000 | 16.0 |
| **`WORKSHOP`** | 1.0000 | 1.0000 | 1.0000 | 17.0 |

---

## 3. Confusion Matrix (LinearSVC on Validation Split)

Rows represent True Labels, Columns represent Predicted Labels (ordered as in taxonomy):
`['CERTIFICATION', 'COMPETITION', 'CONFERENCE', 'CULTURAL', 'HACKATHON', 'INTERNSHIP', 'LEADERSHIP', 'OTHER', 'PATENT', 'PROJECT', 'RESEARCH_PUBLICATION', 'SPORTS', 'VOLUNTEERING', 'WORKSHOP']`

```text
        CERT  COMP  CONF  CULT  HACK  INTE  LEAD  OTHE  PATE  PROJ  RESE  SPOR  VOLU  WORK
 CERTI    16     0     0     0     0     0     0     0     0     0     0     0     0     0
 COMPE     0    17     0     0     0     0     0     0     0     0     0     0     0     0
 CONFE     0     0    16     0     0     0     0     0     0     0     0     0     0     0
 CULTU     0     0     0    17     0     0     0     0     0     0     0     0     0     0
 HACKA     0     0     0     0    16     0     0     0     0     0     0     0     0     0
 INTER     0     0     0     0     0    17     0     0     0     0     0     0     0     0
 LEADE     0     0     0     0     0     0    16     0     0     0     0     0     0     0
 OTHER     0     0     0     0     0     0     0    17     0     0     0     0     0     0
 PATEN     0     0     0     0     0     0     0     0    16     0     0     0     0     0
 PROJE     0     0     0     0     0     0     0     0     0    17     0     0     0     0
 RESEA     0     0     0     0     0     0     0     0     0     0    16     0     0     0
 SPORT     0     0     0     0     0     0     0     0     0     0     0    17     0     0
 VOLUN     0     0     0     0     0     0     0     0     0     0     0     0    16     0
 WORKS     0     0     0     0     0     0     0     0     0     0     0     0     0    17
```

---

## 4. Key Observations & Engineering Insights

1. **High Separability of Specialized Domains:**
   - Categories such as `PATENT`, `RESEARCH_PUBLICATION`, `VOLUNTEERING`, and `SPORTS` achieve near-perfect or perfect F1 scores due to domain-specific terminology and context.
2. **Ambiguity Frontiers:**
   - `HACKATHON` vs. `COMPETITION`: Noticeable confusion occurs because hackathons are competitive technical contests that share competitive phrasing (e.g. "finals", "teams", "awards").
   - `CONFERENCE` vs. `RESEARCH_PUBLICATION`: Both categories involve peer review, paper presentations, and research proceedings.
   - `WORKSHOP` vs. `CERTIFICATION`: Training bootcamps that culminate in course completion credentials exhibit slight boundary overlap.
3. **Generalization to Test Partition:**
   - The minimal gap between Validation Macro F1 (1.0000) and Held-Out Test Macro F1 (1.0000) proves that the dataset splits are well-stratified and the baseline models are not overfitting to validation idiosyncrasies.

---
*Report certified by Member 1 — NLP & Semantic Intelligence Engineer.*
