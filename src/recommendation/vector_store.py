"""
src/recommendation/vector_store.py
==================================
In-memory vector store supporting fast nearest-neighbor cosine similarity search.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.core.logging import logger
from src.recommendation.embeddings import (
    TextEmbeddingEngine,
    compute_cosine_similarity,
    load_npy_array,
    save_npy_array,
)


class VectorStore:
    """Fast, in-memory cosine similarity vector index."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.ids: List[str] = []
        self.vectors: List[List[float]] = []
        self.metadata: Dict[str, Dict[str, Any]] = {}

    def add(self, item_id: str, vector: List[float], meta: Optional[Dict[str, Any]] = None) -> None:
        """Add an item vector and optional metadata to the index."""
        if len(vector) != self.dimension:
            raise ValueError(f"Vector dimension {len(vector)} does not match index dimension {self.dimension}")
        self.ids.append(item_id)
        self.vectors.append(vector)
        if meta:
            self.metadata[item_id] = meta

    def search(self, query_vector: List[float], top_k: int = 10) -> List[Tuple[str, float]]:
        """Search top_k nearest items by cosine similarity."""
        if not self.vectors:
            return []
        if len(query_vector) != self.dimension:
            raise ValueError(f"Query vector dimension {len(query_vector)} != {self.dimension}")

        scores: List[Tuple[str, float]] = []
        for item_id, vec in zip(self.ids, self.vectors):
            score = compute_cosine_similarity(query_vector, vec)
            scores.append((item_id, score))

        # Sort descending by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def save(self, filepath: Union[str, Path]) -> None:
        """Persist vectors to .npy file."""
        save_npy_array(self.vectors, filepath)
        logger.info("Saved %d vectors to %s", len(self.vectors), filepath)

    def load(self, filepath: Union[str, Path], ids: List[str]) -> None:
        """Load vectors from .npy file with corresponding item IDs."""
        loaded_vectors = load_npy_array(filepath)
        if len(loaded_vectors) != len(ids):
            raise ValueError(f"ID count ({len(ids)}) does not match vector count ({len(loaded_vectors)})")
        self.ids = ids
        self.vectors = loaded_vectors
        logger.info("Loaded %d vectors from %s", len(self.vectors), filepath)

    def __len__(self) -> int:
        return len(self.vectors)
