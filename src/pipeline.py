"""Orquestração do processamento ponta a ponta."""

from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json, logging, re
import pandas as pd
from sqlalchemy import select, delete
from .config import resolve
from .database import create_session_factory, session_scope, find_by_protocol, resolve_db_url
from .models import Documento, Atendimento, Chunk, ErroProcessamento
from .pdf_processor import extract_pdf_pages
from .ocr_processor import ocr_page, repair_ocr_text
from .validation import extract_fields, validate_record, clean_text
from .text_processor import preprocess, split_chunks, metadata_json
from .analytics import export_results, generate_charts

RECORD_SPLIT = re.compile(
    r"(?=Protocol[oa]?b?\s+(?:AT\s*-?\s*\d{3}|PROTOCOLO\s*\??))",
    re.I,
)


def configure_logging(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )


def split_records(page_text: str) -> list[str]:
    parts = RECORD_SPLIT.split(clean_text(page_text))
    return [
        part.strip()
        for part in parts
        if re.search(
            r"Protocol[oa]?b?\s+(?:AT\s*-?\s*\d{3}|PROTOCOLO\s*\??)", part, re.I
        )
    ]


def has_ocr_failure(session, doc: Documento) -> bool:
    return (
        session.scalar(
            select(ErroProcessamento.id)
            .where(
                ErroProcessamento.documento_id == doc.id,
                ErroProcessamento.etapa == "ocr",
            )
            .limit(1)
        )
        is not None
    )


def purge_documento(session, doc: Documento) -> None:
    session.execute(
        delete(ErroProcessamento).where(ErroProcessamento.documento_id == doc.id)
    )
    session.delete(doc)
    session.flush()


def atendimento_to_row(item: Atendimento, nome_arquivo: str, metodo: str) -> dict:
    observacoes = ""
    match = re.search(r"Observacoes\s+(.+)$", item.texto_original or "", re.I)
    if match:
        observacoes = match.group(1).strip()
    return {
        "protocolo": item.protocolo,
        "data": item.data,
        "solicitante": item.solicitante or "",
        "email": item.email or "",
        "categoria": item.categoria or "",
        "status": item.status or "",
        "cep": item.cep or "",
        "tempo_minutos": item.tempo_minutos,
        "descricao": item.descricao or "",
        "solucao": item.solucao or "",
        "observacoes": observacoes,
        "classificacao": item.classificacao,
        "motivos": item.motivos or "",
        "documento": nome_arquivo,
        "pagina": item.pagina,
        "metodo": metodo,
    }


def ingest_pages(
    session,
    pdf: Path,
    doc: Documento,
    page_data: list[dict],
    cfg: dict,
    categories: dict,
    rows: list[dict],
    persist: bool,
) -> None:
    for page in page_data:
        text = page["texto"]
        raw_text = text
        if page["metodo"] == "ocr_pendente":
            try:
                raw_text = ocr_page(
                    pdf, page["pagina"], cfg["ocr"]["dpi"], cfg["ocr"]["idioma"]
                )
                text = repair_ocr_text(raw_text)
                page["metodo"] = "ocr"
                logging.info(
                    "OCR concluído: %s p.%s bruto=%s chars limpo=%s chars",
                    pdf.name,
                    page["pagina"],
                    len(raw_text),
                    len(text),
                )
            except Exception as exc:
                message = f"{pdf.name}: {exc}"
                if persist:
                    session.add(
                        ErroProcessamento(
                            documento_id=doc.id,
                            pagina=page["pagina"],
                            etapa="ocr",
                            tipo=type(exc).__name__,
                            mensagem=message,
                        )
                    )
                logging.error("OCR falhou: %s p.%s — %s", pdf.name, page["pagina"], exc)
                continue
        logging.info(
            "Extração registrada: documento=%s pagina=%s metodo=%s",
            pdf.name,
            page["pagina"],
            page["metodo"],
        )
        for raw in split_records(text):
            fields = extract_fields(raw)
            classification, reasons, normalized = validate_record(fields, categories)
            protocol = (
                normalized.get("protocolo")
                or f"INVALIDO-{doc.id}-{page['pagina']}-{len(rows)+1}"
            )
            if find_by_protocol(session, protocol):
                classification = "duplicado"
                reasons.append("protocolo_duplicado")
            status = normalized.get("status_normalizado") or fields.get("status")
            row = {
                **fields,
                "protocolo": protocol,
                "categoria": normalized.get("categoria_normalizada")
                or fields.get("categoria"),
                "status": status,
                "data": normalized.get("data_obj"),
                "tempo_minutos": normalized.get("tempo_obj"),
                "classificacao": classification,
                "motivos": ";".join(reasons),
                "documento": pdf.name,
                "pagina": page["pagina"],
                "metodo": page["metodo"],
            }
            rows.append(row)
            if not persist:
                continue
            if classification == "duplicado":
                session.add(
                    ErroProcessamento(
                        documento_id=doc.id,
                        pagina=page["pagina"],
                        etapa="deduplicacao",
                        tipo="Duplicidade",
                        mensagem=protocol,
                    )
                )
                continue
            item = Atendimento(
                documento_id=doc.id,
                pagina=page["pagina"],
                protocolo=protocol,
                data=normalized.get("data_obj"),
                solicitante=fields.get("solicitante"),
                email=fields.get("email"),
                categoria=row["categoria"],
                descricao=fields.get("descricao"),
                solucao=fields.get("solucao"),
                tempo_minutos=normalized.get("tempo_obj"),
                status=status,
                cep=fields.get("cep"),
                municipio=None,
                uf=None,
                classificacao=classification,
                motivos=row["motivos"],
                texto_original=raw,
                texto_limpo=preprocess(raw),
            )
            session.add(item)
            session.flush()
            for idx, content in enumerate(
                split_chunks(
                    raw,
                    cfg["embeddings"]["tamanho_chunk"],
                    cfg["embeddings"]["sobreposicao"],
                )
            ):
                meta = {
                    "protocolo": protocol,
                    "documento": pdf.name,
                    "pagina": page["pagina"],
                    "categoria": row["categoria"] or "",
                }
                session.add(
                    Chunk(
                        atendimento_id=item.id,
                        documento_id=doc.id,
                        pagina=page["pagina"],
                        indice=idx,
                        conteudo=content,
                        metadata_json=metadata_json(**meta),
                    )
                )


