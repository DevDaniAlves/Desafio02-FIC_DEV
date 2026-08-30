"""Interface Streamlit de consulta ao arquivo de atendimentos (RF16)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES_PATH = ROOT / "data" / "auxiliares" / "categorias.json"
DEFAULT_API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
ALL_CATEGORIES = "(todas)"


def load_categories() -> list[str]:
    if not CATEGORIES_PATH.exists():
        return []
    data = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
    return [item["nome"] for item in data.get("categorias_oficiais", [])]


def check_health(base_url: str) -> dict | None:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def ask_api(base_url: str, pergunta: str, top_k: int, categoria: str | None) -> dict:
    payload = {"pergunta": pergunta, "top_k": top_k}
    if categoria:
        payload["categoria"] = categoria
    response = requests.post(
        f"{base_url.rstrip('/')}/ask", json=payload, timeout=60
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Arquivo de atendimentos", page_icon="📋", layout="wide")
    st.title("Arquivo de atendimentos")
    st.caption(
        "Consulta os protocolos extraídos dos PDFs. A resposta cita o AT-XXX, "
        "o documento e a página de origem."
    )

    with st.sidebar:
        st.header("Consulta")
        api_url = st.text_input("API", value=DEFAULT_API)
        health = check_health(api_url)
        if health:
            st.success(f"API no ar · {health.get('modo', '?')}")
        else:
            st.error("API indisponível. Suba com `uvicorn src.api:app`.")
        categories = load_categories()
        category_choice = st.selectbox("Categoria", [ALL_CATEGORIES, *categories])
        top_k = st.slider("Fontes", 1, 10, 5)
        st.caption("Cada fonte é um trecho de um protocolo persistido no Chroma.")

    question = st.text_area(
        "Pergunta sobre os atendimentos",
        placeholder="Quais problemas de instalação do Python aparecem com maior frequência?",
        height=120,
    )
    consultar = st.button(
        "Consultar arquivo", type="primary", disabled=not question.strip()
    )

    if not consultar:
        return

    categoria = None if category_choice == ALL_CATEGORIES else category_choice
    try:
        data = ask_api(api_url, question.strip(), top_k, categoria)
    except requests.RequestException as exc:
        st.error(f"Não foi possível consultar a API: {exc}")
        return

    st.subheader("Resposta")
    st.write(data.get("resposta", ""))
    escopo = data.get("escopo") or "ktop"
    fontes = data.get("fontes") or []
    if escopo == "completo":
        st.info(
            data.get("aviso")
            or "O sistema enviou a base completa para a contagem."
        )
        st.caption(
            f"Modo: {data.get('modo', '?')} · escopo: completo · "
            f"{data.get('total_base', '?')} na contagem · "
            f"{len(fontes)} no top-k"
        )
    else:
        st.caption(
            f"Modo: {data.get('modo', '?')} · escopo: ktop · "
            f"{len(fontes)} fonte(s)"
        )
        if data.get("aviso"):
            st.warning(data["aviso"])
    st.subheader(f"Protocolos mais semelhantes — top-k ({len(fontes)})")
    if not fontes:
        st.info("Nenhum trecho sustentou a pergunta. Processe e indexe os PDFs.")
        return
    for source in fontes:
        protocolo = source.get("protocolo") or "sem protocolo"
        similaridade = source.get("similaridade")
        score = (
            f"{similaridade:.2f}" if isinstance(similaridade, (int, float)) else "—"
        )
        with st.container(border=True):
            st.markdown(f"**{protocolo}** · similaridade {score}")
            st.caption(
                f"{source.get('documento')} · página {source.get('pagina')} · "
                f"trecho {source.get('indice')} · id {source.get('chunk_id')}"
            )
            if source.get("conteudo"):
                st.write(source["conteudo"])


if __name__ == "__main__" or not os.getenv("PYTEST_CURRENT_TEST"):
    main()
