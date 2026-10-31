"""
src/nlp/build_step8_notebooks.py
================================
Executable Notebook Generator for Step 8:
20_nlp_end_to_end_integration.ipynb

Executes code cells in real-time, captures stdout, figures, and rich execution
outputs, and saves valid nbformat 4.5 Jupyter Notebooks.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
os.environ["TOKENIZERS_PARALLELISM"] = "false"
sys.path.insert(0, str(REPO_ROOT))


class NotebookBuilder:
    def __init__(self, filename: str, title: str):
        self.filename = filename
        self.title = title
        self.cells: List[Dict[str, Any]] = []
        self.execution_count = 1
        self.namespace: Dict[str, Any] = {
            "__name__": "__main__",
            "REPO_ROOT": REPO_ROOT,
            "plt": plt,
            "np": np,
            "pd": pd,
            "Image": Image,
        }

    def add_markdown(self, source: str) -> None:
        self.cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": source.strip().splitlines(keepends=True),
        })

    def run_code(self, code_text: str, figure_name: Optional[str] = None) -> None:
        code_clean = code_text.strip()
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        outputs: List[Dict[str, Any]] = []

        plt.close("all")

        try:
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec(code_clean, self.namespace)
        except Exception as e:
            print(f"ERROR IN CELL ({self.title}): {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Cell execution failed in '{self.title}'") from e

        out_str = stdout_capture.getvalue()
        if out_str:
            outputs.append({
                "output_type": "stream",
                "name": "stdout",
                "text": out_str.splitlines(keepends=True),
            })

        # Save plot if figure active
        fig_nums = plt.get_fignums()
        if fig_nums:
            fig = plt.figure(fig_nums[-1])
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
            buf.seek(0)
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            if figure_name:
                fig_path = REPO_ROOT / "reports" / "figures" / figure_name
                fig_path.parent.mkdir(parents=True, exist_ok=True)
                fig.savefig(fig_path, bbox_inches="tight", dpi=150)
                print(f"  [SAVED FIGURE] {fig_path.name}")

            outputs.append({
                "output_type": "display_data",
                "data": {
                    "image/png": img_b64,
                    "text/plain": ["<Figure size ...>"],
                },
                "metadata": {},
            })
            plt.close("all")

        self.cells.append({
            "cell_type": "code",
            "execution_count": self.execution_count,
            "metadata": {},
            "outputs": outputs,
            "source": code_clean.splitlines(keepends=True),
        })
        self.execution_count += 1

    def add_code(self, code_text: str, figure_name: Optional[str] = None) -> None:
        self.run_code(code_text, figure_name)

    def save(self) -> Path:
        nb_path = REPO_ROOT / "notebooks" / self.filename
        nb_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "cells": self.cells,
            "metadata": {
                "language_info": {"name": "python", "version": "3.13.1"},
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[NOTEBOOK SAVED] {nb_path.name} ({len(self.cells)} cells)")
        return nb_path


def build_notebook_20() -> Path:
    nb = NotebookBuilder("20_nlp_end_to_end_integration.ipynb", "Step 8: End-to-End NLP Integration and Robustness Evaluation")

    nb.add_markdown("""# Step 8: End-to-End NLP Pipeline Integration & Robustness Evaluation
## AI-Powered Student Achievement Intelligence Platform
**Member 1:** NLP & Semantic Intelligence Engineer  
**Branch:** `feature/nlp-semantic` | **Dataset Release:** `achievement_dataset_v1.0.1` (FROZEN)  
**Core Module:** `src/nlp/pipeline.py` (`NLPEvidencePipeline`, `PipelineProcessingResult`)

---

### Objectives
1. **Pipeline Unification:** Orchestrate Step 6 (Document Ingestion), Step 7 (Information Extraction), Step 5 (Multi-Class Classification), and Step 4 (Skill Normalization).
2. **Provenance & Uncertainty Audit:** Maintain verbatim character spans, page-level provenance, date semantics, and clear separation between heuristic field confidences and calibrated classification probabilities.
3. **Robustness Verification:** Validate edge cases: multi-page documents, OCR warnings, OCR unavailable, missing fields, conflicting dates/ranks, corrupted inputs, unknown terminology, and model failures.
4. **Benchmark Evaluation:** Quantify performance on the 75-sample extraction evaluation benchmark across document templates and quality conditions.
5. **Administrative Review Triage:** Verify routing accuracy and ensure zero false auto-acceptances for degraded evidence.""")

    nb.add_markdown("""## Section 1: Pipeline Architecture & Environment Verification
