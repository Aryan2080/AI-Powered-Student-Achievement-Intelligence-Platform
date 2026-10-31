"""
src/nlp/categorization.py
=========================
Multi-Label Domain Categorization Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1

Provides the multi-label categorization engine predicting zero or more
applicable domain tags per achievement record using One-vs-Rest (Binary Relevance)
Logistic Regression over sublinear TF-IDF word and bigram features.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score

from .categorization_dataset import DOMAIN_TAGS, DOMAIN_TAG_NAMES
from .text_preprocessing import normalize_text_for_classification


@dataclass
class CategorizationResult:
    """Auditable structured result of multi-label achievement categorization."""
    predicted_tags: List[str]
    tag_scores: Dict[str, float]
    thresholds: Dict[str, float]
    normalized_text: str
    model_version: str
    confidence_tier: Dict[str, str] = field(default_factory=dict)
    uncertain_tags: List[str] = field(default_factory=list)
    review_recommended: bool = False
    audit_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert categorization result to serializable dictionary."""
        return {
            "predicted_tags": self.predicted_tags,
            "tag_scores": {k: round(v, 4) for k, v in self.tag_scores.items()},
            "thresholds": {k: round(v, 4) for k, v in self.thresholds.items()},
            "confidence_tier": self.confidence_tier,
            "uncertain_tags": self.uncertain_tags,
            "review_recommended": self.review_recommended,
            "normalized_text": self.normalized_text,
            "model_version": self.model_version,
            "audit_metadata": self.audit_metadata,
        }


