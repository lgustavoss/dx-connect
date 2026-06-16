from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Setor(Base):
    """Setor interno para direcionamento de tickets (Suporte, Financeiro, etc.)."""

    __tablename__ = "setores"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_setores_tenant_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False, index=True)
    ativo = Column(Boolean, default=True)
    distribuicao_modo = Column(String(30), nullable=False, default="manual", server_default="manual")
    distribuicao_timeout_minutos = Column(Integer, nullable=False, default=30, server_default="30")
    distribuicao_estrategia = Column(String(30), nullable=False, default="round_robin", server_default="round_robin")
    distribuicao_atendentes_elegiveis = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tickets = relationship("Ticket", back_populates="setor")
    atendentes = relationship(
        "Atendente",
        secondary="atendente_setor",
        back_populates="setores",
    )
