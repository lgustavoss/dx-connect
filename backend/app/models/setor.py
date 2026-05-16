from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tickets = relationship("Ticket", back_populates="setor")
    atendentes = relationship(
        "Atendente",
        secondary="atendente_setor",
        back_populates="setores",
    )
