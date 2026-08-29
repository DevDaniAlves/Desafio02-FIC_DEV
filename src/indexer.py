"""Indexação dos chunks persistidos no ChromaDB."""

from __future__ import annotations
from pathlib import Path
import json
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from .models import Chunk
from .embeddings import EmbeddingService
from .vector_store import ChromaStore
from .database import resolve_db_url


def build_index(cfg: dict) -> int:
    
    # Resolve a URL do banco de dados
    root = Path(cfg["_root"])
    url = resolve_db_url(root, cfg["banco"]["url"])

    with Session(create_engine(url)) as session:
        chunks = list(session.scalars(select(Chunk)).all())

    if not chunks:
        return 0

    service = EmbeddingService(cfg["embeddings"]["modelo"])
    docs = [c.conteudo for c in chunks]
    vectors = service.encode(docs)
    store = ChromaStore(root / cfg["chromadb"]["diretorio"], cfg["chromadb"]["colecao"])
    store.upsert(
        [str(c.id) for c in chunks],
        docs,
        [json.loads(c.metadata_json) for c in chunks],
        vectors.tolist(),
    )
    return len(chunks)


def semantic_query(
    cfg: dict, question: str, top_k: int = 5, category: str | None = None
) -> list[dict]:
    root = Path(cfg["_root"])
    service = EmbeddingService(cfg["embeddings"]["modelo"])
    query = service.encode([question])[0].tolist()
    store = ChromaStore(root / cfg["chromadb"]["diretorio"], cfg["chromadb"]["colecao"])
    where = {"categoria": category} if category else None
    rows = store.query(query, top_k, where)
    return [
        {
            **r["metadata"],
            "conteudo": r["conteudo"],
            "similaridade": round(r["similaridade"], 4),
        }
        for r in rows
    ]
