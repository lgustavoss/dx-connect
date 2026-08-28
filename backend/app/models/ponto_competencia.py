"""Competência mensal e ciência do espelho (#978 / #979)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PontoCompetencia(Base):
    __tablename__ = "ponto_competencias"
    __table_args__ = (
        UniqueConstraint("tenant_id", "ano", "mes", name="uq_ponto_competencias_tenant_ano_mes"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    fechada = Column(Boolean, nullable=False, default=False, server_default="false")
    fechado_em = Column(DateTime(timezone=True), nullable=True)
    fechado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    reaberto_em = Column(DateTime(timezone=True), nullable=True)
    reaberto_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    reabrir_motivo = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fechado_por = relationship("Atendente", foreign_keys=[fechado_por_id])
    reaberto_por = relationship("Atendente", foreign_keys=[reaberto_por_id])


class PontoEspelhoCiencia(Base):
    __tablename__ = "ponto_espelho_ciencias"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "atendente_id",
            "ano",
            "mes",
            name="uq_ponto_espelho_ciencias_atendente_ano_mes",
        ),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    confirmado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # Se ajuste pós-ciência invalidar, fica False e confirmado_em permanece histórico no audit
    ativa = Column(Boolean, nullable=False, default=True, server_default="true")
    invalidada_em = Column(DateTime(timezone=True), nullable=True)
    invalidada_motivo = Column(String(500), nullable=True)

    atendente = relationship("Atendente", foreign_keys=[atendente_id])
