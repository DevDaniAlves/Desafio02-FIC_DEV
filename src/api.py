"""API HTTP de consulta semântica (RF15) e acesso por cota/plano."""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .access import (
    PLANOS,
    assinatura_pendente,
    ativar_pagamento,
    autenticar,
    cadastrar,
    consumir_consulta,
    escolher_plano,
    estado_cota,
    pix_payload,
    pix_qr_data_url,
    session_factory,
    usuario_da_sessao,
    validar_cartao,
    with_access,
)
from .config import load_config
from .indexer import all_atendimentos, semantic_query
from .rag import answer, classify_query, resolve_provider

app = FastAPI(title="Atendimentos FIC_DEV", version="1.0.0")
cfg = load_config()
session_factory(cfg)


class AskRequest(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    categoria: str | None = None


class ContaRequest(BaseModel):
    email: str
    senha: str


class PlanoRequest(BaseModel):
    plano: str


class CartaoRequest(BaseModel):
    numero: str
    validade: str
    cvv: str


def _modo() -> str:
    provider = resolve_provider()
    return f"rag_{provider}" if provider else "recuperacao_local"


def _token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return authorization.strip() or None


def _ip(request: Request, x_client_ip: str | None) -> str:
    if x_client_ip and x_client_ip.strip():
        return x_client_ip.split(",")[0].strip()
    return request.client.host if request.client else "local"


def _cota_bloqueada(estado: dict) -> HTTPException:
    mensagens = {
        "cadastro": "As 3 consultas grátis deste IP acabaram. Cadastre-se e escolha um plano.",
        "plano": "Entre e ative um plano para continuar consultando.",
        "limite_diario": "O limite diário do seu plano acabou. Tente amanhã.",
    }
    return HTTPException(
        status_code=402,
        detail={
            "mensagem": mensagens.get(estado.get("motivo"), "Consulta indisponível."),
            "motivo": estado.get("motivo"),
            "cota": estado,
        },
    )


@app.get("/")
def root():
    return {
        "servico": "Consulta de atendimentos",
        "endpoints": {
            "health": "/health",
            "ask": "POST /ask",
            "cadastro": "POST /auth/cadastro",
            "login": "POST /auth/login",
            "planos": "/planos",
        },
        "modo": _modo(),
        "provedor": resolve_provider(),
    }


@app.get("/health")
def health():
    return {"status": "ok", "modo": _modo(), "provedor": resolve_provider()}


@app.get("/planos")
def listar_planos():
    return {"gratis_por_ip": 3, "planos": list(PLANOS.values())}


@app.post("/auth/cadastro")
def auth_cadastro(payload: ContaRequest):
    try:
        with with_access(cfg) as session:
            user = cadastrar(session, payload.email, payload.senha)
            sessao = autenticar(session, user.email, payload.senha)
            return {"token": sessao.token, "email": user.email}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/auth/login")
def auth_login(payload: ContaRequest):
    try:
        with with_access(cfg) as session:
            sessao = autenticar(session, payload.email, payload.senha)
            user = usuario_da_sessao(session, sessao.token)
            return {"token": sessao.token, "email": user.email if user else payload.email}
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/eu")
def eu(authorization: str | None = Header(default=None)):
    with with_access(cfg) as session:
        user = usuario_da_sessao(session, _token(authorization))
        if not user:
            raise HTTPException(status_code=401, detail="Sessão inválida.")
        return {"email": user.email}


@app.get("/cota")
def cota(
    request: Request,
    authorization: str | None = Header(default=None),
    x_client_ip: str | None = Header(default=None),
):
    with with_access(cfg) as session:
        return estado_cota(session, _ip(request, x_client_ip), _token(authorization))


@app.post("/planos/escolher")
def planos_escolher(payload: PlanoRequest, authorization: str | None = Header(default=None)):
    with with_access(cfg) as session:
        user = usuario_da_sessao(session, _token(authorization))
        if not user:
            raise HTTPException(status_code=401, detail="Faça login para escolher um plano.")
        try:
            item = escolher_plano(session, user.id, payload.plano)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        spec = PLANOS[item.plano]
        return {"plano": item.plano, "status": item.status, "preco": spec["preco"]}


@app.post("/pagar/cartao")
def pagar_cartao(payload: CartaoRequest, authorization: str | None = Header(default=None)):
    with with_access(cfg) as session:
        user = usuario_da_sessao(session, _token(authorization))
        if not user:
            raise HTTPException(status_code=401, detail="Faça login para pagar.")
        try:
            validar_cartao(payload.numero, payload.validade, payload.cvv)
            item = ativar_pagamento(session, user.id, "cartao")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": item.status, "plano": item.plano, "metodo": "cartao"}


@app.post("/pagar/pix")
def pagar_pix(authorization: str | None = Header(default=None)):
    with with_access(cfg) as session:
        user = usuario_da_sessao(session, _token(authorization))
        if not user:
            raise HTTPException(status_code=401, detail="Faça login para pagar.")
        item = assinatura_pendente(session, user.id)
        if not item:
            raise HTTPException(status_code=400, detail="Escolha um plano antes de gerar o PIX.")
        copia = pix_payload(user.email, item.plano)
        return {
            "plano": item.plano,
            "preco": PLANOS[item.plano]["preco"],
            "copia_cola": copia,
            "qr": pix_qr_data_url(copia),
        }


@app.post("/pagar/pix/confirmar")
def pagar_pix_confirmar(authorization: str | None = Header(default=None)):
    with with_access(cfg) as session:
        user = usuario_da_sessao(session, _token(authorization))
        if not user:
            raise HTTPException(status_code=401, detail="Faça login para confirmar o PIX.")
        try:
            item = ativar_pagamento(session, user.id, "pix")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": item.status, "plano": item.plano, "metodo": "pix"}


@app.post("/ask")
def ask(
    payload: AskRequest,
    request: Request,
    authorization: str | None = Header(default=None),
    x_client_ip: str | None = Header(default=None),
):
    ip = _ip(request, x_client_ip)
    token = _token(authorization)
    with with_access(cfg) as session:
        estado = estado_cota(session, ip, token)
        if not estado["pode_consultar"]:
            raise _cota_bloqueada(estado)
    escopo = classify_query(payload.pergunta)
    try:
        preview = semantic_query(
            cfg, payload.pergunta, payload.top_k, payload.categoria
        )
        if escopo == "completo":
            sources = all_atendimentos(cfg, payload.categoria)
        else:
            sources = preview
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Consulta indisponível: {type(exc).__name__}",
        ) from exc
    result = answer(payload.pergunta, sources, escopo=escopo)
    result["escopo"] = escopo
    result["fontes"] = preview
    if escopo == "completo":
        result["total_base"] = len(sources)
        result["aviso"] = (
            f"O sistema enviou todos os {len(sources)} atendimentos para a "
            "contagem porque a pergunta é quantitativa; assim a resposta "
            "fica mais precisa. A lista abaixo mostra só os "
            f"{len(preview)} mais semelhantes (top-k)."
        )
    with with_access(cfg) as session:
        result["cota"] = consumir_consulta(session, ip, token)
    return result
