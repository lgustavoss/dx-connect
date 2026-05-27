from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class EmailInboundReceived(Base):
    """
    Registo de mensagens já processadas via webhook (idempotência por Message-ID).
    """

    __tablename__ = "email_inbound_received"

    id = Column(Integer, primary_key=True, index=True)
    message_id_normalized = Column(String(998), nullable=False, unique=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    from_address = Column(String(512), nullable=True)
    subject = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket")
