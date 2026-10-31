"""
src/nlp/classification.py
=========================
Primary Multi-Class Achievement Classification Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1

This module provides the production classification pipeline for mapping
student achievement descriptions to the 14-category achievement taxonomy:
1. Preprocessing: Unicode NFC normalization, whitespace collapsing, lowercasing.
2. Feature Representation: Sublinear TF-IDF word/bigram vectorization.
3. Classifier: Multi-class Logistic Regression with calibrated class probabilities.
4. Output Schema: Structured `ClassificationResult` with predicted category, confidence,
   category probability distribution, normalized text, and auditable metadata.
5. Model Persistence & Versioning: Bundle serialization via joblib.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .text_preprocessing import normalize_text_for_classification

# Master 14-Category Taxonomy
ACHIEVEMENT_CATEGORIES: List[str] = sorted([
    "CERTIFICATION",
    "COMPETITION",
    "CONFERENCE",
    "CULTURAL",
    "HACKATHON",
    "INTERNSHIP",
    "LEADERSHIP",
    "OTHER",
    "PATENT",
    "PROJECT",
    "RESEARCH_PUBLICATION",
    "SPORTS",
    "VOLUNTEERING",
    "WORKSHOP",
])


@dataclass
class ClassificationResult:
    """Auditable structured result of single achievement categorization."""
    predicted_category: str
    confidence: float
    category_scores: Dict[str, float]
    normalized_text: str
    model_version: str
    audit_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predicted_category": self.predicted_category,
            "confidence": round(self.confidence, 4),
            "category_scores": {k: round(v, 4) for k, v in self.category_scores.items()},
            "normalized_text": self.normalized_text,
            "model_version": self.model_version,
            "audit_metadata": self.audit_metadata,
        }


class AchievementClassifier:
    """
    Production-grade Multi-Class Achievement Classifier.
    """

    def __init__(
        self,
        classifier: Optional[Any] = None,
        vectorizer: Optional[TfidfVectorizer] = None,
        categories: Optional[List[str]] = None,
        model_version: str = "1.0.1",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.model_version = model_version
        self.categories = sorted(categories) if categories is not None else ACHIEVEMENT_CATEGORIES
        self.vectorizer = vectorizer
        self.classifier = classifier
        self.metadata = metadata or {
            "model_type": "TF-IDF + LogisticRegression",
            "model_version": self.model_version,
            "trained_on_dataset_version": "achievement_dataset_v1.0.1",
            "num_classes": len(self.categories),
        }

    @property
    def is_fitted(self) -> bool:
        return (
            self.classifier is not None
            and self.vectorizer is not None
            and hasattr(self.classifier, "classes_")
        )

    def fit(
        self,
        texts: List[str],
        labels: List[str],
        ngram_range: Tuple[int, int] = (1, 2),
        max_features: int = 5000,
        C: float = 1.0,
        random_state: int = 42,
    ) -> AchievementClassifier:
        """
        Fit vectorizer and classifier strictly on training partition data.
        """
        if len(texts) != len(labels):
            raise ValueError(f"texts ({len(texts)}) and labels ({len(labels)}) must have equal length.")
        if len(texts) == 0:
            raise ValueError("Training texts collection cannot be empty.")

        # Normalize texts
        X_norm = [normalize_text_for_classification(t) for t in texts]

        # Fit TF-IDF strictly on train
        self.vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            max_features=max_features,
            sublinear_tf=True,
        )
        X_tfidf = self.vectorizer.fit_transform(X_norm)

        # Fit Logistic Regression
        self.classifier = LogisticRegression(
            C=C,
            max_iter=1000,
            class_weight="balanced",
            random_state=random_state,
        )
        self.classifier.fit(X_tfidf, labels)
        self.categories = sorted(list(self.classifier.classes_))

        self.metadata.update({
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "train_samples": len(texts),
            "feature_count": X_tfidf.shape[1],
            "hyperparameters": {
                "ngram_range": ngram_range,
                "max_features": max_features,
                "C": C,
                "random_state": random_state,
            },
        })
        return self

    def predict_record(
        self,
        record_or_text: Union[str, Dict[str, Any], pd.Series],
    ) -> ClassificationResult:
        """
        Classify a single achievement record or raw text string.
        """
        if not self.is_fitted:
            raise RuntimeError("AchievementClassifier must be fitted or loaded before prediction.")

        # Extract text
        if isinstance(record_or_text, str):
            raw_text = record_or_text
            record_id = None
        elif isinstance(record_or_text, (dict, pd.Series)):
            val = record_or_text.get("achievement_text", record_or_text.get("text", ""))
            if val is None or pd.isna(val) or str(val).strip().lower() in ("nan", "none", "null"):
                raw_text = ""
            else:
                raw_text = str(val)
            record_id = str(record_or_text.get("achievement_id", ""))
        elif record_or_text is None or (isinstance(record_or_text, float) and np.isnan(record_or_text)):
            raw_text = ""
            record_id = None
        else:
            raise TypeError(f"Invalid input type: {type(record_or_text).__name__}. Expected str, dict, or pd.Series.")

        norm_text = normalize_text_for_classification(raw_text)

        # Empty text fallback
        if not norm_text:
            scores = {cat: 1.0 / len(self.categories) for cat in self.categories}
            return ClassificationResult(
                predicted_category="OTHER",
                confidence=round(1.0 / len(self.categories), 4),
                category_scores=scores,
                normalized_text="",
                model_version=self.model_version,
                audit_metadata={
                    "warning": "Empty or non-textual input string. Assigned default 'OTHER' category with uniform confidence.",
                    "record_id": record_id,
                },
            )

        # Vectorize and predict
        assert self.vectorizer is not None
        assert self.classifier is not None

        X_vec = self.vectorizer.transform([norm_text])

        # Get calibrated probability distribution
        if hasattr(self.classifier, "predict_proba"):
            probs = self.classifier.predict_proba(X_vec)[0]
        else:
            # Fallback to softmax over decision function
            df_vals = self.classifier.decision_function(X_vec)[0]
            exp_vals = np.exp(df_vals - np.max(df_vals))
            probs = exp_vals / exp_vals.sum()

        pred_idx = int(np.argmax(probs))
        predicted_cat = str(self.classifier.classes_[pred_idx])
        confidence = float(probs[pred_idx])
        category_scores = {str(cat): float(p) for cat, p in zip(self.classifier.classes_, probs)}

        return ClassificationResult(
            predicted_category=predicted_cat,
            confidence=confidence,
            category_scores=category_scores,
            normalized_text=norm_text,
            model_version=self.model_version,
            audit_metadata={"record_id": record_id} if record_id else {},
        )

    def predict_batch(
        self,
        records_or_texts: Union[List[str], List[Dict[str, Any]], pd.Series, pd.DataFrame],
    ) -> List[ClassificationResult]:
        """
        Execute batch classification over a list of items or pandas structure.
        """
        if isinstance(records_or_texts, pd.DataFrame):
            items = records_or_texts.to_dict(orient="records")
        elif isinstance(records_or_texts, pd.Series):
            items = records_or_texts.tolist()
        elif isinstance(records_or_texts, list):
            items = records_or_texts
        else:
            raise TypeError(f"Unsupported batch input type: {type(records_or_texts).__name__}")

        return [self.predict_record(item) for item in items]

    def save(self, model_path: Union[str, Path]) -> Path:
        """
        Serialize model bundle and metadata to disk.
        """
        out_path = Path(model_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        bundle = {
            "model_version": self.model_version,
            "categories": self.categories,
            "vectorizer": self.vectorizer,
            "classifier": self.classifier,
            "metadata": self.metadata,
        }
        joblib.dump(bundle, out_path, compress=3)

        # Save human-readable companion JSON metadata
        meta_path = out_path.with_suffix(".json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        return out_path

    @classmethod
    def load(cls, model_path: Union[str, Path]) -> AchievementClassifier:
        """
        Load serialized model bundle from disk.
        """
        in_path = Path(model_path)
        if not in_path.exists():
            raise FileNotFoundError(f"Model artifact not found at: {in_path}")

        bundle = joblib.load(in_path)
        classifier = cls(
            classifier=bundle["classifier"],
            vectorizer=bundle["vectorizer"],
            categories=bundle["categories"],
            model_version=bundle.get("model_version", "1.0.1"),
            metadata=bundle.get("metadata", {}),
        )
        return classifier
