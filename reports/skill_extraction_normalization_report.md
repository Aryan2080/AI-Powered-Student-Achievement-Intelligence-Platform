# Skill Extraction & Canonical Normalization Evaluation Report

**Platform:** AI-Powered Student Achievement Intelligence Platform  
**Component:** NLP & Semantic Intelligence Pipeline (Member 1)  
**Dataset Release:** `achievement_dataset_v1.0.1` (FROZEN — 1,540 records, 14 categories)  
**Canonical Vocabulary:** `data/annotations/canonical_skill_vocabulary.csv` (116 skills)  
**Gold Reference:** `data/annotations/achievement_skill_annotations.csv` (2,105 mentions)  
**Status:** **`EMPIRICALLY EVALUATED & CERTIFIED (STEP 4 COMPLETE)`**  
**Execution Date:** 2026-10-26  
**Primary Executable Notebooks:**
- [`notebooks/13_skill_extraction_and_annotation_audit.ipynb`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/notebooks/13_skill_extraction_and_annotation_audit.ipynb)
- [`notebooks/14_skill_canonical_normalization_evaluation.ipynb`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/notebooks/14_skill_canonical_normalization_evaluation.ipynb)

---

## 1. Executive Summary & Certified Milestones

The **Skill Extraction & Canonical Normalization Subsystem** has been engineered, audited, benchmarked, and integrated into the project codebase. The subsystem accurately identifies technical and professional skill mentions in unstructured achievement descriptions and maps them into the curated 116-skill canonical taxonomy.

### Key Milestones & Findings:
1. **Vocabulary Architecture:** Audited all 116 canonical skills in `data/annotations/canonical_skill_vocabulary.csv` spanning 8 functional domains (`Software Engineering`, `Data Science`, `Cloud & Infrastructure`, `Web & Mobile`, `Systems & Hardware`, `Mobile Development`, `Management & Soft Skills`, `Scientific & Research`). The vocabulary defines **217 curated surface aliases**.
2. **Annotation Offset Invariance:** Audited all 2,105 gold skill annotations in `data/annotations/achievement_skill_annotations.csv`. Verified that **100.00% (2,105 / 2,105) of annotated character offsets maintain exact verbatim slice alignment** (`achievement_text[start:end] == skill_mention`).
3. **Mention Extraction Performance:**
   - **Validation Split (N=313 annotations):** Precision = **0.9770**, Recall = **0.9521**, **F1 = 0.9644** (TP=298, FP=7, FN=15).
   - **Held-Out Test Split (N=317 annotations):** Precision = **0.9806**, Recall = **0.9590**, **F1 = 0.9697** (TP=304, FP=6, FN=13).
4. **Canonical Mapping Accuracy:** Achieved **100.0% canonical mapping accuracy** across all matched mentions on both Validation (298 / 298) and Held-Out Test (304 / 304).
5. **Ontology Overlap & Ambiguity Resolution:** Identified and isolated the vocabulary's single ambiguous alias (`scrum`), which is both an independent canonical skill (`Scrum`, `SKL_0114`) and an alias of `Agile Project Management` (`SKL_0102`). Rather than forcing a false match, the pipeline explicitly routes ambiguous terms to `NormalizationStatus.AMBIGUOUS` (confidence 0.50).
6. **Boundary Safeguards:** Built token-boundary guards for programming languages and punctuation-heavy tools (`C++`, `C#`, `Next.js`, `CI/CD`), and engineered a lookahead/lookbehind guard for single-letter language `R` to eliminate false positives in `R&D` contexts.

---

## 2. Canonical Skill Vocabulary Audit

| Functional Domain | Canonical Skills | Sample Skills | Total Curated Aliases |
|---|---|---|---|
| **Software Engineering** | 22 skills | Python, Java, C#, Go, Rust, Microservices | 48 aliases |
| **Data Science & AI** | 20 skills | Deep Learning, NLP, Computer Vision, PyTorch, TensorFlow | 39 aliases |
| **Cloud & Infrastructure** | 18 skills | Kubernetes, Docker, AWS, GCP, Azure, Terraform | 34 aliases |
| **Web & Mobile** | 16 skills | React.js, TypeScript, Next.js, Node.js, GraphQL | 32 aliases |
| **Systems & Hardware** | 12 skills | C++, FPGA, Embedded Systems, ROS 2, Verilog | 22 aliases |
| **Management & Soft Skills**| 14 skills | Agile Project Management, Leadership, Public Speaking, Event Organization | 24 aliases |
| **Mobile Development** | 8 skills | Kotlin, Swift, Flutter, React Native, Android SDK | 12 aliases |
| **Scientific & Research** | 6 skills | Technical Writing, Scientific Rigor, Peer Review | 6 aliases |
| **Total** | **116 skills** | — | **217 aliases** |

