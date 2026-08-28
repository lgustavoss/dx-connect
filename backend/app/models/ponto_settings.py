"""Settings e feriados custom do ponto (#779 / #782)."""

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class PontoSettings(Base):
    __tablename__ = "ponto_settings"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, unique=True)
    usar_feriados_nacionais = Column(Boolean, nullable=False, default=True, server_default="true")
    fecho_automatico_ativo = Column(Boolean, nullable=False, default=False, server_default="false")
    fecho_apos_horas = Column(Integer, nullable=False, default=14, server_default="14")
    # Margem após saída prevista do dia (#961); fecho = min(N horas, saída+margem).
    fecho_margem_pos_saida_minutos = Column(Integer, nullable=False, default=30, server_default="30")
    jornada_diaria_minutos = Column(Integer, nullable=False, default=480, server_default="480")
    # 0 = desligado (#973)
    pausa_minima_minutos = Column(Integer, nullable=False, default=0, server_default="0")
    # NULL = sem teto mensal global (#974)
    he_teto_mensal_minutos = Column(Integer, nullable=True)
    # opcional | recomendada | obrigatoria (#844)
    politica_geolocalizacao = Column(String(20), nullable=False, default="opcional", server_default="opcional")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PontoLocal(Base):
    __tablename__ = "ponto_locais"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    # NULL = legado sem dono (#984); não entra no geofence até reatribuir.
    atendente_id = Column(
        Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    nome = Column(String(255), nullable=False)
    endereco = Column(String(512), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    raio_metros = Column(Integer, nullable=False, default=200, server_default="200")
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")


class PontoFeriado(Base):
    __tablename__ = "ponto_feriados"
    __table_args__ = (UniqueConstraint("tenant_id", "data", name="uq_ponto_feriados_tenant_data"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    data = Column(Date, nullable=False)
    nome = Column(String(255), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
