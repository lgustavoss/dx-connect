from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class WhatsappSettings(Base):
    """Configuração singleton da integração Evolution (uma linha)."""

    __tablename__ = "whatsapp_settings"

    id = Column(Integer, primary_key=True, index=True)
    evolution_base_url = Column(String(500), nullable=True)
    evolution_instance_name = Column(String(120), nullable=True)
    evolution_api_key = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class WhatsappChat(Base):
    __tablename__ = "whatsapp_chats"

    id = Column(Integer, primary_key=True, index=True)
    protocolo = Column(String(32), unique=True, nullable=False, index=True)
    wa_id = Column(String(64), nullable=False, index=True)
    cliente_nome = Column(String(255), nullable=True)
    estado = Column(String(40), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    atendimento_inicio_at = Column(DateTime(timezone=True), nullable=True)
    encerramento_at = Column(DateTime(timezone=True), nullable=True)

    atendente = relationship("Atendente", backref="whatsapp_chats_atendidos")
    mensagens = relationship(
        "WhatsappMensagem",
        back_populates="chat",
        order_by="WhatsappMensagem.created_at",
    )
    vinculos_tickets = relationship("WhatsappChatTicket", back_populates="chat")


class WhatsappMensagem(Base):
    __tablename__ = "whatsapp_mensagens"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("whatsapp_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    direcao = Column(String(20), nullable=False)
    corpo = Column(Text, nullable=False)
    wa_message_id = Column(String(128), nullable=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("WhatsappChat", back_populates="mensagens")
    atendente = relationship("Atendente", backref="whatsapp_mensagens_enviadas")

    __table_args__ = (UniqueConstraint("wa_message_id", name="uq_whatsapp_mensagens_wa_message_id"),)


class WhatsappChatTicket(Base):
    __tablename__ = "whatsapp_chat_tickets"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("whatsapp_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("WhatsappChat", back_populates="vinculos_tickets")
    ticket = relationship("Ticket", backref="whatsapp_vinculos")
    atendente = relationship("Atendente", backref="whatsapp_vinculos_criados")

    __table_args__ = (UniqueConstraint("chat_id", "ticket_id", name="uq_whatsapp_chat_ticket_par"),)
