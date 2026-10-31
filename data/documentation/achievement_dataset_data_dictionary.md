# Achievement Classification Dataset — Data Dictionary
**AI-Powered Student Achievement Intelligence Platform**  
**Version:** 1.0.0  
**Artifact Path:** `data/processed/achievement_classification_dataset.csv`  

---

## 1. Schema Overview

The primary dataset schema consists of 26 structured attributes designed for NLP categorization, extraction evaluation, semantic embedding experiments, and duplicate resolution.

---

## 2. Field Definitions & Specification Table

| Column Name | Data Type | Nullable | Controlled Vocabulary / Format | Description & Example |
|---|---|---|---|---|
| `achievement_id` | String | No | Pattern `^ACH\d{6}$` | Unique, neutral record identifier with zero category leakage. *Example:* `ACH000142` |
| `achievement_text` | String | No | Natural Language ($\ge 35$ chars) | Original achievement narrative or certificate transcription. |
| `normalized_text` | String | No | Unicode NFC, stripped whitespace | Cleaned textual string used as primary model input. |
| `category` | String | No | 14 Primary Taxonomy Labels | Supervised learning target. *Values:* `HACKATHON`, `COMPETITION`, `RESEARCH_PUBLICATION`, `PATENT`, `INTERNSHIP`, `CERTIFICATION`, `PROJECT`, `WORKSHOP`, `CONFERENCE`, `LEADERSHIP`, `SPORTS`, `CULTURAL`, `VOLUNTEERING`, `OTHER`. |
| `domain` | String | No | Curated Technical & Academic Domains | Broad disciplinary field. *Example:* `Artificial Intelligence`, `Robotics & Autonomous Systems`. |
| `level` | String | No | 11 Controlled Levels | Scope of achievement. *Values:* `COLLEGE`, `UNIVERSITY`, `LOCAL`, `DISTRICT`, `STATE`, `NATIONAL`, `INTERNATIONAL`, `ORGANIZATIONAL`, `PROFESSIONAL`, `OTHER`, `UNKNOWN`. |
| `outcome` | String | No | 15 Controlled Outcomes | Result achieved. *Values:* `WINNER`, `FIRST_PLACE`, `SECOND_PLACE`, `THIRD_PLACE`, `FINALIST`, `PARTICIPATION`, `COMPLETION`, `PRESENTED`, `PUBLISHED`, `GRANTED`, `FILED`, `LEADERSHIP`, `RECOGNITION`, `OTHER`, `UNKNOWN`. |
| `event_name` | String | Yes | Realistic Program or Event Title | Name of competition, conference, hackathon, or program. *Example:* `Smart India Hackathon 2024`. |
| `organization` | String | Yes | Company, University, or Agency | Host or issuing entity. *Example:* `Siemens Technology India`, `VIT Vellore`. |
| `achievement_date` | String | Yes | ISO 8601 `YYYY-MM-DD` | Date of achievement or null if unknown. *Example:* `2024-03-15`. |
| `rank` | String | Yes | Discrete Rank or Position | Placement within event. *Example:* `1st Place`, `Runner-Up`, `None`. |
| `skills` | String | Yes | Pipe-delimited list of skill mentions | Extracted skill names. *Example:* `Python\|FastAPI\|Docker`. |
| `source_type` | String | No | 8 Controlled Source Types | Document origin type. *Values:* `CERTIFICATE`, `PROJECT_DESCRIPTION`, `PUBLICATION_METADATA`, `RESUME_TEXT`, `MANUAL_RECORD`, `SYNTHETIC_RECORD`, `PUBLIC_SOURCE`, `OTHER`. |
| `evidence_id` | String | Yes | Pattern `evd_[a-f0-9]{32}` or null | Pointer to underlying physical scan/PDF evidence. Null for synthetic records. |
| `source_id` | String | No | Provenance Source Identifier | Source batch tracker. *Example:* `SRC_SYNTHETIC_GEN_v1_seed42_20261025`. |
| `annotation_status` | String | No | 4 Controlled Statuses | Review level. *Values:* `AUTO_GENERATED`, `HUMAN_REVIEWED`, `NEEDS_REVIEW`, `REJECTED`. |
| `labeler_id` | String | No | Annotator Tracking String | Neutral annotator id. *Example:* `SYNTHETIC_GENERATION`. |
| `quality_status` | String | No | 3 Controlled Statuses | Automated validator result. *Values:* `VALIDATED`, `NEEDS_REVIEW`, `REJECTED`. |
| `record_origin` | String | No | `SYNTHETIC` or `REAL_SOURCE` | Explicit indication of whether the record is generated or real. |
| `generation_id` | String | No | Batch Identification Tag | Identifier of generation run. *Example:* `GEN_v1_seed42_20261025`. |
| `generation_method` | String | No | Strategy Identifier | Technique used. *Example:* `SCENARIO_BASED`. |
| `source_license` | String | No | License Information | Licensing status. *Example:* `SYNTHETIC_NO_LICENSE`. |
| `source_url` | String | Yes | URL or null | Public link for verified real sources (null for synthetic). |
| `source_access_date`| String | Yes | ISO 8601 `YYYY-MM-DD` or null | Verification date for real sources (null for synthetic). |
| `synthetic_status` | String | No | Explicit Indicator | Must be `EXPLICITLY_SYNTHETIC` for all synthetic records. |
| `validation_flags` | String | Yes | Pipe-delimited validation warning flags | Quality review flags, empty for fully validated rows. |

---

## 3. Strict Machine Learning Feature Governance

The following columns are **strictly prohibited** from being fed into classifiers:
- `achievement_id`
- `source_id`
- `generation_id`
- `annotation_status`
- `labeler_id`
- `quality_status`
- `record_origin`
- `generation_method`
- `synthetic_status`
- `validation_flags`

The **recommended primary input** for Member 2's model training is `normalized_text`.

---
*Data Dictionary archived under `data/documentation/achievement_dataset_data_dictionary.md`.*
