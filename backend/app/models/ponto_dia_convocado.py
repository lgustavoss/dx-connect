"""Dia convocado — trabalho excepcional fora da grade (#985)."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PontoDiaConvocado(Base):
    __tablename__ = "ponto_dias_convocados"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    data_ref = Column(Date, nullable=False, index=True)
    inicio = Column(String(5), nullable=False)
    fim = Column(String(5), nullable=False)
    tolerancia_minutos = Column(Integer, nullable=True)
    motivo = Column(String(1000), nullable=False)
    # ativa | cancelada
    estado = Column(String(20), nullable=False, default="ativa", server_default="ativa")
    criado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cancelado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    cancelado_em = Column(DateTime(timezone=True), nullable=True)

    atendente = relationship("Atendente", foreign_keys=[atendente_id])
    criado_por = relationship("Atendente", foreign_keys=[criado_por_id])
    cancelado_por = relationship("Atendente", foreign_keys=[cancelado_por_id])
