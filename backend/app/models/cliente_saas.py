"""Cliente SaaS / licença DeskRudder (control-plane comercial) — #521."""

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base

STATUS_CLIENTE_SAAS = ("trial", "ativo", "suspenso", "churn")


class ClienteSaaS(Base):
    __tablename__ = "clientes_saas"
    __table_args__ = (UniqueConstraint("slug", name="uq_clientes_saas_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    slug = Column(String(80), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="trial")
    plano = Column(String(80), nullable=True)
    data_inicio = Column(Date, nullable=False)
    data_renovacao = Column(Date, nullable=True)
    instancia_url = Column(String(500), nullable=True)
    provisionamento_solicitado = Column(Boolean, nullable=False, default=False)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
