"""OCR de páginas digitalizadas, sem interromper o lote (RF03)."""
from __future__ import annotations
from pathlib import Path
import os
import re
import shutil
import logging

_TESSERACT_CONFIGURED = False

def _tesseract_candidates() -> list[Path]:
    found: list[Path] = []
    env_cmd = os.environ.get("TESSERACT_CMD", "").strip()
    if env_cmd:
        found.append(Path(env_cmd))
    which = shutil.which("tesseract")
    if which:
        found.append(Path(which))
    found.extend([
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path.home() / r"AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        Path("/usr/bin/tesseract"),
        Path("/usr/local/bin/tesseract"),
    ])
    return found

def configure_tesseract() -> Path:
    global _TESSERACT_CONFIGURED
    import pytesseract
    for candidate in _tesseract_candidates():
        if candidate.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            _TESSERACT_CONFIGURED = True
            return candidate
    raise RuntimeError(
        "Tesseract não encontrado. Instale o Tesseract OCR (idioma por) "
        "ou defina TESSERACT_CMD com o caminho do executável."
    )

def repair_ocr_text(text: str) -> str:
    """Preserva o texto bruto à parte; esta versão só uniformiza rótulos para o regex."""
    replacements = [
        (r"(?i)protocolob", "Protocolo"),
        (r"(?i)protocob", "Protocolo"),
        (r"(?i)protocol(?![oa])", "Protocolo"),
        (r"(?i)e[\s-]*mail", "E-mail"),
        (r"(?i)problem\s*a", "Problema"),
        (r"(?i)probk\w*\s*a", "Problema"),
        (r"(?i)soli[cç][aã]?o", "Solucao"),
        (r"(?i)solu[cç][aã]o", "Solucao"),
        (r"(?i)tem\s*po", "Tempo"),
        (r"(?i)observac\w*", "Observacoes"),
        (r"(?i)categor[ií]a", "Categoria"),
        (r"(?i)solicitante", "Solicitante"),
        (r"(?i)\bconcl[uií]+[do]+\b", "Concluido"),
        (r"(?i)em\s+atend\w+", "Em atendimento"),
    ]
    cleaned = text.replace("|", " ")
    for pattern, repl in replacements:
        cleaned = re.sub(pattern, repl, cleaned)
    return cleaned

def _rasterize_page(pdf_path: Path, page_number: int, dpi: int):
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(str(pdf_path))
        try:
            index = page_number - 1
            if index < 0 or index >= len(pdf):
                return None
            image = pdf[index].render(scale=max(dpi, 72) / 72).to_pil()
            return image.convert("L")
        finally:
            pdf.close()
    except Exception as exc:
        logging.warning("pypdfium2 falhou em %s p.%s (%s); tentando pdf2image", pdf_path.name, page_number, exc)
    from pdf2image import convert_from_path
    images = convert_from_path(str(pdf_path), dpi=dpi, first_page=page_number, last_page=page_number)
    return images[0] if images else None

def _ocr_tesseract(image, language: str) -> str:
    import pytesseract
    configure_tesseract()
    config = "--oem 3 --psm 6"
    try:
        return pytesseract.image_to_string(image, lang=language, config=config)
    except pytesseract.TesseractError:
        return pytesseract.image_to_string(image, lang="eng", config=config)

def _ocr_easyocr(image) -> str:
    import numpy as np
    import easyocr
    reader = easyocr.Reader(["pt", "en"], gpu=False)
    lines = reader.readtext(np.array(image.convert("RGB")), detail=0)
    return "\n".join(str(line) for line in lines)

def ocr_page(pdf_path: str | Path, page_number: int, dpi: int = 300, language: str = "por") -> str:
    pdf_path = Path(pdf_path)
    image = _rasterize_page(pdf_path, page_number, dpi)
    if image is None:
        raise RuntimeError(f"Não foi possível converter {pdf_path.name} página {page_number} em imagem")
    try:
        return _ocr_tesseract(image, language)
    except Exception as tess_exc:
        try:
            return _ocr_easyocr(image)
        except Exception as easy_exc:
            raise RuntimeError(
                f"OCR falhou em {pdf_path.name} página {page_number}: "
                f"Tesseract ({tess_exc}); EasyOCR ({easy_exc})"
            ) from tess_exc
