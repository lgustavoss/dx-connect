"""Chat ao vivo do portal público /kb (#468)."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PortalChat(Base):
    __tablename__ = "portal_chats"
    __table_args__ = (
        UniqueConstraint("visitor_token_hash", name="uq_portal_chats_visitor_token_hash"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    protocolo = Column(String(32), unique=True, nullable=False, index=True)
    visitor_token_hash = Column(String(64), nullable=False)
    visitante_nome = Column(String(120), nullable=False)
    visitante_email = Column(String(255), nullable=True)
    estado = Column(String(40), nullable=False, index=True)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="SET NULL"), nullable=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    atendimento_inicio_at = Column(DateTime(timezone=True), nullable=True)
    encerramento_at = Column(DateTime(timezone=True), nullable=True)
    avaliacao_nota = Column(Integer, nullable=True)
    avaliacao_respondida_at = Column(DateTime(timezone=True), nullable=True)
    avaliacao_solicitada = Column(Boolean, nullable=False, default=False)

    setor = relationship("Setor")
    atendente = relationship("Atendente")
    mensagens = relationship(
        "PortalMensagem",
        back_populates="chat",
        order_by="PortalMensagem.id.asc()",
    )
    demandas = relationship(
        "PortalChatDemanda",
        back_populates="chat",
        order_by="PortalChatDemanda.created_at.asc()",
    )
    reads = relationship("PortalChatRead", back_populates="chat", cascade="all, delete-orphan")


class PortalMensagem(Base):
    __tablename__ = "portal_mensagens"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("portal_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    direcao = Column(String(16), nullable=False)
    corpo = Column(Text, nullable=False)
    tipo_midia = Column(String(24), nullable=False, default="texto")
    mimetype = Column(String(128), nullable=True)
    midia_nome_arquivo = Column(String(255), nullable=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    evento_sistema = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("PortalChat", back_populates="mensagens")
    atendente = relationship("Atendente")


class PortalChatRead(Base):
    __tablename__ = "portal_chat_reads"
    __table_args__ = (
        UniqueConstraint("chat_id", "atendente_id", name="uq_portal_chat_reads_chat_atendente"),
    )

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("portal_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)

    chat = relationship("PortalChat", back_populates="reads")
    atendente = relationship("Atendente")
