"""Schemas do painel SaaS / licenças DeskRudder — #521–#522."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl

StatusClienteSaaS = Literal["trial", "ativo", "suspenso", "churn"]

_SLUG_RE = __import__("re").compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validar_slug(v: str) -> str:
    slug = (v or "").strip().lower()
    if not slug or len(slug) > 80:
        raise ValueError("Slug deve ter entre 1 e 80 caracteres")
    if not _SLUG_RE.match(slug):
        raise ValueError("Slug deve conter apenas letras minúsculas, números e hífens")
    return slug


class ClienteSaaSBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=80)
    status: StatusClienteSaaS = "trial"
    plano: str | None = Field(None, max_length=80)
    data_inicio: date
    data_renovacao: date | None = None
    instancia_url: str | None = Field(None, max_length=500)
    notas: str | None = None

    @field_validator("nome")
    @classmethod
    def strip_nome(cls, v: str) -> str:
        nome = (v or "").strip()
        if not nome:
            raise ValueError("Nome é obrigatório")
        return nome

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, v: str) -> str:
        return _validar_slug(v)

    @field_validator("plano")
    @classmethod
    def strip_plano(cls, v: str | None) -> str | None:
        if v is None:
            return None
        plano = v.strip()
        return plano or None

    @field_validator("instancia_url")
    @classmethod
    def normalize_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        url = v.strip()
        if not url:
            return None
        # Aceita host sem esquema; normaliza para https://
        if "://" not in url:
            url = f"https://{url}"
        # Valida via HttpUrl
        return str(HttpUrl(url))

    @field_validator("notas")
    @classmethod
    def strip_notas(cls, v: str | None) -> str | None:
        if v is None:
            return None
        notas = v.strip()
        return notas or None


class ClienteSaaSCreate(ClienteSaaSBase):
    pass


class ClienteSaaSUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=200)
    slug: str | None = Field(None, min_length=1, max_length=80)
    status: StatusClienteSaaS | None = None
    plano: str | None = Field(None, max_length=80)
    data_inicio: date | None = None
    data_renovacao: date | None = None
    instancia_url: str | None = Field(None, max_length=500)
    notas: str | None = None

    @field_validator("nome")
    @classmethod
    def strip_nome(cls, v: str | None) -> str | None:
        if v is None:
            return None
        nome = v.strip()
        if not nome:
            raise ValueError("Nome é obrigatório")
        return nome

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _validar_slug(v)

    @field_validator("plano")
    @classmethod
    def strip_plano(cls, v: str | None) -> str | None:
        if v is None:
            return None
        plano = v.strip()
        return plano or None

    @field_validator("instancia_url")
    @classmethod
    def normalize_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        url = v.strip()
        if not url:
            return None
        if "://" not in url:
            url = f"https://{url}"
        return str(HttpUrl(url))

    @field_validator("notas")
    @classmethod
    def strip_notas(cls, v: str | None) -> str | None:
        if v is None:
            return None
        notas = v.strip()
        return notas or None


class ClienteSaaSRegistrarInstancia(BaseModel):
    instancia_url: str = Field(..., min_length=1, max_length=500)

    @field_validator("instancia_url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        url = (v or "").strip()
        if not url:
            raise ValueError("URL da instância é obrigatória")
        if "://" not in url:
            url = f"https://{url}"
        return str(HttpUrl(url))


class ClienteSaaSRead(ClienteSaaSBase):
    id: int
    provisionamento_solicitado: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
