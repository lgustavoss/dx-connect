"""Schemas — setores (cargos) da equipe SaaS."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SaasSetorRead(BaseModel):
    id: int
    nome: str
    ativo: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SaasSetorCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)


class SaasSetorUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=100)
    ativo: bool | None = None
