"""Solicitações de inclusão/correção de batida (#1135)."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PontoSolicitacaoAjuste(Base):
    __tablename__ = "ponto_solicitacoes_ajuste"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # inclusao | correcao | abono
    estado = Column(String(20), nullable=False, default="pendente")  # pendente | aprovada | rejeitada
    motivo = Column(String(1000), nullable=False)
    data_ref = Column(Date, nullable=False, index=True)
    tipo_batida = Column(String(20), nullable=True)  # entrada | saida (null em abono)
    horario_solicitado = Column(DateTime(timezone=True), nullable=True)  # null em abono
    horario_anterior = Column(DateTime(timezone=True), nullable=True)  # snapshot na correção
    batida_id = Column(Integer, ForeignKey("ponto_batidas.id", ondelete="SET NULL"), nullable=True, index=True)
    anexo_storage_key = Column(String(255), nullable=True)
    anexo_nome = Column(String(255), nullable=True)
    anexo_content_type = Column(String(128), nullable=True)
    anexo_tamanho_bytes = Column(Integer, nullable=True)
    decisao_motivo = Column(String(1000), nullable=True)
    decidido_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    decidido_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    atendente = relationship("Atendente", foreign_keys=[atendente_id])
    decidido_por = relationship("Atendente", foreign_keys=[decidido_por_id])
    batida = relationship("PontoBatida", foreign_keys=[batida_id])
