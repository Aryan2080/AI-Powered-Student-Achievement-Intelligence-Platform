"""
src/nlp/pipeline.py
===================
End-to-End NLP Integration and Robustness Orchestration Pipeline
AI-Powered Student Achievement Intelligence Platform — Member 1

This module orchestrates the complete NLP pipeline for achievement evidence:
1. Ingestion (Step 6): PDF / Image ingestion, provenance tracking, and OCR fallback.
2. Structured Extraction (Step 7): Audited entity extraction with character spans and date semantics.
3. Multi-Class Classification (Step 5): Multi-class taxonomy categorization with probability distributions.
4. Skill Normalization (Step 4): Surface skill mention extraction and canonical vocabulary mapping.
5. Review Triage & Uncertainty: Automated administrative review routing for degraded or ambiguous inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from .categorization import (
    DOMAIN_TAGS,
    AchievementCategorizer,
    CategorizationResult,
)
from .classification import (
    ACHIEVEMENT_CATEGORIES,
    AchievementClassifier,
    ClassificationResult,
)
from .document_ingestion import (
    DocumentExtractionResult,
    DocumentFormat,
    ExtractionMethod,
    ExtractionStatus,
    PageExtractionResult,
    detect_document_format,
    ingest_document,
    normalize_extracted_text,
)
from .information_extraction import (
    ConfidenceStatus,
    EvidenceInformationExtractor,
    ExtractedField,
    ExtractionSource,
    StructuredEvidenceExtraction,
    get_default_extractor,
)
from .skill_normalization import (
    CanonicalSkillVocabulary,
    NormalizationStatus,
    NormalizedSkill,
    SkillNormalizer,
)
from .text_preprocessing import (
    normalize_text_for_classification,
    normalize_unicode,
    normalize_whitespace,
)


# ==============================================================================
# PIPELINE RESULT DATA CONTRACT
# ==============================================================================

@dataclass
class PipelineProcessingResult:
    """
    Complete audited result from end-to-end NLP evidence processing.
    Preserves document ingestion provenance, structured extracted fields,
    multi-class classification distribution, canonical skills, and review triage.
    """
    document_id: str
    pipeline_version: str
    status: str  # "SUCCESS", "REVIEW_REQUIRED", "FAILED"
    ingestion_summary: Dict[str, Any]
    extracted_entities: Dict[str, Any]
    classification: Dict[str, Any]
    skills: List[Dict[str, Any]]
    field_confidence: float
    classification_confidence: float
    overall_confidence: float
    review_required: bool
    review_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    structured_extraction: Optional[StructuredEvidenceExtraction] = None
    classification_result: Optional[ClassificationResult] = None
    domain_tags: List[str] = field(default_factory=list)
    categorization: Dict[str, Any] = field(default_factory=dict)
    categorization_result: Optional[CategorizationResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert pipeline processing result to JSON-serializable dictionary."""
        return {
            "document_id": self.document_id,
            "pipeline_version": self.pipeline_version,
            "status": self.status,
            "ingestion_summary": self.ingestion_summary,
            "extracted_entities": self.extracted_entities,
            "classification": self.classification,
            "skills": self.skills,
            "domain_tags": self.domain_tags,
            "categorization": self.categorization,
            "field_confidence": round(self.field_confidence, 4),
            "classification_confidence": round(self.classification_confidence, 4),
            "overall_confidence": round(self.overall_confidence, 4),
            "review_required": self.review_required,
            "review_reasons": self.review_reasons,
            "warnings": self.warnings,
            "provenance": self.provenance,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize pipeline result to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


# ==============================================================================
# END-TO-END NLP PIPELINE ENGINE
# ==============================================================================

class NLPEvidencePipeline:
    """
    Orchestrates evidence document ingestion, information extraction,
    multi-class achievement categorization, and skill normalization.
    """

    def __init__(
        self,
        classifier: Optional[AchievementClassifier] = None,
        categorizer: Optional[AchievementCategorizer] = None,
        skill_normalizer: Optional[SkillNormalizer] = None,
        extractor: Optional[EvidenceInformationExtractor] = None,
        confidence_threshold: float = 0.60,
        min_classification_confidence: float = 0.35,
        pipeline_version: str = "1.0.1",
    ):
        self.pipeline_version = pipeline_version
        self.confidence_threshold = confidence_threshold
        self.min_classification_confidence = min_classification_confidence

        self.classifier = classifier
        self.categorizer = categorizer
        self.skill_normalizer = skill_normalizer

        if extractor is not None:
            self.extractor = extractor
        else:
            self.extractor = EvidenceInformationExtractor(
                classifier=self.classifier,
                skill_normalizer=self.skill_normalizer,
            )

    @classmethod
    def create_default(
        cls,
        classifier_model_path: Optional[Union[str, Path]] = "models/achievement_classifier_v1.0.1.joblib",
        categorizer_model_path: Optional[Union[str, Path]] = "models/achievement_categorizer_v1.0.1.joblib",
        vocab_path: Optional[Union[str, Path]] = "data/annotations/canonical_skill_vocabulary.csv",
        confidence_threshold: float = 0.60,
        min_classification_confidence: float = 0.35,
    ) -> NLPEvidencePipeline:
        """
        Factory method to construct pipeline with production model assets.
        Falls back safely if model files are missing or incomplete.
        """
        classifier: Optional[AchievementClassifier] = None
        if classifier_model_path:
            p = Path(classifier_model_path)
            if p.exists():
                try:
                    classifier = AchievementClassifier.load(p)
                except Exception:
                    classifier = None

        categorizer: Optional[AchievementCategorizer] = None
        if categorizer_model_path:
            cp = Path(categorizer_model_path)
            if cp.exists():
                try:
                    categorizer = AchievementCategorizer.load(cp)
                except Exception:
                    categorizer = None

        skill_normalizer: Optional[SkillNormalizer] = None
        if vocab_path:
            vp = Path(vocab_path)
            if vp.exists():
                try:
                    vocab = CanonicalSkillVocabulary(vp)
                    skill_normalizer = SkillNormalizer(vocab)
                except Exception:
                    skill_normalizer = None

        extractor = EvidenceInformationExtractor(
            classifier=classifier,
            skill_normalizer=skill_normalizer,
        )

        return cls(
            classifier=classifier,
            categorizer=categorizer,
            skill_normalizer=skill_normalizer,
            extractor=extractor,
            confidence_threshold=confidence_threshold,
            min_classification_confidence=min_classification_confidence,
        )

    # --------------------------------------------------------------------------
    # Main Processing Entrypoints
    # --------------------------------------------------------------------------

    def process_document(
        self,
        document_or_path: Union[str, Path, bytes, DocumentExtractionResult, Dict[str, Any]],
        ocr_callable: Optional[Callable] = None,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PipelineProcessingResult:
        """
        Execute end-to-end processing of an evidence document.
        Accepts a file path, raw bytes, an existing DocumentExtractionResult, or raw text.
        """
        meta = dict(metadata or {})
        warnings: List[str] = []
        review_reasons: List[str] = []

        # ----------------------------------------------------------------------
        # Stage 1: Document Ingestion & Text Extraction (Step 6)
        # ----------------------------------------------------------------------
        doc_result: Optional[DocumentExtractionResult] = None

        if isinstance(document_or_path, DocumentExtractionResult):
            doc_result = document_or_path
            doc_id = document_id or doc_result.document_id
        elif isinstance(document_or_path, (str, Path)) and Path(str(document_or_path)).exists():
            doc_path = Path(str(document_or_path))
            doc_id = document_id or doc_path.stem
            doc_result = ingest_document(
                file_path=doc_path,
                ocr_callable=ocr_callable,
                document_id=doc_id,
            )
        elif isinstance(document_or_path, bytes):
            import tempfile
            doc_id = document_id or f"DOC-BYTES-{abs(hash(document_or_path)) % 100000:05d}"
            # Detect extension or default to .bin / .pdf
            ext = ".pdf" if document_or_path.startswith(b"%PDF") else ".png" if document_or_path.startswith(b"\x89PNG") else ".bin"
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(document_or_path)
                tmp_path = Path(tmp.name)
            try:
                doc_result = ingest_document(
                    file_path=tmp_path,
                    ocr_callable=ocr_callable,
                    document_id=doc_id,
                )
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
        elif isinstance(document_or_path, str):
            # Raw string input (not a path on disk)
            doc_id = document_id or f"DOC-TXT-{abs(hash(document_or_path)) % 100000:05d}"
            norm_text = normalize_extracted_text(document_or_path)
            doc_result = DocumentExtractionResult(
                document_id=doc_id,
                filename="raw_string.txt",
                file_type=DocumentFormat.UNSUPPORTED,
                primary_extraction_method=ExtractionMethod.NONE,
                overall_status=ExtractionStatus.SUCCESS if norm_text else ExtractionStatus.EMPTY_DOCUMENT,
                pages=[
                    PageExtractionResult(
                        page_number=1,
                        raw_text=document_or_path,
                        normalized_text=norm_text,
                        extraction_method=ExtractionMethod.NONE,
                        status=ExtractionStatus.SUCCESS if norm_text else ExtractionStatus.EMPTY_DOCUMENT,
                        char_count=len(norm_text),
                        word_count=len(norm_text.split()),
                    )
                ] if document_or_path else [],
                full_raw_text=document_or_path,
                full_normalized_text=norm_text,
                total_pages=1 if document_or_path else 0,
                is_scanned=False,
                warnings=[],
                metadata={"source_type": "raw_string"},
            )
        elif isinstance(document_or_path, dict):
            # Dictionary input containing 'text' or 'source_text'
            text_val = document_or_path.get("source_text", document_or_path.get("text", ""))
            doc_id = document_id or str(document_or_path.get("document_id", f"DOC-DICT-{id(document_or_path)}"))
            return self.process_text(text=text_val, document_id=doc_id, metadata=document_or_path)
        else:
            # Corrupted / invalid input type
            doc_id = document_id or "DOC-INVALID"
            return self._build_failure_result(
                document_id=doc_id,
                reason=f"Invalid or unparseable input type: {type(document_or_path).__name__}",
                warnings=[f"Received unsupported input type: {type(document_or_path).__name__}"],
            )

        # Ingestion provenance summary
        ingestion_summary = {
            "document_id": doc_result.document_id,
            "file_type": doc_result.file_type.value,
            "primary_extraction_method": doc_result.primary_extraction_method.value,
            "overall_status": doc_result.overall_status.value,
            "total_pages": doc_result.total_pages,
            "is_scanned": doc_result.is_scanned,
            "warnings_count": len(doc_result.warnings),
            "pages": [
                {
                    "page_number": p.page_number,
                    "status": p.status.value,
                    "extraction_method": p.extraction_method.value,
                    "char_count": p.char_count,
                    "word_count": p.word_count,
                }
                for p in doc_result.pages
            ],
        }

        # Check for unrecoverable or degraded ingestion states
        if doc_result.overall_status in (
            ExtractionStatus.EMPTY_DOCUMENT,
            ExtractionStatus.CORRUPTED_FILE,
            ExtractionStatus.FILE_NOT_FOUND,
            ExtractionStatus.UNSUPPORTED_FORMAT,
        ):
            reason_msg = f"Document ingestion failed with status {doc_result.overall_status.value}."
            return self._build_failure_result(
                document_id=doc_id,
                reason=reason_msg,
                warnings=doc_result.warnings or [reason_msg],
                ingestion_summary=ingestion_summary,
            )

        # Propagate ingestion warnings
        warnings.extend(doc_result.warnings)

        if doc_result.overall_status == ExtractionStatus.OCR_UNAVAILABLE:
            review_reasons.append("OCR engine was unavailable for scanned document.")
            warnings.append("Document text may be missing or truncated due to absent OCR engine.")

        if doc_result.overall_status == ExtractionStatus.OCR_FALLBACK_APPLIED:
            warnings.append("Text extracted via optical character recognition; optical artifacts may be present.")

        # ----------------------------------------------------------------------
        # Stage 2: Structured Information Extraction (Step 7)
        # ----------------------------------------------------------------------
        extraction = self.extractor.extract_from_document(doc_result)

        # Merge warnings & review reasons from extractor
        for w in extraction.warnings:
            if w not in warnings:
                warnings.append(w)
        for r in extraction.review_reasons:
            if r not in review_reasons:
                review_reasons.append(r)

        # ----------------------------------------------------------------------
        # Stage 3: Multi-Class Achievement Categorization (Step 5)
        # ----------------------------------------------------------------------
        classification_dict: Dict[str, Any] = {}
        cls_result: Optional[ClassificationResult] = None
        cls_conf = 0.0

        raw_text_for_cls = doc_result.full_normalized_text or doc_result.full_raw_text
        if self.classifier is not None and self.classifier.is_fitted:
            try:
                cls_result = self.classifier.predict_record(raw_text_for_cls)
                cls_conf = float(cls_result.confidence)
                classification_dict = {
                    "predicted_category": cls_result.predicted_category,
                    "confidence": round(cls_result.confidence, 4),
                    "category_scores": {k: round(v, 4) for k, v in cls_result.category_scores.items()},
                    "model_version": cls_result.model_version,
                }

                # Evaluate classification confidence vs threshold
                if cls_conf < self.min_classification_confidence:
                    review_reasons.append(
                        f"Classifier confidence ({cls_conf:.2f}) is below minimum threshold ({self.min_classification_confidence:.2f})."
                    )

                # Check for category conflict between rule extraction and ML model
                rule_cat = extraction.category.value
                if rule_cat and rule_cat != "OTHER" and rule_cat != cls_result.predicted_category:
                    # Model and rule disagree
                    warnings.append(
                        f"Category discrepancy: Rule extracted '{rule_cat}' while classifier predicted '{cls_result.predicted_category}'."
                    )
                    # If classifier confidence is high, consider whether review is needed
                    if cls_conf >= 0.70 and extraction.category.confidence < 0.70:
                        # Classifier is more confident
                        pass
                    elif extraction.category.confidence >= 0.85:
                        # Rule is based on unambiguous cue; preserve rule but note
                        pass
                    else:
                        review_reasons.append(
                            f"Ambiguous category: Cues suggest '{rule_cat}', classifier predicts '{cls_result.predicted_category}'."
                        )
            except Exception as e:
                warnings.append(f"Classifier inference failed with exception: {str(e)}")
                review_reasons.append("Multi-class category classifier failed to execute.")
                classification_dict = {
                    "predicted_category": extraction.category.value or "OTHER",
                    "confidence": 0.0,
                    "category_scores": {c: 1.0 / len(ACHIEVEMENT_CATEGORIES) for c in ACHIEVEMENT_CATEGORIES},
                    "model_version": "error_fallback",
                }
        else:
            # Fallback when classifier is not loaded
            fallback_cat = extraction.category.value or "OTHER"
            cls_conf = extraction.category.confidence if extraction.category.confidence > 0 else 0.50
            classification_dict = {
                "predicted_category": fallback_cat,
                "confidence": round(cls_conf, 4),
                "category_scores": {fallback_cat: cls_conf},
                "model_version": "rule_heuristic_only",
            }
            if not extraction.category.value:
                warnings.append("No machine learning classifier loaded; category defaulted via heuristic.")

        # ----------------------------------------------------------------------
        # Stage 3b: Multi-Label Domain Categorization (Step 10 / Step 12)
        # ----------------------------------------------------------------------
        domain_tags: List[str] = []
        categorization_dict: Dict[str, Any] = {}
        cat_result: Optional[CategorizationResult] = None

        if self.categorizer is not None and self.categorizer.is_fitted:
            try:
                cat_result = self.categorizer.predict_record(raw_text_for_cls)
                domain_tags = list(cat_result.predicted_tags)
                categorization_dict = {
                    "predicted_tags": domain_tags,
                    "domain_tags": domain_tags,
                    "tag_scores": {k: round(v, 4) for k, v in cat_result.tag_scores.items()},
                    "thresholds": {k: round(v, 4) for k, v in cat_result.thresholds.items()},
                    "confidence_tier": getattr(cat_result, "confidence_tier", {}),
                    "uncertain_tags": getattr(cat_result, "uncertain_tags", []),
                    "review_recommended": getattr(cat_result, "review_recommended", False),
                    "model_version": cat_result.model_version,
                }
                if getattr(cat_result, "review_recommended", False):
                    uncertain_str = ", ".join(cat_result.uncertain_tags) if cat_result.uncertain_tags else "detected tags"
                    warnings.append(
                        f"Domain categorization margin is narrow for tags ({uncertain_str}); human verification recommended."
                    )
            except Exception as e:
                warnings.append(f"Categorizer inference failed with exception: {str(e)}")
                categorization_dict = {
                    "predicted_tags": [],
                    "domain_tags": [],
                    "tag_scores": {t: 0.0 for t in DOMAIN_TAGS},
                    "thresholds": {},
                    "confidence_tier": {},
                    "uncertain_tags": [],
                    "review_recommended": False,
                    "model_version": "error_fallback",
                }
        else:
            categorization_dict = {
                "predicted_tags": [],
                "domain_tags": [],
                "tag_scores": {t: 0.0 for t in DOMAIN_TAGS},
                "thresholds": {},
                "confidence_tier": {},
                "uncertain_tags": [],
                "review_recommended": False,
                "model_version": "none",
            }

        # ----------------------------------------------------------------------
        # Stage 4: Date Semantics & Conflict Auditing
        # ----------------------------------------------------------------------
        date_audit = self._audit_dates_and_conflicts(raw_text_for_cls, extraction.issue_date)
        if date_audit.get("has_conflict"):
            review_reasons.append(date_audit["conflict_reason"])
            warnings.append(date_audit["conflict_reason"])

        # ----------------------------------------------------------------------
        # Stage 5: Rank & Outcome Consistency Auditing
        # ----------------------------------------------------------------------
        rank_audit = self._audit_rank_conflicts(raw_text_for_cls, extraction.rank, extraction.outcome)
        if rank_audit.get("has_conflict"):
            review_reasons.append(rank_audit["conflict_reason"])
            warnings.append(rank_audit["conflict_reason"])

        # ----------------------------------------------------------------------
        # Stage 6: Terminology & Domain Completeness Check
        # ----------------------------------------------------------------------
        term_audit = self._audit_terminology(raw_text_for_cls, extraction)
        if term_audit.get("is_unknown"):
            review_reasons.append(term_audit["reason"])
            warnings.append(term_audit["reason"])

        # ----------------------------------------------------------------------
        # Stage 7: Confidence Calibration & Triage Routing
        # ----------------------------------------------------------------------
        field_conf = extraction.overall_confidence
        combined_conf = float(0.6 * field_conf + 0.4 * cls_conf)

        # Check required fields
        if extraction.achievement_title.confidence_status in (ConfidenceStatus.MISSING, ConfidenceStatus.LOW):
            if "Achievement title could not be identified with high confidence." not in review_reasons:
                review_reasons.append("Missing or low-confidence achievement title.")

        if extraction.organization.confidence_status in (ConfidenceStatus.MISSING, ConfidenceStatus.LOW):
            if "Issuing organization is missing or ambiguous." not in review_reasons:
                review_reasons.append("Missing or low-confidence issuing organization.")

        # Determine overall review requirement
        review_required = extraction.review_required or len(review_reasons) > 0 or combined_conf < self.confidence_threshold
        status = "REVIEW_REQUIRED" if review_required else "SUCCESS"

        # Ensure skills have both canonical_name and canonical_skill
        serialized_skills = []
        for s in extraction.normalized_skills:
            s_dict = dict(s)
            if "canonical_name" not in s_dict:
                s_dict["canonical_name"] = s_dict.get("canonical_skill")
            serialized_skills.append(s_dict)

        # Construct Provenance Bundle
        provenance = {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_version": self.pipeline_version,
            "classifier_model_version": getattr(self.classifier, "model_version", None) if self.classifier else None,
            "categorizer_model_version": getattr(self.categorizer, "model_version", None) if self.categorizer else None,
            "vocabulary_size": len(self.skill_normalizer.vocab.canonical_skills) if self.skill_normalizer else 0,
            "document_format": doc_result.file_type.value,
            "is_scanned": doc_result.is_scanned,
            "total_pages": doc_result.total_pages,
            "source_spans": {
                "student_name": extraction.student_name.source_span,
                "student_id": extraction.student_id.source_span,
                "achievement_title": extraction.achievement_title.source_span,
                "organization": extraction.organization.source_span,
                "rank": extraction.rank.source_span,
                "level": extraction.level.source_span,
                "outcome": extraction.outcome.source_span,
                "issue_date": extraction.issue_date.source_span,
                "certificate_id": extraction.certificate_id.source_span,
            },
            "page_references": {
                "student_name": extraction.student_name.page_number,
                "achievement_title": extraction.achievement_title.page_number,
                "organization": extraction.organization.page_number,
                "issue_date": extraction.issue_date.page_number,
            },
            "date_semantics": date_audit,
        }

        return PipelineProcessingResult(
            document_id=doc_id,
            pipeline_version=self.pipeline_version,
            status=status,
            ingestion_summary=ingestion_summary,
            extracted_entities=extraction.to_dict(),
            classification=classification_dict,
            skills=serialized_skills,
            domain_tags=domain_tags,
            categorization=categorization_dict,
            field_confidence=field_conf,
            classification_confidence=cls_conf,
            overall_confidence=combined_conf,
            review_required=review_required,
            review_reasons=review_reasons,
            warnings=warnings,
            provenance=provenance,
            structured_extraction=extraction,
            classification_result=cls_result,
            categorization_result=cat_result,
        )

    def process_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PipelineProcessingResult:
        """
        Process a raw evidence text string through the NLP pipeline.
        """
        return self.process_document(
            document_or_path=text,
            document_id=document_id,
            metadata=metadata,
        )

    def process_batch(
        self,
        items: List[Any],
        ocr_callable: Optional[Callable] = None,
    ) -> List[PipelineProcessingResult]:
        """
        Process a batch of documents or text strings.
        """
        results: List[PipelineProcessingResult] = []
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                doc, doc_id = item
                results.append(self.process_document(doc, ocr_callable=ocr_callable, document_id=doc_id))
            else:
                results.append(self.process_document(item, ocr_callable=ocr_callable))
        return results

    # --------------------------------------------------------------------------
    # Auditing & Sanity Verification Helpers
    # --------------------------------------------------------------------------

    def _audit_dates_and_conflicts(
        self, text: str, primary_date_field: ExtractedField
    ) -> Dict[str, Any]:
        """
        Inspect text for distinct date types (event date, issue date, achievement date)
        and detect conflicting date declarations.
        """
        if not text or not text.strip():
            return {"has_conflict": False, "dates_found": []}

        # Date pattern regex
        date_pattern = (
            r"\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|"
            r"\d{1,2}[-/.]\d{1,2}[-/.]\d{4}|"
            r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
            r"\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4}|"
            r"\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b"
        )

        matches = list(re.finditer(date_pattern, text, re.IGNORECASE))
        unique_date_strings = list({m.group(0).strip() for m in matches})

        # Context cues for event date vs issue date
        event_date_cues = [r"(?:held\s+on|organized\s+on|conducted\s+on|during|event\s+date)\s*[:\-]?\s*"]
        issue_date_cues = [r"(?:issued\s+on|date\s+of\s+issue|given\s+on|dated)\s*[:\-]?\s*"]

        detected_types: Dict[str, str] = {}
        for m in matches:
            date_str = m.group(0)
            prefix = text[max(0, m.start() - 40): m.start()]
            if any(re.search(cue, prefix, re.IGNORECASE) for cue in event_date_cues):
                detected_types[date_str] = "EVENT_DATE"
            elif any(re.search(cue, prefix, re.IGNORECASE) for cue in issue_date_cues):
                detected_types[date_str] = "ISSUE_DATE"
            else:
                detected_types[date_str] = "UNSPECIFIED"

        has_conflict = False
        conflict_reason = ""

        # Conflict 1: Multiple contradictory event dates for a single achievement
        event_dates = [d for d, t in detected_types.items() if t == "EVENT_DATE"]
        if len(set(event_dates)) > 1:
            has_conflict = True
            conflict_reason = f"Conflicting event dates found in evidence: {', '.join(event_dates)}"

        # Conflict 2: More than 3 distinct dates on a single-page certificate without clear roles
        if len(unique_date_strings) >= 3 and not has_conflict:
            has_conflict = True
            conflict_reason = f"Multiple ambiguous dates detected on evidence ({len(unique_date_strings)} found)."

        return {
            "has_conflict": has_conflict,
            "conflict_reason": conflict_reason,
            "unique_date_count": len(unique_date_strings),
            "dates_found": unique_date_strings,
            "date_type_mapping": detected_types,
            "primary_extracted_date": primary_date_field.value,
        }

    def _audit_rank_conflicts(
        self, text: str, rank_field: ExtractedField, outcome_field: ExtractedField
    ) -> Dict[str, Any]:
        """
        Check whether document contains contradictory rank statements.
        E.g. claiming 1st place AND runner-up, or winner AND participant.
        """
        if not text:
            return {"has_conflict": False}

        lower = text.lower()
        winner_cues = bool(re.search(r"\b(1st\s+place|first\s+prize|gold\s+medal|champion|winner)\b", lower))
        runner_up_cues = bool(re.search(r"\b(runner\s*up|2nd\s+place|second\s+prize|silver\s+medal)\b", lower))
        participation_cues = bool(re.search(r"\b(participated\s+in|for\s+participating|certificate\s+of\s+participation)\b", lower))

        has_conflict = False
        reason = ""

        if winner_cues and runner_up_cues:
            has_conflict = True
            reason = "Conflicting rank claims: Both winner (1st place) and runner-up claims found in text."
        elif winner_cues and participation_cues and rank_field.value is None:
            has_conflict = True
            reason = "Ambiguous rank: Document contains both winner and participation terminology."

        return {
            "has_conflict": has_conflict,
            "conflict_reason": reason,
        }

    def _audit_terminology(
        self, text: str, extraction: StructuredEvidenceExtraction
    ) -> Dict[str, Any]:
        """
        Detect if text has zero recognizable academic or extracurricular achievement terminology.
        """
        if not text or len(text.strip()) < 15:
            return {"is_unknown": False}

        # Check if any recognizable entity or skill was extracted
        has_entities = bool(
            extraction.achievement_title.value
            or extraction.organization.value
            or (extraction.category.value and extraction.category.value != "OTHER")
            or extraction.skills.value
            or extraction.rank.value
        )

        # Common domain tokens
        domain_keywords = [
            "award", "certif", "compet", "contest", "hackathon", "intern", "project",
            "publish", "paper", "journal", "confer", "workshop", "present", "merit",
            "winner", "prize", "rank", "lead", "sport", "volunteer", "student", "grade"
        ]
        has_keywords = any(kw in text.lower() for kw in domain_keywords)

        if not has_entities and not has_keywords:
            return {
                "is_unknown": True,
                "reason": "Text does not contain recognizable achievement, academic, or extracurricular terminology.",
            }

        return {"is_unknown": False}

    def _build_failure_result(
        self,
        document_id: str,
        reason: str,
        warnings: List[str],
        ingestion_summary: Optional[Dict[str, Any]] = None,
    ) -> PipelineProcessingResult:
        """Construct failure pipeline result for empty or unparseable input."""
        empty_field = ExtractedField(
            value=None,
            confidence=0.0,
            confidence_status=ConfidenceStatus.MISSING,
            extraction_source=ExtractionSource.DEFAULT,
            warnings=[reason],
        )
        empty_extraction = StructuredEvidenceExtraction(
            document_id=document_id,
            student_name=empty_field,
            student_id=empty_field,
            achievement_title=empty_field,
            organization=empty_field,
            category=empty_field,
            rank=empty_field,
            level=empty_field,
            outcome=empty_field,
            issue_date=empty_field,
            certificate_id=empty_field,
            skills=empty_field,
            normalized_skills=[],
            overall_confidence=0.0,
            review_required=True,
            review_reasons=[reason],
            warnings=warnings,
            metadata={"status": "FAILED"},
        )
        cls_dict = {
            "predicted_category": "OTHER",
            "confidence": 0.0,
            "category_scores": {c: 1.0 / len(ACHIEVEMENT_CATEGORIES) for c in ACHIEVEMENT_CATEGORIES},
            "model_version": "none",
        }

        return PipelineProcessingResult(
            document_id=document_id,
            pipeline_version=self.pipeline_version,
            status="FAILED",
            ingestion_summary=ingestion_summary or {
                "document_id": document_id,
                "file_type": "UNKNOWN",
                "overall_status": "FAILED",
                "total_pages": 0,
            },
            extracted_entities=empty_extraction.to_dict(),
            classification=cls_dict,
            skills=[],
            domain_tags=[],
            categorization={
                "predicted_tags": [],
                "domain_tags": [],
                "tag_scores": {},
                "thresholds": {},
                "model_version": "failed",
            },
            field_confidence=0.0,
            classification_confidence=0.0,
            overall_confidence=0.0,
            review_required=True,
            review_reasons=[reason],
            warnings=warnings,
            provenance={
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "pipeline_version": self.pipeline_version,
                "failure_reason": reason,
            },
            structured_extraction=empty_extraction,
        )


# ==============================================================================
# SINGLETON & CONVENIENCE ACCESSORS
# ==============================================================================

_PIPELINE_SINGLETON: Optional[NLPEvidencePipeline] = None


def get_nlp_pipeline(
    classifier_model_path: Optional[Union[str, Path]] = "models/achievement_classifier_v1.0.1.joblib",
    categorizer_model_path: Optional[Union[str, Path]] = "models/achievement_categorizer_v1.0.1.joblib",
    vocab_path: Optional[Union[str, Path]] = "data/annotations/canonical_skill_vocabulary.csv",
    force_reload: bool = False,
) -> NLPEvidencePipeline:
    """
    Get or initialize the shared singleton instance of NLPEvidencePipeline.
    Ensures models are not re-loaded repeatedly across calls.
    """
    global _PIPELINE_SINGLETON
    if _PIPELINE_SINGLETON is None or force_reload:
        _PIPELINE_SINGLETON = NLPEvidencePipeline.create_default(
            classifier_model_path=classifier_model_path,
            categorizer_model_path=categorizer_model_path,
            vocab_path=vocab_path,
        )
    return _PIPELINE_SINGLETON


def process_evidence_document(
    document_or_path: Union[str, Path, bytes, DocumentExtractionResult, Dict[str, Any]],
    ocr_callable: Optional[Callable] = None,
    document_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> PipelineProcessingResult:
    """
    Convenience function to process an evidence document through the default NLP pipeline.
    """
    pipeline = get_nlp_pipeline()
    return pipeline.process_document(
        document_or_path=document_or_path,
        ocr_callable=ocr_callable,
        document_id=document_id,
        metadata=metadata,
    )
