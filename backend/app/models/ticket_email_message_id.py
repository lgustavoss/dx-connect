from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TicketEmailMessageId(Base):
    """
    Qualquer Message-ID (RFC 5322) já associado a um ticket — inbound ou outbound (#165).
    Usado para resolver respostas (In-Reply-To / References).
    """

    __tablename__ = "ticket_email_message_id"

    id = Column(Integer, primary_key=True, index=True)
    message_id_normalized = Column(String(998), nullable=False, unique=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    # inbound | outbound (opcional; útil para auditoria)
    source = Column(String(20), nullable=True)

    ticket = relationship("Ticket")
