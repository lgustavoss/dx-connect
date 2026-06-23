from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RoutingRule(Base):
    """Regra de roteamento configurável (primeira match ganha)."""

    __tablename__ = "routing_rules"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    nome = Column(String(200), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    ordem = Column(Integer, default=0, nullable=False)
    rede_id = Column(Integer, ForeignKey("redes.id", ondelete="CASCADE"), nullable=True, index=True)
    condicoes = Column(JSON, nullable=False)
    acoes = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rede = relationship("Rede", foreign_keys=[rede_id])
