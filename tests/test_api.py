from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["modo"] in {
        "rag_openai",
        "rag_gemini",
        "recuperacao_local",
    }


def test_root_lists_endpoints():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["endpoints"]["ask"] == "POST /ask"


def test_ask_validation():
    response = client.post("/ask", json={"pergunta": "x"})
    assert response.status_code == 422


@patch("src.api.semantic_query")
def test_ask_returns_local_payload(mock_query, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    mock_query.return_value = [
        {
            "protocolo": "AT-001",
            "documento": "a.pdf",
            "pagina": 1,
            "indice": 0,
            "chunk_id": 4,
            "conteudo": "Erro no pip.",
            "similaridade": 0.81,
        }
    ]
    response = client.post(
        "/ask",
        json={
            "pergunta": "Quais erros de Python?",
            "top_k": 3,
            "categoria": "Python e bibliotecas",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["modo"] == "recuperacao_local"
    assert body["fontes"][0]["protocolo"] == "AT-001"
    mock_query.assert_called_once()
    args, _kwargs = mock_query.call_args
    assert args[1] == "Quais erros de Python?"
    assert args[2] == 3
    assert args[3] == "Python e bibliotecas"


@patch("src.api.semantic_query")
def test_ask_empty_index_is_ok(mock_query, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    mock_query.return_value = []
    response = client.post("/ask", json={"pergunta": "Quais erros de Python?"})
    assert response.status_code == 200
    assert response.json()["modo"] == "sem_fontes"


@patch("src.api.semantic_query", side_effect=RuntimeError("chroma fora"))
def test_ask_unavailable_index_returns_503(_mock_query):
    response = client.post("/ask", json={"pergunta": "Quais erros de Python?"})
    assert response.status_code == 503
    assert "Consulta indisponível" in response.json()["detail"]
