"""Geração de embeddings locais e comparação por cosseno (RF11).

O modelo padrão (`paraphrase-multilingual-MiniLM-L12-v2`) roda offline e
cobre português. Os vetores saem normalizados para a similaridade de cosseno
coincidir com o produto interno usado no Chroma (`hnsw:space: cosine`).
"""

from __future__ import annotations

import numpy as np


class EmbeddingService:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=float)
        return np.asarray(
            self.model.encode(texts, normalize_embeddings=True),
            dtype=float,
        )


def cosine_scores(query_vector: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    query = np.asarray(query_vector, dtype=float).reshape(-1)
    data = np.asarray(matrix, dtype=float)
    if data.size == 0:
        return np.empty((0,), dtype=float)
    query_norm = np.linalg.norm(query)
    data_norm = np.linalg.norm(data, axis=1)
    denominator = np.where(data_norm * query_norm == 0, 1, data_norm * query_norm)
    return (data @ query) / denominator


def top_k(
    query: str,
    texts: list[str],
    service: EmbeddingService,
    k: int = 5,
) -> list[tuple[int, float]]:
    if not texts or k <= 0:
        return []
    vectors = service.encode([query, *texts])
    scores = cosine_scores(vectors[0], vectors[1:])
    order = np.argsort(scores)[::-1][: min(k, len(texts))]
    return [(int(index), float(scores[index])) for index in order]
