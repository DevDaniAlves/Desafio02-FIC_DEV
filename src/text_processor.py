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
    text = normalize_text(text)

    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Parametros de chunk invalidos")

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + size // 2:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap

    return [chunk for chunk in chunks if chunk]


def metadata_json(**kwargs) -> str:
    return json.dumps(kwargs, ensure_ascii=False, sort_keys=True)
