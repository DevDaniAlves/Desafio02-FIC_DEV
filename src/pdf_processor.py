"""Detecção de texto selecionável e extração direta de PDFs (RF02)."""
from __future__ import annotations
from pathlib import Path
import logging

def _from_pdfplumber(path: Path, min_chars: int) -> list[dict]:
    import pdfplumber
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            text = (page.extract_text() or "").strip()
            selectable = bool(page.chars) and len(text) >= min_chars
            pages.append({
                "pagina": number,
                "texto": text if selectable else text,
                "metodo": "extracao_direta" if selectable else "ocr_pendente",
            })
    return pages

def _from_pypdf(path: Path, min_chars: int) -> list[dict]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        pages.append({
            "pagina": number,
            "texto": text,
            "metodo": "extracao_direta" if len(text) >= min_chars else "ocr_pendente",
        })
    return pages

def extract_pdf_pages(path: str | Path, min_chars: int = 40) -> list[dict]:
    path = Path(path)
    try:
        pages = _from_pdfplumber(path, min_chars)
    except Exception as exc:
        logging.warning("pdfplumber falhou em %s (%s); usando pypdf", path.name, exc)
        pages = _from_pypdf(path, min_chars)
    for page in pages:
        logging.info(
            "PDF localizado=%s pagina=%s metodo=%s caracteres=%s",
            path.name, page["pagina"], page["metodo"], len(page["texto"]),
        )
    return pages
