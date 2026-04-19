from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_conversations"

    id = Column(Integer, primary_key=True, index=True)
    wa_id = Column(String(32), nullable=False, unique=True, index=True)
    profile_name = Column(String(255), nullable=True)
    phone_number = Column(String(32), nullable=False)
    status = Column(String(30), nullable=False, server_default="open")
    ai_enabled = Column(Boolean, nullable=False, server_default="false")
    ai_mode = Column(String(20), nullable=False, server_default="assist")
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    linked_ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    linked_ticket = relationship("Ticket", back_populates="whatsapp_conversations")
    messages = relationship(
        "WhatsAppMessage",
        back_populates="conversation",
        order_by="WhatsAppMessage.created_at",
        cascade="all, delete-orphan",
    )


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    wa_message_id = Column(String(255), nullable=True, unique=True, index=True)
    direction = Column(String(20), nullable=False)  # inbound | outbound | system
    sender_phone = Column(String(32), nullable=True)
    recipient_phone = Column(String(32), nullable=True)
    message_type = Column(String(30), nullable=False, server_default="text")
    body = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)
    mime_type = Column(String(100), nullable=True)
    filename = Column(String(255), nullable=True)
    status = Column(String(30), nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    conversation = relationship("WhatsAppConversation", back_populates="messages")
    ticket = relationship("Ticket", back_populates="whatsapp_messages")
