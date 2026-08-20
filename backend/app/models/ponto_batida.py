"""Batidas de ponto (entrada/saída) — épico #761."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PontoBatida(Base):
    __tablename__ = "ponto_batidas"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # entrada | saida
    registrado_em = Column(DateTime(timezone=True), nullable=False, index=True)
    origem = Column(String(20), nullable=True)  # web | mobile
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    atendente = relationship("Atendente", back_populates="ponto_batidas")
