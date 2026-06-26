from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SlaPolicy(Base):
    """Meta de SLA por setor e prioridade (prioridade nula = default do setor)."""

    __tablename__ = "sla_policies"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "setor_id",
            "prioridade",
            "natureza_id",
            name="uq_sla_policies_setor_prioridade_natureza",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="CASCADE"), nullable=False, index=True)
    prioridade = Column(String(20), nullable=True, index=True)
    natureza_id = Column(Integer, ForeignKey("ticket_naturezas.id", ondelete="SET NULL"), nullable=True, index=True)
    business_calendar_id = Column(Integer, ForeignKey("business_calendars.id", ondelete="SET NULL"), nullable=True)
    meta_primeira_resposta_min = Column(Integer, nullable=True)
    meta_resolucao_min = Column(Integer, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setor = relationship("Setor", foreign_keys=[setor_id])
    natureza = relationship("TicketNatureza")
    business_calendar = relationship("BusinessCalendar", back_populates="sla_policies")
