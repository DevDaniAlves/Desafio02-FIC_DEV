"""Cadastro, sessão, cotas (IP grátis / plano por login) e pagamento ilustrativo."""

from __future__ import annotations

import base64
import hashlib
import io
import re
import secrets
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import create_session_factory, resolve_db_url, session_scope
from .models import Assinatura, Sessao, UsoConsulta, Usuario

GRATIS_POR_IP = 3
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PLANOS = {
    "diario_7": {
        "id": "diario_7",
        "nome": "7 fichas por dia",
        "preco": 49,
        "limite_diario": 7,
    },
    "diario_15": {
        "id": "diario_15",
        "nome": "15 fichas por dia",
        "preco": 99,
        "limite_diario": 15,
    },
    "ilimitado": {
        "id": "ilimitado",
        "nome": "Fichas ilimitadas",
        "preco": 199,
        "limite_diario": None,
    },
}


def session_factory(cfg: dict):
    root = Path(cfg["_root"])
    return create_session_factory(resolve_db_url(root, cfg["banco"]["url"]))


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 120_000
    ).hex()
    return f"{salt}:{digest}"


def check_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(":", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 120_000
    ).hex()
    return secrets.compare_digest(candidate, digest)


def cadastrar(session: Session, email: str, senha: str) -> Usuario:
    email = email.strip().lower()
    if not EMAIL_RE.fullmatch(email):
        raise ValueError("Informe um e-mail válido.")
    if len(senha) < 6:
        raise ValueError("A senha precisa ter pelo menos 6 caracteres.")
    user = Usuario(email=email, senha_hash=hash_password(senha))
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("Este e-mail já está cadastrado.") from exc
    return user


def autenticar(session: Session, email: str, senha: str) -> Sessao:
    email = email.strip().lower()
    user = session.scalar(select(Usuario).where(Usuario.email == email))
    if not user or not check_password(senha, user.senha_hash):
        raise ValueError("E-mail ou senha inválidos.")
    token = secrets.token_hex(32)
    item = Sessao(token=token, usuario_id=user.id)
    session.add(item)
    session.flush()
    return item


def usuario_da_sessao(session: Session, token: str | None) -> Usuario | None:
    if not token:
        return None
    row = session.scalar(select(Sessao).where(Sessao.token == token))
    if not row:
        return None
    return session.get(Usuario, row.usuario_id)


def assinatura_ativa(session: Session, usuario_id: int) -> Assinatura | None:
    return session.scalar(
        select(Assinatura)
        .where(Assinatura.usuario_id == usuario_id, Assinatura.status == "ativo")
        .order_by(Assinatura.id.desc())
        .limit(1)
    )


def assinatura_pendente(session: Session, usuario_id: int) -> Assinatura | None:
    return session.scalar(
        select(Assinatura)
        .where(Assinatura.usuario_id == usuario_id, Assinatura.status == "pendente")
        .order_by(Assinatura.id.desc())
        .limit(1)
    )


def escolher_plano(session: Session, usuario_id: int, plano: str) -> Assinatura:
    if plano not in PLANOS:
        raise ValueError("Plano inválido.")
    atual = assinatura_pendente(session, usuario_id)
    if atual:
        atual.plano = plano
        session.flush()
        return atual
    item = Assinatura(usuario_id=usuario_id, plano=plano, status="pendente")
    session.add(item)
    session.flush()
    return item


def validar_cartao(numero: str, validade: str, cvv: str) -> None:
    digits = re.sub(r"\D", "", numero or "")
    if len(digits) != 16:
        raise ValueError("O cartão precisa ter 16 dígitos.")
    match = re.fullmatch(r"\s*(\d{2})\s*/\s*(\d{2})\s*", validade or "")
    if not match:
        raise ValueError("Validade no formato MM/AA.")
    month, year = int(match.group(1)), int(match.group(2)) + 2000
    if month < 1 or month > 12:
        raise ValueError("Mês de validade inválido.")
    last = date(year, month, 1)
    today = date.today().replace(day=1)
    if last < today:
        raise ValueError("A validade precisa ser futura.")
    if not re.fullmatch(r"\d{3,4}", (cvv or "").strip()):
        raise ValueError("Código de segurança inválido.")


