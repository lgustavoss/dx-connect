"""Fatura interna mensal — conferência do financeiro antes de boleto/NFS-e (#326)."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

FATURA_AGUARDANDO = "aguardando_aprovacao"
FATURA_APROVADA = "aprovada"
FATURA_REJEITADA = "rejeitada"
FATURA_CANCELADA = "cancelada"
FATURA_STATUSES = frozenset({FATURA_AGUARDANDO, FATURA_APROVADA, FATURA_REJEITADA, FATURA_CANCELADA})

VENCIMENTO_DIA_PADRAO = 10
DIA_VENCIMENTO_MIN = 1
DIA_VENCIMENTO_MAX = 28

# Gatilho de início da mensalidade (#1339). A instância escolhe um; o contrato pode
# sobrescrever apenas a data de início (negociação).
GATILHO_DATA_INICIO = "data_inicio"
GATILHO_DIAS_APOS_ASSINATURA = "dias_apos_assinatura"
GATILHO_DIAS_APOS_MARCO = "dias_apos_marco"
GATILHO_TICKET_IMPLANTACAO_FECHADO = "ticket_implantacao_fechado"
GATILHO_OPCOES = (
    GATILHO_DATA_INICIO,
    GATILHO_DIAS_APOS_ASSINATURA,
    GATILHO_DIAS_APOS_MARCO,
    GATILHO_TICKET_IMPLANTACAO_FECHADO,
)

ANEXO_BOLETO = "boleto"
ANEXO_NFSE_PDF = "nfse_pdf"
ANEXO_NFSE_XML = "nfse_xml"
ANEXO_TIPOS = frozenset({ANEXO_BOLETO, ANEXO_NFSE_PDF, ANEXO_NFSE_XML})
ANEXO_TIPOS_NFSE = frozenset({ANEXO_NFSE_PDF, ANEXO_NFSE_XML})

TITULO_ABERTO = "aberto"
TITULO_PAGO = "pago"
TITULO_VENCIDO = "vencido"
TITULO_CANCELADO = "cancelado"
TITULO_STATUS_PERSISTIDOS = frozenset({TITULO_ABERTO, TITULO_PAGO, TITULO_CANCELADO})
TITULO_STATUS_FILTRO = frozenset({TITULO_ABERTO, TITULO_PAGO, TITULO_VENCIDO, TITULO_CANCELADO})

# Tipo do título em A receber (#1342): mensalidade nasce da fatura; implantação é título próprio.
TITULO_TIPO_MENSALIDADE = "mensalidade"
TITULO_TIPO_IMPLANTACAO = "implantacao"
TITULO_TIPOS = frozenset({TITULO_TIPO_MENSALIDADE, TITULO_TIPO_IMPLANTACAO})


class FaturamentoPolitica(Base):
    """Singleton da instância: como a mensalidade nasce e vence (#1339).

    O job e a geração manual leem esta linha; `VENCIMENTO_DIA_PADRAO` fica só como
    semente/fallback de banco antigo.
    """

    __tablename__ = "faturamento_politica"

    id = Column(Integer, primary_key=True)
    dia_vencimento = Column(Integer, nullable=False, default=VENCIMENTO_DIA_PADRAO)
    gatilho = Column(String(32), nullable=False, default=GATILHO_DATA_INICIO)
    gatilho_dias = Column(Integer, nullable=False, default=0)
    proporcional_primeira_fatura = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())



class Fatura(Base):
    __tablename__ = "faturamento_faturas"
    __table_args__ = (UniqueConstraint("contrato_id", "competencia", name="uq_faturamento_fatura_contrato_competencia"),)

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("comercial_contratos.id", ondelete="RESTRICT"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True, index=True)
    competencia = Column(String(7), nullable=False, index=True)  # YYYY-MM
    valor = Column(Numeric(14, 2), nullable=False)
    vencimento = Column(Date, nullable=False)
    # Período coberto pela fatura (#1341): a primeira proporcional mostra o recorte real.
    periodo_inicio = Column(Date, nullable=True)
    periodo_fim = Column(Date, nullable=True)
    emite_nfse = Column(Boolean, nullable=False, default=True)
    status = Column(String(32), nullable=False, default=FATURA_AGUARDANDO, index=True)
    rejeicao_motivo = Column(Text, nullable=True)
    gerada_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    aprovada_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    aprovada_em = Column(DateTime(timezone=True), nullable=True)
    boleto_linha_digitavel = Column(String(60), nullable=True)
    boleto_nosso_numero = Column(String(40), nullable=True)
    nfse_numero = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    contrato = relationship("Contrato")
    empresa = relationship("Empresa")
    aprovada_por = relationship("Atendente", foreign_keys=[aprovada_por_id])
    anexos = relationship("FaturaAnexo", back_populates="fatura", cascade="all, delete-orphan")
    titulo = relationship("TituloReceber", back_populates="fatura", uselist=False, cascade="all, delete-orphan")


class FaturaAnexo(Base):
    __tablename__ = "faturamento_anexos"
    __table_args__ = (UniqueConstraint("fatura_id", "tipo", name="uq_faturamento_anexo_fatura_tipo"),)

    id = Column(Integer, primary_key=True, index=True)
    fatura_id = Column(Integer, ForeignKey("faturamento_faturas.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)
    nome_original = Column(String(255), nullable=False)
    content_type = Column(String(128), nullable=True)
    tamanho_bytes = Column(Integer, nullable=False)
    storage_key = Column(String(500), nullable=False)
    enviado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    fatura = relationship("Fatura", back_populates="anexos")
    enviado_por = relationship("Atendente", foreign_keys=[enviado_por_id])


class TituloReceber(Base):
    """Título a receber: mensalidade (nasce da fatura aprovada) ou implantação (#328 / #1342)."""

    __tablename__ = "faturamento_titulos"
    __table_args__ = (
        Index(
            "uq_faturamento_titulo_implantacao_contrato",
            "contrato_id",
            unique=True,
            sqlite_where=text("tipo = 'implantacao'"),
            postgresql_where=text("tipo = 'implantacao'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    fatura_id = Column(
        Integer,
        ForeignKey("faturamento_faturas.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    contrato_id = Column(Integer, ForeignKey("comercial_contratos.id", ondelete="RESTRICT"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True, index=True)
    tipo = Column(String(20), nullable=False, default=TITULO_TIPO_MENSALIDADE)
    competencia = Column(String(7), nullable=False, index=True)
    valor = Column(Numeric(14, 2), nullable=False)
    vencimento = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default=TITULO_ABERTO, index=True)
    pago_em = Column(Date, nullable=True)
    valor_pago = Column(Numeric(14, 2), nullable=True)
    baixa_observacao = Column(Text, nullable=True)
    baixado_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    baixado_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    fatura = relationship("Fatura", back_populates="titulo")
    contrato = relationship("Contrato")
    empresa = relationship("Empresa")
    baixado_por = relationship("Atendente", foreign_keys=[baixado_por_id])
