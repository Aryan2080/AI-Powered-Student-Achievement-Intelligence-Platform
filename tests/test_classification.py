"""
tests/test_classification.py
=============================
Unit tests for the Primary Achievement Classification Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from src.nlp.classification import (
    ACHIEVEMENT_CATEGORIES,
    AchievementClassifier,
    ClassificationResult,
)


@pytest.fixture(scope="module")
def trained_classifier() -> AchievementClassifier:
    """Fixture that fits an AchievementClassifier on a compact multi-class sample."""
    sample_texts = [
        "Won 1st prize in National Hackathon 2023 with Python team.",
        "Published research paper in IEEE Transactions on Machine Learning.",
        "Completed AWS Certified Solutions Architect Professional exam.",
        "Organized Inter-College Cultural Fest and Classical Dance Evening.",
        "Captained University Athletics Team to victory in 400m relay race.",
        "Completed Summer Software Engineering Internship at Microsoft.",
        "Filed international patent for low-power biomedical sensor design.",
        "Volunteered 100 hours teaching underprivileged children with NGO.",
        "Attended 3-day technical workshop on ROS 2 and Robotics Navigation.",
        "Delivered keynote presentation at International AI Conference.",
        "Built full-stack open source student portal project on GitHub.",
        "Elected as President of ACM Student Chapter for annual tenure.",
        "Participated in regional collegiate math olympiad competition.",
        "Awarded university merit commendation for extracurricular activities.",
    ]
    sample_labels = [
        "HACKATHON",
        "RESEARCH_PUBLICATION",
        "CERTIFICATION",
        "CULTURAL",
        "SPORTS",
        "INTERNSHIP",
        "PATENT",
        "VOLUNTEERING",
        "WORKSHOP",
        "CONFERENCE",
        "PROJECT",
        "LEADERSHIP",
        "COMPETITION",
        "OTHER",
    ]
    clf = AchievementClassifier(model_version="1.0.1-test")
    clf.fit(sample_texts, sample_labels, max_features=500)
    return clf


def test_valid_input_prediction(trained_classifier: AchievementClassifier) -> None:
    """Condition 1 & 2: Valid input prediction returns ClassificationResult."""
    text = "Participated in 24-hour hackathon and won best hardware award."
    res = trained_classifier.predict_record(text)
    assert isinstance(res, ClassificationResult)
    assert res.predicted_category in ACHIEVEMENT_CATEGORIES
    assert 0.0 <= res.confidence <= 1.0
    assert len(res.category_scores) == len(ACHIEVEMENT_CATEGORIES)


def test_empty_input_handling(trained_classifier: AchievementClassifier) -> None:
    """Condition 3: Empty string returns fallback OTHER with uniform confidence."""
    res = trained_classifier.predict_record("")
    assert res.predicted_category == "OTHER"
    assert "Empty or non-textual input" in res.audit_metadata.get("warning", "")


def test_missing_text_handling(trained_classifier: AchievementClassifier) -> None:
    """Condition 4: None or NaN input returns safe fallback."""
    res_none = trained_classifier.predict_record(None)  # type: ignore
    assert res_none.predicted_category == "OTHER"

    res_nan = trained_classifier.predict_record({"achievement_text": float("nan")})
    assert res_nan.predicted_category == "OTHER"


def test_invalid_input_type(trained_classifier: AchievementClassifier) -> None:
    """Condition 5: Invalid input types raise TypeError."""
    with pytest.raises(TypeError):
        trained_classifier.predict_record([1, 2, 3])  # type: ignore


def test_category_mapping(trained_classifier: AchievementClassifier) -> None:
    """Condition 6: Master category mapping contains all 14 categories."""
    assert len(ACHIEVEMENT_CATEGORIES) == 14
    for cat in [
        "HACKATHON", "RESEARCH_PUBLICATION", "CERTIFICATION", "CULTURAL",
        "SPORTS", "INTERNSHIP", "PATENT", "VOLUNTEERING", "WORKSHOP",
        "CONFERENCE", "PROJECT", "LEADERSHIP", "COMPETITION", "OTHER"
    ]:
        assert cat in ACHIEVEMENT_CATEGORIES


def test_single_record_dict_input(trained_classifier: AchievementClassifier) -> None:
    """Condition 7: Accepts dictionary representation of achievement record."""
    record = {
        "achievement_id": "ACH-00999",
        "achievement_text": "Completed AWS Cloud Practitioner examination with 92% score.",
    }
    res = trained_classifier.predict_record(record)
    assert res.audit_metadata.get("record_id") == "ACH-00999"
    assert res.predicted_category in ACHIEVEMENT_CATEGORIES


def test_batch_prediction(trained_classifier: AchievementClassifier) -> None:
    """Condition 8: Batch inference over list and DataFrame."""
    texts = [
        "Presented machine learning poster at AI Conference.",
        "Gold medalist in 100m sprint athletics meet.",
    ]
    batch_res = trained_classifier.predict_batch(texts)
    assert len(batch_res) == 2
    assert all(isinstance(r, ClassificationResult) for r in batch_res)

    df = pd.DataFrame({"achievement_text": texts, "achievement_id": ["A1", "A2"]})
    df_res = trained_classifier.predict_batch(df)
    assert len(df_res) == 2
    assert df_res[0].audit_metadata.get("record_id") == "A1"


def test_prediction_reproducibility(trained_classifier: AchievementClassifier) -> None:
    """Condition 9: Predictions are 100% deterministic and reproducible."""
    text = "Co-inventor on patent application for implantable medical device."
    run1 = trained_classifier.predict_record(text)
    run2 = trained_classifier.predict_record(text)
    assert run1.predicted_category == run2.predicted_category
    assert run1.confidence == run2.confidence
    assert run1.category_scores == run2.category_scores


def test_output_schema(trained_classifier: AchievementClassifier) -> None:
    """Condition 10: ClassificationResult matches strict output contract."""
    res = trained_classifier.predict_record("Completed summer internship at tech startup.")
    res_dict = res.to_dict()
    assert "predicted_category" in res_dict
    assert "confidence" in res_dict
    assert "category_scores" in res_dict
    assert "normalized_text" in res_dict
    assert "model_version" in res_dict
    assert "audit_metadata" in res_dict


def test_model_save_and_load(trained_classifier: AchievementClassifier) -> None:
    """Condition 11: Model serialization and loading via joblib preserves predictions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_path = Path(tmp_dir) / "test_classifier.joblib"
        trained_classifier.save(model_path)
        assert model_path.exists()
        assert model_path.with_suffix(".json").exists()

        loaded_clf = AchievementClassifier.load(model_path)
        assert loaded_clf.is_fitted is True

        text = "Published peer-reviewed paper in IEEE journal."
        pred_orig = trained_classifier.predict_record(text)
        pred_loaded = loaded_clf.predict_record(text)

        assert pred_orig.predicted_category == pred_loaded.predicted_category
        assert abs(pred_orig.confidence - pred_loaded.confidence) < 1e-6
