"""Hora extra para atendimento WhatsApp após jornada (#965)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PontoHoraExtra(Base):
    __tablename__ = "ponto_hora_extra"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    # pendente | aprovada | rejeitada | expirada
    estado = Column(String(20), nullable=False, default="pendente", server_default="pendente")
    motivo = Column(String(1000), nullable=True)
    # resto_do_dia | ate_horario | duracao (só quando aprovada)
    modo = Column(String(20), nullable=True)
    ate_em = Column(DateTime(timezone=True), nullable=True)
    # solicitacao | admin (#966)
    origem = Column(String(20), nullable=False, default="solicitacao", server_default="solicitacao")
    decidido_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    decidido_em = Column(DateTime(timezone=True), nullable=True)
    decisao_motivo = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    atendente = relationship("Atendente", foreign_keys=[atendente_id])
    decidido_por = relationship("Atendente", foreign_keys=[decidido_por_id])
