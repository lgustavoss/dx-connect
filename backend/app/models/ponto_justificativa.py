"""Justificativas de ponto (#774)."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PontoJustificativa(Base):
    __tablename__ = "ponto_justificativas"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    data_ref = Column(Date, nullable=False, index=True)
    tipo = Column(String(32), nullable=False)  # falta | esquecimento | folga_com_ponto | outro
    motivo = Column(String(1000), nullable=False)
    estado = Column(String(20), nullable=False, default="pendente")  # pendente | aprovada | rejeitada
    decisao_motivo = Column(String(1000), nullable=True)
    decidido_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    decidido_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    atendente = relationship("Atendente", foreign_keys=[atendente_id])
    decidido_por = relationship("Atendente", foreign_keys=[decidido_por_id])
