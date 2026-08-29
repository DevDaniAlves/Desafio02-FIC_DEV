import pytest

from src.indexer import _row_from_match
from src.vector_store import ChromaStore


def test_query_returns_id_and_sync_removes_orphans(tmp_path):
    pytest.importorskip("chromadb")
    store = ChromaStore(tmp_path / "chroma", "atendimentos")
    store.sync(
        ["1", "2"],
        ["primeiro", "segundo"],
        [
            {"protocolo": "AT-001", "chunk_id": 1, "indice": 0, "pagina": 1},
            {"protocolo": "AT-002", "chunk_id": 2, "indice": 0, "pagina": 2},
        ],
        [[1.0, 0.0], [0.0, 1.0]],
    )
    store.sync(
        ["2"],
        ["segundo"],
        [{"protocolo": "AT-002", "chunk_id": 2, "indice": 0, "pagina": 2}],
        [[0.0, 1.0]],
    )
    rows = store.query([0.0, 1.0], top_k=5)
    ids = [row["id"] for row in rows]
    assert ids == ["2"]
    assert rows[0]["metadata"]["protocolo"] == "AT-002"
    assert rows[0]["metadata"]["chunk_id"] == 2


def test_query_on_empty_collection_returns_empty_list(tmp_path):
    pytest.importorskip("chromadb")
    store = ChromaStore(tmp_path / "chroma", "atendimentos")
    assert store.query([0.1, 0.2], top_k=5) == []


def test_semantic_row_exposes_chunk_id():
    row = _row_from_match(
        {
            "id": "12",
            "conteudo": "trecho",
            "metadata": {
                "protocolo": "AT-001",
                "documento": "a.pdf",
                "pagina": 1,
                "categoria": "Instalação",
                "indice": 0,
            },
            "similaridade": 0.87654,
        }
    )
    assert row["chunk_id"] == 12
    assert row["protocolo"] == "AT-001"
    assert row["documento"] == "a.pdf"
    assert row["pagina"] == 1
    assert row["indice"] == 0
    assert row["conteudo"] == "trecho"
    assert row["similaridade"] == 0.8765
