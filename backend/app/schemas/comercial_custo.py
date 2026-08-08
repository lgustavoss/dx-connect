"""Schemas do catálogo comercial de custos (#321)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TipoCusto = Literal["percentual_sm", "valor_fixo", "composto_tef"]


class SalarioMinimoCreate(BaseModel):
    valor: Decimal = Field(..., gt=0)
    vigencia_inicio: date
    vigencia_fim: date | None = None

    @model_validator(mode="after")
    def _vigencia(self):
        if self.vigencia_fim is not None and self.vigencia_fim < self.vigencia_inicio:
            raise ValueError("vigencia_fim deve ser >= vigencia_inicio")
        return self


class SalarioMinimoUpdate(BaseModel):
    valor: Decimal | None = Field(None, gt=0)
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None


class SalarioMinimoAtualizarValor(BaseModel):
    """Novo valor a partir de uma data — fecha o vigente e preserva o histórico."""

    valor: Decimal = Field(..., gt=0)
    vigencia_inicio: date = Field(..., description="Data a partir da qual o novo valor passa a valer")


class SalarioMinimoRead(BaseModel):
    id: int
    valor: Decimal
    vigencia_inicio: date
    vigencia_fim: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CustoCatalogoItemCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    slug: str = Field(..., min_length=1, max_length=50)
    descricao: str | None = None
    tipo: TipoCusto
    percentual_sm: Decimal | None = Field(None, ge=0, le=1000)
    valor_fixo: Decimal | None = Field(None, ge=0)
    tef_base: Decimal | None = Field(None, ge=0)
    tef_adicional: Decimal | None = Field(None, ge=0)
    ordem: int = 0
    ativo: bool = True
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        s = v.strip().lower()
        if not s:
            raise ValueError("slug inválido")
        return s

    @model_validator(mode="after")
    def _campos_por_tipo(self):
        if self.vigencia_fim is not None and self.vigencia_inicio is not None:
            if self.vigencia_fim < self.vigencia_inicio:
                raise ValueError("vigencia_fim deve ser >= vigencia_inicio")
        if self.tipo == "percentual_sm":
            if self.percentual_sm is None:
                raise ValueError("percentual_sm é obrigatório para tipo percentual_sm")
        elif self.tipo == "valor_fixo":
            if self.valor_fixo is None:
                raise ValueError("valor_fixo é obrigatório para tipo valor_fixo")
        elif self.tipo == "composto_tef":
            if self.tef_base is None or self.tef_adicional is None:
                raise ValueError("tef_base e tef_adicional são obrigatórios para composto_tef")
        return self


class CustoCatalogoItemUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=120)
    slug: str | None = Field(None, min_length=1, max_length=50)
    descricao: str | None = None
    tipo: TipoCusto | None = None
    percentual_sm: Decimal | None = Field(None, ge=0, le=1000)
    valor_fixo: Decimal | None = Field(None, ge=0)
    tef_base: Decimal | None = Field(None, ge=0)
    tef_adicional: Decimal | None = Field(None, ge=0)
    ordem: int | None = None
    ativo: bool | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None


class CustoCatalogoItemRead(BaseModel):
    id: int
    nome: str
    slug: str
    descricao: str | None = None
    tipo: str
    percentual_sm: Decimal | None = None
    valor_fixo: Decimal | None = None
    tef_base: Decimal | None = None
    tef_adicional: Decimal | None = None
    ordem: int
    ativo: bool
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CustoSimularRequest(BaseModel):
    item_ids: list[int] = Field(..., min_length=1)
    quantidade_pdvs: int = Field(1, ge=1, le=500)
    data_referencia: date | None = None


class CustoSimularLinha(BaseModel):
    item_id: int
    nome: str
    slug: str
    tipo: str
    valor: Decimal


class CustoSimularResponse(BaseModel):
    data_referencia: date
    salario_minimo: Decimal | None
    salario_minimo_id: int | None
    quantidade_pdvs: int
    linhas: list[CustoSimularLinha]
    total: Decimal
