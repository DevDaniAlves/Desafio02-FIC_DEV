from pathlib import Path
from src.pdf_processor import extract_pdf_pages

ROOT = Path(__file__).resolve().parents[1]
PDFS = ROOT / "data" / "pdfs"

def test_pdf_digital_usa_extracao_direta():
    pages = extract_pdf_pages(PDFS / "atendimentos_digitais.pdf")
    assert pages
    assert all(page["metodo"] == "extracao_direta" for page in pages)
    assert all(page["texto"] for page in pages)

def test_pdf_digitalizado_encaminha_ocr():
    pages = extract_pdf_pages(PDFS / "atendimentos_digitalizados.pdf")
    assert pages
    assert all(page["metodo"] == "ocr_pendente" for page in pages)
