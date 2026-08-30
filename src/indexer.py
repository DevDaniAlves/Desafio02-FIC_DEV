"""Indexação e recuperação semântica dos chunks no ChromaDB (RF13)."""

from __future__ import annotations
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload
from .models import Atendimento, Chunk
from .embeddings import EmbeddingService
from .vector_store import ChromaStore
from .database import resolve_db_url
from .text_processor import metadata_from_chunk


def _store(cfg: dict) -> ChromaStore:
    root = Path(cfg["_root"])
    return ChromaStore(root / cfg["chromadb"]["diretorio"], cfg["chromadb"]["colecao"])


def build_index(cfg: dict) -> int:
    root = Path(cfg["_root"])
    url = resolve_db_url(root, cfg["banco"]["url"])

    with Session(create_engine(url)) as session:
        chunks = list(session.scalars(select(Chunk)).all())

    store = _store(cfg)
    if not chunks:
        store.sync([], [], [], [])
        return 0

    service = EmbeddingService(cfg["embeddings"]["modelo"])
    docs = [c.conteudo for c in chunks]
    vectors = service.encode(docs)
    store.sync(
        [str(c.id) for c in chunks],
        docs,
        [metadata_from_chunk(c) for c in chunks],
        vectors.tolist(),
    )
    return len(chunks)


def _row_from_match(row: dict) -> dict:
    metadata = dict(row.get("metadata") or {})
    chunk_id = metadata.get("chunk_id", row.get("id"))
    if isinstance(chunk_id, str) and chunk_id.isdigit():
        chunk_id = int(chunk_id)
    return {
        **metadata,
        "chunk_id": chunk_id,
        "conteudo": row["conteudo"],
        "similaridade": round(row["similaridade"], 4),
    }


def semantic_query(
    cfg: dict, question: str, top_k: int = 5, category: str | None = None
) -> list[dict]:
    service = EmbeddingService(cfg["embeddings"]["modelo"])
    query = service.encode([question])[0].tolist()
    store = _store(cfg)
    where = {"categoria": category} if category else None
    return [_row_from_match(row) for row in store.query(query, top_k, where)]


def all_atendimentos(cfg: dict, category: str | None = None) -> list[dict]:
    """Base inteira do SQLite: um registro por protocolo, sem recorte top-k."""
    root = Path(cfg["_root"])
    url = resolve_db_url(root, cfg["banco"]["url"])
    with Session(create_engine(url)) as session:
        stmt = select(Atendimento).options(selectinload(Atendimento.documento))
        if category:
            stmt = stmt.where(Atendimento.categoria == category)
        items = list(session.scalars(stmt).all())
    return [
        {
            "protocolo": item.protocolo,
            "documento": item.documento.nome_arquivo if item.documento else "",
            "pagina": item.pagina,
            "indice": 0,
            "chunk_id": item.id,
            "conteudo": item.texto_original,
            "descricao": item.descricao or "",
            "similaridade": 1.0,
            "categoria": item.categoria or "",
        }
        for item in items
    ]
