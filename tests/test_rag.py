from types import SimpleNamespace

from src.rag import (
    _context_from_sources,
    _message_text,
    answer,
    count_problems,
    format_frequency_answer,
    local_answer,
    parse_scope,
    resolve_provider,
)

SOURCES = [
    {
        "protocolo": "AT-001",
        "pagina": 1,
        "chunk_id": 7,
        "indice": 0,
        "conteudo": "Falha na instalação do Python.",
    }
]


def _clear_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)


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
    _clear_keys(monkeypatch)
    result = answer("Quais erros de Python?", SOURCES)
    assert result["modo"] == "recuperacao_local"
    assert result["fontes"][0]["protocolo"] == "AT-001"


def test_answer_without_sources_skips_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    result = answer("Quais erros de Python?", [])
    assert result["modo"] == "sem_fontes"
    assert result["fontes"] == []


def test_provider_gemini_when_only_gemini(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    assert resolve_provider() == "gemini"


def test_provider_openai_when_only_openai(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert resolve_provider() == "openai"


def test_provider_both_follow_ai_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    assert resolve_provider() == "gemini"
    monkeypatch.setenv("AI_PROVIDER", "openai")
    assert resolve_provider() == "openai"


def test_count_problems_orders_by_frequency():
    ranked = count_problems(
        [
            {"protocolo": "AT-001", "descricao": "pip nao e reconhecido no terminal."},
            {"protocolo": "AT-002", "descricao": "Ambiente virtual nao ativa no terminal."},
            {"protocolo": "AT-003", "descricao": "pip nao e reconhecido no terminal."},
        ]
    )
    assert ranked[0]["problema"] == "pip nao e reconhecido no terminal."
    assert ranked[0]["quantidade"] == 2
    assert ranked[0]["protocolos"] == ["AT-001", "AT-003"]
    assert ranked[1]["quantidade"] == 1
    text = format_frequency_answer(ranked, 3)
    assert "pip nao e reconhecido no terminal. — 2" in text
    assert "AT-001, AT-003" in text


def test_answer_completo_does_not_call_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    result = answer(
        "Quais mais aparecem?",
        [
            {"protocolo": "AT-001", "descricao": "pip nao e reconhecido no terminal."},
            {"protocolo": "AT-002", "descricao": "pip nao e reconhecido no terminal."},
        ],
        escopo="completo",
    )
    assert result["modo"] == "contagem"
    assert "— 2" in result["resposta"]


def test_parse_scope_completo_and_ktop():
    assert parse_scope("completo") == "completo"
    assert parse_scope("completo.") == "completo"
    assert parse_scope("ktop") == "ktop"
    assert parse_scope("ktop\nporque é semelhança") == "ktop"
    assert parse_scope("") == "ktop"


def test_context_completo_header():
    text = _context_from_sources(
        [{"protocolo": "AT-001", "documento": "a.pdf", "pagina": 1, "indice": 0, "conteudo": "x"}],
        escopo="completo",
    )
    assert "base completa" in text


def test_context_includes_protocol_and_problem():
    text = _context_from_sources(
        [
            {
                "protocolo": "AT-003",
                "documento": "a.pdf",
                "pagina": 1,
                "indice": 0,
                "conteudo": "Problema pip nao e reconhecido no terminal.",
            }
        ]
    )
    assert "AT-003" in text
    assert "pip nao e reconhecido" in text
    assert "1 atendimento" in text


def test_message_text_from_gemini_blocks():
    response = SimpleNamespace(
        text="",
        content=[
            {
                "type": "text",
                "text": "Não há informação suficiente no contexto.",
                "extras": {"signature": "abc"},
            }
        ],
    )
    assert _message_text(response) == "Não há informação suficiente no contexto."


def test_message_text_from_plain_string():
    assert _message_text(SimpleNamespace(text="ok", content="ok")) == "ok"


def test_provider_both_default_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert resolve_provider() == "openai"
