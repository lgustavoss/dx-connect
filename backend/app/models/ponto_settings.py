"""Settings e feriados custom do ponto (#779 / #782)."""

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class PontoSettings(Base):
    __tablename__ = "ponto_settings"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, unique=True)
    usar_feriados_nacionais = Column(Boolean, nullable=False, default=True, server_default="true")
    fecho_automatico_ativo = Column(Boolean, nullable=False, default=False, server_default="false")
    fecho_apos_horas = Column(Integer, nullable=False, default=14, server_default="14")
    # Meta de horas do dia para cores do calendário (#842); default 8h.
    jornada_diaria_minutos = Column(Integer, nullable=False, default=480, server_default="480")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PontoFeriado(Base):
    __tablename__ = "ponto_feriados"
    __table_args__ = (UniqueConstraint("tenant_id", "data", name="uq_ponto_feriados_tenant_data"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    data = Column(Date, nullable=False)
    nome = Column(String(255), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
