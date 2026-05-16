from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TenantInboundAddress(Base):
    """
    Endereço de encaminhamento ``{local_part}@{INBOUND_EMAIL_DOMAIN}``.

    Convenção: ``{setor_slug}.t{tenant_id}`` (ex.: ``suporte.t1``, ``financeiro.t1``).
    """

    __tablename__ = "tenant_inbound_addresses"
    __table_args__ = (UniqueConstraint("local_part", name="uq_tenant_inbound_local_part"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    local_part = Column(String(128), nullable=False)
    label = Column(String(100), nullable=True)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="RESTRICT"), nullable=False)
    default_empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="inbound_addresses")
    setor = relationship("Setor")
    default_empresa = relationship("Empresa")
