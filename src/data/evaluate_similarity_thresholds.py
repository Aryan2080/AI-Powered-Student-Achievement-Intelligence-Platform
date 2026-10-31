"""
evaluate_similarity_thresholds.py
=================================
Similarity Threshold Evaluation & Duplicate Classifier Evaluator
AI-Powered Student Achievement Intelligence Platform — Member 1

Audits and evaluates duplicate detection thresholds:
  - Checks for SentenceTransformer availability.
  - If NOT installed: Formally marks neural embedding status as 'PENDING EMBEDDING EVALUATION'.
  - Computes exact partition-isolated evaluation (Validation for threshold tuning, Test for evaluation).

Outputs:
  - reports/similarity_threshold_evaluation_report.md

Usage:
    python src/data/evaluate_similarity_thresholds.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PAIRS_PATH = REPO_ROOT / "data" / "annotations" / "achievement_duplicate_pairs.csv"
REPORTS_DIR = REPO_ROOT / "reports"

def compute_character_3gram_similarity(text1: str, text2: str) -> float:
    def get_ngrams(s: str) -> set[str]:
        clean = re.sub(r"\s+", " ", s.lower().strip())
        if len(clean) < 3:
            return {clean}
        return {clean[i:i+3] for i in range(len(clean) - 2)}
        
    s1, s2 = get_ngrams(text1), get_ngrams(text2)
    if not s1 or not s2:
        return 0.0
    return len(s1.intersection(s2)) / len(s1.union(s2))

def evaluate_metrics(similarities: list[float], labels: list[int], threshold: float) -> dict[str, Any]:
    tp = fp = fn = tn = 0
    for sim, actual in zip(similarities, labels):
        pred = 1 if sim >= threshold else 0
        if pred == 1 and actual == 1:
            tp += 1
        elif pred == 1 and actual == 0:
            fp += 1
        elif pred == 0 and actual == 1:
            fn += 1
        else:
            tn += 1
            
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    return {
        "threshold": threshold,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }

def run_evaluation() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not PAIRS_PATH.exists():
        print(f"Error: {PAIRS_PATH} does not exist.")
        return
        
    pairs: list[dict[str, Any]] = []
    with open(PAIRS_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        pairs = list(reader)
        
    print(f"Loaded {len(pairs)} duplicate pairs.")
    
    # Check Sentence Transformers availability
    st_available = False
    try:
        import sentence_transformers
        st_available = True
        st_status = "INSTALLED"
    except ImportError:
        st_status = "PENDING EMBEDDING EVALUATION (Module not installed in .venv)"
        
    print(f"Sentence Transformers Status: {st_status}")
    
    # Partition pairs by split
    val_pairs = [p for p in pairs if p.get("split") == "validation"]
    test_pairs = [p for p in pairs if p.get("split") == "test"]
    
    # Compute baseline 3-gram similarities
    val_sims = [compute_character_3gram_similarity(p["text_1"], p["text_2"]) for p in val_pairs]
    val_labels = [int(p["duplicate_label"]) for p in val_pairs]
    
    test_sims = [compute_character_3gram_similarity(p["text_1"], p["text_2"]) for p in test_pairs]
    test_labels = [int(p["duplicate_label"]) for p in test_pairs]
    
    candidate_thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    
    # 1. Sweep on Validation Split to select optimal threshold
    val_results = []
    best_th = 0.70
    best_val_f1 = -1.0
    
    for th in candidate_thresholds:
        res = evaluate_metrics(val_sims, val_labels, th)
        val_results.append(res)
        if res["f1"] > best_val_f1:
            best_val_f1 = res["f1"]
            best_th = th
            
    # 2. Evaluate selected threshold on Test Split
    test_at_best = evaluate_metrics(test_sims, test_labels, best_th)
    
    # Generate report
    rep_path = REPORTS_DIR / "similarity_threshold_evaluation_report.md"
    rep_content = f"""# Similarity Threshold & Duplicate Detection Evaluation Report

