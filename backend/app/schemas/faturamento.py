from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


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
    emite_nfse: bool
    status: str
    rejeicao_motivo: str | None = None
    gerada_em: datetime | None = None
    aprovada_por_id: int | None = None
    aprovada_por_nome: str | None = None
    aprovada_em: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FaturaGerarIn(BaseModel):
    contrato_id: int
    competencia: str | None = Field(None, description="YYYY-MM; omite = mês atual (America/Sao_Paulo)")


class FaturaGerarCompetenciaIn(BaseModel):
    competencia: str | None = None


class FaturaRejeitarIn(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=2000)


class FaturaGerarCompetenciaOut(BaseModel):
    competencia: str
    criadas: int
    existentes: int
    reabertas: int = 0


class ContratoElegivelRead(BaseModel):
    id: int
    empresa_id: int | None = None
    empresa_nome: str | None = None
    cnpj: str | None = None
    razao_social: str | None = None
    valor_mensalidade: Decimal
