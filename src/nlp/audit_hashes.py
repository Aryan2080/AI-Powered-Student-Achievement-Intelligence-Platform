"""
src/nlp/audit_hashes.py
Compute SHA-256 hashes for exact audited files.
"""
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

files_to_hash = [
    "data/processed/achievement_classification_dataset.csv",
    "data/processed/achievement_categorization_dataset.csv",
    "data/processed/achievement_categorization_dataset.jsonl",
    "data/splits/train.csv",
    "data/splits/validation.csv",
    "data/splits/test.csv",
    "data/splits/categorization_train.csv",
    "data/splits/categorization_validation.csv",
    "data/splits/categorization_test.csv",
    "data/annotations/categorization_reviewed_reference_samples.jsonl",
    "models/achievement_categorizer_v1.0.1.joblib",
    "models/achievement_classifier_v1.0.1.joblib",
]

results = {}
for rel_path in files_to_hash:
    full_path = REPO_ROOT / rel_path
    if not full_path.exists():
        results[rel_path] = "FILE_NOT_FOUND"
        continue
    h = hashlib.sha256()
    with open(full_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    results[rel_path] = {
        "sha256": h.hexdigest(),
        "size_bytes": full_path.stat().st_size,
    }

print(json.dumps(results, indent=2))
