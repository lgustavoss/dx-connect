from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Tenant(Base):
    """Instância lógica do Connect (cliente SaaS ou instalação interna)."""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    inbound_addresses = relationship(
        "TenantInboundAddress",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
