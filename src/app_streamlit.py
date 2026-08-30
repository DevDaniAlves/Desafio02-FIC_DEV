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
PLAN_LABELS = {
    "diario_7": "7 fichas/dia · R$ 49/mês",
    "diario_15": "15 fichas/dia · R$ 99/mês",
    "ilimitado": "Ilimitado · R$ 199/mês",
}


def load_categories() -> list[str]:
    if not CATEGORIES_PATH.exists():
        return []
    data = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
    return [item["nome"] for item in data.get("categorias_oficiais", [])]


def client_ip() -> str:
    try:
        import streamlit as st

        ip = getattr(st.context, "ip_address", None)
        if ip:
            return str(ip)
        forwarded = (st.context.headers.get("X-Forwarded-For") or "").split(",")[0]
        return forwarded.strip() or "local"
    except Exception:
        return "local"


def headers(token: str | None) -> dict[str, str]:
    out = {"X-Client-IP": client_ip()}
    if token:
        out["Authorization"] = f"Bearer {token}"
    return out


def check_health(base_url: str) -> dict | None:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def get_cota(base_url: str, token: str | None) -> dict | None:
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/cota", headers=headers(token), timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def ask_api(
    base_url: str,
    pergunta: str,
    top_k: int,
    categoria: str | None,
    token: str | None,
) -> requests.Response:
    payload = {"pergunta": pergunta, "top_k": top_k}
    if categoria:
        payload["categoria"] = categoria
    return requests.post(
        f"{base_url.rstrip('/')}/ask",
        json=payload,
        headers=headers(token),
        timeout=60,
    )


def _render_auth(st, api_url: str) -> None:
    token = st.session_state.get("token")
    cota = get_cota(api_url, token)
    if cota and cota.get("autenticado"):
        st.success(cota.get("email"))
        if cota.get("plano"):
            resto = cota.get("restantes")
            st.caption(
                f"Plano {PLAN_LABELS.get(cota['plano'], cota['plano'])}. "
                + (
                    "Fichas ilimitadas hoje."
                    if resto is None
                    else f"Restam {resto} fichas hoje."
                )
            )
        else:
            st.warning("Sem plano ativo. Escolha um abaixo para continuar.")
        if st.button("Sair"):
            st.session_state.pop("token", None)
            st.rerun()
        return

    st.caption("3 fichas grátis por IP, sem cadastro.")
    if cota:
        st.caption(f"Restam {cota.get('restantes', 0)} fichas grátis neste IP.")
    modo = st.radio("Acesso", ["Entrar", "Cadastrar"], horizontal=True)
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    rota = "/auth/login" if modo == "Entrar" else "/auth/cadastro"
    if st.button(modo, type="primary"):
        try:
            response = requests.post(
                f"{api_url.rstrip('/')}{rota}",
                json={"email": email, "senha": senha},
                timeout=15,
            )
            if response.status_code >= 400:
                detail = response.json().get("detail", response.text)
                st.error(detail)
            else:
                st.session_state["token"] = response.json()["token"]
                st.rerun()
        except requests.RequestException as exc:
            st.error(f"Falha no acesso: {exc}")


