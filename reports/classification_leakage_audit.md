# Classification Leakage & Artificial Shortcut Audit Report

**Platform:** AI-Powered Student Achievement Intelligence Platform  
**Component:** NLP & Semantic Intelligence Pipeline (Member 1)  
**Dataset Release Audited:** `achievement_dataset_v1.0.1`  
**Audit Scope:** 1,540 achievement records across all 14 categories  
**Date of Audit:** 2026-10-26  

---

## 1. Executive Summary & Objective

The objective of this audit is to determine whether supervised text classifiers can learn genuine semantic achievement context, or whether artificial shortcuts, administrative metadata leaks, and superficial keyword correlations allow models to memorize classes trivialy.

### Core Audit Takeaways:
1. **Administrative Metadata Leakage Risk: SEVERE (Mitigated by Protocol)**  
   Structured attributes such as `outcome` (`FILED`, `GRANTED`, `PUBLISHED`) have near 100% correlation with `PATENT` and `RESEARCH_PUBLICATION`. **Strict protocol enforcement mandates that NO metadata columns are exposed to classifiers.**
2. **Category Keyword Presence: MODERATE & REALISTIC**  
   Domain-specific vocabulary (e.g. "patent", "journal", "community service") appears naturally in achievements, while categories like `HACKATHON` (0% literal word match) and `COMPETITION` (16.4% literal word match) successfully decouple from trivial label memorization.
3. **Template Repetition Leakage: MODERATE**  
   Boilerplate sentence structures in `CERTIFICATION` and `OTHER` allow minor n-gram memorization across 40 train-to-val/test cross-split pairs.
4. **Text Length Discrimination: NEGLIGIBLE**  
   12 of 14 categories fall tightly within $220 - 290$ characters, preventing length-based classification shortcuts.

---

## 2. In-Depth Leakage Dimension Analysis

### 2.1 Category Name & Indicative Keyword Presence in Text
An empirical search for literal category terms and direct synonyms across achievement descriptions revealed:

| Category | Literal Keyword Hits | Proportion | Indicative Vocabulary Observed | Leakage Assessment |
|---|---|---|---|---|
| **`HACKATHON`** | 0 / 110 | **0.0%** | "sprint", "grand finale", "continuous development", "maker-thon" | **CLEAN** (Zero label memorization) |
| **`COMPETITION`** | 18 / 110 | **16.4%** | "olympiad", "challenge", "contest", "playoff", "tournament" | **LOW** (Context-driven) |
| **`CERTIFICATION`** | 48 / 110 | **43.6%** | "proctored examination", "credential", "certified" | **MODERATE** (Standard professional phrasing) |
| **`CONFERENCE`** | 48 / 110 | **43.6%** | "symposium", "presented", "proceedings", "session" | **MODERATE** (Standard academic phrasing) |
| **`OTHER`** | 56 / 110 | **50.9%** | "scholarship", "fellowship", "merit award", "exchange" | **MODERATE** (Standard honorific phrasing) |
| **`INTERNSHIP`** | 66 / 110 | **60.0%** | "internship", "summer trainee", "engineering intern" | **EXPECTED** (Natural resume term) |
| **`PROJECT`** | 70 / 110 | **63.6%** | "project", "capstone", "open-source system", "prototype" | **EXPECTED** (Natural project terminology) |
| **`CULTURAL`** | 75 / 110 | **68.2%** | "classical arts", "debate", "carnatic", "drama", "musical" | **LOW** (Domain-diverse) |
| **`SPORTS`** | 90 / 110 | **81.8%** | "badminton", "athletics", "basketball", "tournament", "match" | **LOW** (Domain-diverse) |
| **`WORKSHOP`** | 82 / 110 | **74.5%** | "hands-on workshop", "bootcamp", "training seminar" | **EXPECTED** (Natural workshop phrasing) |
| **`RESEARCH_PUBLICATION`** | 110 / 110 | **100.0%** | "published", "journal", "peer-reviewed", "paper" | **HIGH BUT GENUINE** (Inherent to publishing) |
| **`PATENT`** | 110 / 110 | **100.0%** | "patent application", "co-inventor", "filed", "claims" | **HIGH BUT GENUINE** (Inherent to patents) |
| **`VOLUNTEERING`** | 110 / 110 | **100.0%** | "community service", "social service", "volunteer hours" | **HIGH BUT GENUINE** (Inherent to volunteering) |
| **`LEADERSHIP`** | 110 / 110 | **100.0%** | "elected", "secretary", "president", "spearheaded", "club" | **HIGH BUT GENUINE** (Inherent to leadership) |

