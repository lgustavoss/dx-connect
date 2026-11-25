"""Schemas — pools Boleto Cloud no control-plane (#1392)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BoletoPoolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    apelido: str
    email_login: str | None = None
    api_base_url: str
    faixa_teto: int | None = None
    notas: str | None = None
    ativo: bool
    tem_api_key: bool
    clientes_vinculados: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BoletoPoolUpsert(BaseModel):
    apelido: str = Field(..., min_length=1, max_length=120)
    email_login: str | None = Field(default=None, max_length=255)
    api_base_url: str = Field(
        default="https://sandbox.boletocloud.com/api/v1",
        min_length=8,
        max_length=255,
    )
    faixa_teto: int | None = Field(default=None, ge=1)
    notas: str | None = None
    ativo: bool = True
    api_key: str | None = Field(default=None, max_length=512)


class BoletoPoolLista(BaseModel):
    items: list[BoletoPoolRead]
    total: int


class BoletoCloudTestarResultado(BaseModel):
    ok: bool
    mensagem: str
    http_status: int | None = None


class BoletoVinculoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_saas_id: int
    cliente_nome: str | None = None
    cliente_slug: str | None = None
    pool_id: int
    pool_apelido: str | None = None
    vigencia_de: datetime
    vigencia_ate: datetime | None = None
    ativo_agora: bool
    notas: str | None = None
    created_at: datetime | None = None


class BoletoVinculoCreate(BaseModel):
    pool_id: int
    vigencia_de: datetime | None = None
    notas: str | None = None
    # Se True, encerra o vínculo ativo anterior (vigencia_ate = agora).
    encerrar_anterior: bool = True


class BoletoVinculoLista(BaseModel):
    items: list[BoletoVinculoRead]
    total: int


# --- Compatibilidade com o formulário piloto (um pool) ---

class BoletoCloudRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    apelido: str
    api_base_url: str
    ativo: bool
    tem_api_key: bool
    tem_conta_token: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BoletoCloudUpsert(BaseModel):
    apelido: str = Field(..., min_length=1, max_length=120)
    api_base_url: str = Field(
        default="https://sandbox.boletocloud.com/api/v1",
        min_length=8,
        max_length=255,
    )
    ativo: bool = True
    api_key: str | None = Field(default=None, max_length=512)
    conta_token: str | None = Field(default=None, max_length=512)
