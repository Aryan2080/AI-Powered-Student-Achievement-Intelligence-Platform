"""Contract tests for Member 1 NLP integration."""
from src.integration.nlp_adapter import Member1NLPAdapter


def test_member1_adapter_normalization_and_skill_extraction():
    adapter = Member1NLPAdapter()
    raw = "Engineered a Deep Learning Model in Python and PyTorch for Real-Time Object Detection with OpenCV."
    norm = adapter.clean_and_normalize(raw)
    skills = adapter.extract_canonical_skills(raw)

    assert "deep learning" in norm.lower()
    assert "Python" in skills
    assert "PyTorch" in skills
    assert "OpenCV" in skills


def test_member1_adapter_domain_tag_inference():
    adapter = Member1NLPAdapter()
    tags = adapter.infer_domain_tags_from_text("Autonomous agent using BERT and natural language understanding.")
    assert "lbl_domain_nlp" in tags
