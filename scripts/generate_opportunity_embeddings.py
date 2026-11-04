"""
scripts/generate_opportunity_embeddings.py
==========================================
Python CLI for batch embedding generation and validation for opportunities.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import json
from pathlib import Path
from src.core.config import settings
from src.recommendation.embeddings import TextEmbeddingEngine, save_npy_array


def main():
    json_path = settings.OPPORTUNITIES_JSON_PATH
    output_npy = settings.OPPORTUNITY_EMBEDDINGS_PATH

    print(f"Reading opportunities from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        opportunities = json.load(f)

    engine = TextEmbeddingEngine(model_name=settings.EMBEDDING_MODEL_NAME)
    texts = [engine.compose_opportunity_text(opp) for opp in opportunities]

    print(f"Generating 384-d embeddings for {len(texts)} opportunities...")
    vectors = engine.encode_batch(texts)

    output_npy.parent.mkdir(parents=True, exist_ok=True)
    save_npy_array(vectors, output_npy)
    print(f"Successfully saved embeddings to {output_npy}")
    print(f"Matrix shape: ({len(vectors)}, {len(vectors[0])})")


if __name__ == "__main__":
    main()