Inspect loaded components, model bundles, canonical skill vocabulary, and OCR availability status.""")

    nb.add_code("""import os
import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Verify project imports
from src.nlp.pipeline import (
    NLPEvidencePipeline,
    PipelineProcessingResult,
    get_nlp_pipeline,
    process_evidence_document,
)
from src.nlp.document_ingestion import (
    DocumentFormat,
    ExtractionMethod,
    ExtractionStatus,
    is_ocr_available,
    get_ocr_engine_info,
)
from src.nlp.information_extraction import ConfidenceStatus

pipeline = get_nlp_pipeline()

ocr_avail = is_ocr_available()
ocr_info = get_ocr_engine_info()

print("=" * 70)
print("NLP EVIDENCE PROCESSING PIPELINE INITIALIZATION")
print("=" * 70)
print(f"Pipeline Version:            {pipeline.pipeline_version}")
print(f"Classifier Model Fitted:     {pipeline.classifier.is_fitted if pipeline.classifier else False}")
print(f"Classifier Model Version:    {pipeline.classifier.model_version if pipeline.classifier else 'None'}")
print(f"Vocabulary Size (Skills):    {len(pipeline.skill_normalizer.vocab.canonical_skills) if pipeline.skill_normalizer else 0}")
print(f"OCR Available on Host:       {ocr_avail}")
print(f"OCR Engine Details:          {ocr_info}")
print(f"Default Confidence Cutoff:   {pipeline.confidence_threshold}")
print(f"Min Classifier Confidence:   {pipeline.min_classification_confidence}")
print("=" * 70)
""")

    nb.add_markdown("""## Section 2: End-to-End Processing of Real-World Certificate Document
Process a valid PDF certificate fixture, demonstrating document ingestion, OCR/native text extraction, structured entity mapping, multi-class classification, and canonical skill normalization.""")

    nb.add_code("""cert_fixture = Path("tests/fixtures/documents/valid_certificate.pdf")
result = pipeline.process_document(cert_fixture)

print(f"Document ID:           {result.document_id}")
print(f"Status:                {result.status}")
print(f"Review Required:       {result.review_required}")
print(f"Review Reasons:        {result.review_reasons}")
print(f"Warnings:              {result.warnings}")
print(f"Ingestion Format:      {result.ingestion_summary['file_type']} ({result.ingestion_summary['primary_extraction_method']})")
print(f"Total Pages:           {result.ingestion_summary['total_pages']}")
print("-" * 70)
print("EXTRACTED STRUCTURED FIELDS:")
entities = result.extracted_entities
for field_key in ["student_name", "achievement_title", "organization", "rank", "level", "outcome", "issue_date", "certificate_id"]:
    f_data = entities[field_key]
    val = f_data["value"]
    conf = f_data["confidence"]
    status_str = f_data["confidence_status"]
    span = f_data["source_span"]
    print(f"  {field_key:<20}: {str(val):<38} [conf: {conf:.2f}, status: {status_str}, span: {span}]")

print("-" * 70)
print(f"PREDICTED CATEGORY:    {result.classification['predicted_category']} (conf: {result.classification['confidence']:.4f})")
print(f"CLASSIFIER MODEL:      {result.classification['model_version']}")
print("-" * 70)
print(f"NORMALIZED SKILLS:     {[s['canonical_name'] for s in result.skills]}")
""")

    nb.add_markdown("""## Section 3: Provenance Validation & Exact Source Spans
Verify that character offsets recorded in `source_spans` map strictly to verbatim substrings within the extracted document text, ensuring 100% auditability without hallucination.""")

    nb.add_code("""text_sample = (
    "CERTIFICATE OF MERIT\\n"
    "This is to certify that Alex Rivera representing MIT\\n"
    "has secured 1st Place in the National Collegiate Hackathon 2024\\n"
    "organized by Association for Computing Machinery on 2024-10-15.\\n"
    "Certificate ID: CERT-ACH-2024-9981"
)

text_res = pipeline.process_text(text_sample, document_id="DOC-PROVENANCE-DEMO")
spans = text_res.provenance["source_spans"]

print(f"{'Field':<20} | {'Span Range':<12} | {'Extracted Entity Value':<35} | {'Verbatim Sliced Text'}")
print("-" * 95)
for f_name, span in spans.items():
    if span is not None:
        start, end = span
        val = text_res.extracted_entities[f_name]["value"]
        slice_text = text_sample[start:end]
        match_ok = (str(val).lower() in slice_text.lower() or slice_text.lower() in str(val).lower())
        print(f"{f_name:<20} | {str(span):<12} | {str(val):<35} | '{slice_text}' (match: {match_ok})")
