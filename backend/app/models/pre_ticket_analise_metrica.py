"""Métricas por chamada de análise IA (#815)."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class PreTicketAnaliseMetrica(Base):
    __tablename__ = "pre_ticket_analise_metricas"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    sessao_id = Column(
        Integer,
        ForeignKey("pre_ticket_sessoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    sucesso = Column(Boolean, nullable=False, default=False, server_default="false")
    erro_tipo = Column(String(40), nullable=False, default="ok", server_default="ok")
    latencia_ms = Column(Integer, nullable=False, default=0)
    model = Column(String(80), nullable=True)
    prompt_version = Column(String(20), nullable=True)
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    custo_estimado_usd = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
