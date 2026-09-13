"""Alertas operacionais por instância no control-plane (#1036 / #1037)."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

SEVERIDADES_ALERTA_OPS = ("amarelo", "vermelho")
ESTADOS_ALERTA_OPS = ("ativo", "mitigado", "resolvido")
MODULOS_ALERTA_OPS = ("api", "stack", "sync", "auth", "realtime", "jobs")


class SaasAlertaOps(Base):
    __tablename__ = "saas_alertas_ops"
    __table_args__ = (
        UniqueConstraint(
            "cliente_saas_id",
            "codigo_sinal",
            "ciclo_id",
            name="uq_saas_alertas_ops_cliente_sinal_ciclo",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    cliente_saas_id = Column(
        Integer,
        ForeignKey("clientes_saas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo_sinal = Column(String(64), nullable=False, index=True)
    modulo = Column(String(32), nullable=False, index=True)
    severidade = Column(String(16), nullable=False, index=True)
    estado = Column(String(16), nullable=False, default="ativo", index=True)
    # Incrementa a cada novo ciclo aberto após resolução (permite reabrir o mesmo sinal).
    ciclo_id = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    mitigated_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    evidencia = Column(JSON, nullable=True)
    titulo = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    cliente = relationship("ClienteSaaS", backref="alertas_ops")
    eventos = relationship(
        "SaasAlertaOpsEvento",
        back_populates="alerta",
        cascade="all, delete-orphan",
        order_by="SaasAlertaOpsEvento.created_at",
    )


class SaasAlertaOpsEvento(Base):
    __tablename__ = "saas_alertas_ops_eventos"

    id = Column(Integer, primary_key=True, index=True)
    alerta_id = Column(
        Integer,
        ForeignKey("saas_alertas_ops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = Column(String(32), nullable=False)
    mensagem = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    alerta = relationship("SaasAlertaOps", back_populates="eventos")
