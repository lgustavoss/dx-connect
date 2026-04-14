from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TicketRead(Base):
    """Última vez que o atendente abriu/viu o ticket (marca mensagens como lidas)."""

    __tablename__ = "ticket_reads"
    __table_args__ = (UniqueConstraint("atendente_id", "ticket_id", name="uq_ticket_reads_atendente_ticket"),)

    id = Column(Integer, primary_key=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    atendente = relationship("Atendente", backref="ticket_reads")
    ticket = relationship("Ticket", backref="ticket_read_entries")
