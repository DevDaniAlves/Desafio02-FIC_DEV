import numpy as np
import pytest

from src.embeddings import cosine_scores, top_k


class StubEmbeddingService:
    def encode(self, texts: list[str]) -> np.ndarray:
        mapping = {
            "python": [1.0, 0.0],
            "erro no pip": [0.9, 0.1],
            "problema de senha": [0.0, 1.0],
        }
        return np.asarray([mapping[text] for text in texts], dtype=float)


def test_cosine_identical_and_orthogonal():
    scores = cosine_scores(np.array([1.0, 0.0]), np.array([[1.0, 0.0], [0.0, 1.0]]))
    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(0.0)


def test_cosine_empty_matrix():
    scores = cosine_scores(np.array([1.0, 0.0]), np.empty((0, 2)))
    assert scores.shape == (0,)


def test_top_k_orders_by_similarity():
    ranked = top_k(
        "python",
        ["problema de senha", "erro no pip"],
        StubEmbeddingService(),
        k=2,
    )
    assert [index for index, _score in ranked] == [1, 0]
    assert ranked[0][1] > ranked[1][1]


def test_top_k_empty_or_invalid():
    service = StubEmbeddingService()
    assert top_k("python", [], service) == []
    assert top_k("python", ["erro no pip"], service, k=0) == []
