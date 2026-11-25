"""Schemas — contas bancárias de cobrança na instância (#1392)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CobrancaContaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    apelido: str
    banco_codigo: str | None = None
    banco_nome: str | None = None
    agencia: str | None = None
    agencia_dv: str | None = None
    conta: str | None = None
    conta_dv: str | None = None
    carteira: str | None = None
    titular_nome: str | None = None
    titular_documento: str | None = None
    ativo: bool
    padrao: bool
    tem_token: bool
    notas: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CobrancaContaUpsert(BaseModel):
    apelido: str = Field(..., min_length=1, max_length=120)
    banco_codigo: str | None = Field(default=None, max_length=10)
    banco_nome: str | None = Field(default=None, max_length=120)
    agencia: str | None = Field(default=None, max_length=20)
    agencia_dv: str | None = Field(default=None, max_length=4)
    conta: str | None = Field(default=None, max_length=32)
    conta_dv: str | None = Field(default=None, max_length=4)
    carteira: str | None = Field(default=None, max_length=20)
    titular_nome: str | None = Field(default=None, max_length=200)
    titular_documento: str | None = Field(default=None, max_length=20)
    ativo: bool = True
    padrao: bool = False
    notas: str | None = None
    # Só atualiza se enviado (não vazio).
    boleto_cloud_token: str | None = Field(default=None, max_length=512)


class CobrancaContaLista(BaseModel):
    items: list[CobrancaContaRead]
    total: int
