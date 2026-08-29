"""Criação do banco, sessão e operações CRUD."""

from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.orm import sessionmaker, Session
from .models import Atendimento, Base, Documento, ErroProcessamento

_ATENDIMENTO_UPDATABLE = frozenset(
    {
        "pagina",
        "data",
        "solicitante",
        "email",
        "categoria",
        "descricao",
        "solucao",
        "tempo_minutos",
        "status",
        "cep",
        "municipio",
        "uf",
        "classificacao",
        "motivos",
        "texto_original",
        "texto_limpo",
    }
)
_DOCUMENTO_UPDATABLE = frozenset(
    {"nome_arquivo", "hash_sha256", "total_paginas", "metodo"}
)


def resolve_db_url(root: str | Path, db_url: str) -> str:
    """Monta uma URL SQLite absoluta, válida no Windows e no Linux.

    Caminhos relativos do config (ex.: sqlite:///database/atendimentos.db)
    são resolvidos a partir da raiz do projeto. Path.as_posix() garante
    barras '/', evitando a barra invertida do Windows na URL.
    """
    parsed = make_url(db_url)
    if parsed.get_backend_name() != "sqlite":
        return db_url
    database = parsed.database
    if not database or database == ":memory:":
        return db_url
    path = Path(database)
    if not path.is_absolute():
        path = Path(root) / path
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(URL.create(drivername="sqlite", database=path.as_posix()))


def create_session_factory(url: str, *, recreate: bool = False):
    engine = create_engine(url, future=True)
    if recreate:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory):
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def find_by_protocol(session: Session, protocol: str) -> Atendimento | None:
    return session.scalar(select(Atendimento).where(Atendimento.protocolo == protocol))


def update_atendimento(
    session: Session, protocol: str, **fields
) -> Atendimento | None:
    unknown = set(fields) - _ATENDIMENTO_UPDATABLE
    if unknown:
        raise ValueError(f"Campos não atualizáveis: {sorted(unknown)}")
    item = find_by_protocol(session, protocol)
    if not item:
        return None
    for name, value in fields.items():
        setattr(item, name, value)
    session.flush()
    return item


def update_documento(session: Session, doc: Documento, **fields) -> Documento:
    unknown = set(fields) - _DOCUMENTO_UPDATABLE
    if unknown:
        raise ValueError(f"Campos não atualizáveis: {sorted(unknown)}")
    for name, value in fields.items():
        setattr(doc, name, value)
    session.flush()
    return doc


def delete_by_protocol(session: Session, protocol: str) -> bool:
    item = find_by_protocol(session, protocol)
    if not item:
        return False
    session.delete(item)
    session.flush()
    return True


def purge_documento(session: Session, doc: Documento) -> None:
    """Exclusão controlada: erros, atendimentos (e chunks em cascata) e o documento."""
    session.execute(
        delete(ErroProcessamento).where(ErroProcessamento.documento_id == doc.id)
    )
    for protocol in [item.protocolo for item in list(doc.atendimentos)]:
        delete_by_protocol(session, protocol)
    session.expire(doc, ["atendimentos"])
    session.delete(doc)
    session.flush()
