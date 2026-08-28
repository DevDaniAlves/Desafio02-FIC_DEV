"""Cliente tolerante a falhas para consulta de CEP."""
from __future__ import annotations
import requests

def lookup_cep(cep: str, base_url: str, timeout: int=8) -> dict | None:
    digits="".join(ch for ch in cep if ch.isdigit())
    if len(digits)!=8: return None
    try:
        response=requests.get(f"{base_url.rstrip('/')}/{digits}/json/",timeout=timeout,headers={"User-Agent":"fic-dev-desafio/1.0"})
        response.raise_for_status(); data=response.json()
        if data.get("erro"): return None
        return {"municipio":data.get("localidade"),"uf":data.get("uf"),"logradouro":data.get("logradouro")}
    except (requests.RequestException,ValueError):
        return None
