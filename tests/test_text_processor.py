from src.text_processor import split_chunks, preprocess, tokens


def test_chunks_have_overlap_and_limit():
    chunks = split_chunks("texto de exemplo " * 100, size=120, overlap=20)
    assert len(chunks) > 1 and all(len(c) <= 120 for c in chunks)


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
