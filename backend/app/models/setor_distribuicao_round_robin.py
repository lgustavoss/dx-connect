from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func

from app.database import Base


class SetorDistribuicaoRoundRobin(Base):
    """Estado persistido do round-robin por setor."""

    __tablename__ = "setor_distribuicao_round_robin"

    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="CASCADE"), primary_key=True)
    last_atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
