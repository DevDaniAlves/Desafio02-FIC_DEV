"""Recuperação local e resposta RAG com OpenAI ou Gemini (RF14).

Sem chave devolve os trechos recuperados. Com as duas chaves, `AI_PROVIDER`
escolhe o modelo (`openai` ou `gemini`). Sem fontes, o modelo não é chamado.
"""

from __future__ import annotations

import os

SYSTEM = (
    "Você consulta um arquivo de atendimentos. O contexto abaixo JÁ contém os "
    "protocolos recuperados: use o campo Problema de cada um. "
    "Responda com o que esses registros mostram. Se a pergunta pedir frequência "
    "ou os mais comuns, agrupe problemas semelhantes e conte quantos protocolos "
    "aparecem em cada grupo, citando os AT-XXX. "
    "Não diga que faltam dados só porque o recorte não é a base inteira: "
    "diga que a conta vale para os atendimentos recuperados. "
    "Só recuse se nenhum registro tiver relação com a pergunta."
)
PROVIDERS = ("openai", "gemini")


def _has_key(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def resolve_provider() -> str | None:
    openai = _has_key("OPENAI_API_KEY")
    gemini = _has_key("GEMINI_API_KEY")
    if openai and gemini:
        choice = (os.getenv("AI_PROVIDER") or "openai").strip().lower()
        return choice if choice in PROVIDERS else "openai"
    if gemini:
        return "gemini"
    if openai:
        return "openai"
    return None


def default_model(provider: str) -> str:
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-lite"
    return os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"


def local_answer(question: str, sources: list[dict]) -> dict:
    if not sources:
        return {
            "resposta": (
                "Não há informação suficiente no índice para responder. "
                "Processe os PDFs e execute a indexação antes de consultar."
            ),
            "modo": "sem_fontes",
            "pergunta": question,
            "fontes": [],
        }
    return {
        "resposta": (
            "Modo local: foram recuperados os trechos mais semelhantes. "
            "Configure OPENAI_API_KEY ou GEMINI_API_KEY para gerar uma síntese."
        ),
        "modo": "recuperacao_local",
        "pergunta": question,
        "fontes": sources,
    }


def _message_text(response) -> str:
    """LangChain/Gemini pode devolver blocos `[{type, text, extras}]`; a UI quer só o texto."""
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
        return "\n".join(parts).strip()
    return str(content)


def _context_from_sources(sources: list[dict]) -> str:
    blocks = [
        (
            f"Atendimento {item.get('protocolo') or 'sem protocolo'} "
            f"(documento {item.get('documento')}, página {item.get('pagina')}, "
            f"trecho {item.get('indice')})\n"
            f"{item.get('conteudo') or ''}"
        )
        for item in sources
    ]
    return (
        f"{len(sources)} atendimento(s) recuperado(s) do arquivo:\n\n"
        + "\n\n".join(blocks)
    )


def _chat_model(provider: str, model: str):
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model, temperature=0)


def answer(
    question: str, sources: list[dict], model: str | None = None
) -> dict:
    provider = resolve_provider()
    if not sources or not provider:
        return local_answer(question, sources)
    chosen = model or default_model(provider)
    try:
        from langchain_core.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM),
                (
                    "human",
                    "Pergunta do usuário: {question}\n\n"
                    "Atendimentos enviados para você responder:\n{context}",
                ),
            ]
        )
        chain = prompt | _chat_model(provider, chosen)
        response = chain.invoke(
            {"question": question, "context": _context_from_sources(sources)}
        )
        return {
            "resposta": _message_text(response),
            "modo": f"rag_{provider}",
            "provedor": provider,
            "fontes": sources,
        }
    except Exception as exc:
        result = local_answer(question, sources)
        result["aviso"] = (
            f"Falha no modelo {chosen} ({provider}): {type(exc).__name__}: {exc}"
        )
        return result
