from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BusinessCalendar(Base):
    """Calendário comercial reutilizável (SLA, futuro: outros módulos)."""

    __tablename__ = "business_calendars"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="CASCADE"), nullable=True, index=True)
    nome = Column(String(120), nullable=False)
    horario_timezone = Column(String(64), nullable=False, default="America/Sao_Paulo", server_default="America/Sao_Paulo")
    horario_inicio = Column(String(5), nullable=True)
    horario_fim = Column(String(5), nullable=True)
    horario_semana_json = Column(Text, nullable=True)
    usar_feriados_nacionais = Column(Boolean, nullable=False, default=False, server_default="false")
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setor = relationship("Setor", foreign_keys=[setor_id])
    sla_policies = relationship("SlaPolicy", back_populates="business_calendar")
