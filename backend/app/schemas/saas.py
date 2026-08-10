"""Schemas do painel SaaS / licenças DeskRudder — #521–#522."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl

StatusClienteSaaS = Literal["trial", "ativo", "suspenso", "churn"]
AprovacaoStatusSaaS = Literal["pendente", "aprovado", "rejeitado"]

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validar_slug(v: str) -> str:
    slug = (v or "").strip().lower()
    if not slug or len(slug) > 80:
        raise ValueError("Slug deve ter entre 1 e 80 caracteres")
    if not _SLUG_RE.match(slug):
        raise ValueError("Slug deve conter apenas letras minúsculas, números e hífens")
    return slug


def _validar_email_opcional(v: str | None) -> str | None:
    if v is None:
        return None
    email = v.strip().lower()
    if not email:
        return None
    if not _EMAIL_RE.match(email):
        raise ValueError("E-mail de contacto inválido")
    return email


class ClienteSaaSBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=80)
    status: StatusClienteSaaS = "trial"
    plano: str | None = Field(None, max_length=80)
    data_inicio: date
    data_renovacao: date | None = None
    instancia_url: str | None = Field(None, max_length=500)
    contato_email: str | None = Field(None, max_length=255)
    contato_nome: str | None = Field(None, max_length=200)
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

    @field_validator("contato_email")
    @classmethod
    def normalize_contato_email(cls, v: str | None) -> str | None:
        return _validar_email_opcional(v)

    @field_validator("contato_nome")
    @classmethod
    def strip_contato_nome(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None

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
    contato_email: str | None = Field(None, max_length=255)
    contato_nome: str | None = Field(None, max_length=200)
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

    @field_validator("contato_email")
    @classmethod
    def normalize_contato_email(cls, v: str | None) -> str | None:
        return _validar_email_opcional(v)

    @field_validator("contato_nome")
    @classmethod
    def strip_contato_nome(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None

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


class ClienteSaaSConfirmarProvisionamento(BaseModel):
    """Body opcional ao confirmar provisionamento ops-assisted (#524)."""

    instancia_url: str | None = Field(None, max_length=500)

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


class ClienteSaaSRenovar(BaseModel):
    dias: int | None = Field(None, ge=1, le=3650)
    nova_data: date | None = None


class ClienteSaaSAprovar(BaseModel):
    notas: str | None = None
    ativar: bool = True

    @field_validator("notas")
    @classmethod
    def strip_notas_aprovar(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class ClienteSaaSRejeitar(BaseModel):
    notas: str | None = None

    @field_validator("notas")
    @classmethod
    def strip_notas_rejeitar(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class ClienteSaaSRead(ClienteSaaSBase):
    id: int
    api_port: int | None = None
    provisionamento_solicitado: bool = False
    provisionamento_status: str | None = None
    provisionamento_mensagem: str | None = None
    provisionamento_atualizado_em: datetime | None = None
    aprovacao_status: AprovacaoStatusSaaS = "aprovado"
    aprovacao_notas: str | None = None
    aprovacao_em: datetime | None = None
    comandos_ops: str | None = None
    dias_para_renovacao: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SaasResumoRead(BaseModel):
    clientes_total: int = 0
    por_status: dict[str, int] = Field(default_factory=dict)
    vencendo_em_breve: int = 0
    vencidas_ativas: int = 0
    provisionamento_pendente: int = 0
    provisionamento_falha: int = 0
    aprovacoes_pendentes: int = 0
    leads_novos: int = 0
    leads_em_atendimento: int = 0
    janela_renovacao_dias: int = 14