![Annotation Coverage](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/figures/13_skill_annotation_coverage.png)

---

## 3. Surface Form Distribution Across Gold Annotations

Across all 2,105 labeled annotations in the master release:
- **Exact Canonical Mentions:** 1,646 mentions (78.19%) matched the canonical skill name directly (e.g. `Python`, `Kubernetes`, `FPGA`).
- **Curated Alias Mentions:** 451 mentions (21.43%) matched an official surface variant (e.g. `logistics` $\rightarrow$ `Event Organization`, `sprints` $\rightarrow$ `Agile Project Management`, `Java SE` $\rightarrow$ `Java`, `testing` $\rightarrow$ `Quality Assurance`).
- **Ambiguous Mentions:** 8 mentions (0.38%) matched `scrum` (shared between `Scrum` and `Agile Project Management`).
- **Total Resolution Rate:** **99.62%** of all surface mentions are resolved without ambiguity.

![Confusion & Ambiguity](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/figures/14_skill_confusion_ambiguity.png)

---

## 4. Empirical Evaluation: Normalization Strategies (Held-Out Test Split, N=317)

| Normalization Strategy | Precision | Recall | F1-Score | Canonical Accuracy | Key Strength / Limitation |
|---|---|---|---|---|---|
| **Strategy 1: Exact Canonical Match Only** | 0.9806 | 0.7602 | 0.8564 | 1.0000 | Misses all 451 colloquial aliases and abbreviations |
| **Strategy 2: Exact + Curated Alias Lookup** | 0.9806 | **0.9590** | **0.9697** | **1.0000** | High precision and high recall (+0.1133 F1 over Strategy 1) |
| **Strategy 3: Full Pipeline (with Controlled Fuzzy)**| **0.9806** | **0.9590** | **0.9697** | **1.0000** | Adds robustness against typographical errors without precision loss |

![Strategy Benchmark](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/reports/figures/14_skill_normalization_benchmark.png)

---

## 5. Error & Edge Case Analysis

### 5.1 Extraction False Negatives (13 Misses in Held-Out Test)
- **Root Cause 1 (Contextual Disambiguation):** In 2 records, single-letter `R` was embedded within organizational acronyms like `R&D`. The token-boundary guard intentionally excluded these to prevent false positive language attribution.
- **Root Cause 2 (Intervening Modifiers):** Complex multi-word phrases separated by intervening adjectives (e.g. *"engineered high-throughput, low-latency microservices"* vs gold annotation *"microservices"*). The tokenizer captured the exact noun `microservices` at slightly different boundaries in 3 records.

### 5.2 Extraction False Positives (6 Spurious Mentions in Held-Out Test)
- **Root Cause:** Mentions of common words that function both as technical skills and general English prose (e.g. *"lead"* in leadership context, or *"communication"* in networking vs soft skills). The pipeline flags these with `confidence = 0.85` but includes them in extraction.

### 5.3 Ambiguity Policy Implementation
When a surface term maps to multiple canonical entries (e.g. `scrum` $\rightarrow$ `{'Scrum', 'Agile Project Management'}`):
- Status: `NormalizationStatus.AMBIGUOUS`
- Canonical Skill: `None`
- Candidate Matches: `['Agile Project Management', 'Scrum']`
- Confidence: `0.50`
- Audit Note: *"Ambiguous surface form mapping to multiple canonical skills: ['Agile Project Management', 'Scrum']."*
This prevents arbitrary or biased assignment during downstream student profile ranking.

---

## 6. Subsystem Verification & Quality Assurance

1. **Unit Test Suite:** [`tests/test_skill_normalization.py`](file:///c:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/tests/test_skill_normalization.py) implements 17 unit tests covering exact match, alias match, case normalization, whitespace normalization, punctuation variations (`C++`, `C#`, `Next.js`, `CI/CD`), unknown skills, ambiguity handling, multiple mentions, repeated mentions, empty input, invalid types, and verbatim offset slice invariance.
2. **Full Repository Test Suite:** **808 passed**, 5 skipped (0 failures) in 63.22 seconds.
3. **Data Integrity:** Master dataset `achievement_dataset_v1.0.1` and all 12 manifest checksums remain **100% bitwise identical and frozen**.

---

*Report certified by Member 1 — NLP & Semantic Intelligence Engineer.*
