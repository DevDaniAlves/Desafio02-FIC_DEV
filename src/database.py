"""Criação do banco, sessão e operações CRUD."""

from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, Atendimento


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


def create_session_factory(url: str):
    engine = create_engine(url, future=True)
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


def delete_by_protocol(session: Session, protocol: str) -> bool:
    item = find_by_protocol(session, protocol)
    if not item:
        return False
    session.delete(item)
    return True