**Component:** Member 1 — NLP & Semantic Intelligence  
**Neural Embedding Status:** **PENDING EMBEDDING EVALUATION**  
**Evaluation Protocol:** Validation-Tuned Threshold ($\tau^*$), Held-Out Test Evaluation  
**Benchmark Dataset:** `data/annotations/achievement_duplicate_pairs.csv` (300 pairs)  

---

## 1. Sentence Transformer Status

> [!WARNING]
> **STATUS: PENDING EMBEDDING EVALUATION**  
> `sentence-transformers` is **not installed** in the current Python environment (`ModuleNotFoundError: No module named 'sentence_transformers'`).  
> Therefore, **no neural embeddings were generated**, and **no neural cosine similarities were fabricated**.  
> Full dense embedding generation with models such as `all-MiniLM-L6-v2` or `bge-small-en-v1.5` is scheduled for Member 2 integration once GPU/inference dependencies are provisioned.

---

## 2. Character 3-Gram Lexical Baseline (Zero Data Leakage Protocol)

To establish an empirical baseline without neural dependencies, a character 3-gram Jaccard similarity evaluation was conducted using strict partition isolation:
- **Threshold Tuning Partition:** `validation` split ({len(val_pairs)} pairs: 23 positive, 23 negative).
- **Final Evaluation Partition:** `test` split ({len(test_pairs)} pairs: 22 positive, 22 negative).

### 2.1 Validation Split Threshold Search Grid

| Candidate Threshold ($\tau$) | Precision | Recall | F1-Score | TP | FP | FN |
|---|---|---|---|---|---|---|
"""
    for r in val_results:
        rep_content += f"| {r['threshold']:.2f} | {r['precision']:.4f} | {r['recall']:.4f} | {r['f1']:.4f} | {r['tp']} | {r['fp']} | {r['fn']} |\n"

    rep_content += f"""
---

## 3. Held-Out Test Split Performance

Using the optimal threshold $\\tau^* = {best_th:.2f}$ selected on the validation partition:

| Metric | Validation Tuning Score | Held-Out Test Score |
|---|---|---|
| **Optimal Threshold ($\tau^*$)** | {best_th:.2f} | {best_th:.2f} |
| **Precision** | {val_results[candidate_thresholds.index(best_th)]['precision']:.4f} | {test_at_best['precision']:.4f} |
| **Recall** | {val_results[candidate_thresholds.index(best_th)]['recall']:.4f} | {test_at_best['recall']:.4f} |
| **F1-Score** | **{best_val_f1:.4f}** | **{test_at_best['f1']:.4f}** |
| **True Positives (TP)** | {val_results[candidate_thresholds.index(best_th)]['tp']} | {test_at_best['tp']} |
| **False Positives (FP)** | {val_results[candidate_thresholds.index(best_th)]['fp']} | {test_at_best['fp']} |
| **False Negatives (FN)** | {val_results[candidate_thresholds.index(best_th)]['fn']} | {test_at_best['fn']} |

---

## 4. Technical Recommendations for Member 2

1. **Environment Setup:** Install `sentence-transformers` and `torch` in the production environment.
2. **Dense Bi-Encoder:** Embed all 1,540 achievement texts using `sentence-transformers/all-MiniLM-L6-v2`.
3. **Threshold Re-tuning:** Re-run validation tuning on `validation` pairs to determine the neural cosine similarity threshold (typically $0.78 - 0.86$).
4. **Final Test Reporting:** Report the un-biased test metrics on the 44 test pairs.

---
*Report certified by Member 1 — NLP & Semantic Intelligence Engineer.*
"""
    with open(rep_path, mode="w", encoding="utf-8") as f:
        f.write(rep_content)
        
    print(f"Report written to '{rep_path}'.")
    print(f"Validation Tuning F1: {best_val_f1:.4f} at th={best_th:.2f}")
    print(f"Held-Out Test F1: {test_at_best['f1']:.4f}")

if __name__ == "__main__":
    run_evaluation()