def process_all(cfg: dict) -> pd.DataFrame:
    """
    Processa todos os documentos da pasta de entrada.

    1. Carrega a configuração do sistema.
    2. Cria o diretório de saída se não existir.
    3. Configura o logging.
    4. Carrega as categorias.
    5. Cria a sessão do banco de dados.
    6. Processa cada documento da pasta de entrada.
    7. Exporta os resultados.
    8. Gera os gráficos.

    Args:
        cfg (dict): Configuração do sistema.

    Returns:
        pd.DataFrame: DataFrame com os resultados do processamento.

    """

    root = Path(cfg["_root"])
    output = resolve(root, cfg["saida"]["diretorio"])
    output.mkdir(parents=True, exist_ok=True)
    
    configure_logging(output / cfg["saida"]["log"])
    
    categories = json.loads(
        (root / "data" / "auxiliares" / "categorias.json").read_text(encoding="utf-8")
    )
    
    factory = create_session_factory(resolve_db_url(root, cfg["banco"]["url"]))
    pdf_dir = resolve(root, cfg["entrada"]["diretorio_pdfs"])
    rows: list[dict] = []
    with session_scope(factory) as session:
        for pdf in sorted(pdf_dir.glob(cfg["entrada"]["padrao"])):
            logging.info("Documento localizado: %s", pdf.name)
            digest = sha256(pdf.read_bytes()).hexdigest()
            page_data = extract_pdf_pages(
                pdf, cfg["ocr"]["min_caracteres_extracao_direta"]
            )
            existing = session.scalar(
                select(Documento).where(Documento.hash_sha256 == digest)
            )
            if existing and has_ocr_failure(session, existing):
                logging.info("Reprocessando documento com falha de OCR: %s", pdf.name)
                purge_documento(session, existing)
                existing = None
            if existing:
                logging.info(
                    "Documento já processado; reutilizando registros: %s", pdf.name
                )
                rows.extend(
                    atendimento_to_row(item, pdf.name, existing.metodo)
                    for item in existing.atendimentos
                )
                if not existing.atendimentos:
                    ingest_pages(
                        session,
                        pdf,
                        existing,
                        page_data,
                        cfg,
                        categories,
                        rows,
                        persist=False,
                    )
                else:
                    for err in session.scalars(
                        select(ErroProcessamento).where(
                            ErroProcessamento.documento_id == existing.id,
                            ErroProcessamento.etapa == "deduplicacao",
                        )
                    ):
                        rows.append(
                            {
                                "protocolo": err.mensagem,
                                "data": None,
                                "solicitante": "",
                                "email": "",
                                "categoria": "",
                                "status": "",
                                "cep": "",
                                "tempo_minutos": None,
                                "descricao": "",
                                "solucao": "",
                                "observacoes": "",
                                "classificacao": "duplicado",
                                "motivos": "protocolo_duplicado",
                                "documento": pdf.name,
                                "pagina": err.pagina,
                                "metodo": existing.metodo,
                            }
                        )
                continue
            method = (
                "ocr"
                if all(page["metodo"] == "ocr_pendente" for page in page_data)
                else "extracao_direta"
            )
            doc = Documento(
                nome_arquivo=pdf.name,
                hash_sha256=digest,
                total_paginas=len(page_data),
                metodo=method,
            )
            session.add(doc)
            session.flush()
            ingest_pages(
                session, pdf, doc, page_data, cfg, categories, rows, persist=True
            )
    df = pd.DataFrame(rows)
    if not df.empty:
        export_results(df, output, cfg["saida"]["csv"], cfg["saida"]["indicadores"])
        generate_charts(df, resolve(root, cfg["saida"]["graficos"]))
    return df
