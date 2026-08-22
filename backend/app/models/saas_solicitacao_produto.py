"""Cópia das solicitações de produto das instâncias — fila do control-plane (#855)."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SaasSolicitacaoProduto(Base):
    __tablename__ = "saas_solicitacoes_produto"
    __table_args__ = (
        UniqueConstraint(
            "instance_slug",
            "origem_solicitacao_id",
            name="uq_saas_solicitacoes_produto_origem",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    cliente_saas_id = Column(
        Integer, ForeignKey("clientes_saas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    instance_slug = Column(String(80), nullable=False, index=True)
    origem_solicitacao_id = Column(Integer, nullable=False)
    tipo = Column(String(32), nullable=False, index=True)
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=False)
    status = Column(String(40), nullable=False, default="aberta", server_default="aberta", index=True)
    versao_contexto = Column(String(64), nullable=True)
    autor_nome = Column(String(255), nullable=True)
    created_at_origem = Column(DateTime(timezone=True), nullable=True)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    motivo_nao_desenvolvimento = Column(Text, nullable=True)
    triagem_atualizada_em = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    github_repo = Column(String(200), nullable=True)
    github_issue_number = Column(Integer, nullable=True)
    github_issue_url = Column(String(500), nullable=True)
    protocolo = Column(String(32), nullable=True, unique=True, index=True)
    grupo_id = Column(Integer, nullable=True, index=True)

    cliente = relationship("ClienteSaaS", foreign_keys=[cliente_saas_id])
    comentarios = relationship(
        "SaasSolicitacaoProdutoComentario",
        back_populates="solicitacao",
        order_by="SaasSolicitacaoProdutoComentario.created_at",
        cascade="all, delete-orphan",
    )
    anexos = relationship(
        "SaasSolicitacaoProdutoAnexo",
        back_populates="solicitacao",
        order_by="SaasSolicitacaoProdutoAnexo.created_at",
        cascade="all, delete-orphan",
    )


class SaasSolicitacaoProdutoComentario(Base):
    __tablename__ = "saas_solicitacoes_produto_comentarios"

    id = Column(Integer, primary_key=True, index=True)
    solicitacao_id = Column(
        Integer,
        ForeignKey("saas_solicitacoes_produto.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    corpo = Column(Text, nullable=False)
    publico_cliente = Column(Boolean, nullable=False, default=True, server_default="true")
    autor_atendente_id = Column(Integer, nullable=True)
    autor_nome = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    solicitacao = relationship("SaasSolicitacaoProduto", back_populates="comentarios")


class SaasSolicitacaoProdutoAnexo(Base):
    """Cópia da mídia da instância no control-plane (mesmo storage_key do markdown)."""

    __tablename__ = "saas_solicitacoes_produto_anexos"
    __table_args__ = (
        UniqueConstraint(
            "solicitacao_id",
            "storage_key",
            name="uq_saas_solicitacoes_produto_anexos_key",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    solicitacao_id = Column(
        Integer,
        ForeignKey("saas_solicitacoes_produto.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    papel = Column(String(16), nullable=False, default="anexo", server_default="anexo")
    nome_original = Column(String(255), nullable=False)
    content_type = Column(String(128), nullable=True)
    tamanho_bytes = Column(Integer, nullable=False)
    storage_key = Column(String(80), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    solicitacao = relationship("SaasSolicitacaoProduto", back_populates="anexos")
