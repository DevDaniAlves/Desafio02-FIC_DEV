"""Modelos SQLAlchemy do domínio."""
from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import String, Text, Integer, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Documento(Base):
    __tablename__ = "documentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome_arquivo: Mapped[str] = mapped_column(String(255), unique=True)
    hash_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    total_paginas: Mapped[int] = mapped_column(Integer)
    metodo: Mapped[str] = mapped_column(String(30))
    processado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    atendimentos: Mapped[list["Atendimento"]] = relationship(back_populates="documento", cascade="all, delete-orphan")

class Atendimento(Base):
    __tablename__ = "atendimentos"
    __table_args__ = (UniqueConstraint("protocolo", name="uq_atendimento_protocolo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos.id"))
    pagina: Mapped[int] = mapped_column(Integer)
    protocolo: Mapped[str] = mapped_column(String(30))
    data: Mapped[date | None] = mapped_column(Date, nullable=True)
    solicitante: Mapped[str | None] = mapped_column(String(160), nullable=True)
    email: Mapped[str | None] = mapped_column(String(180), nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    solucao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tempo_minutos: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cep: Mapped[str | None] = mapped_column(String(10), nullable=True)
    municipio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    classificacao: Mapped[str] = mapped_column(String(30), default="valido")
    motivos: Mapped[str | None] = mapped_column(Text, nullable=True)
    texto_original: Mapped[str] = mapped_column(Text)
    texto_limpo: Mapped[str] = mapped_column(Text)
    documento: Mapped[Documento] = relationship(back_populates="atendimentos")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="atendimento", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    atendimento_id: Mapped[int] = mapped_column(ForeignKey("atendimentos.id"))
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos.id"))
    pagina: Mapped[int] = mapped_column(Integer)
    indice: Mapped[int] = mapped_column(Integer)
    conteudo: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text)
    atendimento: Mapped[Atendimento] = relationship(back_populates="chunks")

class ErroProcessamento(Base):
    __tablename__ = "erros_processamento"
    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[int | None] = mapped_column(ForeignKey("documentos.id"), nullable=True)
    pagina: Mapped[int | None] = mapped_column(Integer, nullable=True)
    etapa: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(80))
    mensagem: Mapped[str] = mapped_column(Text)
    registrado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
