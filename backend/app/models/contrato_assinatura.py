"""Assinatura eletrônica do contrato — DocuSeal multiparte ou anexo externo (#1380 / #1429)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

PROVEDOR_DOCUSEAL = "docuseal"
PROVEDOR_EXTERNO = "externo"
PROVEDORES = frozenset({PROVEDOR_DOCUSEAL, PROVEDOR_EXTERNO})

PAPEL_CONTRATANTE = "contratante"
PAPEL_CONTRATADA = "contratada"
PAPEL_TESTEMUNHA = "testemunha"
PAPEIS = frozenset({PAPEL_CONTRATANTE, PAPEL_CONTRATADA, PAPEL_TESTEMUNHA})
# Papéis que o DocuSeal template deve ter (testemunhas: Testemunha 1..N).
DOCUSEAL_ROLE_FIXO = {
    PAPEL_CONTRATANTE: "Contratante",
    PAPEL_CONTRATADA: "Contratada",
}
MAX_TESTEMUNHAS = 4

STATUS_PENDENTE = "pendente"
STATUS_ENVIADO = "enviado"
STATUS_VISUALIZADO = "visualizado"
STATUS_PARCIAL = "parcial"
STATUS_ASSINADO = "assinado"
STATUS_RECUSADO = "recusado"
STATUS_EXPIRADO = "expirado"
STATUS_CANCELADO = "cancelado"
STATUS_ERRO = "erro"
STATUS_ASSINATURA = frozenset(
    {
        STATUS_PENDENTE,
        STATUS_ENVIADO,
        STATUS_VISUALIZADO,
        STATUS_PARCIAL,
        STATUS_ASSINADO,
        STATUS_RECUSADO,
        STATUS_EXPIRADO,
        STATUS_CANCELADO,
        STATUS_ERRO,
    }
)
# Envelope ainda «vivo» — só um por contrato (índice único parcial).
STATUS_ATIVOS = frozenset(
    {STATUS_PENDENTE, STATUS_ENVIADO, STATUS_VISUALIZADO, STATUS_PARCIAL}
)


class ContratoAssinatura(Base):
    __tablename__ = "contrato_assinaturas"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(
        Integer,
        ForeignKey("comercial_contratos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provedor = Column(String(20), nullable=False, default=PROVEDOR_DOCUSEAL, index=True)
    status = Column(String(20), nullable=False, default=STATUS_PENDENTE, index=True)
    submission_id = Column(String(80), nullable=True, index=True)
    # Legado / atalho: primeiro link (contratante). Fonte da verdade = partes.
    submitter_slug = Column(String(120), nullable=True)
    link_assinatura = Column(String(500), nullable=True)
    enviado_em = Column(DateTime(timezone=True), nullable=True)
    visualizado_em = Column(DateTime(timezone=True), nullable=True)
    assinado_em = Column(DateTime(timezone=True), nullable=True)
    expira_em = Column(DateTime(timezone=True), nullable=True)
    pdf_assinado_path = Column(String(255), nullable=True)
    audit_log_path = Column(String(255), nullable=True)
    selfie_path = Column(String(255), nullable=True)
    pdf_sha256 = Column(String(64), nullable=True)
    audit_sha256 = Column(String(64), nullable=True)
    criado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    ultimo_erro = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    contrato = relationship("Contrato", back_populates="assinaturas")
    criado_por = relationship("Atendente", foreign_keys=[criado_por_id])
    partes = relationship(
        "ContratoAssinaturaParte",
        back_populates="assinatura",
        cascade="all, delete-orphan",
        order_by="ContratoAssinaturaParte.ordem",
    )


class ContratoAssinaturaParte(Base):
    """Uma pessoa/papel no envelope (#1429)."""

    __tablename__ = "contrato_assinatura_partes"

    id = Column(Integer, primary_key=True, index=True)
    assinatura_id = Column(
        Integer,
        ForeignKey("contrato_assinaturas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    papel = Column(String(20), nullable=False, index=True)
    ordem = Column(Integer, nullable=False, default=0)
    nome = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    cpf = Column(String(11), nullable=True)  # 11 dígitos; obrigatório no fluxo DocuSeal
    telefone = Column(String(40), nullable=True)
    role_docuseal = Column(String(80), nullable=False)
    submitter_slug = Column(String(120), nullable=True)
    link_assinatura = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default=STATUS_ENVIADO)
    visualizado_em = Column(DateTime(timezone=True), nullable=True)
    assinado_em = Column(DateTime(timezone=True), nullable=True)
    ultimo_erro = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    assinatura = relationship("ContratoAssinatura", back_populates="partes")