def ativar_pagamento(session: Session, usuario_id: int, metodo: str) -> Assinatura:
    pendente = assinatura_pendente(session, usuario_id)
    if not pendente:
        raise ValueError("Escolha um plano antes de pagar.")
    for item in session.scalars(
        select(Assinatura).where(
            Assinatura.usuario_id == usuario_id, Assinatura.status == "ativo"
        )
    ):
        item.status = "substituido"
    pendente.status = "ativo"
    pendente.metodo = metodo
    session.flush()
    return pendente


def pix_payload(email: str, plano: str) -> str:
    preco = PLANOS[plano]["preco"]
    return (
        f"00020126360014BR.GOV.BCB.PIX0114arquivo@fic.dev"
        f"5204000053039865405{preco:05.2f}5802BR"
        f"5925ARQUIVO ATENDIMENTOS FIC6009CACERES"
        f"62070503***6304MOCK"
    )


def pix_qr_png(payload: str) -> bytes:
    import qrcode

    image = qrcode.make(payload, box_size=6, border=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def pix_qr_data_url(payload: str) -> str:
    raw = pix_qr_png(payload)
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def _usos_gratis(session: Session, ip: str) -> int:
    return int(
        session.scalar(
            select(func.count(UsoConsulta.id)).where(
                UsoConsulta.usuario_id.is_(None), UsoConsulta.ip == ip
            )
        )
        or 0
    )


def _usos_hoje(session: Session, usuario_id: int) -> int:
    inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return int(
        session.scalar(
            select(func.count(UsoConsulta.id)).where(
                UsoConsulta.usuario_id == usuario_id, UsoConsulta.criado_em >= inicio
            )
        )
        or 0
    )


def estado_cota(session: Session, ip: str, token: str | None) -> dict:
    user = usuario_da_sessao(session, token)
    if not user:
        usados = _usos_gratis(session, ip)
        return {
            "autenticado": False,
            "email": None,
            "plano": None,
            "limite": GRATIS_POR_IP,
            "usados": usados,
            "restantes": max(GRATIS_POR_IP - usados, 0),
            "pode_consultar": usados < GRATIS_POR_IP,
            "motivo": None if usados < GRATIS_POR_IP else "cadastro",
        }
    ativa = assinatura_ativa(session, user.id)
    if not ativa:
        return {
            "autenticado": True,
            "email": user.email,
            "plano": None,
            "limite": 0,
            "usados": 0,
            "restantes": 0,
            "pode_consultar": False,
            "motivo": "plano",
        }
    spec = PLANOS[ativa.plano]
    if spec["limite_diario"] is None:
        return {
            "autenticado": True,
            "email": user.email,
            "plano": ativa.plano,
            "limite": None,
            "usados": _usos_hoje(session, user.id),
            "restantes": None,
            "pode_consultar": True,
            "motivo": None,
        }
    usados = _usos_hoje(session, user.id)
    return {
        "autenticado": True,
        "email": user.email,
        "plano": ativa.plano,
        "limite": spec["limite_diario"],
        "usados": usados,
        "restantes": max(spec["limite_diario"] - usados, 0),
        "pode_consultar": usados < spec["limite_diario"],
        "motivo": None if usados < spec["limite_diario"] else "limite_diario",
    }


def consumir_consulta(session: Session, ip: str, token: str | None) -> dict:
    estado = estado_cota(session, ip, token)
    if not estado["pode_consultar"]:
        raise PermissionError(estado["motivo"] or "cota")
    user = usuario_da_sessao(session, token)
    session.add(UsoConsulta(ip=ip, usuario_id=user.id if user else None))
    session.flush()
    return estado_cota(session, ip, token)


def with_access(cfg: dict):
    return session_scope(session_factory(cfg))
