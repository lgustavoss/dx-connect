"""Solicitações de melhoria / problema (#799)."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SolicitacaoMelhoria(Base):
    __tablename__ = "solicitacoes_melhoria"

    id = Column(Integer, primary_key=True, index=True)
    # Instância / tenant — isolamento “organização” (#800 / #801).
    organizacao_id = Column(Integer, nullable=False, index=True)
    autor_atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    autor_nome = Column(String(255), nullable=True)
    tipo = Column(String(32), nullable=False, index=True)  # sugestao | problema
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=False)
    status = Column(String(40), nullable=False, default="aberta", server_default="aberta", index=True)
    motivo_nao_desenvolvimento = Column(Text, nullable=True)
    versao_contexto = Column(String(64), nullable=True)
    github_repo = Column(String(200), nullable=True)
    github_issue_number = Column(Integer, nullable=True)
    github_issue_url = Column(String(500), nullable=True)
    github_last_sync_at = Column(DateTime(timezone=True), nullable=True)
    github_last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    autor = relationship("Atendente", foreign_keys=[autor_atendente_id])
    historico = relationship(
        "SolicitacaoMelhoriaHistorico",
        back_populates="solicitacao",
        order_by="SolicitacaoMelhoriaHistorico.created_at",
        cascade="all, delete-orphan",
    )
    comentarios = relationship(
        "SolicitacaoMelhoriaComentario",
        back_populates="solicitacao",
        order_by="SolicitacaoMelhoriaComentario.created_at",
        cascade="all, delete-orphan",
    )
    anexos = relationship(
        "SolicitacaoMelhoriaAnexo",
        back_populates="solicitacao",
        order_by="SolicitacaoMelhoriaAnexo.created_at",
        cascade="all, delete-orphan",
    )


class SolicitacaoMelhoriaHistorico(Base):
    __tablename__ = "solicitacoes_melhoria_historico"

    id = Column(Integer, primary_key=True, index=True)
    solicitacao_id = Column(
        Integer, ForeignKey("solicitacoes_melhoria.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status_anterior = Column(String(40), nullable=True)
    status_novo = Column(String(40), nullable=False)
    motivo = Column(Text, nullable=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    mensagem_publica = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    solicitacao = relationship("SolicitacaoMelhoria", back_populates="historico")
    atendente = relationship("Atendente")


class SolicitacaoMelhoriaComentario(Base):
    __tablename__ = "solicitacoes_melhoria_comentarios"

    id = Column(Integer, primary_key=True, index=True)
    solicitacao_id = Column(
        Integer, ForeignKey("solicitacoes_melhoria.id", ondelete="CASCADE"), nullable=False, index=True
    )
    corpo = Column(Text, nullable=False)
    publico_cliente = Column(Boolean, nullable=False, default=True, server_default="true")
    origem = Column(String(32), nullable=False, default="manual", server_default="manual")
    origem_externa_id = Column(String(80), nullable=True, index=True)
    autor_atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    autor_nome = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    solicitacao = relationship("SolicitacaoMelhoria", back_populates="comentarios")
    autor = relationship("Atendente", foreign_keys=[autor_atendente_id])


class SolicitacaoMelhoriaAnexo(Base):
    __tablename__ = "solicitacoes_melhoria_anexos"

    id = Column(Integer, primary_key=True, index=True)
    solicitacao_id = Column(
        Integer, ForeignKey("solicitacoes_melhoria.id", ondelete="CASCADE"), nullable=True, index=True
    )
    autor_atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    papel = Column(String(16), nullable=False, default="anexo", server_default="anexo")
    nome_original = Column(String(255), nullable=False)
    content_type = Column(String(128), nullable=True)
    tamanho_bytes = Column(Integer, nullable=False)
    storage_key = Column(String(80), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    solicitacao = relationship("SolicitacaoMelhoria", back_populates="anexos")
    autor = relationship("Atendente", foreign_keys=[autor_atendente_id])

