from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TicketNatureza(Base):
    __tablename__ = "ticket_naturezas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    ordem = Column(Integer, default=0, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    motivos = relationship("TicketMotivo", back_populates="natureza", order_by="TicketMotivo.ordem")


class TicketMotivo(Base):
    __tablename__ = "ticket_motivos"
    __table_args__ = (UniqueConstraint("natureza_id", "slug", name="uq_ticket_motivo_natureza_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    natureza_id = Column(Integer, ForeignKey("ticket_naturezas.id", ondelete="RESTRICT"), nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    slug = Column(String(50), nullable=False)
    ordem = Column(Integer, default=0, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    natureza = relationship("TicketNatureza", back_populates="motivos")
    tickets = relationship("Ticket", back_populates="motivo")
