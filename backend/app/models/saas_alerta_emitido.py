"""Dedup de alertas de renovação SaaS (#528)."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SaasAlertaEmitido(Base):
    __tablename__ = "saas_alerta_emitidos"
    __table_args__ = (
        UniqueConstraint(
            "cliente_saas_id",
            "evento",
            "referencia_data",
            name="uq_saas_alerta_emitidos_cliente_evento_ref",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    cliente_saas_id = Column(
        Integer,
        ForeignKey("clientes_saas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evento = Column(String(40), nullable=False)
    referencia_data = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cliente = relationship("ClienteSaaS", backref="alertas_emitidos")
