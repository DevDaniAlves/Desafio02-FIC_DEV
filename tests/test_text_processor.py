from src.text_processor import split_chunks, preprocess

def test_chunks_have_overlap_and_limit():
    chunks=split_chunks("texto de exemplo "*100,size=120,overlap=20)
    assert len(chunks)>1 and all(len(c)<=120 for c in chunks)

def test_preprocess_removes_common_words():
    assert "para" not in preprocess("A senha para o ambiente virtual")
