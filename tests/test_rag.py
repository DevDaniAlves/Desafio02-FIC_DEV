from src.rag import answer, local_answer

SOURCES = [
    {
        "protocolo": "AT-001",
        "pagina": 1,
        "chunk_id": 7,
        "indice": 0,
        "conteudo": "Falha na instalação do Python.",
    }
]


def test_local_answer_without_sources():
    result = local_answer("Quais erros de Python?", [])
    assert result["modo"] == "sem_fontes"
    assert result["fontes"] == []
    assert "informação suficiente" in result["resposta"]


def test_local_answer_returns_sources():
    result = local_answer("Quais erros de Python?", SOURCES)
    assert result["modo"] == "recuperacao_local"
    assert result["fontes"] == SOURCES
    assert result["pergunta"] == "Quais erros de Python?"


def test_answer_without_key_stays_local(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = answer("Quais erros de Python?", SOURCES)
    assert result["modo"] == "recuperacao_local"
    assert result["fontes"][0]["protocolo"] == "AT-001"


def test_answer_without_sources_skips_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    result = answer("Quais erros de Python?", [])
    assert result["modo"] == "sem_fontes"
    assert result["fontes"] == []
