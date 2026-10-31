"""
src/nlp/audit_provenance_deep.py
Inspect the exact derivation sources in achievement_categorization_dataset.jsonl
"""
import json
from pathlib import Path
from collections import defaultdict
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
jsonl_path = REPO_ROOT / "data" / "processed" / "achievement_categorization_dataset.jsonl"

records = []
with open(jsonl_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

print(f"Loaded {len(records)} records from {jsonl_path.name}")
first_rec = records[0]
print("\nFirst record keys:", list(first_rec.keys()))
print("First record domain_tags:", first_rec.get("domain_tags"), type(first_rec.get("domain_tags")))
print("First record derivation_sources:", first_rec.get("derivation_sources"), type(first_rec.get("derivation_sources")))

# Detailed tag derivation inspection
tag_provenance = defaultdict(lambda: {"total": 0, "source_domain": 0, "skill": 0, "text_cue": 0, "source_domain_only": 0, "skill_only": 0, "text_cue_only": 0, "multi_source": 0})

for r in records:
    # Tags can be in domain_tags (pipe-separated string or list)
    tags = r.get("domain_tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split("|") if t.strip()]
    elif not isinstance(tags, list):
        tags = []

    derivations = r.get("derivation_sources", {})
    if isinstance(derivations, str):
        try:
            derivations = json.loads(derivations)
        except:
            derivations = {}

    for t in tags:
        tag_provenance[t]["total"] += 1
        srcs = derivations.get(t, [])
        if isinstance(srcs, str):
            srcs = [srcs]

        has_sd = any("source_domain" in s for s in srcs)
        has_sk = any("skill" in s for s in srcs)
        has_tc = any("text_cue" in s for s in srcs)

        if has_sd:
            tag_provenance[t]["source_domain"] += 1
        if has_sk:
            tag_provenance[t]["skill"] += 1
        if has_tc:
            tag_provenance[t]["text_cue"] += 1

        active_count = int(has_sd) + int(has_sk) + int(has_tc)
        if active_count > 1:
            tag_provenance[t]["multi_source"] += 1
        elif has_sd:
            tag_provenance[t]["source_domain_only"] += 1
        elif has_sk:
            tag_provenance[t]["skill_only"] += 1
        elif has_tc:
            tag_provenance[t]["text_cue_only"] += 1

df_res = pd.DataFrame.from_dict(tag_provenance, orient="index")
print("\n=== COMPLETE DERIVATION PROVENANCE PER TAG ===")
print(df_res.to_string())

# Save to file
out_p = REPO_ROOT / "reports" / "step11_provenance_table.json"
df_res.to_json(out_p, indent=2, orient="index")
print(f"\n[OK] Saved to {out_p}")
