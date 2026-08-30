from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)
COTA_OK = {
    "pode_consultar": True,
    "motivo": None,
    "restantes": 2,
    "autenticado": False,
}


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


def test_cadastro_rejeita_email_duplicado():
    payload = {"email": "unico.teste@exemplo.br", "senha": "segredo1"}
    first = client.post("/auth/cadastro", json=payload)
    assert first.status_code == 200
    second = client.post("/auth/cadastro", json=payload)
    assert second.status_code == 409


@patch("src.api.estado_cota", return_value={"pode_consultar": False, "motivo": "cadastro"})
def test_ask_blocks_when_free_quota_is_over(_cota):
    response = client.post("/ask", json={"pergunta": "Quais erros de Python?"})
    assert response.status_code == 402
    assert "3 consultas grátis" in response.json()["detail"]["mensagem"]


@patch("src.api.consumir_consulta", return_value=COTA_OK)
@patch("src.api.estado_cota", return_value=COTA_OK)
@patch("src.api.classify_query", return_value="ktop")
@patch("src.api.semantic_query")
def test_ask_returns_local_payload(mock_query, _mock_scope, _cota, _uso, monkeypatch):
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


@patch("src.api.consumir_consulta", return_value=COTA_OK)
@patch("src.api.estado_cota", return_value=COTA_OK)
@patch("src.api.classify_query", return_value="ktop")
@patch("src.api.semantic_query")
def test_ask_empty_index_is_ok(mock_query, _mock_scope, _cota, _uso, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    mock_query.return_value = []
    response = client.post("/ask", json={"pergunta": "Quais erros de Python?"})
    assert response.status_code == 200
    assert response.json()["modo"] == "sem_fontes"


@patch("src.api.estado_cota", return_value=COTA_OK)
@patch("src.api.classify_query", return_value="ktop")
@patch("src.api.semantic_query", side_effect=RuntimeError("chroma fora"))
def test_ask_unavailable_index_returns_503(_mock_query, _mock_scope, _cota):
    response = client.post("/ask", json={"pergunta": "Quais erros de Python?"})
    assert response.status_code == 503
    assert "Consulta indisponível" in response.json()["detail"]


@patch("src.api.consumir_consulta", return_value=COTA_OK)
@patch("src.api.estado_cota", return_value=COTA_OK)
@patch("src.api.classify_query", return_value="completo")
@patch("src.api.all_atendimentos")
@patch("src.api.semantic_query")
def test_ask_completo_uses_full_base(
    mock_query, mock_all, _mock_scope, _cota, _uso, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    mock_query.return_value = [
        {
            "protocolo": "AT-003",
            "documento": "a.pdf",
            "pagina": 1,
            "indice": 0,
            "chunk_id": 3,
            "conteudo": "pip",
            "similaridade": 0.8,
        }
    ]
    mock_all.return_value = [
        {
            "protocolo": "AT-001",
            "descricao": "pip nao e reconhecido no terminal.",
            "conteudo": "Problema pip nao e reconhecido no terminal. Solucao Ok",
        },
        {
            "protocolo": "AT-002",
            "descricao": "pip nao e reconhecido no terminal.",
            "conteudo": "Problema pip nao e reconhecido no terminal. Solucao Ok",
        },
        {
            "protocolo": "AT-010",
            "descricao": "Extensao Python nao encontra o interpretador.",
            "conteudo": "Problema Extensao Python nao encontra o interpretador. Solucao Ok",
        },
    ]
    response = client.post(
        "/ask", json={"pergunta": "Quais problemas mais aparecem?", "top_k": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escopo"] == "completo"
    assert body["modo"] == "contagem"
    assert body["total_base"] == 3
    assert [item["protocolo"] for item in body["fontes"]] == ["AT-003"]
    assert "pip nao e reconhecido no terminal. — 2" in body["resposta"]
    assert "enviou todos os 3" in body["aviso"]
    mock_all.assert_called_once()
    mock_query.assert_called_once()