def _render_planos(st, api_url: str, cota: dict) -> None:
    if not cota.get("autenticado") or cota.get("plano"):
        return
    st.subheader("Escolha o bloco de fichas")
    st.caption("Pagamento ilustrativo — não há cobrança real.")
    plano = st.radio(
        "Plano",
        list(PLAN_LABELS),
        format_func=lambda key: PLAN_LABELS[key],
    )
    if st.button("Reservar plano"):
        response = requests.post(
            f"{api_url.rstrip('/')}/planos/escolher",
            json={"plano": plano},
            headers=headers(st.session_state.get("token")),
            timeout=15,
        )
        if response.status_code >= 400:
            st.error(response.json().get("detail", response.text))
        else:
            st.session_state["plano_pendente"] = plano
            st.success("Plano reservado. Pague abaixo para ativar.")

    metodo = st.radio("Pagamento", ["Cartão", "PIX"], horizontal=True)
    if metodo == "Cartão":
        numero = st.text_input("Número (16 dígitos)")
        validade = st.text_input("Validade MM/AA")
        cvv = st.text_input("Código de segurança", type="password")
        if st.button("Pagar"):
            requests.post(
                f"{api_url.rstrip('/')}/planos/escolher",
                json={"plano": plano},
                headers=headers(st.session_state.get("token")),
                timeout=15,
            )
            response = requests.post(
                f"{api_url.rstrip('/')}/pagar/cartao",
                json={"numero": numero, "validade": validade, "cvv": cvv},
                headers=headers(st.session_state.get("token")),
                timeout=15,
            )
            if response.status_code >= 400:
                st.error(response.json().get("detail", response.text))
            else:
                st.success("Pagamento ilustrativo confirmado. Plano ativo.")
                st.rerun()
        return

    if st.button("Gerar QR PIX"):
        requests.post(
            f"{api_url.rstrip('/')}/planos/escolher",
            json={"plano": plano},
            headers=headers(st.session_state.get("token")),
            timeout=15,
        )
        response = requests.post(
            f"{api_url.rstrip('/')}/pagar/pix",
            headers=headers(st.session_state.get("token")),
            timeout=15,
        )
        if response.status_code >= 400:
            st.error(response.json().get("detail", response.text))
        else:
            st.session_state["pix"] = response.json()
    pix = st.session_state.get("pix")
    if pix:
        st.image(pix["qr"], caption=f"PIX estático · R$ {pix['preco']}")
        st.code(pix["copia_cola"])
        if st.button("Já paguei"):
            response = requests.post(
                f"{api_url.rstrip('/')}/pagar/pix/confirmar",
                headers=headers(st.session_state.get("token")),
                timeout=15,
            )
            if response.status_code >= 400:
                st.error(response.json().get("detail", response.text))
            else:
                st.session_state.pop("pix", None)
                st.success("PIX ilustrativo confirmado. Plano ativo.")
                st.rerun()


def _render_resposta(st, data: dict) -> None:
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
    if data.get("cota"):
        resto = data["cota"].get("restantes")
        if resto is not None:
            st.caption(f"Fichas restantes: {resto}")
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


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Arquivo de atendimentos", page_icon="📋", layout="wide")
    st.title("Arquivo de atendimentos")
    st.caption(
        "Consulta os protocolos extraídos dos PDFs. Três fichas grátis por IP; "
        "depois, cadastro e um bloco de fichas mensal."
    )

    with st.sidebar:
        st.header("Balcão")
        api_url = st.text_input("API", value=DEFAULT_API)
        health = check_health(api_url)
        if health:
            st.success(f"API no ar · {health.get('modo', '?')}")
        else:
            st.error("API indisponível. Suba com `uvicorn src.api:app`.")
        _render_auth(st, api_url)
        categories = load_categories()
        category_choice = st.selectbox("Categoria", [ALL_CATEGORIES, *categories])
        top_k = st.slider("Fontes", 1, 10, 5)
        st.caption("Cada fonte é um trecho de um protocolo persistido no Chroma.")

    token = st.session_state.get("token")
    cota = get_cota(api_url, token) or {}
    _render_planos(st, api_url, cota)

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
        response = ask_api(api_url, question.strip(), top_k, categoria, token)
    except requests.RequestException as exc:
        st.error(f"Não foi possível consultar a API: {exc}")
        return
    if response.status_code == 402:
        detalhe = response.json().get("detail", {})
        if isinstance(detalhe, dict):
            st.error(detalhe.get("mensagem", "Cota esgotada."))
        else:
            st.error(str(detalhe))
        return
    if response.status_code >= 400:
        st.error(f"Não foi possível consultar a API: {response.text}")
        return
    _render_resposta(st, response.json())


if __name__ == "__main__" or not os.getenv("PYTEST_CURRENT_TEST"):
    main()
