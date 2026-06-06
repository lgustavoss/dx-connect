"""Vínculos laterais entre tickets (#115): duplicado_de, relacionado_a."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

TIPO_DUPLICADO_DE = "duplicado_de"
TIPO_RELACIONADO_A = "relacionado_a"
TIPOS_VINCULO = frozenset({TIPO_DUPLICADO_DE, TIPO_RELACIONADO_A})


class TicketVinculo(Base):
    __tablename__ = "ticket_vinculos"
    __table_args__ = (
        UniqueConstraint("ticket_id", "related_ticket_id", "tipo", name="uq_ticket_vinculos_par_tipo"),
        CheckConstraint("ticket_id <> related_ticket_id", name="ck_ticket_vinculos_distintos"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    related_ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(32), nullable=False)
    created_by_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", foreign_keys=[ticket_id], back_populates="vinculos_saida")
    related_ticket = relationship("Ticket", foreign_keys=[related_ticket_id], back_populates="vinculos_entrada")
    created_by = relationship("Atendente")
