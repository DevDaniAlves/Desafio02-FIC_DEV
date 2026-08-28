"""Extração direta de texto e encaminhamento de páginas para OCR."""
from __future__ import annotations
from pathlib import Path
from pypdf import PdfReader

def extract_pdf_pages(path: str | Path, min_chars: int = 40) -> list[dict]:
    reader=PdfReader(str(path)); pages=[]
    for number,page in enumerate(reader.pages,1):
        text=(page.extract_text() or "").strip()
        pages.append({"pagina":number,"texto":text,"metodo":"extracao_direta" if len(text)>=min_chars else "ocr_pendente"})
    return pages
