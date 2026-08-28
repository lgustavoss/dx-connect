"""Coberturas / troca de plantão (#970)."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PontoCobertura(Base):
    __tablename__ = "ponto_coberturas"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    solicitante_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    cobertor_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    data_ref = Column(Date, nullable=False, index=True)
    motivo = Column(String(1000), nullable=True)
    # pendente_cobertor | pendente_admin | aprovada | rejeitada | cancelada
    estado = Column(String(32), nullable=False, default="pendente_cobertor", server_default="pendente_cobertor")
    # solicitacao | admin
    origem = Column(String(20), nullable=False, default="solicitacao", server_default="solicitacao")
    resposta_cobertor = Column(String(20), nullable=True)  # aceita | recusa
    respondido_em = Column(DateTime(timezone=True), nullable=True)
    decidido_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    decidido_em = Column(DateTime(timezone=True), nullable=True)
    decisao_motivo = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    solicitante = relationship("Atendente", foreign_keys=[solicitante_id])
    cobertor = relationship("Atendente", foreign_keys=[cobertor_id])
    decidido_por = relationship("Atendente", foreign_keys=[decidido_por_id])
