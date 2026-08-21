"""Schemas de contrato comercial (#324 / #349–#352)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ContratoTemplateCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    conteudo_html: str = Field(..., min_length=1)
    vigencia_inicio: datetime | None = None
    ativo: bool = True


class ContratoTemplateUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=120)
    conteudo_html: str | None = Field(None, min_length=1)
    vigencia_inicio: datetime | None = None
    ativo: bool | None = None


class ContratoTemplateRead(BaseModel):
    id: int
    nome: str
    versao: int
    conteudo_html: str
    vigencia_inicio: datetime | None = None
    ativo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContratoTemplatePreviewIn(BaseModel):
    conteudo_html: str = Field(..., min_length=1)


class ContratoTemplatePreviewOut(BaseModel):
    html: str


class ContratoChaveCatalogoItem(BaseModel):
    grupo: str
    chave: str
    descricao: str


class ContratoGerarIn(BaseModel):
    linha_id: int
    template_id: int | None = None
    data_inicio: date | None = None
    fidelidade_meses: int = Field(12, ge=1, le=60)
    setup_valor: Decimal | None = None
    setup_isento: bool = False
    deslocamento_cliente: bool = True
    alimentacao_cliente: bool = True
    hospedagem_cliente: bool = True
    multa_max_mensalidades: int = Field(3, ge=0, le=12)
    sem_reajuste: bool = False
    reajuste_percentual: Decimal | None = Field(None, ge=0, le=100)
    reajuste_rotulo: str | None = Field(None, max_length=80)


class ContratoPoliticaRead(BaseModel):
    reajuste_percentual: Decimal
    reajuste_rotulo: str

    model_config = ConfigDict(from_attributes=True)


class ContratoPoliticaUpdate(BaseModel):
    reajuste_percentual: Decimal | None = Field(None, ge=0, le=100)
    reajuste_rotulo: str | None = Field(None, max_length=80)


class ContratoMarcarEnviadoIn(BaseModel):
    enviado_em: datetime | None = None


class ContratoMarcarAssinadoIn(BaseModel):
    assinado_em: datetime | None = None
    avancar_funil: bool = False
    referencia_externa: str | None = Field(None, max_length=120)


class ContratoPdfRead(BaseModel):
    id: int
    contrato_id: int
    gerado_por_id: int
    conteudo_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContratoInternoRead(BaseModel):
    total_custo: Decimal | None = None
    margem_calculada: Decimal | None = None
    margem_percentual: Decimal | None = None
    lucro_bruto: Decimal | None = None


class MultaRescisaoEstimativa(BaseModel):
    """Ajuda operacional — não é cobrança nem parecer jurídico."""

    aplicavel: bool
    dentro_fidelidade: bool
    meses_restantes: int
    multa_max_mensalidades: int
    mensalidades_estimadas: int
    valor_mensalidade: Decimal
    valor_estimado: Decimal | None = None
    aviso: str


class ContratoRead(BaseModel):
    id: int
    negociacao_linha_cnpj_id: int
    negociacao_id: int | None = None
    empresa_id: int | None = None
    rede_id: int | None = None
    template_id: int
    template_nome: str | None = None
    template_versao: int | None = None
    gerado_por_id: int
    status: str
    valor_mensalidade: Decimal
    snapshot_itens: list
    data_inicio: date
    data_fim_fidelidade: date
    fidelidade_meses: int
    setup_valor: Decimal | None = None
    setup_isento: bool
    deslocamento_cliente: bool
    alimentacao_cliente: bool
    hospedagem_cliente: bool
    multa_max_mensalidades: int
    reajuste_percentual: Decimal
    reajuste_rotulo: str
    pdf_assinado_nome_original: str | None = None
    tem_pdf_assinado: bool = False
    referencia_externa: str | None = None
    enviado_em: datetime | None = None
    assinado_em: datetime | None = None
    created_at: datetime
    pdf_atual_id: int | None = None
    pdfs: list[ContratoPdfRead] = []
    cnpj: str | None = None
    razao_social: str | None = None
    responsavel_id: int | None = None
    responsavel_nome: str | None = None
    lead_nome: str | None = None
    conteudo_html_snapshot: str | None = None
    dias_restantes_fidelidade: int | None = None
    multa_rescisao: MultaRescisaoEstimativa | None = None
    interno: ContratoInternoRead | None = None
    implantacao_ticket_id: int | None = None
    implantacao_ticket_protocolo: str | None = None

    model_config = ConfigDict(from_attributes=True)
