import json
from types import SimpleNamespace

import pytest

from src.text_processor import (
    metadata_from_chunk,
    metadata_json,
    preprocess,
    source_metadata,
    split_chunks,
    tokens,
)


def test_chunks_have_overlap_and_limit():
    chunks = split_chunks("texto de exemplo " * 100, size=120, overlap=20)
    assert len(chunks) > 1 and all(len(c) <= 120 for c in chunks)


def test_chunks_overlap_on_contiguous_text():
    text = "abcdefghij" * 20
    chunks = split_chunks(text, size=50, overlap=10)
    assert len(chunks) > 1
    assert all(len(c) <= 50 for c in chunks)
    for previous, current in zip(chunks, chunks[1:]):
        assert current.startswith(previous[-10:])


def test_chunks_end_on_complete_words():
    text = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"
    original = set(text.split())
    chunks = split_chunks(text, size=25, overlap=5)
    assert len(chunks) > 1
    for chunk in chunks[:-1]:
        assert chunk.split()[-1] in original


def test_chunks_progress_when_overlap_is_large():
    text = "palavra " * 40
    chunks = split_chunks(text, size=20, overlap=18)
    assert len(chunks) > 1
    assert all(chunk for chunk in chunks)


@pytest.mark.parametrize(
    "size, overlap",
    [(0, 0), (-1, 0), (10, 10), (10, 11), (20, -1)],
)
def test_chunks_reject_invalid_params(size, overlap):
    with pytest.raises(ValueError, match="invalidos"):
        split_chunks("texto de exemplo", size=size, overlap=overlap)


def test_source_metadata_contains_required_fields():
    meta = source_metadata(
        chunk_id=3,
        indice=1,
        atendimento_id=9,
        protocolo="AT-001",
        documento="a.pdf",
        pagina=2,
        categoria="Instalação",
    )
    assert meta == {
        "chunk_id": 3,
        "indice": 1,
        "atendimento_id": 9,
        "protocolo": "AT-001",
        "documento": "a.pdf",
        "pagina": 2,
        "categoria": "Instalação",
    }
    assert json.loads(metadata_json(**meta)) == meta


def test_metadata_from_chunk_fills_ids_from_sql():
    chunk = SimpleNamespace(
        id=7,
        indice=2,
        atendimento_id=4,
        pagina=3,
        metadata_json=json.dumps(
            {"protocolo": "AT-010", "documento": "b.pdf", "categoria": ""}
        ),
    )
    meta = metadata_from_chunk(chunk)
    assert meta["chunk_id"] == 7
    assert meta["indice"] == 2
    assert meta["atendimento_id"] == 4
    assert meta["pagina"] == 3
    assert meta["protocolo"] == "AT-010"
    assert meta["documento"] == "b.pdf"
    assert meta["categoria"] == ""


def test_preprocess_removes_common_words():
    assert "para" not in preprocess("A senha para o ambiente virtual")


def test_preprocess_keeps_content_tokens():
    parts = preprocess("A senha para o ambiente virtual").split()
    assert "para" not in parts
    assert any(token.startswith("senh") for token in parts)
    assert "virtual" in parts


def test_tokens_stem_portuguese_plurals():
    stemmed = tokens("instalações computadores")
    assert "instalações" not in stemmed
    assert "computadores" not in stemmed
    assert any(token.startswith("instal") for token in stemmed)
    assert any(token.startswith("comput") for token in stemmed)
