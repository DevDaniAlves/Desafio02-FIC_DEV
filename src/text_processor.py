"""Limpeza linguística e divisão de texto em chunks."""
from __future__ import annotations
import json, re, unicodedata

STOPWORDS={"a","o","as","os","de","da","do","das","dos","e","em","um","uma","para","por","com","que","no","na"}

def normalize_text(text: str) -> str:
    return re.sub(r"\s+"," ",text.replace("\x00"," ")).strip()

def tokens(text: str) -> list[str]:
    plain=unicodedata.normalize("NFKD",text.lower()).encode("ascii","ignore").decode()
    return [t for t in re.findall(r"[a-z0-9]+",plain) if t not in STOPWORDS]

def lemma_light(token: str) -> str:
    for suffix in ("mente","coes","cao","ando","endo","idos","adas","ado","ida","s"):
        if token.endswith(suffix) and len(token)>len(suffix)+3: return token[:-len(suffix)]
    return token

def preprocess(text: str) -> str:
    return " ".join(lemma_light(t) for t in tokens(text))

def split_chunks(text: str, size: int=500, overlap: int=80) -> list[str]:
    text=normalize_text(text)
    if size<=0 or overlap<0 or overlap>=size: raise ValueError("Parametros de chunk invalidos")
    chunks=[]; start=0
    while start<len(text):
        end=min(len(text),start+size)
        if end<len(text):
            boundary=text.rfind(" ",start,end)
            if boundary>start+size//2: end=boundary
        chunks.append(text[start:end].strip())
        if end>=len(text): break
        start=end-overlap
    return [c for c in chunks if c]

def metadata_json(**kwargs) -> str:
    return json.dumps(kwargs,ensure_ascii=False,sort_keys=True)
