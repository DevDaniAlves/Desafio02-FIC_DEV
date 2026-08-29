from __future__ import annotations
import requests

_EMPTY = {"municipio": None, "uf": None}


def lookup_cep(cep: str, base_url: str, timeout: int = 8) -> dict | None:
    """Consulta CEP e retorna município e UF. Lança None se falha."""

    digits = "".join(ch for ch in cep if ch.isdigit())

    if len(digits) != 8:
        return None

    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/{digits}/json/",
            timeout=timeout,
            headers={"User-Agent": "fic-dev-desafio/1.0"},
        )

        response.raise_for_status()

        data = response.json()

        if data.get("erro"):
            return None

        return {
            "municipio": data.get("localidade"),
            "uf": data.get("uf"),
            "logradouro": data.get("logradouro"),
        }

    except (requests.RequestException, ValueError, TypeError):
        return None


def complement_cep(cep: str | None, cfg: dict) -> dict:
    """Complementa município e UF. Nunca lança: falha da API devolve None."""
    api = cfg.get("api") or {}

    base_url = api.get("cep_base_url")

    if not cep or not base_url:
        return dict(_EMPTY)

    try:
        timeout = int(api.get("timeout_segundos", 8))

    except (TypeError, ValueError):
        timeout = 8

    data = lookup_cep(cep, base_url, timeout)

    if not data:
        return dict(_EMPTY)

    return {"municipio": data.get("municipio"), "uf": data.get("uf")}