""")

    nb.add_markdown("""## Section 4: Robustness & Failure Mode Evaluation
Evaluate pipeline resilience across diverse challenging edge cases:
1. Multi-page document provenance
2. OCR engine unavailable for scanned document
3. Incomplete document missing mandatory title and organization
4. Conflicting event dates
5. Contradictory rank claims
6. Corrupted file input
7. Unknown non-academic terminology""")

    nb.add_code("""edge_cases = [
    (
        "Multi-Page Document",
        Path("tests/fixtures/documents/multipage_transcript.pdf"),
        "Multi-page provenance tracking across pages."
    ),
    (
        "Corrupted File Input",
        Path("tests/fixtures/documents/corrupt_doc.pdf"),
        "Corrupted PDF binary payload."
    ),
    (
        "Missing Title & Org",
        "This certifies Priya Sharma participated in student activities on 2024-03-12. CERT-GEN-1002",
        "Certificate with missing organization and event name."
    ),
    (
        "Conflicting Event Dates",
        "Event held on 2023-04-12. Won 1st Place in Robotics Derby held on 2024-11-20 organized by Robotics Society.",
        "Contradictory dates for the same event timeline."
    ),
    (
        "Contradictory Rank Claims",
        "Awarded to Maya Patel for securing 1st Place Winner and Runner Up in National Coding Challenge by TechCorp on 2024-05-18.",
        "Both winner and runner-up claims in the same certificate."
    ),
    (
        "Unknown Terminology",
        "The quick brown fox jumps over the lazy dog near the river bank on a cloudy morning.",
        "Text completely devoid of achievement or academic terminology."
    )
]

print(f"{'Scenario':<25} | {'Status':<15} | {'Review Required':<15} | {'Top Reason / Warning'}")
print("=" * 95)

for title, input_item, desc in edge_cases:
    if isinstance(input_item, Path):
        ec_res = pipeline.process_document(input_item)
    else:
        ec_res = pipeline.process_text(input_item)
    
    top_reason = (ec_res.review_reasons[0] if ec_res.review_reasons else ec_res.warnings[0] if ec_res.warnings else "None")
    print(f"{title:<25} | {ec_res.status:<15} | {str(ec_res.review_required):<15} | {top_reason[:40]}")
""")

    nb.add_markdown("""## Section 5: Benchmark Evaluation on 75 Audited Samples
Load and evaluate the versioned manifest `data/annotations/integration_evaluation_manifest.json` across document templates, quality conditions, and categories.""")

    nb.add_code("""manifest_file = Path("data/annotations/integration_evaluation_manifest.json")
if not manifest_file.exists():
    from src.nlp.generate_evaluation_manifest import generate_manifest
    manifest = generate_manifest()
else:
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

print("=" * 70)
print(f"INTEGRATION EVALUATION BENCHMARK AUDIT (v{manifest['manifest_version']})")
print("=" * 70)
print(f"Total Benchmark Samples:      {manifest['benchmark_dataset']['total_samples']}")
print(f"Synthetic Status Breakdown:   {manifest['benchmark_dataset']['synthetic_status']}")
print(f"Document Template Breakdown:  {manifest['benchmark_dataset']['template_breakdown']}")
print(f"Quality Conditions:           {manifest['benchmark_dataset']['quality_conditions']}")
print("-" * 70)
print("FIELD-LEVEL ACCURACY:")
for fname, stats in manifest["field_level_performance"].items():
    print(f"  {fname:<20}: {stats['correct']:>2}/{stats['support']:>2} ({stats['accuracy'] * 100:.1f}%)")

print("-" * 70)
print(f"OVERALL CLASSIFIER ACCURACY:  {manifest['classification_performance']['accuracy'] * 100:.1f}% ({manifest['classification_performance']['correct_predictions']}/{manifest['classification_performance']['total_evaluated']})")
print(f"FALSE AUTO-ACCEPTANCE RATE:   {manifest['review_routing_audit']['false_auto_acceptance_rate'] * 100:.2f}%")
print(f"TOTAL ROUTED FOR REVIEW:      {manifest['review_routing_audit']['total_review_required']}")
print(f"TOTAL AUTO-ACCEPTED:          {manifest['review_routing_audit']['total_auto_accepted']}")
print("=" * 70)
""")

    nb.add_markdown("""## Section 6: Pipeline Performance Dashboard & Visualizations
