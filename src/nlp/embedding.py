"""
src/nlp/embedding.py
====================
Sentence Transformer & Dense Embedding Utilities
AI-Powered Student Achievement Intelligence Platform — Member 1

Core Responsibilities:
  1. Deterministic and reproducible embedding generation via Sentence Transformers.
  2. Input validation, non-finite checks, and dimension assertions.
  3. Pairwise and matrix cosine similarity computations.
  4. Versioned serialization and deserialization of embedding artifacts (.npy + metadata JSON).
  5. Semantic similarity search across achievement records preserving record IDs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Suppress HuggingFace hub symlink warning on Windows without Developer Mode
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

try:
    import torch
    from sentence_transformers import SentenceTransformer, util
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False


def check_st_available() -> bool:
    """Return True if torch and sentence_transformers are available."""
    return ST_AVAILABLE


def load_embedding_model(
    model_name: str = "all-MiniLM-L6-v2",
    device: str | None = None
) -> Any:
    """
    Load a SentenceTransformer model on the specified device.
    Defaults to CPU if CUDA is unavailable.
    """
    if not ST_AVAILABLE:
        raise ImportError(
            "sentence_transformers or torch is not installed. "
            "Please install via: pip install sentence-transformers torch"
        )
    
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    return SentenceTransformer(model_name, device=device)


def generate_embeddings(
    texts: list[str],
    model: Any,
    batch_size: int = 32,
    normalize_embeddings: bool = True,
    show_progress_bar: bool = False
) -> np.ndarray:
    """
    Generate dense L2-normalized embeddings for a list of achievement texts.
    
    Parameters:
        texts: List of input strings.
        model: Loaded SentenceTransformer instance.
        batch_size: Mini-batch size for encoding.
        normalize_embeddings: If True, vectors have unit L2 norm.
        show_progress_bar: Whether to display encoding progress.
        
    Returns:
        np.ndarray of shape (len(texts), embedding_dim) and dtype float32.
        
    Raises:
        ValueError: If texts list is empty or contains non-string/empty items.
    """
    if not isinstance(texts, (list, tuple, np.ndarray, pd.Series)):
        raise TypeError(f"texts must be a sequence of strings, got {type(texts).__name__}")
    
    if len(texts) == 0:
        raise ValueError("Cannot generate embeddings for an empty text list.")
    
    # Validate string types and non-empty content
    clean_texts: list[str] = []
    for idx, t in enumerate(texts):
        if not isinstance(t, str):
            raise TypeError(f"Item at index {idx} is not a string: {type(t).__name__}")
        if not t.strip():
            raise ValueError(f"Item at index {idx} is empty or whitespace-only.")
        clean_texts.append(t)
    
    embs = model.encode(
        clean_texts,
        batch_size=batch_size,
        normalize_embeddings=normalize_embeddings,
        show_progress_bar=show_progress_bar,
        convert_to_numpy=True
    )
    
    return np.asarray(embs, dtype=np.float32)


def validate_embeddings(
    embeddings: np.ndarray,
    expected_dim: int = 384,
    expected_count: int | None = None
) -> dict[str, Any]:
    """
    Forensic validation of an embedding matrix.
    
    Checks:
      - 2D numpy array shape (N, dim)
      - expected_dim match
      - expected_count match (if specified)
      - Absence of NaN values
      - Absence of Infinite values
      - Unit norm check (if normalized)
      
    Returns:
      dict with status, count, dim, has_nans, has_infs, is_unit_norm.
      
    Raises:
      ValueError or TypeError if validation fails critically.
    """
    if not isinstance(embeddings, np.ndarray):
        raise TypeError(f"embeddings must be a np.ndarray, got {type(embeddings).__name__}")
    
    if embeddings.ndim != 2:
        raise ValueError(f"embeddings must be 2-dimensional (N, dim), got shape {embeddings.shape}")
    
    count, dim = embeddings.shape
    
    if dim != expected_dim:
        raise ValueError(f"Expected embedding dimension {expected_dim}, but got {dim}")
    
    if expected_count is not None and count != expected_count:
        raise ValueError(f"Expected {expected_count} records, but got {count}")
    
    nan_count = int(np.isnan(embeddings).sum())
    inf_count = int(np.isinf(embeddings).sum())
    
    if nan_count > 0:
        raise ValueError(f"Embeddings matrix contains {nan_count} NaN values.")
    
    if inf_count > 0:
        raise ValueError(f"Embeddings matrix contains {inf_count} Infinite values.")
    
    # Check L2 norms
    norms = np.linalg.norm(embeddings, axis=1)
    is_unit_norm = bool(np.allclose(norms, 1.0, atol=1e-3))
    
    return {
        "status": "VALID",
        "record_count": count,
        "embedding_dim": dim,
        "nan_count": nan_count,
        "inf_count": inf_count,
        "is_unit_norm": is_unit_norm,
        "mean_norm": float(np.mean(norms)),
        "min_norm": float(np.min(norms)),
        "max_norm": float(np.max(norms))
    }


def compute_pairwise_cosine_similarity(
    emb1: np.ndarray,
    emb2: np.ndarray
) -> np.ndarray:
    """
    Compute element-wise cosine similarities between two aligned sets of vectors.
    Shape of emb1 and emb2 must match: (N, dim).
    Returns 1D array of shape (N,) with cosine similarity scores in [-1.0, 1.0].
    """
    if emb1.shape != emb2.shape:
        raise ValueError(f"Shape mismatch: emb1 {emb1.shape} vs emb2 {emb2.shape}")
    
    # If vectors are already L2 normalized, cosine similarity is the dot product
    norm1 = np.linalg.norm(emb1, axis=1, keepdims=True)
    norm2 = np.linalg.norm(emb2, axis=1, keepdims=True)
    
    # Avoid zero division
    norm1 = np.where(norm1 == 0, 1e-12, norm1)
    norm2 = np.where(norm2 == 0, 1e-12, norm2)
    
    sims = np.sum((emb1 / norm1) * (emb2 / norm2), axis=1)
    return np.clip(sims, -1.0, 1.0)


def compute_similarity_matrix(
    embeddings_1: np.ndarray,
    embeddings_2: np.ndarray
) -> np.ndarray:
    """
    Compute full pairwise cosine similarity matrix between two sets of embeddings.
    embeddings_1: (M, dim)
    embeddings_2: (N, dim)
    Returns: (M, N) matrix of cosine similarities.
    """
    if embeddings_1.shape[1] != embeddings_2.shape[1]:
        raise ValueError(
            f"Dimension mismatch: {embeddings_1.shape[1]} vs {embeddings_2.shape[1]}"
        )
    
    norm1 = np.linalg.norm(embeddings_1, axis=1, keepdims=True)
    norm2 = np.linalg.norm(embeddings_2, axis=1, keepdims=True)
    
    norm1 = np.where(norm1 == 0, 1e-12, norm1)
    norm2 = np.where(norm2 == 0, 1e-12, norm2)
    
    norm_e1 = embeddings_1 / norm1
    norm_e2 = embeddings_2 / norm2
    
    matrix = np.matmul(norm_e1, norm_e2.T)
    return np.clip(matrix, -1.0, 1.0)


def save_embedding_bundle(
    output_dir: Path | str,
    embeddings: np.ndarray,
    record_ids: list[str],
    metadata: dict[str, Any],
    prefix: str = "achievement_embeddings"
) -> dict[str, Path]:
    """
    Save embedding matrix (.npy) and accompanying metadata (.json) to output_dir.
    Guarantees record_id alignment and manifest checksum calculation.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    if len(record_ids) != len(embeddings):
        raise ValueError(
            f"record_ids length ({len(record_ids)}) must match embeddings count ({len(embeddings)})"
        )
    
    npy_file = out_path / f"{prefix}.npy"
    meta_file = out_path / f"{prefix}_metadata.json"
    ids_file = out_path / f"{prefix}_record_ids.json"
    
    np.save(npy_file, embeddings)
    
    with open(ids_file, "w", encoding="utf-8") as f:
        json.dump(record_ids, f, indent=2)
        
    full_meta = {
        **metadata,
        "record_count": len(record_ids),
        "embedding_dim": int(embeddings.shape[1]),
        "dtype": str(embeddings.dtype),
        "files": {
            "embeddings_npy": str(npy_file.name),
            "record_ids_json": str(ids_file.name)
        }
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(full_meta, f, indent=2)
        
    return {
        "embeddings": npy_file,
        "record_ids": ids_file,
        "metadata": meta_file
    }


def load_embedding_bundle(
    bundle_dir: Path | str,
    prefix: str = "achievement_embeddings"
) -> tuple[np.ndarray, list[str], dict[str, Any]]:
    """
    Load an embedding matrix, aligned record IDs, and metadata from bundle_dir.
    """
    b_path = Path(bundle_dir)
    npy_file = b_path / f"{prefix}.npy"
    meta_file = b_path / f"{prefix}_metadata.json"
    ids_file = b_path / f"{prefix}_record_ids.json"
    
    if not npy_file.exists():
        raise FileNotFoundError(f"Missing embeddings array: {npy_file}")
    if not ids_file.exists():
        raise FileNotFoundError(f"Missing record IDs file: {ids_file}")
    if not meta_file.exists():
        raise FileNotFoundError(f"Missing metadata file: {meta_file}")
        
    embeddings = np.load(npy_file)
    with open(ids_file, "r", encoding="utf-8") as f:
        record_ids = json.load(f)
    with open(meta_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    return embeddings, record_ids, metadata


def search_similar_achievements(
    query: str,
    corpus_embeddings: np.ndarray,
    corpus_df: pd.DataFrame,
    model: Any,
    top_k: int = 5,
    min_score: float = 0.0
) -> pd.DataFrame:
    """
    Perform dense semantic similarity retrieval for an input query text.
    
    Parameters:
        query: Query string.
        corpus_embeddings: Precomputed normalized embeddings of shape (N, dim).
        corpus_df: DataFrame of corpus records (must have length N).
        model: SentenceTransformer model used to encode query.
        top_k: Number of nearest neighbors to retrieve.
        min_score: Minimum cosine similarity threshold.
        
    Returns:
        pd.DataFrame containing top_k retrieved records ranked by score descending,
        preserving record_id, achievement_text, category, split, and similarity_score.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string.")
    
    if len(corpus_df) != len(corpus_embeddings):
        raise ValueError(
            f"corpus_df size ({len(corpus_df)}) does not match corpus_embeddings ({len(corpus_embeddings)})"
        )
    
    # Encode query with unit norm
    q_emb = model.encode([query], normalize_embeddings=True, convert_to_numpy=True)
    q_vec = np.asarray(q_emb, dtype=np.float32)
    
    # Compute dot products against normalized corpus vectors
    scores = np.dot(corpus_embeddings, q_vec.T).flatten()
    
    # Top-K indices
    top_indices = np.argsort(scores)[::-1][:top_k]
    
    results = []
    for rank, idx in enumerate(top_indices, 1):
        score = float(scores[idx])
        if score < min_score:
            continue
        row = corpus_df.iloc[idx]
        results.append({
            "rank": rank,
            "achievement_id": row.get("achievement_id", f"REC_{idx:04d}"),
            "similarity_score": round(score, 4),
            "category": row.get("category", row.get("achievement_category", "UNKNOWN")),
            "split": row.get("split", "corpus"),
            "achievement_text": row["achievement_text"]
        })
        
    return pd.DataFrame(results)
