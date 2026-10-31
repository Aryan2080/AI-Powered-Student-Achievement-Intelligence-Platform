# Student Achievement Intelligence Platform — Dataset Directory

This directory hosts the primary datasets, metadata, schemas, split partitions, and annotation guidelines constructed for the **AI-Powered Student Achievement Intelligence Platform** (Member 1 scope).

---

## 1. Directory Structure

```text
data/
├── README.md                                    # This directory documentation
├── processed/
│   ├── achievement_classification_dataset.csv   # Primary CSV dataset (1,540 validated records)
│   └── achievement_classification_dataset.jsonl # JSON Lines version (1,540 JSON records)
├── schema/
│   └── achievement_classification_schema.json   # Formal JSON Schema specification
├── manifests/
│   └── achievement_classification_manifest.json # Generation manifest and version card
├── config/
│   └── synthetic_generation_config.json        # Reproducible generation hyperparameters
├── splits/
│   ├── train.csv                               # 70% stratified training split (1,078 records)
│   ├── validation.csv                          # 15% stratified validation split (224 records)
│   ├── test.csv                                # 15% stratified test split (238 records)
│   └── split_manifest.json                     # Split verification & zero-leakage manifest
├── annotations/
│   ├── achievement_taxonomy.json               # Full 14-class taxonomy definitions
│   ├── achievement_annotation_guide.md         # Annotation manual & boundary resolution guide
│   ├── canonical_skill_vocabulary.csv          # Controlled skill lexicon (45 skills + aliases)
│   ├── achievement_skill_annotations.csv       # Span-level skill annotations (1,769 spans)
│   ├── extraction_evaluation_samples.jsonl     # 75 structured OCR/IE test cases
│   └── achievement_duplicate_pairs.csv         # 300 labeled duplicate/non-duplicate pairs
└── documentation/
    └── achievement_dataset_data_dictionary.md  # Comprehensive data dictionary
```

---

## 2. Key Dataset Characteristics

- **Total Validated Records:** 1,540
- **Categories:** Exactly 14 primary classes (110 records per class, balanced 1:1)
- **Controlled Vocabularies:** 11 levels, 15 outcomes, 25+ academic/technical domains
- **Dataset Version:** `achievement_dataset_v1.0.0`
- **Random Seed:** 42 (fully deterministic and reproducible)
- **Provenance:** 100% explicitly synthetic (`record_origin = SYNTHETIC`)

---

## 3. How to Reproduce

Execute the following commands from the project root:

```bash
# 1. Generate the dataset and schema
python src/data/generate_achievement_dataset.py

# 2. Run data validation audit
python src/data/validate_achievement_dataset.py

# 3. Perform duplicate detection audit
python src/data/deduplicate_achievement_dataset.py

# 4. Create stratified train/val/test splits
python src/data/create_dataset_splits.py

# 5. Generate skill vocabulary and span annotations
python src/data/generate_skill_annotations.py

# 6. Generate OCR & extraction evaluation benchmark
python src/data/generate_extraction_samples.py

# 7. Generate duplicate-pair evaluation dataset
python src/data/generate_duplicate_pairs.py

# 8. Evaluate similarity thresholds
python src/data/evaluate_similarity_thresholds.py

# 9. Compute statistics and produce EDA report
python src/data/achievement_dataset_statistics.py
```

---

## 4. Governance & Limitations

1. **Synthetic Nature:** All records are synthetically constructed to avoid private student data exposure.
2. **Preliminary Benchmark:** This dataset is designed for pipeline engineering, baseline ML modeling, and threshold calibration. Real-world validation against genuine evidence will be conducted in subsequent phases.
3. **No Target Leakage:** Identifier columns (`achievement_id`, `source_id`, `generation_id`) must not be used as features during classification model training.
