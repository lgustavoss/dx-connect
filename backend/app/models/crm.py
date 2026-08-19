"""CRM — leads, funil, negociação multi-CNPJ (#322 / #337–#339 / #344)."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

# Tipos de estágio do funil
FUNIL_TIPO_ABERTO = "aberto"
FUNIL_TIPO_GANHO = "ganho"
FUNIL_TIPO_PERDIDO = "perdido"
FUNIL_TIPOS = frozenset({FUNIL_TIPO_ABERTO, FUNIL_TIPO_GANHO, FUNIL_TIPO_PERDIDO})

# Atividades
ATIVIDADE_NOTA = "nota"
ATIVIDADE_LIGACAO = "ligacao"
ATIVIDADE_REUNIAO = "reuniao"
ATIVIDADE_MUDANCA_ESTAGIO = "mudanca_estagio"
ATIVIDADE_DOCUMENTO = "documento_anexado"
ATIVIDADE_TIPOS = frozenset(
    {ATIVIDADE_NOTA, ATIVIDADE_LIGACAO, ATIVIDADE_REUNIAO, ATIVIDADE_MUDANCA_ESTAGIO, ATIVIDADE_DOCUMENTO}
)

# Seed padrão do funil (#339)
FUNIL_SEED = (
    ("lead", "Lead", 10, FUNIL_TIPO_ABERTO),
    ("em_negociacao", "Em negociação", 20, FUNIL_TIPO_ABERTO),
    ("documentacao", "Documentação", 30, FUNIL_TIPO_ABERTO),
    ("proposta_enviada", "Proposta enviada", 40, FUNIL_TIPO_ABERTO),
    ("contrato_assinado", "Contrato assinado", 50, FUNIL_TIPO_GANHO),
    ("implantacao", "Implantação", 60, FUNIL_TIPO_GANHO),
    ("perdido", "Perdido", 90, FUNIL_TIPO_PERDIDO),
)

SLUG_DOCUMENTACAO = "documentacao"


class FunilEstagio(Base):
    __tablename__ = "crm_funil_estagios"
    __table_args__ = (UniqueConstraint("slug", name="uq_crm_funil_estagio_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    ordem = Column(Integer, nullable=False, default=0, index=True)
    tipo = Column(String(20), nullable=False, default=FUNIL_TIPO_ABERTO)
    ativo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CrmLead(Base):
    __tablename__ = "crm_leads"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    telefone = Column(String(40), nullable=True)
    email = Column(String(255), nullable=True)
    empresa_texto = Column(String(255), nullable=True)
    origem = Column(String(80), nullable=True)
    notas = Column(Text, nullable=True)
    responsavel_id = Column(Integer, ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False, index=True)
    estagio_id = Column(Integer, ForeignKey("crm_funil_estagios.id", ondelete="RESTRICT"), nullable=False, index=True)
    perdido_em = Column(DateTime(timezone=True), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    responsavel = relationship("Atendente", foreign_keys=[responsavel_id])
    estagio = relationship("FunilEstagio")
    negociacoes = relationship("CrmNegociacao", back_populates="lead", cascade="all, delete-orphan")


class CrmNegociacao(Base):
    __tablename__ = "crm_negociacoes"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False, index=True)
    responsavel_id = Column(Integer, ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False, index=True)
    estagio_id = Column(Integer, ForeignKey("crm_funil_estagios.id", ondelete="RESTRICT"), nullable=False, index=True)
    # True = negociação ativa do lead (no máximo uma por lead)
    ativa = Column(Boolean, nullable=False, default=True, index=True)
    titulo = Column(String(255), nullable=True)
    nome_base_webposto = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    lead = relationship("CrmLead", back_populates="negociacoes")
    responsavel = relationship("Atendente", foreign_keys=[responsavel_id])
    estagio = relationship("FunilEstagio")
    linhas = relationship(
        "CrmNegociacaoCnpjLinha",
        back_populates="negociacao",
        cascade="all, delete-orphan",
    )
    atividades = relationship(
        "CrmNegociacaoAtividade",
        back_populates="negociacao",
        cascade="all, delete-orphan",
    )


class CrmNegociacaoCnpjLinha(Base):
    __tablename__ = "crm_negociacao_cnpj_linhas"

    id = Column(Integer, primary_key=True, index=True)
    negociacao_id = Column(
        Integer, ForeignKey("crm_negociacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cnpj = Column(String(18), nullable=True, index=True)
    razao_social = Column(String(255), nullable=True)
    # Composição do pacote + overrides usados no motor de custos
    item_ids = Column(JSON, nullable=False, default=lambda: [])
    quantidade_pdvs = Column(Integer, nullable=False, default=1)
    desconto_posto_100k = Column(Boolean, nullable=False, default=False)
    tef_override = Column(JSON, nullable=True)
    valor_negociado = Column(Numeric(14, 2), nullable=False, default=0)
    snapshot_custo = Column(JSON, nullable=True)
    total_custo = Column(Numeric(14, 2), nullable=True)
    margem_calculada = Column(Numeric(14, 2), nullable=True)
    dados_fiscais = Column(JSON, nullable=True)
    # Preenchido pós-contrato (#324)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True)
    ordem = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    negociacao = relationship("CrmNegociacao", back_populates="linhas")


class CrmNegociacaoAtividade(Base):
    __tablename__ = "crm_negociacao_atividades"

    id = Column(Integer, primary_key=True, index=True)
    negociacao_id = Column(
        Integer, ForeignKey("crm_negociacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    autor_id = Column(Integer, ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False)
    tipo = Column(String(40), nullable=False, default=ATIVIDADE_NOTA)
    texto = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    negociacao = relationship("CrmNegociacao", back_populates="atividades")
    autor = relationship("Atendente", foreign_keys=[autor_id])
