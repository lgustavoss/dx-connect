"""Schemas CRM — leads, funil, negociações (#322 / #336–#340)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.comercial_custo import CustoTefOverride


def _normalizar_cnpj_opcional(v: str | None) -> str | None:
    if v is None:
        return None
    digits = "".join(c for c in str(v) if c.isdigit())
    if not digits:
        return None
    if len(digits) != 14:
        raise ValueError("CNPJ deve ter 14 dígitos.")
    return digits


class FunilEstagioRead(BaseModel):
    id: int
    slug: str
    nome: str
    ordem: int
    tipo: str
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class FunilEstagioCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=50)
    nome: str = Field(..., min_length=1, max_length=120)
    ordem: int = 0
    tipo: str = "aberto"
    ativo: bool = True


class FunilEstagioUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=120)
    ordem: int | None = None
    tipo: str | None = None
    ativo: bool | None = None


class CrmLeadCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)
    telefone: str | None = Field(None, max_length=40)
    email: str | None = Field(None, max_length=255)
    empresa_texto: str | None = Field(None, max_length=255)
    origem: str | None = Field(None, max_length=80)
    notas: str | None = None
    responsavel_id: int | None = None  # default = utilizador logado
    criar_negociacao: bool = True
    titulo_negociacao: str | None = Field(None, max_length=255)


class CrmLeadUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=255)
    telefone: str | None = Field(None, max_length=40)
    email: str | None = Field(None, max_length=255)
    empresa_texto: str | None = Field(None, max_length=255)
    origem: str | None = Field(None, max_length=80)
    notas: str | None = None
    responsavel_id: int | None = None
    ativo: bool | None = None


class CrmLeadRead(BaseModel):
    id: int
    nome: str
    telefone: str | None = None
    email: str | None = None
    empresa_texto: str | None = None
    origem: str | None = None
    notas: str | None = None
    responsavel_id: int
    estagio_id: int
    estagio_slug: str | None = None
    estagio_nome: str | None = None
    perdido_em: datetime | None = None
    ativo: bool
    negociacao_ativa_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DadosFiscaisLinha(BaseModel):
    nome: str | None = Field(None, max_length=255)
    nome_fantasia: str | None = Field(None, max_length=255)
    inscricao_estadual: str | None = Field(None, max_length=20)
    endereco: str | None = Field(None, max_length=255)
    numero: str | None = Field(None, max_length=20)
    complemento: str | None = Field(None, max_length=100)
    bairro: str | None = Field(None, max_length=100)
    cidade: str | None = Field(None, max_length=100)
    estado: str | None = Field(None, max_length=2)
    cep: str | None = Field(None, max_length=10)
    email: str | None = Field(None, max_length=255)
    telefone: str | None = Field(None, max_length=20)
    resp_legal_nome: str | None = Field(None, max_length=255)
    resp_legal_cpf: str | None = Field(None, max_length=14)
    resp_legal_rg: str | None = Field(None, max_length=20)
    resp_legal_orgao_emissor: str | None = Field(None, max_length=30)
    resp_legal_nacionalidade: str | None = Field(None, max_length=50)
    resp_legal_estado_civil: str | None = Field(None, max_length=30)
    resp_legal_cargo: str | None = Field(None, max_length=100)
    resp_legal_email: str | None = Field(None, max_length=255)
    resp_legal_telefone: str | None = Field(None, max_length=20)
    resp_legal_endereco: str | None = Field(None, max_length=255)
    resp_legal_numero: str | None = Field(None, max_length=20)
    resp_legal_complemento: str | None = Field(None, max_length=100)
    resp_legal_bairro: str | None = Field(None, max_length=100)
    resp_legal_cidade: str | None = Field(None, max_length=100)
    resp_legal_estado: str | None = Field(None, max_length=2)
    resp_legal_cep: str | None = Field(None, max_length=10)


class CrmLinhaCreate(BaseModel):
    cnpj: str | None = None
    razao_social: str | None = Field(None, max_length=255)
    dados_fiscais: DadosFiscaisLinha | None = None
    item_ids: list[int] = Field(default_factory=list)
    quantidade_pdvs: int = Field(1, ge=1, le=500)
    desconto_posto_100k: bool = False
    tef_override: CustoTefOverride | None = None
    valor_negociado: Decimal = Field(Decimal("0"), ge=0)
    ordem: int = 0

    @field_validator("cnpj", mode="before")
    @classmethod
    def _cnpj(cls, v):
        return _normalizar_cnpj_opcional(v)


class CrmLinhaUpdate(BaseModel):
    cnpj: str | None = None
    razao_social: str | None = Field(None, max_length=255)
    dados_fiscais: DadosFiscaisLinha | None = None
    item_ids: list[int] | None = None
    quantidade_pdvs: int | None = Field(None, ge=1, le=500)
    desconto_posto_100k: bool | None = None
    tef_override: CustoTefOverride | None = None
    valor_negociado: Decimal | None = Field(None, ge=0)
    ordem: int | None = None
    # True = limpar override TEF
    limpar_tef_override: bool = False

    @field_validator("cnpj", mode="before")
    @classmethod
    def _cnpj(cls, v):
        if v is None:
            return None
        return _normalizar_cnpj_opcional(v)


class CrmLinhaRead(BaseModel):
    id: int
    negociacao_id: int
    cnpj: str | None = None
    razao_social: str | None = None
    dados_fiscais: dict[str, Any] | None = None
    item_ids: list[int] = Field(default_factory=list)
    quantidade_pdvs: int
    desconto_posto_100k: bool
    tef_override: dict[str, Any] | None = None
    valor_negociado: Decimal
    snapshot_custo: dict[str, Any] | None = None
    total_custo: Decimal | None = None
    margem_calculada: Decimal | None = None
    empresa_id: int | None = None
    ordem: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CrmNegociacaoCreate(BaseModel):
    lead_id: int
    titulo: str | None = Field(None, max_length=255)
    responsavel_id: int | None = None
    linhas: list[CrmLinhaCreate] = Field(default_factory=list)


class CrmNegociacaoUpdate(BaseModel):
    titulo: str | None = Field(None, max_length=255)
    nome_base_webposto: str | None = Field(None, max_length=255)
    responsavel_id: int | None = None


class CrmNegociacaoRead(BaseModel):
    id: int
    lead_id: int
    responsavel_id: int
    estagio_id: int
    estagio_slug: str | None = None
    estagio_nome: str | None = None
    ativa: bool
    titulo: str | None = None
    nome_base_webposto: str | None = None
    linhas: list[CrmLinhaRead] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CrmMoverEstagioRequest(BaseModel):
    estagio_id: int | None = None
    estagio_slug: str | None = None
    nota: str | None = None


class CrmAtividadeCreate(BaseModel):
    tipo: str = "nota"
    texto: str = Field(..., min_length=1)


class CrmAtividadeRead(BaseModel):
    id: int
    negociacao_id: int
    autor_id: int
    tipo: str
    texto: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
