# Duplicate Pair Benchmark Dataset Report

**Author:** Member 1 — NLP & Semantic Intelligence Engineer  
**Dataset Path:** `data/annotations/achievement_duplicate_pairs.csv`  
**Total Pairs:** 300  
**Split Leakage Status:** **ZERO LEAKAGE (Strictly Split-Isolated)**

---

## 1. Summary of Pair Distributions

| Metric | Count | Ratio |
|---|---|---|
| **Positive Pairs (Label = 1: Same Achievement)** | 150 | 50.0% |
| **Negative Pairs (Label = 0: Different Achievement)** | 150 | 50.0% |
| **Total Evaluation Pairs** | 300 | 100.0% |

---

## 2. Split Partition Allocation (Zero Data Leakage)

All record pairs are constructed strictly from within their designated dataset split partition. No pair crosses train/val/test boundaries.

| Split Partition | Positive Pairs | Negative Pairs | Total Pairs | Partition Share |
|---|---|---|---|---|
| **Train** | 105 | 105 | 210 | 70.0% |
| **Validation** | 23 | 23 | 46 | 15.3% |
| **Test** | 22 | 22 | 44 | 14.7% |
| **Total** | **150** | **150** | **300** | **100.0%** |

---

## 3. Duplicate Type Breakdown

Positive and negative pairs are constructed to reflect realistic surface variation vs. semantic identity.

### Positive Pair Families (True Duplicates)
- **`PARAPHRASE_RESTRUCTURED`**: Inverted syntactic clauses and alternate sentence ordering describing the exact same project and event.
- **`RESUME_BULLET_VARIANT`**: Condensed telegraphic resume bullet point expressing the same achievement.
- **`OFFICIAL_CITATION_VARIANT`**: Formal certificate citation phrasing corresponding to the same award.
- **`CONCISE_SUMMARY_VARIANT`**: Abstracted 1-sentence summary of the original narrative.

### Hard Negative Pair Families (Distinct Achievements)
- **`SAME_EVENT_DIFFERENT_ACHIEVEMENT`**: Two distinct students or teams who participated in the exact same event (e.g. Smart India Hackathon) with distinct problem statements and outcomes.
- **`SAME_CATEGORY_DIFFERENT_ACHIEVEMENT`**: Achievements within the same category (e.g., two distinct research publications or sports tournaments) with overlapping domain vocabulary.

### Detailed Counts:
- **`PARAPHRASE_RESTRUCTURED`**: 39 pairs
- **`OFFICIAL_CITATION_VARIANT`**: 30 pairs
- **`RESUME_BULLET_VARIANT`**: 39 pairs
- **`CONCISE_SUMMARY_VARIANT`**: 42 pairs
- **`SAME_EVENT_DIFFERENT_ACHIEVEMENT`**: 74 pairs
- **`SAME_CATEGORY_DIFFERENT_ACHIEVEMENT`**: 76 pairs

---

## 4. Usage Guidelines for Member 2 & Threshold Evaluation

1. **Threshold Search:** Use `src/data/evaluate_similarity_thresholds.py` to evaluate cosine similarity thresholds across sentence transformer embeddings.
2. **Evaluation Protocol:**
   - **Hyperparameter/Threshold Tuning:** Train and tune cosine similarity cutoffs exclusively on the `validation` partition (46 pairs).
   - **Final Generalization Evaluation:** Evaluate the selected cutoff on the `test` partition (44 pairs) to produce unbiased precision, recall, and F1 metrics.
3. **Ground Truth:** The column `duplicate_label` represents the true binary label:
   - `1`: Identical underlying student achievement.
   - `0`: Distinct student achievements.
4. **No Target Leakage:**
   - `achievement_id_2` contains a `_V2` suffix in synthetic positive examples to identify provenance; do not use ID string patterns as classification features.
   - Pairs never cross split boundaries.

---
*Report archived in `reports/duplicate_pair_dataset_report.md`.*