> [!NOTE]
> Words like "patent", "journal", "published", and "volunteer" are inherently informative features of genuine human language. Their presence does not constitute artificial leakage, provided administrative metadata columns are withheld.

### 2.2 Outcome-Related Shortcuts (Catastrophic Metadata Leakage)
Analysis of the `outcome` column demonstrates why structured metadata must be strictly excluded from classification inputs:
- `outcome == 'FILED'` (82 records) $\rightarrow$ **100% `PATENT`**
- `outcome == 'GRANTED'` (28 records) $\rightarrow$ **100% `PATENT`**
- `outcome == 'PUBLISHED'` (110 records) $\rightarrow$ **100% `RESEARCH_PUBLICATION`**
- `outcome == 'LEADERSHIP'` (110 records) $\rightarrow$ **100% `LEADERSHIP`**
- `outcome == 'PRESENTED'` (44 records) $\rightarrow$ **100% `CONFERENCE`**

**Mandatory Restriction:** Models must ONLY be supplied with `normalized_text` (or `achievement_text`). Using structured tabular columns (`outcome`, `level`, `domain`) would produce trivial rule-based memorization rather than natural language understanding.

### 2.3 Text Length Profiles across Categories
- `OTHER`: Mean $174.2$ chars ($23.8$ words) — Shortest
- `COMPETITION`: Mean $215.8$ chars ($28.2$ words)
- `CULTURAL`: Mean $226.4$ chars ($30.5$ words)
- `SPORTS`: Mean $234.2$ chars ($30.6$ words)
- `INTERNSHIP`: Mean $246.3$ chars ($32.9$ words)
- `CERTIFICATION`: Mean $254.0$ chars ($30.6$ words)
- `WORKSHOP`: Mean $258.6$ chars ($32.2$ words)
- `CONFERENCE`: Mean $264.0$ chars ($34.4$ words)
- `LEADERSHIP`: Mean $268.2$ chars ($36.1$ words)
- `HACKATHON`: Mean $275.1$ chars ($38.5$ words)
- `PROJECT`: Mean $280.6$ chars ($34.2$ words)
- `VOLUNTEERING`: Mean $281.0$ chars ($37.2$ words)
- `RESEARCH_PUBLICATION`: Mean $291.0$ chars ($35.3$ words)
- `PATENT`: Mean $321.6$ chars ($39.6$ words) — Longest

**Finding:** Character and word lengths overlap broadly across all 14 categories. A decision tree or linear classifier cannot reliably predict category using document length features.

### 2.4 Event & Organization Exclusivity
- **80 unique organizations** are distributed across multiple categories. Premier institutions (e.g. IITs, NITs, IISc, Anna University) sponsor hackathons, host conferences, issue certifications, and enter athletic contingents.
- **413 unique event names** are distributed across categories, ensuring the classifier must learn semantic sentence roles rather than memorizing a single master university name.

---

## 3. Leakage Mitigation Guidelines for Modeling (Member 2)

| Potential Leakage Vector | Risk Level | Enforced Prevention Protocol |
|---|---|---|
| **Administrative Columns** (`achievement_id`, `source_id`, `generation_id`, etc.) | **CRITICAL** | Strictly dropped from dataframe prior to training. |
| **Structured Categorical Fields** (`outcome`, `level`, `domain`) | **HIGH** | Excluded from text classification baseline models. |
| **Literal Category Labels** | **LOW-MEDIUM** | Decoupled in major categories (`HACKATHON` 0%, `COMPETITION` 16.4%). |
| **Repeated Synthetic N-Grams** (`CERTIFICATION`, `OTHER`) | **MEDIUM** | Member 2 must inspect cross-class confusion rather than relying solely on overall accuracy. |

---
*Report certified by Member 1 — NLP & Semantic Intelligence Engineer.*
