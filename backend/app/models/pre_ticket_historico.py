"""Histórico interno de ações no pré-ticket (#814)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PreTicketHistorico(Base):
    __tablename__ = "pre_ticket_historico"

    id = Column(Integer, primary_key=True)
    sessao_id = Column(
        Integer,
        ForeignKey("pre_ticket_sessoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    acao = Column(String(40), nullable=False)
    detalhe = Column(Text, nullable=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    atendente_nome = Column(String(255), nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sessao = relationship("PreTicketSessao", back_populates="historico")
    atendente = relationship("Atendente")
