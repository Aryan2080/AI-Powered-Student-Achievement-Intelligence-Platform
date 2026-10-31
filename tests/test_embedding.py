"""
tests/test_embedding.py
=======================
Unit tests for Sentence Transformer embedding utilities
AI-Powered Student Achievement Intelligence Platform — Member 1
"""
import json
import numpy as np
import pandas as pd
import pytest

from nlp.embedding import (
    check_st_available,
    load_embedding_model,
    generate_embeddings,
    validate_embeddings,
    compute_pairwise_cosine_similarity,
    compute_similarity_matrix,
    save_embedding_bundle,
    load_embedding_bundle,
    search_similar_achievements,
)


@pytest.fixture(scope="module")
def model():
    """Shared lightweight embedding model fixture."""
    if not check_st_available():
        pytest.skip("Sentence Transformers / PyTorch not available in this environment")
    return load_embedding_model("all-MiniLM-L6-v2", device="cpu")


class TestEmbeddingGeneration:
    def test_embedding_dimensionality_and_norm(self, model):
        texts = [
            "Won 1st place in Smart India Hackathon 2023.",
            "Published research paper on deep learning in IEEE conference."
        ]
        embs = generate_embeddings(texts, model, batch_size=2, normalize_embeddings=True)
        assert isinstance(embs, np.ndarray)
        assert embs.shape == (2, 384)
        assert embs.dtype == np.float32
        
        # Check L2 norms are ~1.0
        norms = np.linalg.norm(embs, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-3)

    def test_empty_input_list_raises_valueerror(self, model):
        with pytest.raises(ValueError, match="Cannot generate embeddings for an empty text list"):
            generate_embeddings([], model)

    def test_invalid_input_types_raise_typeerror(self, model):
        with pytest.raises(TypeError):
            generate_embeddings(None, model)
            
        with pytest.raises(TypeError, match="not a string"):
            generate_embeddings(["Valid text", 12345], model)

    def test_whitespace_only_string_raises_valueerror(self, model):
        with pytest.raises(ValueError, match="empty or whitespace-only"):
            generate_embeddings(["   ", "Another achievement"], model)

    def test_reproducibility(self, model):
        text = ["Co-inventor on patent application #20241098 filed with EPO."]
        emb1 = generate_embeddings(text, model)
        emb2 = generate_embeddings(text, model)
        assert np.allclose(emb1, emb2, atol=1e-6)


class TestEmbeddingValidation:
    def test_validate_valid_embeddings(self):
        embs = np.random.randn(10, 384).astype(np.float32)
        embs /= np.linalg.norm(embs, axis=1, keepdims=True)
        res = validate_embeddings(embs, expected_dim=384, expected_count=10)
        assert res["status"] == "VALID"
        assert res["record_count"] == 10
        assert res["embedding_dim"] == 384
        assert res["nan_count"] == 0
        assert res["inf_count"] == 0
        assert res["is_unit_norm"] is True

    def test_validate_dimension_mismatch_raises(self):
        embs = np.random.randn(5, 128).astype(np.float32)
        with pytest.raises(ValueError, match="Expected embedding dimension 384"):
            validate_embeddings(embs, expected_dim=384)

    def test_validate_count_mismatch_raises(self):
        embs = np.random.randn(5, 384).astype(np.float32)
        with pytest.raises(ValueError, match="Expected 10 records"):
            validate_embeddings(embs, expected_dim=384, expected_count=10)

    def test_validate_nan_detection_raises(self):
        embs = np.random.randn(4, 384).astype(np.float32)
        embs[1, 10] = np.nan
        with pytest.raises(ValueError, match="contains 1 NaN values"):
            validate_embeddings(embs, expected_dim=384)

    def test_validate_inf_detection_raises(self):
        embs = np.random.randn(4, 384).astype(np.float32)
        embs[2, 20] = np.inf
        with pytest.raises(ValueError, match="contains 1 Infinite values"):
            validate_embeddings(embs, expected_dim=384)


class TestSimilarityCalculations:
    def test_identical_vectors_have_similarity_one(self):
        v = np.random.randn(3, 384).astype(np.float32)
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        sims = compute_pairwise_cosine_similarity(v, v)
        assert np.allclose(sims, 1.0, atol=1e-5)

    def test_orthogonal_vectors_have_similarity_zero(self):
        v1 = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        v2 = np.array([[0.0, 1.0, 0.0]], dtype=np.float32)
        sims = compute_pairwise_cosine_similarity(v1, v2)
        assert np.allclose(sims, 0.0, atol=1e-5)

    def test_similarity_matrix_shape(self):
        v1 = np.random.randn(4, 384).astype(np.float32)
        v2 = np.random.randn(6, 384).astype(np.float32)
        mat = compute_similarity_matrix(v1, v2)
        assert mat.shape == (4, 6)
        assert np.all(mat >= -1.0) and np.all(mat <= 1.0)


class TestBundlePersistence:
    def test_save_and_load_embedding_bundle(self, tmp_path):
        embs = np.random.randn(5, 384).astype(np.float32)
        record_ids = [f"ACH_{i:04d}" for i in range(5)]
        meta = {"model_name": "all-MiniLM-L6-v2", "version": "1.0.0"}
        
        bundle = save_embedding_bundle(tmp_path, embs, record_ids, meta, prefix="test_bundle")
        assert bundle["embeddings"].exists()
        assert bundle["record_ids"].exists()
        assert bundle["metadata"].exists()
        
        loaded_embs, loaded_ids, loaded_meta = load_embedding_bundle(tmp_path, prefix="test_bundle")
        assert np.allclose(embs, loaded_embs)
        assert loaded_ids == record_ids
        assert loaded_meta["model_name"] == "all-MiniLM-L6-v2"
        assert loaded_meta["record_count"] == 5

    def test_mismatched_ids_and_embeddings_raises(self, tmp_path):
        embs = np.random.randn(5, 384).astype(np.float32)
        record_ids = ["ACH_1", "ACH_2"]  # only 2 IDs for 5 embs
        with pytest.raises(ValueError, match="must match embeddings count"):
            save_embedding_bundle(tmp_path, embs, record_ids, {}, prefix="bad_bundle")


class TestSemanticSearch:
    def test_search_similar_achievements_returns_ranked_dataframe(self, model):
        corpus_df = pd.DataFrame([
            {"achievement_id": "ACH001", "achievement_text": "Won 1st prize in hackathon developing AI vision app.", "category": "HACKATHON", "split": "train"},
            {"achievement_id": "ACH002", "achievement_text": "Published a robotics paper in an IEEE international conference.", "category": "RESEARCH_PUBLICATION", "split": "train"},
            {"achievement_id": "ACH003", "achievement_text": "Captained university soccer team to state athletics finals.", "category": "SPORTS", "split": "validation"}
        ])
        corpus_embs = generate_embeddings(corpus_df["achievement_text"].tolist(), model)
        
        query = "Winner in programming coding contest"
        res = search_similar_achievements(query, corpus_embs, corpus_df, model, top_k=2)
        
        assert isinstance(res, pd.DataFrame)
        assert len(res) == 2
        assert "rank" in res.columns
        assert "similarity_score" in res.columns
        assert res.iloc[0]["rank"] == 1
        # Top result should be the hackathon achievement
        assert res.iloc[0]["achievement_id"] == "ACH001"
        assert res.iloc[0]["category"] == "HACKATHON"
        assert res.iloc[0]["similarity_score"] > res.iloc[1]["similarity_score"]
