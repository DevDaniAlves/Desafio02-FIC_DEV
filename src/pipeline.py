"""Orquestração do processamento ponta a ponta."""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json, logging, re
import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .config import resolve
from .database import create_session_factory, session_scope, find_by_protocol
from .models import Documento, Atendimento, Chunk, ErroProcessamento
from .pdf_processor import extract_pdf_pages
from .ocr_processor import ocr_page
from .validation import extract_fields, validate_record, clean_text
from .text_processor import preprocess, split_chunks, metadata_json
from .analytics import export_results, generate_charts

def configure_logging(path: Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s",handlers=[logging.FileHandler(path,encoding="utf-8"),logging.StreamHandler()])

def split_records(page_text: str) -> list[str]:
    parts=re.split(r"(?=Protocolo\s+(?:AT-\d{3}|PROTOCOLO\?))",clean_text(page_text),flags=re.I)
    return [p.strip() for p in parts if re.search(r"Protocolo\s+",p,re.I)]

def process_all(cfg: dict) -> pd.DataFrame:
    root=Path(cfg["_root"]); output=resolve(root,cfg["saida"]["diretorio"]); output.mkdir(parents=True,exist_ok=True)
    configure_logging(output/cfg["saida"]["log"])
    categories=json.loads((root/"data"/"auxiliares"/"categorias.json").read_text(encoding="utf-8"))
    db_url=cfg["banco"]["url"]
    if db_url.startswith("sqlite:/// "): db_url="sqlite:///"+str(root/db_url.removeprefix("sqlite:/// "))
    elif db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"): db_url="sqlite:///"+str(root/db_url[10:])
    factory=create_session_factory(db_url)
    pdf_dir=resolve(root,cfg["entrada"]["diretorio_pdfs"]); rows=[]
    with session_scope(factory) as session:
        for pdf in sorted(pdf_dir.glob(cfg["entrada"]["padrao"])):
            digest=sha256(pdf.read_bytes()).hexdigest(); page_data=extract_pdf_pages(pdf,cfg["ocr"]["min_caracteres_extracao_direta"])
            if session.scalar(select(Documento).where(Documento.hash_sha256==digest)):
                logging.info("Documento já processado; ignorando: %s",pdf.name)
                continue
            method="ocr" if all(p["metodo"]=="ocr_pendente" for p in page_data) else "extracao_direta"
            doc=Documento(nome_arquivo=pdf.name,hash_sha256=digest,total_paginas=len(page_data),metodo=method); session.add(doc); session.flush()
            for page in page_data:
                text=page["texto"]
                if page["metodo"]=="ocr_pendente":
                    try: text=ocr_page(pdf,page["pagina"],cfg["ocr"]["dpi"],cfg["ocr"]["idioma"]); page["metodo"]="ocr"
                    except Exception as exc:
                        session.add(ErroProcessamento(documento_id=doc.id,pagina=page["pagina"],etapa="ocr",tipo=type(exc).__name__,mensagem=str(exc))); logging.exception("OCR falhou: %s p.%s",pdf.name,page["pagina"]); continue
                for raw in split_records(text):
                    fields=extract_fields(raw); classification,reasons,normalized=validate_record(fields,categories)
                    protocol=normalized.get("protocolo") or f"INVALIDO-{doc.id}-{page['pagina']}-{len(rows)+1}"
                    if find_by_protocol(session,protocol): classification="duplicado"; reasons.append("protocolo_duplicado")
                    row={**fields,"protocolo":protocol,"categoria":normalized.get("categoria_normalizada") or fields.get("categoria"),"data":normalized.get("data_obj"),"tempo_minutos":normalized.get("tempo_obj"),"classificacao":classification,"motivos":";".join(reasons),"documento":pdf.name,"pagina":page["pagina"],"metodo":page["metodo"]}
                    rows.append(row)
                    if classification=="duplicado":
                        session.add(ErroProcessamento(documento_id=doc.id,pagina=page["pagina"],etapa="deduplicacao",tipo="Duplicidade",mensagem=protocol)); continue
                    item=Atendimento(documento_id=doc.id,pagina=page["pagina"],protocolo=protocol,data=normalized.get("data_obj"),solicitante=fields.get("solicitante"),email=fields.get("email"),categoria=row["categoria"],descricao=fields.get("descricao"),solucao=fields.get("solucao"),tempo_minutos=normalized.get("tempo_obj"),status=fields.get("status"),cep=fields.get("cep"),municipio=None,uf=None,classificacao=classification,motivos=row["motivos"],texto_original=raw,texto_limpo=preprocess(raw))
                    session.add(item); session.flush()
                    for idx,content in enumerate(split_chunks(raw,cfg["embeddings"]["tamanho_chunk"],cfg["embeddings"]["sobreposicao"])):
                        meta={"protocolo":protocol,"documento":pdf.name,"pagina":page["pagina"],"categoria":row["categoria"] or ""}
                        session.add(Chunk(atendimento_id=item.id,documento_id=doc.id,pagina=page["pagina"],indice=idx,conteudo=content,metadata_json=metadata_json(**meta)))
    df=pd.DataFrame(rows)
    if not df.empty:
        export_results(df,output,cfg["saida"]["csv"],cfg["saida"]["indicadores"]); generate_charts(df,resolve(root,cfg["saida"]["graficos"]))
    return df
