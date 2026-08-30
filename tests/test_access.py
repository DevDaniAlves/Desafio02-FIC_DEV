import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.access import (
    cadastrar,
    autenticar,
    consumir_consulta,
    escolher_plano,
    estado_cota,
    validar_cartao,
    ativar_pagamento,
)
from src.models import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    item = Session(engine)
    yield item
    item.close()


def test_cadastro_rejeita_email_repetido(session):
    cadastrar(session, "ana@exemplo.br", "segredo1")
    session.commit()
    with pytest.raises(ValueError, match="já está cadastrado"):
        cadastrar(session, "ana@exemplo.br", "segredo2")


def test_cartao_exige_16_digitos_e_validade_futura():
    with pytest.raises(ValueError, match="16 dígitos"):
        validar_cartao("123", "12/99", "123")
    with pytest.raises(ValueError, match="futura"):
        validar_cartao("1234567812345678", "01/20", "123")
    validar_cartao("1234567812345678", "12/99", "123")


def test_gratis_por_ip_acaba_na_terceira(session):
    for _ in range(3):
        estado = consumir_consulta(session, "10.0.0.8", None)
    assert estado["restantes"] == 0
    with pytest.raises(PermissionError):
        consumir_consulta(session, "10.0.0.8", None)
    assert estado_cota(session, "10.0.0.9", None)["restantes"] == 3


def test_plano_diario_por_login(session):
    user = cadastrar(session, "bob@exemplo.br", "segredo1")
    sessao = autenticar(session, "bob@exemplo.br", "segredo1")
    escolher_plano(session, user.id, "diario_7")
    ativar_pagamento(session, user.id, "cartao")
    estado = estado_cota(session, "1.1.1.1", sessao.token)
    assert estado["pode_consultar"] is True
    assert estado["limite"] == 7
    assert estado["restantes"] == 7
