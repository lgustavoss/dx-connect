"""Contrato comercial por CNPJ da negociação (#324 / #349–#352)."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

CONTRATO_RASCUNHO = "rascunho"
CONTRATO_ENVIADO = "enviado"
CONTRATO_ASSINADO = "assinado"
CONTRATO_CANCELADO = "cancelado"
CONTRATO_RENOVADO = "renovado"
CONTRATO_STATUSES = frozenset(
    {
        CONTRATO_RASCUNHO,
        CONTRATO_ENVIADO,
        CONTRATO_ASSINADO,
        CONTRATO_CANCELADO,
        CONTRATO_RENOVADO,
    }
)
CONTRATO_STATUS_ATIVOS = frozenset({CONTRATO_RASCUNHO, CONTRATO_ENVIADO, CONTRATO_ASSINADO})

FIDELIDADE_MESES_PADRAO = 12
MULTA_MAX_MENSALIDADES_PADRAO = 3


class ContratoTemplate(Base):
    __tablename__ = "comercial_contrato_templates"
    __table_args__ = (UniqueConstraint("nome", "versao", name="uq_comercial_contrato_template_nome_versao"),)

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False, index=True)
    versao = Column(Integer, nullable=False, default=1)
    conteudo_html = Column(Text, nullable=False)
    vigencia_inicio = Column(DateTime(timezone=True), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    contratos = relationship("Contrato", back_populates="template")


class Contrato(Base):
    __tablename__ = "comercial_contratos"

    id = Column(Integer, primary_key=True, index=True)
    negociacao_linha_cnpj_id = Column(
        Integer,
        ForeignKey("crm_negociacao_cnpj_linhas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id = Column(
        Integer, ForeignKey("comercial_contrato_templates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    gerado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(20), nullable=False, default=CONTRATO_RASCUNHO, index=True)
    valor_mensalidade = Column(Numeric(14, 2), nullable=False)
    snapshot_custo = Column(JSON, nullable=True)
    snapshot_itens = Column(JSON, nullable=False, default=lambda: [])
    snapshot_comercial = Column(JSON, nullable=False, default=lambda: {})
    data_inicio = Column(Date, nullable=False)
    data_fim_fidelidade = Column(Date, nullable=False)
    fidelidade_meses = Column(Integer, nullable=False, default=FIDELIDADE_MESES_PADRAO)
    setup_valor = Column(Numeric(14, 2), nullable=True)
    setup_isento = Column(Boolean, nullable=False, default=False)
    deslocamento_cliente = Column(Boolean, nullable=False, default=True)
    alimentacao_cliente = Column(Boolean, nullable=False, default=True)
    hospedagem_cliente = Column(Boolean, nullable=False, default=True)
    multa_max_mensalidades = Column(Integer, nullable=False, default=MULTA_MAX_MENSALIDADES_PADRAO)
    reajuste_percentual = Column(Numeric(7, 4), nullable=False, default=0)
    reajuste_rotulo = Column(String(80), nullable=False, default="")
    pdf_assinado_storage_key = Column(String(255), nullable=True)
    pdf_assinado_nome_original = Column(String(255), nullable=True)
    referencia_externa = Column(String(120), nullable=True)
    enviado_em = Column(DateTime(timezone=True), nullable=True)
    assinado_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    template = relationship("ContratoTemplate", back_populates="contratos")
    linha = relationship("CrmNegociacaoCnpjLinha")
    gerado_por = relationship("Atendente", foreign_keys=[gerado_por_id])
    pdfs = relationship(
        "ContratoPdf",
        back_populates="contrato",
        cascade="all, delete-orphan",
        order_by="ContratoPdf.id",
    )


class ContratoPdf(Base):
    """Versão de PDF gerada a partir do snapshot HTML (#352)."""

    __tablename__ = "comercial_contrato_pdfs"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(
        Integer, ForeignKey("comercial_contratos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gerado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False)
    conteudo_html_snapshot = Column(Text, nullable=False)
    conteudo_hash = Column(String(64), nullable=False)
    pdf_storage_key = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    contrato = relationship("Contrato", back_populates="pdfs")
    gerado_por = relationship("Atendente", foreign_keys=[gerado_por_id])


class ContratoPolitica(Base):
    """Singleton da instância: reajuste padrão dos contratos (#354)."""

    __tablename__ = "comercial_contrato_politica"

    id = Column(Integer, primary_key=True)
    reajuste_percentual = Column(Numeric(7, 4), nullable=False, default=0)
    reajuste_rotulo = Column(String(80), nullable=False, default="")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