class AchievementCategorizer:
    """
    Multi-Label Domain Categorizer using Binary Relevance Logistic Regression.
    Predicts independent, non-mutually-exclusive domain tags per achievement.
    """

    def __init__(
        self,
        vectorizer: Optional[TfidfVectorizer] = None,
        classifiers: Optional[Dict[str, LogisticRegression]] = None,
        thresholds: Optional[Dict[str, float]] = None,
        tags: Optional[List[str]] = None,
        model_version: str = "1.0.1",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.model_version = model_version
        self.tags = list(tags) if tags is not None else list(DOMAIN_TAGS)
        self.vectorizer = vectorizer
        self.classifiers = classifiers or {}
        self.thresholds = thresholds or {t: 0.50 for t in self.tags}
        self.metadata = metadata or {
            "model_type": "BinaryRelevanceLogisticRegression",
            "model_version": model_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @property
    def is_fitted(self) -> bool:
        """Check whether the vectorizer and all tag classifiers are fitted."""
        if self.vectorizer is None or not self.classifiers:
            return False
        return len(self.classifiers) == len(self.tags)

    def fit(
        self,
        X_train: List[str],
        Y_train_df: pd.DataFrame,
        X_val: Optional[List[str]] = None,
        Y_val_df: Optional[pd.DataFrame] = None,
        ngram_range: Tuple[int, int] = (1, 2),
        max_features: int = 5000,
        C: float = 1.0,
        random_state: int = 42,
    ) -> AchievementCategorizer:
        """
        Fit the multi-label vectorizer and independent tag classifiers.
        Calibrates decision thresholds on validation data when provided.
        """
        if not X_train:
            raise ValueError("X_train cannot be empty.")

        norm_train = [normalize_text_for_classification(t) for t in X_train]

        # Fit TF-IDF exclusively on train
        self.vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            max_features=max_features,
            sublinear_tf=True,
        )
        X_train_vec = self.vectorizer.fit_transform(norm_train)

        # Vectorize validation if present
        X_val_vec = None
        if X_val is not None:
            norm_val = [normalize_text_for_classification(t) for t in X_val]
            X_val_vec = self.vectorizer.transform(norm_val)

        self.classifiers = {}
        val_f1_scores = {}

        for tag in self.tags:
            col_name = f"tag_{tag}" if f"tag_{tag}" in Y_train_df.columns else tag
            if col_name not in Y_train_df.columns:
                raise KeyError(f"Target column '{col_name}' missing from training labels DataFrame.")

            y_tag = Y_train_df[col_name].to_numpy()

            # Train binary classifier for this tag
            clf = LogisticRegression(
                C=C,
                max_iter=1000,
                class_weight="balanced",
                random_state=random_state,
            )
            clf.fit(X_train_vec, y_tag)
            self.classifiers[tag] = clf

            # Threshold Calibration on Validation Split
            if X_val_vec is not None and Y_val_df is not None:
                val_col = f"tag_{tag}" if f"tag_{tag}" in Y_val_df.columns else tag
                y_val_tag = Y_val_df[val_col].to_numpy()

                # Get validation probabilities
                if hasattr(clf, "predict_proba"):
                    val_probs = clf.predict_proba(X_val_vec)[:, 1]
                else:
                    val_probs = 1.0 / (1.0 + np.exp(-clf.decision_function(X_val_vec)))

                # Grid search optimal threshold for F1
                best_t = 0.50
                best_f1 = -1.0
                for candidate_t in np.linspace(0.20, 0.80, 25):
                    pred_binary = (val_probs >= candidate_t).astype(int)
                    score = f1_score(y_val_tag, pred_binary, zero_division=0)
                    if score > best_f1:
                        best_f1 = score
                        best_t = float(candidate_t)

                self.thresholds[tag] = round(best_t, 3)
                val_f1_scores[tag] = round(best_f1, 4)
            else:
                self.thresholds[tag] = 0.50

        self.metadata.update({
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "train_samples": len(X_train),
            "val_samples": len(X_val) if X_val is not None else 0,
            "feature_count": X_train_vec.shape[1],
            "thresholds": self.thresholds,
            "validation_f1_per_tag": val_f1_scores,
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
    ) -> CategorizationResult:
        """
        Predict multi-label domain tags for a single achievement.
        """
        if not self.is_fitted:
            raise RuntimeError("AchievementCategorizer must be fitted or loaded before prediction.")

        # Extract text
        if isinstance(record_or_text, str):
            raw_text = record_or_text
            record_id = None
        elif isinstance(record_or_text, (dict, pd.Series)):
            val = record_or_text.get("achievement_text", record_or_text.get("text", ""))
            raw_text = str(val) if pd.notna(val) else ""
            record_id = str(record_or_text.get("achievement_id", ""))
        elif record_or_text is None:
            raw_text = ""
            record_id = None
        else:
            raise TypeError(f"Invalid input type: {type(record_or_text).__name__}")

        norm_text = normalize_text_for_classification(raw_text)

        # Empty text fallback: return empty tag list, do NOT assign domain_other
        if not norm_text:
            return CategorizationResult(
                predicted_tags=[],
                tag_scores={t: 0.0 for t in self.tags},
                thresholds=dict(self.thresholds),
                normalized_text="",
                model_version=self.model_version,
                audit_metadata={
                    "warning": "Empty or non-textual input. Zero tags assigned.",
                    "record_id": record_id,
                },
            )

        assert self.vectorizer is not None
        X_vec = self.vectorizer.transform([norm_text])

        tag_scores: Dict[str, float] = {}
        predicted_tags: List[str] = []
        confidence_tier: Dict[str, str] = {}
        uncertain_tags: List[str] = []
        review_recommended = False

        for tag in self.tags:
            clf = self.classifiers[tag]
            if hasattr(clf, "predict_proba"):
                prob = float(clf.predict_proba(X_vec)[0, 1])
            else:
                prob = float(1.0 / (1.0 + np.exp(-clf.decision_function(X_vec)[0])))

            thresh = self.thresholds[tag]
            tag_scores[tag] = prob
            margin = prob - thresh

            if prob >= thresh:
                predicted_tags.append(tag)
                if margin >= 0.15:
                    confidence_tier[tag] = "HIGH"
                elif margin >= 0.05:
                    confidence_tier[tag] = "MEDIUM"
                else:
                    confidence_tier[tag] = "LOW_MARGIN"
                    uncertain_tags.append(tag)
                    review_recommended = True
            else:
                # Near-boundary negative prediction (narrowly missed threshold)
                if abs(margin) < 0.05:
                    uncertain_tags.append(tag)
                    review_recommended = True

        return CategorizationResult(
            predicted_tags=predicted_tags,
            tag_scores=tag_scores,
            thresholds=dict(self.thresholds),
            normalized_text=norm_text,
            model_version=self.model_version,
            confidence_tier=confidence_tier,
            uncertain_tags=uncertain_tags,
            review_recommended=review_recommended,
            audit_metadata={"record_id": record_id} if record_id else {},
        )

    def predict_batch(
        self,
        records_or_texts: Union[List[str], List[Dict[str, Any]], pd.Series, pd.DataFrame],
    ) -> List[CategorizationResult]:
        """Execute multi-label prediction across a batch of records."""
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
        """Serialize categorizer model bundle and metadata to disk."""
        out_path = Path(model_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        bundle = {
            "model_version": self.model_version,
            "tags": self.tags,
            "vectorizer": self.vectorizer,
            "classifiers": self.classifiers,
            "thresholds": self.thresholds,
            "metadata": self.metadata,
        }
        joblib.dump(bundle, out_path, compress=3)

        meta_path = out_path.with_suffix(".json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        print(f"AchievementCategorizer saved successfully to: {out_path}")
        return out_path

    @classmethod
    def load(cls, model_path: Union[str, Path]) -> AchievementCategorizer:
        """Load serialized categorizer bundle from disk."""
        in_path = Path(model_path)
        if not in_path.exists():
            raise FileNotFoundError(f"Model artifact not found at: {in_path}")

        bundle = joblib.load(in_path)
        categorizer = cls(
            vectorizer=bundle["vectorizer"],
            classifiers=bundle["classifiers"],
            thresholds=bundle.get("thresholds"),
            tags=bundle.get("tags"),
            model_version=bundle.get("model_version", "1.0.1"),
            metadata=bundle.get("metadata", {}),
        )
        return categorizer
