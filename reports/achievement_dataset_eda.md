# Exploratory Data Analysis (EDA) Report
## Primary Achievement Classification Dataset
**AI-Powered Student Achievement Intelligence Platform — Member 1**  
**Date of Audit:** 2026-10-26  
**Dataset Version:** `achievement_dataset_v1.0.1`  
**Dataset Source:** `data/processed/achievement_classification_dataset.csv`  

---

## 1. Dataset Dimensions & Volume Overview

| Dimension | Measured Value | Requirement Specification | Compliance Status |
|---|---|---|---|
| **Total Validated Records** | **1540** | Target: ~1,500 records | **PASS** (102.7% of target) |
| **Synthetic Records** | **1540** (100.0%) | Explicitly Synthetic | **PASS** |
| **Real Source Records** | **0** (0.0%) | Verified Public Sources Only | Documented |
| **Active Categories** | **14** | Exactly 14 Primary Categories | **PASS** |
| **Minimum Records per Category** | **110** | Minimum: $\ge 80$ | **PASS** |
| **Maximum Records per Category** | **110** | Balanced (100–120) | **PASS** |
| **Quality Status** | **VALIDATED: 1540** | 100% Passed Validation | **PASS** |

---

## 2. Category Distribution & Class Balance

Every single one of the 14 taxonomy categories contains exactly **110 records**, establishing zero class imbalance.

| Taxonomy Category | Record Count | Percentage | Class Balance Ratio |
|---|---|---|---|
| **`CERTIFICATION`** | 110 | 7.14% | 1.00 (Balanced) |
| **`COMPETITION`** | 110 | 7.14% | 1.00 (Balanced) |
| **`CONFERENCE`** | 110 | 7.14% | 1.00 (Balanced) |
| **`CULTURAL`** | 110 | 7.14% | 1.00 (Balanced) |
| **`HACKATHON`** | 110 | 7.14% | 1.00 (Balanced) |
| **`INTERNSHIP`** | 110 | 7.14% | 1.00 (Balanced) |
| **`LEADERSHIP`** | 110 | 7.14% | 1.00 (Balanced) |
| **`OTHER`** | 110 | 7.14% | 1.00 (Balanced) |
| **`PATENT`** | 110 | 7.14% | 1.00 (Balanced) |
| **`PROJECT`** | 110 | 7.14% | 1.00 (Balanced) |
| **`RESEARCH_PUBLICATION`** | 110 | 7.14% | 1.00 (Balanced) |
| **`SPORTS`** | 110 | 7.14% | 1.00 (Balanced) |
| **`VOLUNTEERING`** | 110 | 7.14% | 1.00 (Balanced) |
| **`WORKSHOP`** | 110 | 7.14% | 1.00 (Balanced) |

---

## 3. Verified Train / Validation / Test Splits (70 / 15 / 15)

Data partitions satisfy the strict 70/15/15 ratio with zero overlap:

| Partition File | Record Count | Exact Proportion | Verification Status |
|---|---|---|---|
| **`data/splits/train.csv`** | **1078** | **70.00%** (70.00%) | **PASS** |
| **`data/splits/validation.csv`** | **231** | **15.00%** (15.00%) | **PASS** |
| **`data/splits/test.csv`** | **231** | **15.00%** (15.00%) | **PASS** |
| **Total Split Records** | **1540** | **100.00%** | **PASS** |

---

## 4. Text Length & Complexity Analysis

Text descriptions feature natural variation across short resume bullet points, standard narrative achievements, and detailed project and publication descriptions.

| Metric | Minimum | Mean $\pm$ Std | Median | Maximum |
|---|---|---|---|---|
| **Raw Character Length** | 142 | 256.51 $\pm$ 45.63 | 255.0 | 417 |
| **Word Count** | 20 | 34.63 $\pm$ 6.22 | 34.0 | 59 |
| **Sentence Count** | 1 | 1.93 $\pm$ 0.43 | 2.0 | 4 |

---

## 5. Structured Attribute Distributions

### 5.1 Achievement Level (`level`)
| Controlled Level | Count | Proportion |
|---|---|---|
| `INTERNATIONAL` | 329 | 21.36% |
| `NATIONAL` | 284 | 18.44% |
| `PROFESSIONAL` | 220 | 14.29% |
| `STATE` | 202 | 13.12% |
| `UNIVERSITY` | 201 | 13.05% |
| `COLLEGE` | 152 | 9.87% |
| `ORGANIZATIONAL` | 64 | 4.16% |
| `DISTRICT` | 50 | 3.25% |
| `LOCAL` | 38 | 2.47% |

### 5.2 Achievement Outcome (`outcome`)
| Controlled Outcome | Count | Proportion |
|---|---|---|
| `COMPLETION` | 359 | 23.31% |
| `RECOGNITION` | 323 | 20.97% |
| `PARTICIPATION` | 200 | 12.99% |
| `LEADERSHIP` | 110 | 7.14% |
| `PUBLISHED` | 110 | 7.14% |
| `SECOND_PLACE` | 84 | 5.45% |
| `FILED` | 82 | 5.32% |
| `THIRD_PLACE` | 64 | 4.16% |
| `WINNER` | 58 | 3.77% |
| `PRESENTED` | 44 | 2.86% |
| `FIRST_PLACE` | 41 | 2.66% |
| `FINALIST` | 37 | 2.40% |
| `GRANTED` | 28 | 1.82% |

---

## 6. Missingness & Sparsity Profile

Missing values in structured attributes reflect realistic institutional reporting (e.g. non-competitive projects have no rank; certifications have issuers rather than distinct event names).

| Schema Field | Null / Missing Count | Sparsity Percentage | Clinical Justification |
|---|---|---|---|
| **`event_name`** | 220 | 14.29% | Projects, internships, and scholarships do not have formal competitive event names. |
| **`organization`** | 0 | 0.0% | Attribute populated where applicable. |
| **`achievement_date`** | 193 | 12.53% | Realistic missing date information; preserved as null per annotation guidelines. |
| **`rank`** | 660 | 42.86% | Rank is not applicable for certifications, internships, workshops, or volunteering. |
| **`skills`** | 0 | 0.0% | Attribute populated where applicable. |
| **`evidence_id`** | 1540 | 100.0% | Synthetic records intentionally carry null external evidence links. |
| **`source_url`** | 1540 | 100.0% | Synthetic records intentionally carry null external evidence links. |
| **`source_access_date`** | 1540 | 100.0% | Synthetic records intentionally carry null external evidence links. |
| **`validation_flags`** | 1540 | 100.0% | Zero flags indicating 100% clean record integrity. |

---

## 7. Skill Mention Analysis

- **Total Extracted Skill Mentions:** 2105
- **Unique Canonical Skills Mentioned:** 113
- **Top 10 Most Frequent Canonical Skills:**
  1. **Event Organization**: 91 mentions
  1. **Microservices**: 83 mentions
  1. **R**: 73 mentions
  1. **Embedded Systems**: 73 mentions
  1. **Public Speaking**: 60 mentions
  1. **Agile Project Management**: 59 mentions
  1. **Quality Assurance**: 50 mentions
  1. **Kubernetes**: 50 mentions
  1. **Cybersecurity**: 49 mentions
  1. **Deep Learning**: 44 mentions

---
*Comprehensive EDA report generated automatically by `src/data/achievement_dataset_statistics.py`.*
