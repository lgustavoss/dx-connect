from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TicketCsatInvite(Base):
    __tablename__ = "ticket_csat_invites"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket = relationship("Ticket", backref="csat_invites")
    atendente = relationship("Atendente", backref="ticket_csat_invites")


class TicketAvaliacao(Base):
    __tablename__ = "ticket_avaliacoes"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    nota = Column(Integer, nullable=False)
    comentario = Column(Text, nullable=True)
    respondida_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    invite_id = Column(Integer, ForeignKey("ticket_csat_invites.id", ondelete="SET NULL"), nullable=True)

    ticket = relationship("Ticket", backref="avaliacao", uselist=False)
    atendente = relationship("Atendente", backref="ticket_avaliacoes")
    invite = relationship("TicketCsatInvite", backref="avaliacao", uselist=False)

    __table_args__ = (UniqueConstraint("ticket_id", name="uq_ticket_avaliacoes_ticket_id"),)
