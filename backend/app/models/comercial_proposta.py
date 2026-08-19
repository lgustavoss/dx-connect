"""Proposta comercial versionada a partir da negociação CRM (#323 / #345–#347)."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

PROPOSTA_RASCUNHO = "rascunho"
PROPOSTA_ENVIADA = "enviada"
PROPOSTA_SUBSTITUIDA = "substituida"
PROPOSTA_STATUSES = frozenset({PROPOSTA_RASCUNHO, PROPOSTA_ENVIADA, PROPOSTA_SUBSTITUIDA})

CANAL_EMAIL = "email"
CANAL_IMPRESSO = "impresso"
CANAL_OUTRO = "outro"
PROPOSTA_CANAIS = frozenset({CANAL_EMAIL, CANAL_IMPRESSO, CANAL_OUTRO})


class PropostaTemplate(Base):
    __tablename__ = "comercial_proposta_templates"
    __table_args__ = (UniqueConstraint("nome", "versao", name="uq_comercial_proposta_template_nome_versao"),)

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False, index=True)
    versao = Column(Integer, nullable=False, default=1)
    conteudo_html = Column(Text, nullable=False)
    vigencia_inicio = Column(DateTime(timezone=True), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    propostas = relationship("Proposta", back_populates="template")


class Proposta(Base):
    __tablename__ = "comercial_propostas"

    id = Column(Integer, primary_key=True, index=True)
    negociacao_id = Column(
        Integer, ForeignKey("crm_negociacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id = Column(
        Integer, ForeignKey("comercial_proposta_templates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    gerado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(20), nullable=False, default=PROPOSTA_RASCUNHO, index=True)
    conteudo_html_snapshot = Column(Text, nullable=False)
    conteudo_hash = Column(String(64), nullable=False)
    linha_ids = Column(JSON, nullable=False, default=lambda: [])
    pdf_storage_key = Column(String(255), nullable=True)
    canal = Column(String(20), nullable=True)
    enviado_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    template = relationship("PropostaTemplate", back_populates="propostas")
    negociacao = relationship("CrmNegociacao")
    gerado_por = relationship("Atendente", foreign_keys=[gerado_por_id])
