"""OCR das páginas rasterizadas, com dependências carregadas sob demanda."""
from __future__ import annotations
from pathlib import Path

def ocr_page(pdf_path: str | Path, page_number: int, dpi: int = 300, language: str = "por") -> str:
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("Instale pdf2image e pytesseract para executar OCR") from exc
    images=convert_from_path(str(pdf_path),dpi=dpi,first_page=page_number,last_page=page_number)
    if not images: return ""
    try: return pytesseract.image_to_string(images[0],lang=language)
    except pytesseract.TesseractError:
        return pytesseract.image_to_string(images[0],lang="eng")
