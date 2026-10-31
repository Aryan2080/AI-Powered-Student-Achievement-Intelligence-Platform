# Downstream Preprocessing Handoff Specification for Member 2
## AI-Powered Student Achievement Intelligence Platform
**From:** Member 1 — NLP & Semantic Intelligence Engineer  
**To:** Member 2 — Machine Learning & Predictive Modeling Engineer  
**Dataset Release:** `achievement_dataset_v1.0.1`  
**Core Module:** [`src.nlp.text_preprocessing`](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/src/nlp/text_preprocessing.py)  
**Status:** Certified & Production Ready (Audited)  

---

## 1. Executive Summary & Purpose

This handoff contract establishes the exact preprocessing interfaces, verified dataset disk paths, canonical vocabulary contracts, and anti-leakage protocols for downstream modeling workflows. All functions are implemented in [`src/nlp/text_preprocessing.py`](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/src/nlp/text_preprocessing.py), backed by 20 unit tests in [`tests/test_text_preprocessing.py`](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/tests/test_text_preprocessing.py), and demonstrated across 6 executable notebooks in [`notebooks/`](file:///C:/Users/Balaji/OneDrive/Desktop/SUPERVISED%20PROJECT/AI-Powered-Student-Achievement-Intelligence-Platform/notebooks/).

---

## 2. Verified Canonical Dataset Paths on Disk

All downstream models must load datasets from the verified disk locations registered in `data/manifests/achievement_classification_manifest.json`:

```python
# Primary Master Datasets (1,540 records, 14 categories)
PRIMARY_CSV   = "data/processed/achievement_classification_dataset.csv"
PRIMARY_JSONL = "data/processed/achievement_classification_dataset.jsonl"

# Disjoint Stratified Split Partitions
TRAIN_CSV = "data/splits/train.csv"       # 1,078 records (70.00%)
VAL_CSV   = "data/splits/validation.csv"  #   231 records (15.00%)
TEST_CSV  = "data/splits/test.csv"        #   231 records (15.00%)

# Pre-computed Sentence Transformer Embeddings (all-MiniLM-L6-v2, 384 dimensions)
ALL_EMBEDDINGS_NPY = "data/embeddings/achievement_dataset_v1.0.1/achievement_embeddings_all_MiniLM_L6_v2.npy" # (1540, 384)
TRAIN_EMBEDDINGS   = "data/embeddings/achievement_dataset_v1.0.1/train_embeddings.npy"                        # (1078, 384)
VAL_EMBEDDINGS     = "data/embeddings/achievement_dataset_v1.0.1/validation_embeddings.npy"                   # (231, 384)
TEST_EMBEDDINGS    = "data/embeddings/achievement_dataset_v1.0.1/test_embeddings.npy"                         # (231, 384)
EMBEDDING_IDS_JSON = "data/embeddings/achievement_dataset_v1.0.1/achievement_embeddings_all_MiniLM_L6_v2_record_ids.json"
EMBEDDING_META_JSON= "data/embeddings/achievement_dataset_v1.0.1/achievement_embeddings_all_MiniLM_L6_v2_metadata.json"

# Annotation & Vocabulary Assets
SKILL_VOCAB_CSV  = "data/annotations/canonical_skill_vocabulary.csv"    # 116 canonical skills
SKILL_ANN_CSV    = "data/annotations/achievement_skill_annotations.csv" # 2,105 labeled mentions
DUPLICATE_PAIRS  = "data/annotations/achievement_duplicate_pairs.csv"   # 300 labeled pairs
```

---

## 3. Quick-Start Import Guide

```python
from src.nlp.text_preprocessing import (
    normalize_text_for_classification,
    prepare_text_for_skill_extraction,
    prepare_text_for_sentence_transformer,
    prepare_text_for_duplicate_detection,
    preprocess_dataframe,
    tokenize_words,
)
```

---

## 4. Task-Specific API Reference & Usage Contracts

### 4.1 Task 1: Achievement Classification (14 Categories)
Evaluated and certified on **AchievementClassifier** (TF-IDF + LogisticRegression) achieving **1.0000 Macro F1** on held-out test data:

```python
from src.nlp.classification import AchievementClassifier

# 1. Option A: Load pre-trained certified production classifier (Recommended)
classifier = AchievementClassifier.load("models/achievement_classifier_v1.0.1.joblib")

# 2. Single record prediction with calibrated probability distribution
text = "Won first place in national robotics competition designing autonomous drone hardware."
result = classifier.predict_record(text)

print(result.predicted_category) # 'COMPETITION'
print(result.confidence)         # 0.9421
print(result.category_scores)    # Full probability distribution across 14 categories

# 3. High-throughput batch inference over DataFrames (17,500 records/sec on CPU)
batch_results = classifier.predict_batch(train_df)
# Output: List[ClassificationResult]
```

> **CRITICAL DIRECTIVES:**  
> 1. **Do NOT remove stopwords or apply heuristic stemming:** Benchmarks show stopword removal discards critical ranking tokens (*first*, *second*, *top*) without accuracy gain, while stemming corrupts domain vocabulary.
> 2. **Inference Latency:** `AchievementClassifier` operates at **0.057 ms/record** with zero neural dependency overhead. It is the designated primary engine for multi-class categorization.

---

### 4.2 Task 2: Skill Extraction & Canonical Normalization
For token extraction, span labeling, and mapping into the 116 canonical skill vocabulary:

```python
from src.nlp.skill_normalization import CanonicalSkillVocabulary, SkillNormalizer

# 1. Initialize vocabulary and normalizer
vocab = CanonicalSkillVocabulary("data/annotations/canonical_skill_vocabulary.csv")
normalizer = SkillNormalizer(vocab, fuzzy_threshold=0.88, min_fuzzy_len=5)

# 2. Extract and normalize skills from achievement text
text = "Engineered microservices using Python and containerized with Docker for Kubernetes deployment."
normalized_skills = normalizer.extract_and_normalize(text)

for s in normalized_skills:
    print(f"Mention: {s.mention.mention_text} -> Canonical: {s.canonical_skill} (Domain: {s.skill_domain}, Status: {s.normalization_status.value})")
    # Exact verbatim offset invariant:
    assert text[s.mention.start_offset : s.mention.end_offset] == s.mention.mention_text

# 3. Direct mention normalization
res = normalizer.normalize_mention("golang")
print(res.canonical_skill)            # 'Go'
print(res.normalization_status.value) # 'ALIAS_MATCH'
```

> **CRITICAL DIRECTIVES:**  
> 1. **Do NOT lowercase or strip text before mention extraction:** Verbatim offsets in `data/annotations/achievement_skill_annotations.csv` depend 100% on raw character offsets.
> 2. **Explicit Ambiguity Guard:** The surface term `scrum` maps to both `Scrum` and `Agile Project Management`. The normalizer prudently flags this as `NormalizationStatus.AMBIGUOUS` (confidence 0.50). Do not force arbitrary canonical assignments for ambiguous terms.

---

### 4.3 Task 3: Sentence Transformers & Dense Semantic Retrieval
For embedding generation, semantic representation, and downstream clustering:

```python
from src.nlp.embedding import (
    load_embedding_model,
    generate_embeddings,
    load_embedding_bundle,
    compute_similarity_matrix,
    search_similar_achievements,
)

# 1. Option A: Load pre-computed, certified embeddings directly from disk (Recommended)
embeddings, record_ids, metadata = load_embedding_bundle(
    "data/embeddings/achievement_dataset_v1.0.1",
    model_name="all-MiniLM-L6-v2"
)
# embeddings.shape == (1540, 384), float32, unit L2-normalized

# 2. Option B: Generate new embeddings on new text queries
model = load_embedding_model("sentence-transformers/all-MiniLM-L6-v2")
query_embedding = generate_embeddings(["Won 1st place in national machine learning hackathon"], model=model)

# 3. Dense Neural Retrieval (Top-5 matches across 1,540 achievements)
results = search_similar_achievements(
    query_embedding=query_embedding[0],
    corpus_embeddings=embeddings,
    corpus_metadata=train_df.to_dict(orient="records"),
    top_k=5,
)
```

> **CERTIFIED TOKEN BUDGET & TRUNCATION SAFETY:**  
> Verified via `AutoTokenizer`: corpus minimum is 24 tokens, median is 46.0 tokens, and maximum is 81 tokens (< 128 max capacity). Truncation risk is **0.00% across all 1,540 achievement records**. Embeddings are $\ell_2$-normalized (`float32`). Pre-split embeddings are also saved directly as `train_embeddings.npy` (1078, 384), `validation_embeddings.npy` (231, 384), and `test_embeddings.npy` (231, 384).

---

### 4.4 Task 4: Advanced Duplicate Detection & Structured Verification
For high-precision de-duplication combining dense semantic candidate retrieval with structured evidence verification:

```python
from src.nlp.duplicate_detection import (
    DuplicateDecision,
    verify_duplicate_candidate,
    batch_verify_duplicate_pairs,
)

# 1. Single Candidate Pair Verification
result = verify_duplicate_candidate(
    record_1={
        "achievement_id": "ACH-001",
        "achievement_text": "Won 1st place in National AI Hackathon 2023.",
        "event_name": "National AI Hackathon",
        "rank": "1st Place",
        "achievement_date": "2023-11-15",
    },
    record_2={
        "achievement_id": "ACH-002",
        "achievement_text": "Won 1st place in National AI Hackathon 2023.",
        "event_name": "National AI Hackathon",
        "rank": "1st Place",
        "achievement_date": "2023-11-15",
    },
    cosine_similarity=0.88,
    retrieval_threshold=0.50,
    high_similarity_threshold=0.70,
)

print(result.decision)      # DuplicateDecision.DUPLICATE
print(result.confidence)    # 0.88
print(result.explanation)   # Detailed evidence rationale

# 2. Batch Verification Over DataFrames
batch_results = batch_verify_duplicate_pairs(
    pairs_df=candidate_pairs_df,
    main_dataset_df=full_dataset_df,
    cosine_similarities=computed_cosine_sims,
    retrieval_threshold=0.50,
)
```

> **CRITICAL DIRECTIVE (DO NOT USE COSINE SIMILARITY ALONE):**  
> Benchmarks show that dense Sentence Transformer similarity alone produces **12 false positives** on held-out test data because distinct achievements at the same event share ~0.61 cosine similarity. Always use the combined multi-stage pipeline (`verify_duplicate_candidate`), which eliminates 100% of false positives (Precision: 1.0000, F1: 0.9000). Always route `DuplicateDecision.REVIEW_REQUIRED` records to an administrative triage queue rather than merging destructively.

---

### 4.5 Task 5: Evidence Document Ingestion, PDF Text Extraction & OCR
For ingesting student achievement evidence files (certificates, transcripts, badges, awards, scanned letters):

```python
from src.nlp.document_ingestion import (
    DocumentFormat,
    ExtractionMethod,
    ExtractionStatus,
    ingest_document,
    batch_ingest_documents,
)

# 1. Single Document Ingestion
doc_result = ingest_document("data/evidence/student_certificate.pdf")

print(doc_result.document_id)               # e.g., 'DOC-A81B92C4'
print(doc_result.file_type)                 # DocumentFormat.PDF
print(doc_result.overall_status)            # ExtractionStatus.SUCCESS
print(doc_result.primary_extraction_method) # ExtractionMethod.NATIVE_PDF
print(doc_result.total_pages)               # 1
print(doc_result.full_normalized_text)      # Normalized text ready for classification
print(doc_result.is_scanned)                # False

# 2. Accessing Page-Level Provenance
for page in doc_result.pages:
    print(f"Page {page.page_number}: {page.word_count} words, Method: {page.extraction_method.value}")

# 3. Batch Document Ingestion
results = batch_ingest_documents([
    "path/to/cert1.pdf",
    "path/to/badge.png",
    "path/to/award.jpg",
])
```

> **CRITICAL DIRECTIVES:**  
> 1. **Native Stream First:** The ingestion pipeline automatically attempts fast native PDF text parsing first (0.7–0.9 ms/page). OCR fallback is invoked automatically ONLY when pages are scanned or image-only (`is_scanned=True`).
> 2. **Graceful Handling of Missing OCR:** If Tesseract is not installed on the system, image-based documents return `ExtractionStatus.OCR_UNAVAILABLE` with non-fatal diagnostic warnings instead of raising unhandled exceptions.
> 3. **Downstream Integration:** The transcribed `full_normalized_text` is pre-aligned with `clean_text` / `normalize_text_for_classification` and should be passed directly into `AchievementClassifier.predict_record()` and `SkillNormalizer.extract_and_normalize()`.

---

### 4.6 Task 6: Structured Information Extraction from Evidence Text
For parsing transcribed evidence documents into validated, schema-aligned achievement records:

```python
from src.nlp.document_ingestion import ingest_document
from src.nlp.information_extraction import (
    ConfidenceStatus,
    ExtractionSource,
    ExtractedField,
    StructuredEvidenceExtraction,
    extract_information_from_document,
    extract_information_from_text,
    get_default_extractor,
)

# 1. End-to-End Ingestion & Information Extraction
doc_result = ingest_document("data/evidence/student_certificate.pdf")
extraction = extract_information_from_document(doc_result)

# 2. Accessing Audited Fields with Provenance
print(extraction.student_name.value)         # 'Alex Rivera'
print(extraction.student_name.confidence)    # 0.90
print(extraction.student_name.source_span)   # (36, 47)
print(extraction.achievement_title.value)    # 'National Collegiate Hackathon 2024'
print(extraction.organization.value)         # 'Association for Computing Machinery'
print(extraction.rank.value)                 # '1st Place'
print(extraction.level.value)                # 'NATIONAL'
print(extraction.outcome.value)              # 'WINNER'
print(extraction.issue_date.value)           # '2024-10-15'
print(extraction.certificate_id.value)       # 'CERT-ACH-2024-9981'
print(extraction.category.value)             # 'HACKATHON'
print(extraction.skills.value)               # ['Python', 'Docker', 'Machine Learning']

# 3. Triage & Administrative Review Routing
if extraction.review_required:
    print("Action Required: Route to Administrative Review Queue!")
    print(f"Reasons: {extraction.review_reasons}")
    # Examples: Missing title, missing organization, ambiguous date, or degraded OCR

# 4. JSON Serialization
serialized_dict = extraction.to_dict()
```

> **CRITICAL DIRECTIVES:**  
> 1. **No Hallucination Policy:** Fields not present in evidence text receive explicit `ConfidenceStatus.MISSING` with `value=None`. Downstream pipelines must never infer missing names, dates, or certificate IDs without administrative review.
> 2. **Triage Flags:** Always check `extraction.review_required`. When True, route the submission to a human review queue rather than executing automated record promotion.
> 3. **Downstream Integration:** Extracted entities directly map into `AchievementClassificationRecord` fields (`achievement_text`, `event_name`, `organization`, `achievement_date`, `rank`, `level`, `outcome`, `category`, `skills`).

---

### 4.7 Task 7: End-to-End NLP Pipeline Integration & Robustness Orchestration
For end-to-end evidence processing uniting ingestion, information extraction, multi-class categorization, canonical skill normalization, and triage routing:

```python
from src.nlp.pipeline import (
    NLPEvidencePipeline,
    PipelineProcessingResult,
    get_nlp_pipeline,
    process_evidence_document,
)

# 1. Initialize shared singleton pipeline (models loaded once into memory)
pipeline = get_nlp_pipeline()

# 2. Process an evidence document (supports PDF, PNG, JPEG, raw text, or bytes)
result: PipelineProcessingResult = pipeline.process_document(
    "data/evidence/student_certificate.pdf"
)

# 3. Inspect Processed Result & Status
print(f"Document ID:             {result.document_id}")
print(f"Overall Status:          {result.status}")           # 'SUCCESS', 'REVIEW_REQUIRED', 'FAILED'
print(f"Review Required Flag:    {result.review_required}")  # True if degraded or incomplete
print(f"Review Reasons:          {result.review_reasons}")   # Explanations for triage routing
print(f"System Warnings:         {result.warnings}")

# 4. Access Ingestion Provenance
print(f"File Format:             {result.ingestion_summary['file_type']}")
print(f"Total Pages:             {result.ingestion_summary['total_pages']}")
print(f"Extraction Method:       {result.ingestion_summary['primary_extraction_method']}")

# 5. Access Audited Structured Entities & Character Spans
entities = result.extracted_entities
print(f"Student Name:            {entities['student_name']['value']} {entities['student_name']['source_span']}")
print(f"Achievement Title:       {entities['achievement_title']['value']} {entities['achievement_title']['source_span']}")
print(f"Organization:            {entities['organization']['value']} {entities['organization']['source_span']}")
print(f"Rank / Standing:         {entities['rank']['value']}")
print(f"Outcome Status:          {entities['outcome']['value']}")
print(f"Issue / Event Date:      {entities['issue_date']['value']}")

# 6. Access Calibrated Multi-Class Categorization
print(f"Predicted Category:      {result.classification['predicted_category']}")
print(f"Calibrated Confidence:   {result.classification['confidence']}")
print(f"Probability Distribution:{result.classification['category_scores']}")

# 7. Access Normalized Canonical Skills
for skill in result.skills:
    print(f"Skill: {skill['canonical_name']} (ID: {skill['skill_id']}, Domain: {skill['skill_domain']})")

# 8. Lossless JSON Serialization
json_payload = result.to_json(indent=2)
```

> **CRITICAL DIRECTIVES:**  
> 1. **Confidence Semantics Distinction:**
>    - `result.field_confidence`: Heuristic score reflecting lexical cue certainty and span match quality.
>    - `result.classification_confidence`: Calibrated empirical posterior probability from multi-class Logistic Regression (`predict_proba`).
>    - Downstream consumers must never conflate heuristic field confidence with statistical class posterior probability.
> 2. **Date Semantics Policy:**
>    - Event execution dates (`held on`, `conducted on`) and formal issuance dates (`issued on`, `dated`) are distinguished in provenance.
>    - Contradictory dates for the same event timeline automatically trigger `result.review_required = True`.
> 3. **Triage Gatekeeping:**
>    - Automated ingestion must inspect `result.status == "SUCCESS"` and `result.review_required is False` before committing achievement records to primary datastores.
>    - All flagged records must be dispatched to the administrative audit queue with `result.review_reasons`.

---

### 4.8 Task 8: Multi-Label Domain Categorization & Taxonomy Orthogonality
For predicting zero or more technical and academic domain tags independently of the single-label primary category:

```python
from src.nlp.categorization import (
    DOMAIN_TAGS,
    DOMAIN_TAG_NAMES,
    AchievementCategorizer,
    CategorizationResult,
)
from src.nlp.pipeline import get_nlp_pipeline

# 1. Standalone Multi-Label Categorizer
categorizer = AchievementCategorizer.load("models/achievement_categorizer_v1.0.1.joblib")

achievement_text = (
    "Developed a real-time computer vision system for traffic analytics using YOLOv8 "
    "and deep learning algorithms, deployed on AWS with RESTful microservices."
)
cat_result: CategorizationResult = categorizer.predict_record(achievement_text)

print(cat_result.predicted_tags)  # ['lbl_domain_ai', 'lbl_domain_cv', 'lbl_domain_ml', 'lbl_domain_systems', 'lbl_domain_web']
print(cat_result.tag_scores)      # e.g., {'lbl_domain_ai': 0.842, 'lbl_domain_cv': 0.791, ...}
print(cat_result.thresholds)      # Validation-calibrated decision thresholds Tk in [0.25, 0.625]

# 2. Unified End-to-End Pipeline Integration
pipeline = get_nlp_pipeline()
pipeline_result = pipeline.process_text(achievement_text, document_id="DEMO-001")

# Single-Label Primary Classification (Form of Achievement)
print(pipeline_result.classification["predicted_category"])  # e.g., 'PROJECT' (1-of-14 classes)

# Multi-Label Domain Tags (Technical Disciplines Involved)
print(pipeline_result.domain_tags)                           # ['lbl_domain_ai', 'lbl_domain_cv', ...]
print(pipeline_result.categorization["tag_scores"])          # Probability distributions per domain tag
```

> **CRITICAL DIRECTIVES FOR MEMBER 2:**  
> 1. **Strict Taxonomy Orthogonality:**
>    - Primary category (`result.classification['predicted_category']`) answers *"What form did this achievement take?"* (e.g. `CERTIFICATION`, `HACKATHON`, `INTERNSHIP`).
>    - Domain tags (`result.domain_tags`) answer *"What technical/academic disciplines were demonstrated?"* (e.g. `lbl_domain_ai`, `lbl_domain_web`, `lbl_domain_systems`).
>    - Never collapse multi-label domain tags into single-label classification or vice versa.
> 2. **Zero-Tag Handling & Rejection:**
>    - Non-technical or ambiguous achievements (such as fine arts, sports, or student governance) may receive **zero** domain tags.
>    - Never force-assign `lbl_domain_other` unless the text explicitly reflects non-computing disciplines. If all tag probabilities are below calibrated thresholds, preserve an empty tag list `[]`.
> 3. **Database Schema Integration:**
>    - Recommend relational junction table `achievement_domain_tags` with `(achievement_id, domain_tag, confidence)` for efficient filtering and indexing.
>    - Alternatively, store as PostgreSQL native array `VARCHAR(50)[]` or `JSONB` in the primary achievements table.

---

## 5. Immutable DataFrame Batch Processing

To transform entire pandas DataFrames safely without mutating source objects:

```python
from src.nlp.text_preprocessing import preprocess_dataframe

# Returns a fresh DataFrame copy with the new column
processed_df = preprocess_dataframe(
    df=train_df,
    text_column="achievement_text",
    task="classification",          # options: "classification", "skill_extraction", "sentence_transformer", "duplicate_detection"
    output_column="processed_text"
)
```

---

## 6. Verification Checklist for Member 2

Before deploying or training models on Member 2's branch:

- [x] Verify that training, validation, and test splits match exact record counts:
  - `train.csv`: 1,078 records
  - `validation.csv`: 231 records
  - `test.csv`: 231 records
- [x] Vectorizers must be fitted ONLY on `train.csv`.
- [x] Target labels (`category`) map to the 14 standard classes.
- [x] Skill extraction spans must use verbatim text from `prepare_text_for_skill_extraction`.
- [x] Canonical skill vocabulary references `data/annotations/canonical_skill_vocabulary.csv` (116 canonical skills).
- [x] Embeddings should preserve casing via `prepare_text_for_sentence_transformer`.
- [x] Duplicate detection must retain numeric tokens via `prepare_text_for_duplicate_detection`.
- [x] Multi-label domain categorization dataset matches frozen master records:
  - `data/processed/achievement_categorization_dataset.csv`: 1,540 records, 21 columns
  - `data/splits/categorization_{train,validation,test}.csv`: 1,078 / 231 / 231 records (zero ID leakage)
  - `data/annotations/categorization_reviewed_reference_samples.jsonl`: 45 audited gold reference samples
- [x] Multi-label categorizer model bundle present at `models/achievement_categorizer_v1.0.1.joblib` and companion `.json` metadata.
- [x] Unified pipeline exposes `domain_tags` and `categorization` without breaking backward compatibility.
