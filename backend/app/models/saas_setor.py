"""Setores (cargos) da equipe DeskRudder no control-plane — Admin, Dev, Comercial, etc."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

saas_ops_setor = Table(
    "saas_ops_setor",
    Base.metadata,
    Column("atendente_id", Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), primary_key=True),
    Column("saas_setor_id", Integer, ForeignKey("saas_setores.id", ondelete="CASCADE"), primary_key=True),
)


class SaasSetor(Base):
    """Setor/cargo da equipe ops (não confundir com setor de tickets do helpdesk)."""

    __tablename__ = "saas_setores"
    __table_args__ = (UniqueConstraint("tenant_id", "nome", name="uq_saas_setores_tenant_nome"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    ops = relationship(
        "Atendente",
        secondary=saas_ops_setor,
        back_populates="saas_setores",
    )
