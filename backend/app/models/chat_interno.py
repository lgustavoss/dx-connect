from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

TIPO_CONVERSA_DIRETA = "direta"
TIPO_CONVERSA_SETOR = "setor"
TIPO_CONVERSA_GRUPO = "grupo"

PAPEL_PARTICIPANTE_MEMBRO = "membro"
PAPEL_PARTICIPANTE_ADMIN = "admin"

TIPO_MENSAGEM_TEXTO = "texto"
TIPO_MENSAGEM_IMAGEM = "imagem"
TIPO_MENSAGEM_VIDEO = "video"
TIPO_MENSAGEM_AUDIO = "audio"
TIPO_MENSAGEM_DOCUMENTO = "documento"

TIPOS_MENSAGEM_MIDIA = frozenset(
    {TIPO_MENSAGEM_IMAGEM, TIPO_MENSAGEM_VIDEO, TIPO_MENSAGEM_AUDIO, TIPO_MENSAGEM_DOCUMENTO}
)


class ConversaInterna(Base):
    """Conversa de chat interno (direta 1:1 ou canal de setor)."""

    __tablename__ = "conversas_internas"
    __table_args__ = (
        CheckConstraint(
            "(tipo = 'setor' AND setor_id IS NOT NULL) OR (tipo IN ('direta', 'grupo') AND setor_id IS NULL)",
            name="ck_conversas_internas_tipo_setor",
        ),
        UniqueConstraint("tenant_id", "setor_id", name="uq_conversas_internas_tenant_setor"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False, index=True)
    titulo = Column(String(120), nullable=True)
    setor_id = Column(Integer, ForeignKey("setores.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setor = relationship("Setor", backref="conversas_internas")
    participantes = relationship(
        "ConversaInternaParticipante",
        back_populates="conversa",
        cascade="all, delete-orphan",
    )
    mensagens = relationship(
        "MensagemInterna",
        back_populates="conversa",
        cascade="all, delete-orphan",
        order_by="MensagemInterna.created_at",
    )
    leituras = relationship(
        "ConversaInternaLeitura",
        back_populates="conversa",
        cascade="all, delete-orphan",
    )


class ConversaInternaParticipante(Base):
    """Participantes de conversas diretas e grupos (canal setor usa vínculo lazy em atendente_setor)."""

    __tablename__ = "conversas_internas_participantes"
    __table_args__ = (
        UniqueConstraint("conversa_id", "atendente_id", name="uq_conversas_internas_participantes"),
    )

    conversa_id = Column(
        Integer,
        ForeignKey("conversas_internas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    atendente_id = Column(
        Integer,
        ForeignKey("atendentes.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    papel = Column(String(20), nullable=False, server_default=PAPEL_PARTICIPANTE_MEMBRO)
    silenciado_em = Column(DateTime(timezone=True), nullable=True)

    conversa = relationship("ConversaInterna", back_populates="participantes")
    atendente = relationship("Atendente", backref="conversas_internas_participantes")


class MensagemInterna(Base):
    __tablename__ = "mensagens_internas"

    id = Column(Integer, primary_key=True, index=True)
    conversa_id = Column(
        Integer,
        ForeignKey("conversas_internas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    corpo = Column(Text, nullable=False)
    tipo_midia = Column(String(24), nullable=False, server_default=TIPO_MENSAGEM_TEXTO, index=True)
    mimetype = Column(String(128), nullable=True)
    nome_arquivo = Column(String(500), nullable=True)
    storage_key = Column(String(255), nullable=True)
    tamanho_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    editada_em = Column(DateTime(timezone=True), nullable=True)
    apagada_em = Column(DateTime(timezone=True), nullable=True)
    reply_to_message_id = Column(
        Integer,
        ForeignKey("mensagens_internas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reply_preview = Column(String(500), nullable=True)
    reply_autor_nome = Column(String(200), nullable=True)
    # Ex.: [{"tipo":"user","atendente_id":12,"rotulo":"Maria"},{"tipo":"all"}]
    mencoes = Column(JSON, nullable=True)

    conversa = relationship("ConversaInterna", back_populates="mensagens")
    atendente = relationship("Atendente", backref="mensagens_internas")
    reply_to = relationship("MensagemInterna", remote_side=[id], foreign_keys=[reply_to_message_id])
    reacoes = relationship(
        "MensagemInternaReacao",
        back_populates="mensagem",
        cascade="all, delete-orphan",
    )


class MensagemInternaReacao(Base):
    __tablename__ = "mensagens_internas_reacoes"
    __table_args__ = (
        UniqueConstraint("mensagem_id", "atendente_id", name="uq_mensagens_internas_reacoes_mensagem_atendente"),
    )

    id = Column(Integer, primary_key=True, index=True)
    mensagem_id = Column(
        Integer,
        ForeignKey("mensagens_internas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atendente_id = Column(
        Integer,
        ForeignKey("atendentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    emoji = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mensagem = relationship("MensagemInterna", back_populates="reacoes")
    atendente = relationship("Atendente", backref="mensagens_internas_reacoes")


class ConversaInternaLeitura(Base):
    __tablename__ = "conversas_internas_leituras"
    __table_args__ = (
        UniqueConstraint("atendente_id", "conversa_id", name="uq_conversas_internas_leituras"),
    )

    id = Column(Integer, primary_key=True, index=True)
    conversa_id = Column(
        Integer,
        ForeignKey("conversas_internas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atendente_id = Column(
        Integer,
        ForeignKey("atendentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    historico_oculto_ate = Column(DateTime(timezone=True), nullable=True)

    conversa = relationship("ConversaInterna", back_populates="leituras")
    atendente = relationship("Atendente", backref="conversas_internas_leituras")


class MensagemInternaOculta(Base):
    """Mensagem oculta apenas para um atendente (apagar para mim)."""

    __tablename__ = "mensagens_internas_ocultas"
    __table_args__ = (
        UniqueConstraint("mensagem_id", "atendente_id", name="uq_mensagens_internas_ocultas"),
    )

    id = Column(Integer, primary_key=True, index=True)
    mensagem_id = Column(
        Integer,
        ForeignKey("mensagens_internas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    atendente_id = Column(
        Integer,
        ForeignKey("atendentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ocultada_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mensagem = relationship("MensagemInterna", backref="ocultacoes")
    atendente = relationship("Atendente", backref="mensagens_internas_ocultas")
