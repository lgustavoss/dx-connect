from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SlaAlertaEmitido(Base):
    """Registro de alerta SLA já disparado (debounce por ticket/meta/evento)."""

    __tablename__ = "sla_alerta_emitidos"
    __table_args__ = (
        UniqueConstraint("ticket_id", "meta", "evento", name="uq_sla_alerta_emitidos_ticket_meta_evento"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    meta = Column(String(30), nullable=False)
    evento = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket = relationship("Ticket", backref="sla_alertas_emitidos")
