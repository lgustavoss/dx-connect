from sqlalchemy import Column, Integer, String, Boolean, DateTime, SmallInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class StatusTicket(Base):
    """Status do ticket (cadastrável): Aberto, Em atendimento, Resolvido, Fechado, etc."""

    __tablename__ = "status_ticket"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    ordem = Column(SmallInteger, default=0)  # para ordenação na UI
    ativo = Column(Boolean, default=True)
    pausa_sla = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tickets = relationship("Ticket", back_populates="status")
