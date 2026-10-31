"""
src/nlp/export_step11_metrics_csv.py
Export per-tag metrics across subsets to a clean CSV report.
"""
import json
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
metrics_json = REPO_ROOT / "reports" / "step11_per_tag_metrics.json"

with open(metrics_json, "r", encoding="utf-8") as f:
    data = json.load(f)

per_tag = data["per_tag"]
rows = []

for subset_name, tags_dict in per_tag.items():
    for tag_name, m in tags_dict.items():
        rows.append({
            "subset": subset_name,
            "tag": tag_name,
            "canonical_name": m["name"],
            "support": m["support"],
            "neg_support": m["neg_support"],
            "tp": m["tp"],
            "fp": m["fp"],
            "fn": m["fn"],
            "tn": m["tn"],
            "precision": round(m["precision"], 4),
            "recall": round(m["recall"], 4),
            "f1": round(m["f1"], 4),
            "threshold": m["threshold"],
        })

df = pd.DataFrame(rows)
csv_path = REPO_ROOT / "reports" / "step11_per_tag_metrics.csv"
df.to_csv(csv_path, index=False)
print(f"Saved {len(df)} rows to {csv_path}")
