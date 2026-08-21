"""Fatura interna mensal — conferência do financeiro antes de boleto/NFS-e (#326)."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

FATURA_AGUARDANDO = "aguardando_aprovacao"
FATURA_APROVADA = "aprovada"
FATURA_REJEITADA = "rejeitada"
FATURA_CANCELADA = "cancelada"
FATURA_STATUSES = frozenset({FATURA_AGUARDANDO, FATURA_APROVADA, FATURA_REJEITADA, FATURA_CANCELADA})

VENCIMENTO_DIA_PADRAO = 10


class Fatura(Base):
    __tablename__ = "faturamento_faturas"
    __table_args__ = (UniqueConstraint("contrato_id", "competencia", name="uq_faturamento_fatura_contrato_competencia"),)

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("comercial_contratos.id", ondelete="RESTRICT"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True, index=True)
    competencia = Column(String(7), nullable=False, index=True)  # YYYY-MM
    valor = Column(Numeric(14, 2), nullable=False)
    vencimento = Column(Date, nullable=False)
    emite_nfse = Column(Boolean, nullable=False, default=True)
    status = Column(String(32), nullable=False, default=FATURA_AGUARDANDO, index=True)
    rejeicao_motivo = Column(Text, nullable=True)
    gerada_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    aprovada_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    aprovada_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    contrato = relationship("Contrato")
    empresa = relationship("Empresa")
    aprovada_por = relationship("Atendente", foreign_keys=[aprovada_por_id])
