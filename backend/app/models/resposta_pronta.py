from sqlalchemy import Column, ForeignKey, Integer, SmallInteger, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RespostaPronta(Base):
    """Macro de texto reutilizável no ticket (global ou por setor)."""

    __tablename__ = "respostas_prontas"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="SET NULL"), nullable=True, index=True)
    titulo = Column(String(200), nullable=False)
    corpo = Column(Text, nullable=False)
    ordem = Column(SmallInteger, default=0, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setor = relationship("Setor", foreign_keys=[setor_id])
