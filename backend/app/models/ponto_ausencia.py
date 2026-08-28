"""Ausências programadas de ponto (#976)."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PontoAusencia(Base):
    __tablename__ = "ponto_ausencias"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    # ferias | folga_programada
    tipo = Column(String(32), nullable=False)
    desde = Column(Date, nullable=False, index=True)
    ate = Column(Date, nullable=False, index=True)
    motivo = Column(String(1000), nullable=True)
    # pendente | aprovada | rejeitada
    estado = Column(String(20), nullable=False, default="pendente", server_default="pendente")
    # solicitacao | admin
    origem = Column(String(20), nullable=False, default="solicitacao", server_default="solicitacao")
    decidido_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    decidido_em = Column(DateTime(timezone=True), nullable=True)
    decisao_motivo = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    atendente = relationship("Atendente", foreign_keys=[atendente_id])
    decidido_por = relationship("Atendente", foreign_keys=[decidido_por_id])
