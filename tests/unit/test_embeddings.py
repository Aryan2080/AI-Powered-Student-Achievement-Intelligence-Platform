"""Unit tests for dense vector embeddings and cosine similarity."""
import math
import pytest
from src.recommendation.embeddings import TextEmbeddingEngine, compute_cosine_similarity


def test_embedding_dimension_and_norm():
    engine = TextEmbeddingEngine()
    vec = engine.encode("FastAPI backend with PyTorch deep learning")
    assert len(vec) == 384
    norm = math.sqrt(sum(x * x for x in vec))
    assert norm == pytest.approx(1.0, rel=1e-3)


def test_cosine_similarity_symmetry_and_bounds():
    engine = TextEmbeddingEngine()
    v1 = engine.encode("Computer Vision with OpenCV and YOLO")
    v2 = engine.encode("Image segmentation using deep neural networks")
    v3 = engine.encode("Classical financial accounting procedures")

    sim_related = compute_cosine_similarity(v1, v2)
    sim_unrelated = compute_cosine_similarity(v1, v3)

    assert 0.0 <= sim_related <= 1.0
    assert 0.0 <= sim_unrelated <= 1.0
    assert sim_related > sim_unrelated
