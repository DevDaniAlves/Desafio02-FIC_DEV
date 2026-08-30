"""Recuperação local e resposta RAG opcional com OpenAI/LangChain (RF14).

Sem `OPENAI_API_KEY` devolve os trechos recuperados. Sem fontes, não chama o
modelo: a resposta deixa claro que o índice não sustentou a pergunta.
"""

from __future__ import annotations

import os

SYSTEM = (
    "Responda somente com base no contexto. "
    "Se a resposta não estiver sustentada, diga que não há informação suficiente. "
    "Cite os protocolos utilizados."
)


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
            "Configure OPENAI_API_KEY para gerar uma síntese."
        ),
        "modo": "recuperacao_local",
        "pergunta": question,
        "fontes": sources,
    }


def _context_from_sources(sources: list[dict]) -> str:
    return "\n\n".join(
        (
            f"[Fonte {item.get('protocolo')} p.{item.get('pagina')} "
            f"chunk {item.get('chunk_id')} #{item.get('indice')}] "
            f"{item.get('conteudo')}"
        )
        for item in sources
    )


def answer(
    question: str, sources: list[dict], model: str = "gpt-4.1-mini"
) -> dict:
    if not sources or not os.getenv("OPENAI_API_KEY"):
        return local_answer(question, sources)
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM),
                ("human", "Pergunta: {question}\n\nContexto:\n{context}"),
            ]
        )
        chain = prompt | ChatOpenAI(model=model, temperature=0)
        response = chain.invoke(
            {"question": question, "context": _context_from_sources(sources)}
        )
        return {"resposta": response.content, "modo": "rag", "fontes": sources}
    except Exception as exc:
        result = local_answer(question, sources)
        result["aviso"] = f"Falha no modelo: {type(exc).__name__}"
        return result
