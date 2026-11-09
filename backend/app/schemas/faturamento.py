from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GatilhoFaturamento = Literal[
    "data_inicio",
    "dias_apos_assinatura",
    "dias_apos_marco",
    "ticket_implantacao_fechado",
]


class FaturamentoPoliticaRead(BaseModel):
    dia_vencimento: int
    gatilho: str
    gatilho_dias: int
    proporcional_primeira_fatura: bool

    model_config = ConfigDict(from_attributes=True)


class FaturamentoPoliticaUpdate(BaseModel):
    dia_vencimento: int | None = Field(None, ge=1, le=28)
    gatilho: GatilhoFaturamento | None = None
    gatilho_dias: int | None = Field(None, ge=0, le=365)
    proporcional_primeira_fatura: bool | None = None



class TituloReceberRead(BaseModel):
    id: int
    fatura_id: int | None = None
    contrato_id: int
    empresa_id: int | None = None
    empresa_nome: str | None = None
    cnpj: str | None = None
    razao_social: str | None = None
    tipo: str = "mensalidade"
    competencia: str
    valor: Decimal
    vencimento: date
    status: str
    status_persistido: str
    pago_em: date | None = None
    valor_pago: Decimal | None = None
    baixa_observacao: str | None = None
    baixado_por_id: int | None = None
    baixado_por_nome: str | None = None
    baixado_em: datetime | None = None
    tem_boleto: bool = False

    model_config = ConfigDict(from_attributes=True)


class TituloBaixaIn(BaseModel):
    pago_em: date | None = None
    valor_pago: Decimal | None = None
    observacao: str | None = Field(None, max_length=2000)
    # Exceção para baixa sem boleto anexado (#1387): 10–500 chars (mínimo no service).
    sem_documento_motivo: str | None = Field(None, max_length=500)


class FaturaAnexoRead(BaseModel):
    id: int
    tipo: str
    nome_original: str
    content_type: str | None = None
    tamanho_bytes: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FaturaRead(BaseModel):
    id: int
    contrato_id: int
    empresa_id: int | None = None
    empresa_nome: str | None = None
    cnpj: str | None = None
    razao_social: str | None = None
    competencia: str
    valor: Decimal
    vencimento: date
    periodo_inicio: date | None = None
    periodo_fim: date | None = None
    emite_nfse: bool
    status: str
    rejeicao_motivo: str | None = None
    gerada_em: datetime | None = None
    aprovada_por_id: int | None = None
    aprovada_por_nome: str | None = None
    aprovada_em: datetime | None = None
    boleto_linha_digitavel: str | None = None
    boleto_nosso_numero: str | None = None
    nfse_numero: str | None = None
    documentos_completos: bool = False
    anexos: list[FaturaAnexoRead] = Field(default_factory=list)
    titulo: TituloReceberRead | None = None

    model_config = ConfigDict(from_attributes=True)


class FaturaGerarIn(BaseModel):
    contrato_id: int
    competencia: str | None = Field(None, description="YYYY-MM; omite = mês atual (America/Sao_Paulo)")


class FaturaGerarCompetenciaIn(BaseModel):
    competencia: str | None = None


class FaturaRejeitarIn(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=2000)


class FaturaCancelarIn(BaseModel):
    motivo: str | None = Field(None, max_length=2000)


class TituloCancelarIn(BaseModel):
    motivo: str | None = Field(None, max_length=2000)


class TituloEstornoIn(BaseModel):
    motivo: str | None = Field(None, max_length=2000)


class FaturaDocumentosIn(BaseModel):
    boleto_linha_digitavel: str | None = Field(None, max_length=60)
    boleto_nosso_numero: str | None = Field(None, max_length=40)
    nfse_numero: str | None = Field(None, max_length=40)


class FaturaGerarCompetenciaOut(BaseModel):
    competencia: str
    criadas: int
    existentes: int
    reabertas: int = 0
    aguardando: int = 0


class ContratoElegivelRead(BaseModel):
    id: int
    empresa_id: int | None = None
    empresa_nome: str | None = None
    cnpj: str | None = None
    razao_social: str | None = None
    valor_mensalidade: Decimal
    dia_vencimento: int | None = None
    inicio_mensalidade: date | None = None
    aguardando_motivo: str | None = None
    rede_id: int | None = None
    rede_nome: str | None = None


class ResumoFaixaRead(BaseModel):
    chave: str
    label: str
    quantidade: int
    valor: Decimal


class ResumoPrevisaoRead(BaseModel):
    competencia: str
    titulos: Decimal
    mensalidades_ativas: Decimal
    total: Decimal


class ResumoAReceberRead(BaseModel):
    competencia: str
    total_aberto: Decimal
    total_vencido: Decimal
    quantidade_titulos: int
    faixas: list[ResumoFaixaRead]
    previsao_mes: ResumoPrevisaoRead
    # #1385: a ficha 360 usa o mesmo resumo, sem baixar a lista inteira de títulos.
    proximo_vencimento: date | None = None
    pago_ano: Decimal = Decimal("0.00")
    pago_ano_quantidade: int = 0
