"""Sessão de pré-ticket com IA (#808)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PreTicketSessao(Base):
    __tablename__ = "pre_ticket_sessoes"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True, index=True)
    criado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False, index=True)
    contexto = Column(Text, nullable=False)
    problema = Column(Text, nullable=False)
    impacto = Column(Text, nullable=True)
    evidencias = Column(Text, nullable=True)
    urgencia = Column(String(40), nullable=True)
    # rascunho | analisado | aprovado | publicado | descartado
    estado = Column(String(30), nullable=False, default="rascunho", server_default="rascunho")
    prompt_version = Column(String(20), nullable=True)
    analise_json = Column(Text, nullable=True)
    rascunho_titulo = Column(String(255), nullable=True)
    rascunho_corpo = Column(Text, nullable=True)
    github_repo = Column(String(120), nullable=True)
    github_issue_number = Column(Integer, nullable=True)
    github_issue_url = Column(String(500), nullable=True)
    github_last_error = Column(Text, nullable=True)
    rascunho_publicado_titulo = Column(String(255), nullable=True)
    rascunho_publicado_corpo = Column(Text, nullable=True)
    aprovado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    aprovado_em = Column(DateTime(timezone=True), nullable=True)
    publicado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    publicado_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    historico = relationship(
        "PreTicketHistorico",
        back_populates="sessao",
        order_by="PreTicketHistorico.created_at",
        cascade="all, delete-orphan",
    )
