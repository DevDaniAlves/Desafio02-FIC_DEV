"""Limpeza linguística e divisão de texto em chunks.

Biblioteca escolhida: NLTK.
- Tokenização: Punkt (`word_tokenize`, idioma português).
- Stopwords: corpus `stopwords` em português.
- Processo equivalente à lematização: RSLPStemmer (sufixos do português).

Decisões de limpeza:
- O original não é alterado neste módulo; o pipeline grava `texto_original` e
  `texto_limpo` em colunas distintas.
- Minúsculas e espaços são normalizados; acentos são mantidos porque a lista
  de stopwords e o RSLP dependem da grafia em português (ex.: "não").
- Pontuação isolada é descartada; números e identificadores alfanuméricos ficam.
- Os chunks usados em embeddings continuam no texto bruto (apenas espaços),
  para não degradar o modelo semântico.

Chunking (janela deslizante por caracteres):
- Tamanho padrão 500: cabe na janela do MiniLM multilingual (~128 tokens) e
  evita truncar o embedding.
- Sobreposição padrão 80 (~16%): o final de um trecho reaparece no início do
  seguinte para não perder o contexto na fronteira.
- Se o limite cair no meio de uma palavra, o corte recua ao último espaço
  dentro da janela (palavras maiores que o tamanho ainda são cortadas).
- O avanço nunca recua: se a sobreposição não progredir, o próximo início é
  o fim do trecho atual.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

NLTK_PACKAGES = (
    ("tokenizers/punkt", "punkt"),
    ("tokenizers/punkt_tab", "punkt_tab"),
    ("corpora/stopwords", "stopwords"),
    ("stemmers/rslp", "rslp"),
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\x00", " ")).strip()


def _ensure_nltk() -> None:
    import nltk

    for resource, package in NLTK_PACKAGES:
        try:
            nltk.data.find(resource)
        except LookupError:
            nltk.download(package, quiet=True)


@lru_cache(maxsize=1)
def _nlp_tools():
    """Carrega stemmer e stopwords uma vez, baixando dados do NLTK se faltarem."""
    _ensure_nltk()
    from nltk.corpus import stopwords
    from nltk.stem import RSLPStemmer

    return RSLPStemmer(), frozenset(stopwords.words("portuguese"))


def tokens(text: str) -> list[str]:
    from nltk.tokenize import word_tokenize

    stemmer, stopword_set = _nlp_tools()
    cleaned = normalize_text(text).lower()
    raw_tokens = word_tokenize(cleaned, language="portuguese")
    result: list[str] = []
    for token in raw_tokens:
        if not any(char.isalnum() for char in token):
            continue
        if token in stopword_set:
            continue
        result.append(stemmer.stem(token))
    return result


def preprocess(text: str) -> str:
    return " ".join(tokens(text))


def split_chunks(text: str, size: int = 500, overlap: int = 80) -> list[str]:
    """Divide o texto em janelas de `size` caracteres com sobreposição.

    A unidade é o caractere, não o token, para caber no MiniLM. A sobreposição
    replica o sufixo de um trecho no prefixo do próximo. O corte prefere o
    último espaço dentro da janela, para não partir palavras.
    """
    text = normalize_text(text)

    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Parametros de chunk invalidos")

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        next_start = end - overlap
        start = end if next_start <= start else next_start

    return [chunk for chunk in chunks if chunk]


def source_metadata(
    *,
    chunk_id: int,
    indice: int,
    atendimento_id: int,
    protocolo: str,
    documento: str,
    pagina: int,
    categoria: str = "",
) -> dict:
    """Metadados de proveniência persistidos no SQLite e copiados ao ChromaDB."""
    return {
        "chunk_id": int(chunk_id),
        "indice": int(indice),
        "atendimento_id": int(atendimento_id),
        "protocolo": protocolo or "",
        "documento": documento or "",
        "pagina": int(pagina),
        "categoria": categoria or "",
    }


def metadata_from_chunk(chunk, stored: dict | None = None) -> dict:
    """Completa o JSON gravado com id, índice e FKs do registro relacional."""
    payload = dict(stored or {})
    if not payload and getattr(chunk, "metadata_json", None):
        payload = json.loads(chunk.metadata_json or "{}")
    return source_metadata(
        chunk_id=chunk.id,
        indice=chunk.indice,
        atendimento_id=chunk.atendimento_id,
        protocolo=payload.get("protocolo") or "",
        documento=payload.get("documento") or "",
        pagina=chunk.pagina,
        categoria=payload.get("categoria") or "",
    )


def metadata_json(**kwargs) -> str:
    return json.dumps(kwargs, ensure_ascii=False, sort_keys=True)
