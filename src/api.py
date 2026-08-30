"""API HTTP de consulta semântica (RF15)."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .config import load_config
from .indexer import semantic_query
from .rag import answer, resolve_provider

app = FastAPI(title="Atendimentos FIC_DEV", version="1.0.0")
cfg = load_config()


class AskRequest(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    categoria: str | None = None


def _modo() -> str:
    provider = resolve_provider()
    return f"rag_{provider}" if provider else "recuperacao_local"


@app.get("/")
def root():
    return {
        "servico": "Consulta de atendimentos",
        "endpoints": {"health": "/health", "ask": "POST /ask"},
        "modo": _modo(),
        "provedor": resolve_provider(),
    }


@app.get("/health")
def health():
    return {"status": "ok", "modo": _modo(), "provedor": resolve_provider()}


@app.post("/ask")
def ask(payload: AskRequest):
    try:
        sources = semantic_query(
            cfg, payload.pergunta, payload.top_k, payload.categoria
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Consulta indisponível: {type(exc).__name__}",
        ) from exc
    return answer(payload.pergunta, sources)
