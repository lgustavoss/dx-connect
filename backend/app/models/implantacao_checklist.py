"""Checklist de implantação copiado para o ticket após contrato assinado (#325 / #358)."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

CHAVE_CADASTRAR_PDVS = "cadastrar_pdvs"

ITENS_PADRAO: tuple[tuple[str, str | None, bool, str | None], ...] = (
    ("Coleta de documentos", "Contrato assinado, dados fiscais e acessos necessários.", True, None),
    ("Cadastro na base WebPosto", "Criar ou confirmar a base e os logins operacionais.", True, None),
    ("Cadastrar PDVs", "Cadastrar os PDVs da empresa (cadastro operacional).", True, CHAVE_CADASTRAR_PDVS),
    ("Treinamento da equipe", "Treinamento de operação (caixa, retaguarda, helpdesk).", True, None),
    ("Validação operacional", "Conferir operação no dia a dia antes de encerrar a implantação.", False, None),
)


class ImplantacaoChecklistTemplate(Base):
    __tablename__ = "implantacao_checklist_templates"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    versao = Column(Integer, nullable=False, default=1)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="SET NULL"), nullable=True, index=True)
    ativo = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setor = relationship("Setor")
    itens = relationship(
        "ImplantacaoChecklistTemplateItem",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ImplantacaoChecklistTemplateItem.ordem",
    )


class ImplantacaoChecklistTemplateItem(Base):
    __tablename__ = "implantacao_checklist_template_itens"
    __table_args__ = (UniqueConstraint("template_id", "ordem", name="uq_implantacao_template_item_ordem"),)

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("implantacao_checklist_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=True)
    ordem = Column(Integer, nullable=False, default=1)
    obrigatorio = Column(Boolean, nullable=False, default=True)
    chave = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    template = relationship("ImplantacaoChecklistTemplate", back_populates="itens")


class TicketChecklistItem(Base):
    """Snapshot dos itens do template no ticket de implantação."""

    __tablename__ = "ticket_checklist_itens"
    __table_args__ = (UniqueConstraint("ticket_id", "ordem", name="uq_ticket_checklist_item_ordem"),)

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    template_item_id = Column(
        Integer,
        ForeignKey("implantacao_checklist_template_itens.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=True)
    ordem = Column(Integer, nullable=False, default=1)
    obrigatorio = Column(Boolean, nullable=False, default=True)
    chave = Column(String(64), nullable=True, index=True)
    concluido = Column(Boolean, nullable=False, default=False)
    concluido_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    concluido_em = Column(DateTime(timezone=True), nullable=True)
    observacao = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    ticket = relationship("Ticket", back_populates="checklist_itens")
    concluido_por = relationship("Atendente")
