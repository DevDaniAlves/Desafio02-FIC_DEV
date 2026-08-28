"""Extração por regex, normalização e validação dos registros."""
from __future__ import annotations
from datetime import datetime
import re, unicodedata

EMAIL_RE=re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PROTO_RE=re.compile(r"^AT-\d{3}$")
CEP_RE=re.compile(r"^\d{5}-?\d{3}$")
FIELD_PATTERNS={
 "protocolo":r"Protocolo\s+(AT-\d{3}|PROTOCOLO\?)", "data":r"Data\s+(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})",
 "solicitante":r"Solicitante\s+(.+?)\s+E-mail", "email":r"E-mail\s+(\S+)", "categoria":r"Categoria\s+(.+?)\s+Status",
 "status":r"Status\s+(Concluido|Pendente|Em atendimento)", "cep":r"CEP\s*/?\s*cidade\s+(\S+)",
 "tempo_minutos":r"Tempo\s+(-?\d+)?\s*min", "descricao":r"Problema\s+(.+?)\s+Solucao",
 "solucao":r"Solucao\s+(.+?)\s+Observacoes", "observacoes":r"Observacoes\s+(.+)$"}

def clean_text(text: str) -> str:
    text=text.replace("\x00", " ")
    return re.sub(r"\s+", " ", text).strip()

def extract_fields(text: str) -> dict:
    clean=clean_text(text); result={}
    for key,pattern in FIELD_PATTERNS.items():
        match=re.search(pattern,clean,re.I|re.S)
        result[key]=match.group(1).strip() if match else ""
    return result

def parse_date(value: str):
    for fmt in ("%d/%m/%Y","%Y-%m-%d"):
        try: return datetime.strptime(value,fmt).date()
        except ValueError: pass
    return None

def normalize_key(value: str) -> str:
    value=unicodedata.normalize("NFKD",value).encode("ascii","ignore").decode().lower().strip()
    return re.sub(r"\s+"," ",value)

def normalize_category(value: str, categories: dict) -> str | None:
    target=normalize_key(value)
    for item in categories.get("categorias_oficiais",[]):
        if target in {normalize_key(item["nome"]),*(normalize_key(v) for v in item["variacoes"])}:
            return item["nome"]
    return None

def validate_record(record: dict, categories: dict) -> tuple[str,list[str],dict]:
    r=dict(record); reasons=[]
    protocol=r.get("protocolo","").strip().upper(); r["protocolo"]=protocol
    if not PROTO_RE.fullmatch(protocol): reasons.append("protocolo_invalido")
    r["data_obj"]=parse_date(r.get("data", ""))
    if not r["data_obj"]: reasons.append("data_invalida")
    if not EMAIL_RE.fullmatch(r.get("email", "")): reasons.append("email_invalido")
    cep=r.get("cep","").strip(); r["cep"]=cep
    if not CEP_RE.fullmatch(cep): reasons.append("cep_invalido")
    r["categoria_normalizada"]=normalize_category(r.get("categoria",""),categories)
    if not r["categoria_normalizada"]: reasons.append("categoria_invalida")
    try:
        r["tempo_obj"]=float(r.get("tempo_minutos",""))
        if r["tempo_obj"] < 0: raise ValueError
    except (ValueError,TypeError):
        r["tempo_obj"]=None; reasons.append("tempo_invalido")
    for required in ("solicitante","descricao"):
        if not r.get(required,"").strip(): reasons.append(f"{required}_ausente")
    classification="valido" if not reasons else ("incompleto" if any(x.endswith("_ausente") for x in reasons) else "invalido")
    return classification,reasons,r
