"""Recuperação local e resposta RAG com OpenAI ou Gemini (RF14).

Sem chave devolve os trechos recuperados. Com as duas chaves, `AI_PROVIDER`
escolhe o modelo (`openai` ou `gemini`). Sem fontes, o modelo não é chamado.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict

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
PROBLEMA_RE = re.compile(r"Problema\s+(.+?)\s+Solucao", re.I | re.S)
CLASSIFY = (
    "Classifique a pergunta do arquivo de atendimentos em UMA palavra: "
    "ktop ou completo.\n"
    "completo SOMENTE se pedir frequência, os que mais aparecem, os mais comuns, "
    "quantos, totais, listar todos ou validar a base inteira.\n"
    "ktop para todo o resto: semelhança, um protocolo, o que aconteceu, "
    "pior caso, mais demorado, mais lento, extremo de um recorte.\n"
    "Exemplos: 'quais problemas mais aparecem?' -> completo. "
    "'Qual o problema mais demorado de se resolver?' -> ktop. "
    "'Qual o pior caso de senha?' -> ktop.\n"
    "Responda somente: ktop ou completo"
)


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


def problema_texto(item: dict) -> str:
    raw = (item.get("descricao") or "").strip()
    if raw:
        return raw
    match = PROBLEMA_RE.search(item.get("conteudo") or "")
    if match:
        return match.group(1).strip()
    return "(sem problema)"


def count_problems(sources: list[dict]) -> list[dict]:
    """Agrupa pelo texto do Problema e ordena do mais frequente para o menos."""
    groups: dict[str, list[str]] = defaultdict(list)
    for item in sources:
        protocolo = item.get("protocolo") or "sem protocolo"
        groups[problema_texto(item)].append(protocolo)
    ranked = [
        {"problema": name, "quantidade": len(protocols), "protocolos": protocols}
        for name, protocols in groups.items()
    ]
    ranked.sort(key=lambda row: (-row["quantidade"], row["problema"]))
    return ranked


def format_frequency_answer(ranked: list[dict], total: int) -> str:
    if not ranked:
        return "Não há atendimentos na base para contar."
    lines = [
        f"Contagem da base completa ({total} atendimento(s)), "
        "do que mais aparece para o que menos aparece. "
        "Cada linha é o campo Problema, sem reagrupar textos diferentes.",
        "",
    ]
    for index, row in enumerate(ranked, start=1):
        protocolos = ", ".join(row["protocolos"])
        lines.append(
            f"{index}. {row['problema']} — {row['quantidade']} "
            f"({protocolos})"
        )
    return "\n".join(lines)


def parse_scope(text: str) -> str:
    first = (text or "").strip().lower().split()
    token = first[0].strip(".:;") if first else ""
    if token.startswith("completo"):
        return "completo"
    return "ktop"


def classify_query(question: str) -> str:
    """Pede ao modelo se a pergunta é top-k semântico ou precisa da base toda."""
    provider = resolve_provider()
    if not provider:
        return "ktop"
    try:
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [("system", CLASSIFY), ("human", "{question}")]
        )
        chain = prompt | _chat_model(provider, default_model(provider))
        return parse_scope(_message_text(chain.invoke({"question": question})))
    except Exception:
        return "ktop"


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


def _context_from_sources(sources: list[dict], escopo: str = "ktop") -> str:
    blocks = [
        (
            f"Atendimento {item.get('protocolo') or 'sem protocolo'} "
            f"(documento {item.get('documento')}, página {item.get('pagina')}, "
            f"trecho {item.get('indice')})\n"
            f"{item.get('conteudo') or ''}"
        )
        for item in sources
    ]
    if escopo == "completo":
        header = f"{len(sources)} atendimento(s) da base completa:\n\n"
    else:
        header = f"{len(sources)} atendimento(s) mais semelhantes (top-k):\n\n"
    return header + "\n\n".join(blocks)


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
    question: str,
    sources: list[dict],
    model: str | None = None,
    escopo: str = "ktop",
) -> dict:
    if escopo == "completo":
        ranked = count_problems(sources)
        return {
            "resposta": format_frequency_answer(ranked, len(sources)),
            "modo": "contagem",
            "escopo": "completo",
            "fontes": sources,
        }
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
            {
                "question": question,
                "context": _context_from_sources(sources, escopo),
            }
        )
        return {
            "resposta": _message_text(response),
            "modo": f"rag_{provider}",
            "provedor": provider,
            "escopo": escopo,
            "fontes": sources,
        }
    except Exception as exc:
        result = local_answer(question, sources)
        result["aviso"] = (
            f"Falha no modelo {chosen} ({provider}): {type(exc).__name__}: {exc}"
        )
        return result
