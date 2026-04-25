from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class TicketAnexo(Base):
    __tablename__ = "ticket_anexos"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    # Opcional: anexo associado a uma mensagem (publico/interno/abertura)
    mensagem_id = Column(Integer, ForeignKey("ticket_mensagens.id", ondelete="SET NULL"), nullable=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)

    visibilidade = Column(String(20), nullable=False, default="publico")  # publico | interno
    nome_original = Column(String(255), nullable=False)
    content_type = Column(String(128), nullable=True)
    tamanho_bytes = Column(Integer, nullable=False)
    storage_key = Column(String(500), nullable=False)  # basename no disco/object storage

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", backref="anexos")
    mensagem = relationship("TicketMensagem", backref="anexos")
    atendente = relationship("Atendente", backref="ticket_anexos_enviados")