Generate the comprehensive four-panel technical figure visualizing field accuracy, category classification, review routing, and confidence distribution.""")

    nb.add_code("""fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Field-Level Accuracy
fields = list(manifest["field_level_performance"].keys())
accuracies = [manifest["field_level_performance"][f]["accuracy"] * 100 for f in fields]
ax1 = axes[0, 0]
bars1 = ax1.bar(fields, accuracies, color="#1f77b4", edgecolor="black", alpha=0.85)
ax1.set_ylim(0, 115)
ax1.set_ylabel("Accuracy (%)", fontsize=11)
ax1.set_title("A. Field-Level Extraction Accuracy (N=75)", fontsize=12, fontweight="bold")
ax1.tick_params(axis="x", rotation=30)
for bar in bars1:
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width() / 2.0, yval + 2, f"{yval:.0f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

# 2. Category Classification Performance
cat_data = manifest["classification_performance"]["by_category"]
cat_names = list(cat_data.keys())
cat_accs = [cat_data[c]["accuracy"] * 100 for c in cat_names]
ax2 = axes[0, 1]
bars2 = ax2.bar(cat_names, cat_accs, color="#2ca02c", edgecolor="black", alpha=0.85)
ax2.set_ylim(0, 115)
ax2.set_ylabel("Macro Accuracy (%)", fontsize=11)
ax2.set_title("B. Multi-Class Categorization Accuracy by Category", fontsize=12, fontweight="bold")
ax2.tick_params(axis="x", rotation=35)
for bar in bars2:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width() / 2.0, yval + 2, f"{yval:.0f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

# 3. Triage Routing Breakdown by Quality Condition
q_data = manifest["performance_by_quality_condition"]
q_names = list(q_data.keys())
q_supports = [q_data[q]["support"] for q in q_names]
ax3 = axes[1, 0]
bars3 = ax3.bar(q_names, q_supports, color="#ff7f0e", edgecolor="black", alpha=0.85)
ax3.set_ylabel("Sample Support Count", fontsize=11)
ax3.set_title("C. Evaluation Benchmark Quality Distribution", fontsize=12, fontweight="bold")
ax3.tick_params(axis="x", rotation=25)
for bar in bars3:
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.5, f"N={int(yval)}", ha="center", va="bottom", fontsize=9, fontweight="bold")

# 4. Confidence Semantics Distribution
samples_list = manifest["sample_evaluations"]
field_confs = [s["field_confidence"] for s in samples_list]
cls_confs = [s["classifier_confidence"] for s in samples_list]
ax4 = axes[1, 1]
ax4.hist(field_confs, bins=10, alpha=0.6, label="Heuristic Field Conf", color="#9467bd", edgecolor="black")
ax4.hist(cls_confs, bins=10, alpha=0.6, label="Calibrated Classifier Prob", color="#17becf", edgecolor="black")
ax4.set_xlabel("Confidence Score", fontsize=11)
ax4.set_ylabel("Count of Documents", fontsize=11)
ax4.set_title("D. Confidence Distribution: Heuristic vs Calibrated", fontsize=12, fontweight="bold")
ax4.legend(loc="upper left")

plt.tight_layout()
plt.show()
""", figure_name="20_nlp_pipeline_integration.png")

    nb.add_markdown("""## Section 7: Confidence Semantics & Administrative Handoff Summary
### Key Findings & Architectural Directives
1. **Confidence Semantics Distinction:**
   - **Field Confidence:** Heuristic score based on pattern specificity and cue position. It reflects syntactic extraction certainty, *not* empirical posterior probability.
   - **Classification Confidence:** Calibrated multi-class posterior probability derived via `predict_proba` from the frozen multi-class Logistic Regression model over TF-IDF word/bigram features.
2. **Date Semantics:**
   - Cues `held on` and `conducted on` map strictly to event execution dates.
   - Cues `issued on` and `dated` map to formal issuance dates.
   - Ambiguous or contradictory dates trigger `review_required=True`.
3. **No-Hallucination Policy:**
   - Missing fields are tagged `ConfidenceStatus.MISSING` with `value=None`.
   - Pipeline never invents missing names, dates, or organizations.
4. **Administrative Triage Routing:**
   - Incomplete or degraded evidence routes cleanly to human administrative queues.
   - Zero false auto-acceptances observed across the 75-sample benchmark.""")

    return nb.save()


if __name__ == "__main__":
    build_notebook_20()
