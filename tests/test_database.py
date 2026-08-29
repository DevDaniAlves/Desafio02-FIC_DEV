import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.engine.url import make_url
from src.database import (
    create_session_factory,
    delete_by_protocol,
    find_by_protocol,
    purge_documento,
    resolve_db_url,
    session_scope,
    update_atendimento,
    update_documento,
)
from src.models import Atendimento, Chunk, Documento, ErroProcessamento
from src.text_processor import metadata_from_chunk, metadata_json, source_metadata


def test_sqlite_url_is_absolute_and_posix(tmp_path):
    url = resolve_db_url(tmp_path, "sqlite:///database/atendimentos.db")
    parsed = make_url(url)
    path = Path(parsed.database)

    assert parsed.get_backend_name() == "sqlite"
    assert "\\" not in url
    assert path.is_absolute()
    assert path.as_posix() == parsed.database
    assert path.parent.exists()


def test_memory_and_non_sqlite_urls_are_unchanged():
    root = Path(".")
    assert resolve_db_url(root, "sqlite:///:memory:") == "sqlite:///:memory:"
    assert resolve_db_url(root, "postgresql://localhost/app") == "postgresql://localhost/app"


def _seed_atendimento(session, protocol: str = "AT-001") -> Atendimento:
    doc = Documento(
        nome_arquivo="amostra.pdf",
        hash_sha256="a" * 64,
        total_paginas=1,
        metodo="extracao_direta",
    )
    session.add(doc)
    session.flush()
    item = Atendimento(
        documento_id=doc.id,
        pagina=1,
        protocolo=protocol,
        solicitante="Ana",
        texto_original="Protocolo AT-001",
        texto_limpo="senha ambiente virtual",
        cep="78200-000",
    )
    session.add(item)
    session.flush()
    chunk = Chunk(
        atendimento_id=item.id,
        documento_id=doc.id,
        pagina=1,
        indice=0,
        conteudo="conteudo",
        metadata_json="{}",
    )
    session.add(chunk)
    session.flush()
    chunk.metadata_json = metadata_json(
        **source_metadata(
            chunk_id=chunk.id,
            indice=0,
            atendimento_id=item.id,
            protocolo=protocol,
            documento="amostra.pdf",
            pagina=1,
            categoria="Instalação",
        )
    )
    session.flush()
    return item


def test_chunk_metadata_preserva_vinculo_com_a_fonte():
    factory = create_session_factory("sqlite:///:memory:")
    with session_scope(factory) as session:
        item = _seed_atendimento(session)
        chunk = session.scalars(select(Chunk)).one()
        meta = json.loads(chunk.metadata_json)
        indexed = metadata_from_chunk(chunk)
        assert meta["chunk_id"] == chunk.id
        assert meta["indice"] == 0
        assert meta["atendimento_id"] == item.id
        assert meta["protocolo"] == "AT-001"
        assert meta["documento"] == "amostra.pdf"
        assert meta["pagina"] == 1
        assert meta["categoria"] == "Instalação"
        assert indexed["chunk_id"] == chunk.id
        assert indexed["protocolo"] == "AT-001"


def test_update_consulta_e_exclusao_controlada():
    factory = create_session_factory("sqlite:///:memory:")
    with session_scope(factory) as session:
        _seed_atendimento(session)
        found = find_by_protocol(session, "AT-001")
        assert found is not None
        updated = update_atendimento(
            session, "AT-001", municipio="Cáceres", uf="MT"
        )
        assert updated is not None
        assert updated.municipio == "Cáceres"
        assert updated.uf == "MT"
        assert delete_by_protocol(session, "AT-001") is True
        assert find_by_protocol(session, "AT-001") is None
        assert session.scalars(select(Chunk)).all() == []
        assert delete_by_protocol(session, "AT-001") is False


def test_purge_documento_remove_erros_e_atendimentos():
    factory = create_session_factory("sqlite:///:memory:")
    with session_scope(factory) as session:
        item = _seed_atendimento(session)
        session.add(
            ErroProcessamento(
                documento_id=item.documento_id,
                pagina=1,
                etapa="ocr",
                tipo="RuntimeError",
                mensagem="falha",
            )
        )
        session.flush()
        doc = session.get(Documento, item.documento_id)
        purge_documento(session, doc)
        assert session.get(Documento, item.documento_id) is None
        assert find_by_protocol(session, "AT-001") is None
        assert session.scalars(select(ErroProcessamento)).all() == []


def test_recreate_sqlite_file(tmp_path):
    url = resolve_db_url(tmp_path, "sqlite:///database/atendimentos.db")
    factory = create_session_factory(url)
    with session_scope(factory) as session:
        _seed_atendimento(session)
    factory = create_session_factory(url, recreate=True)
    with session_scope(factory) as session:
        assert find_by_protocol(session, "AT-001") is None
        assert session.scalars(select(Documento)).all() == []


def test_update_documento_e_rejeita_campo_invalido():
    factory = create_session_factory("sqlite:///:memory:")
    with session_scope(factory) as session:
        item = _seed_atendimento(session)
        doc = session.get(Documento, item.documento_id)
        update_documento(session, doc, metodo="ocr", total_paginas=3)
        assert doc.metodo == "ocr"
        assert doc.total_paginas == 3
        try:
            update_atendimento(session, "AT-001", protocolo="AT-999")
        except ValueError as exc:
            assert "protocolo" in str(exc)
        else:
            raise AssertionError("deveria rejeitar atualização de protocolo")
