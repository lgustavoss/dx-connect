from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class WhatsappChatRead(Base):
    """Última vez que o atendente viu o chat WhatsApp (marca respostas como lidas)."""

    __tablename__ = "whatsapp_chat_reads"
    __table_args__ = (UniqueConstraint("atendente_id", "chat_id", name="uq_whatsapp_chat_reads_atendente_chat"),)

    id = Column(Integer, primary_key=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id = Column(Integer, ForeignKey("whatsapp_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    atendente = relationship("Atendente", backref="whatsapp_chat_reads")
    chat = relationship("WhatsappChat", backref="read_entries")

