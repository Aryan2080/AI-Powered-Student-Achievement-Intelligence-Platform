# Human Domain Categorization Review Checklist & Protocol (Step 14)

**Project:** AI-Powered Student Achievement Intelligence Platform  
**Target File:** `data/annotations/domain_categorization_annotation_task.csv`  
**Taxonomy Guide:** `data/annotations/domain_categorization_annotation_guide.md`  
**Role:** Domain Annotators (Annotator A & Annotator B) & Lead Adjudicator

---

## 1. Quick Reference: 10 Domain Tags Taxonomy

Annotators must only assign tags from this standardized 10-tag taxonomy:

| Domain Tag Identifier | Canonical Name | Primary Indicators & Trigger Keywords | Negative Exclusions |
|:---|:---|:---|:---|
| `lbl_domain_ai` | Artificial Intelligence | High-level AI concepts, search, autonomous agents, heuristics, LLM prompts | Pure statistical analysis without AI |
| `lbl_domain_ml` | Machine Learning | Deep learning, neural networks, PyTorch, TensorFlow, Scikit-learn, XGBoost | Standard software engineering |
| `lbl_domain_nlp` | Natural Language Processing | Text classification, transformers, BERT, LLMs, tokenization, translation, summarization | Speech audio hardware alone |
| `lbl_domain_cv` | Computer Vision | Image processing, CNNs, YOLO, OpenCV, object detection, segmentation | Standard web graphics/UI |
| `lbl_domain_security` | Cybersecurity & Privacy | Network security, ethical hacking, cryptography, penetration testing, IAM, SIEM, SOC | Standard bug fixing |
| `lbl_domain_systems` | Systems, Cloud & DevOps | Distributed systems, AWS, GCP, Azure, Docker, Kubernetes, Linux, microservices | Static single-page HTML |
| `lbl_domain_web` | Web & Mobile Development | Frontend (React, Angular), backend (FastAPI, Node.js, Django), mobile (Flutter, iOS, Android), REST APIs | Backend CLI algorithms without web |
| `lbl_domain_data` | Data Engineering & Analytics | SQL, ETL pipelines, Apache Spark, Kafka, BigQuery, data warehousing, Pandas | Basic spreadsheet data entry |
| `lbl_domain_hardware` | Hardware & Embedded Systems | Microcontrollers (Arduino, ESP32, Raspberry Pi), FPGA, Verilog, VHDL, PCB design, sensors | Pure simulation software without hardware |
| `lbl_domain_other` | Non-Computing Domain | Performing arts, athletics, sports, debate, fine arts, music competitions | Technical computing achievements |

---

## 2. Annotator Instructions (Blind Review Phase)

### Golden Rules
1. **Blind Review:** You must annotate based strictly on the text provided in `achievement_text`. Never look at model predictions or heuristic hints.
2. **Independent Work:** Annotator A must only edit columns A-D for their role; Annotator B must only edit columns B-D for their role. Never discuss cases during blind annotation.
3. **Multi-Tag Syntax:** Separate multiple tags with a pipe symbol `|` without spaces.
   - Example: `lbl_domain_ai|lbl_domain_ml|lbl_domain_cv`
4. **Zero-Tag Policy (Crucial):**
   - For genuine non-computing achievements (athletics, student governance, debate tournaments, cultural competitions, social service), enter **`NONE`** in the tag column.
   - **Do NOT leave the cell blank** if you reviewed it and found zero technical computing tags. Blank represents an unreviewed record!
5. **Uncertainty Flagging:**
   - If the text is vague, ambiguous, or lacks sufficient technical details to decide confidently:
     - Set `annotator_a_uncertain = TRUE` (or `annotator_b_uncertain = TRUE`).
     - Enter an explanatory note in `annotator_a_notes`.
     - The system will automatically route this record to the Lead Adjudicator queue even if both annotators assign the same tags.
6. **Completion Status:**
   - When finished reviewing a record, change `annotator_a_status` from `PENDING` to `COMPLETED`.

---

## 3. Spreadsheet Column Guide (`domain_categorization_annotation_task.csv`)

| Column Name | Editor | Description / Permitted Values |
|:---|:---:|:---|
| `achievement_id` | Read-Only | Stable record identifier (e.g. `ACH000007`). |
| `achievement_text` | Read-Only | Verbatim evidence description to be annotated. |
| `primary_category` | Read-Only | Primary form (e.g. `HACKATHON`, `CERTIFICATION`). |
| `split` | Read-Only | Always `test`. |
| `annotator_a_name` | Annotator A | Full name or identifier of Annotator A. |
| `annotator_a_tags` | Annotator A | One or more tags separated by `\|`, or `NONE` for zero-tag achievements. |
| `annotator_a_notes` | Annotator A | Optional rationale or cues found in the text. |
| `annotator_a_uncertain` | Annotator A | `TRUE` if ambiguous or uncertain; otherwise `FALSE`. |
| `annotator_a_status` | Annotator A | `PENDING` while working; `COMPLETED` when finished. |
| `annotator_b_name` | Annotator B | Full name or identifier of Annotator B. |
| `annotator_b_tags` | Annotator B | One or more tags separated by `\|`, or `NONE` for zero-tag achievements. |
| `annotator_b_notes` | Annotator B | Optional rationale or cues found in the text. |
| `annotator_b_uncertain` | Annotator B | `TRUE` if ambiguous or uncertain; otherwise `FALSE`. |
| `annotator_b_status` | Annotator B | `PENDING` while working; `COMPLETED` when finished. |
| `disagreement_status` | System / Lead | Automatically determined (`AWAITING_REVIEWS`, `AGREED`, `DISAGREED`, `RESOLVED`). |
| `adjudicated_tags` | Lead Adjudicator | Final authoritative tag list (or `NONE`). |
| `adjudication_notes` | Lead Adjudicator | Mandatory justification explaining the adjudication decision. |
| `adjudicator` | Lead Adjudicator | Mandatory identifier of the Lead Adjudicator. |
| `annotation_status` | Lead Adjudicator | `PENDING_HUMAN_REVIEW` until adjudicated/verified; then `VERIFIED`. |

---

## 4. Lead Adjudicator Protocol

1. **Intake & Queue Generation:**
   - Execute the workflow inspection:
     ```bash
     python -c "from src.nlp.annotation_workflow import import_annotation_task_csv, detect_disagreements; recs = import_annotation_task_csv('data/annotations/domain_categorization_annotation_task.csv'); print(detect_disagreements(recs))"
     ```
   - The queue isolates all records where:
     - Tag sets differ (`annotator_a_tags != annotator_b_tags`).
     - Either annotator flagged `uncertain = TRUE`.
2. **Adjudication Standards:**
   - Cross-reference conflicting tags against `data/annotations/domain_categorization_annotation_guide.md`.
   - Ensure decisions reflect verbatim textual evidence rather than assumed project scope.
   - For confirmed non-computing records, assign `adjudicated_tags = NONE`.
3. **Formal Resolution:**
   - Enter adjudicated tags in `adjudicated_tags`.
   - Enter comprehensive reasoning in `adjudication_notes`.
   - Enter your identifier in `adjudicator`.
   - Set `annotation_status = VERIFIED`.
   - Set `disagreement_status = RESOLVED`.
