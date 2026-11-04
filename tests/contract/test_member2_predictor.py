"""Contract tests for Member 2 ML model inference."""
from src.integration.ml_model_adapter import Member2PredictorAdapter, FakePredictor
from src.nlp.taxonomy import ACHIEVEMENT_CATEGORIES, DOMAIN_TAGS


def test_member2_fakepredictor_contract():
    pred = FakePredictor()
    res = pred.predict("Won 1st prize at national robotics hackathon building autonomous rovers.")

    assert res["primary_classification"]["category"] == "HACKATHON"
    assert res["primary_classification"]["category"] in ACHIEVEMENT_CATEGORIES
    assert 0.0 <= res["primary_classification"]["confidence"] <= 1.0
    assert "mock" in res["model_version"].lower()

    # Domain tags check
    domain_tags = res["domain_categorization"]["tags"]
    for t in domain_tags:
        assert t in DOMAIN_TAGS


def test_member2_adapter_graceful_fallback():
    adapter = Member2PredictorAdapter()
    res = adapter.predict("Published a paper in IEEE conference on deep learning.")
    assert res["primary_classification"]["category"] in ACHIEVEMENT_CATEGORIES
    assert res["inference_status"] in ["SUCCESS_V1", "SUCCESS_MOCK", "SUCCESS_V2"]
