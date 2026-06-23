"""Demandas registradas por sessão de chat WhatsApp (#423)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

DESFECHOS_DEMANDA = frozenset({"resolvido_sessao", "escalado_ticket"})


class WhatsappChatDemanda(Base):
    __tablename__ = "whatsapp_chat_demandas"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("whatsapp_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    natureza_id = Column(Integer, ForeignKey("ticket_naturezas.id", ondelete="RESTRICT"), nullable=False, index=True)
    motivo_id = Column(Integer, ForeignKey("ticket_motivos.id", ondelete="SET NULL"), nullable=True, index=True)
    desfecho = Column(String(24), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True)
    descricao_curta = Column(String(500), nullable=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chat = relationship("WhatsappChat", back_populates="demandas")
    natureza = relationship("TicketNatureza")
    motivo = relationship("TicketMotivo")
    ticket = relationship("Ticket")
    atendente = relationship("Atendente")
