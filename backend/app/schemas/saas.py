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
    plano_id: int | None = None
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
    lead_comercial_id: int | None = None
    modulo_ids: list[int] | None = Field(
        None, description="Mix custom de módulos; se omitido, usa os do plano"
    )
    usuarios_contratados: int | None = Field(
        None, ge=0, description="Usuários contratados (extra além dos inclusos)"
    )
    preco_mensal_negociado: float | None = Field(
        None,
        ge=0,
        description="Valor mensal fechado na negociação; se vazio, usa a estimativa do catálogo",
    )


class ClienteSaaSUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=200)
    slug: str | None = Field(None, min_length=1, max_length=80)
    status: StatusClienteSaaS | None = None
    plano: str | None = Field(None, max_length=80)
    plano_id: int | None = None
    data_inicio: date | None = None
    data_renovacao: date | None = None
    instancia_url: str | None = Field(None, max_length=500)
    contato_email: str | None = Field(None, max_length=255)
    contato_nome: str | None = Field(None, max_length=200)
    notas: str | None = None
    modulo_ids: list[int] | None = None
    usuarios_contratados: int | None = Field(None, ge=0)
    preco_mensal_negociado: float | None = Field(None, ge=0)

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
    # Por omissão cria/enfileira a base Docker do cliente após aprovação.
    provisionar: bool = True
    plano_id: int | None = None

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


# --- Catálogo comercial: módulos e planos ---

_CODIGO_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validar_codigo(v: str) -> str:
    codigo = (v or "").strip().lower()
    if not codigo or len(codigo) > 80:
        raise ValueError("Código deve ter entre 1 e 80 caracteres")
    if not _CODIGO_RE.match(codigo):
        raise ValueError("Código deve conter apenas letras minúsculas, números e hífens")
    return codigo


class SaasModuloBrief(BaseModel):
    id: int
    codigo: str
    nome: str
    ativo: bool = True
    preco_mensal: float | None = None

    model_config = ConfigDict(from_attributes=True)


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
    stack_status: str | None = None
    stack_ops_pendente: str | None = None
    stack_ops_mensagem: str | None = None
    stack_ops_atualizado_em: datetime | None = None
    lead_comercial_id: int | None = None
    entrega_notificada_em: datetime | None = None
    comandos_ops: str | None = None
    comandos_stack: str | None = None
    dias_para_renovacao: int | None = None
    plano_modulos: list[SaasModuloBrief] = Field(default_factory=list)
    modulos_contratados: list[SaasModuloBrief] = Field(default_factory=list)
    modulos_snapshot: list[str] = Field(default_factory=list)
    max_postos: int | None = None
    max_usuarios: int | None = None
    usuarios_inclusos: int | None = None
    preco_usuario_extra: float | None = None
    preco_modulos: float | None = None
    preco_usuarios_extra: float | None = None
    preco_mensal_estimado: float | None = None
    preco_mensal_negociado: float | None = None
    preco_mensal_efetivo: float | None = None
    ingest_token_configurado: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SaasInstanciaResumo(BaseModel):
    id: int
    slug: str
    nome: str
    status: str
    api_port: int | None = None
    stack_status: str | None = None
    provisionamento_status: str | None = None
    instancia_url: str | None = None


class SaasTimelineEvent(BaseModel):
    id: int
    action: str
    label: str
    atendente_id: int | None = None
    payload: dict | None = None
    created_at: datetime | None = None


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
    base_dominio_provisionamento: str = "deskrudder.com.br"
    instancias: list[SaasInstanciaResumo] = Field(default_factory=list)


class SaasModuloCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=80)
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: str | None = None
    preco_mensal: float | None = Field(None, ge=0)

    @field_validator("codigo")
    @classmethod
    def normalize_codigo(cls, v: str) -> str:
        return _validar_codigo(v)

    @field_validator("nome")
    @classmethod
    def strip_nome(cls, v: str) -> str:
        nome = (v or "").strip()
        if not nome:
            raise ValueError("Nome é obrigatório")
        return nome

    @field_validator("descricao")
    @classmethod
    def strip_descricao(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class SaasModuloUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=120)
    descricao: str | None = None
    preco_mensal: float | None = Field(None, ge=0)

    @field_validator("nome")
    @classmethod
    def strip_nome(cls, v: str | None) -> str | None:
        if v is None:
            return None
        nome = v.strip()
        if not nome:
            raise ValueError("Nome é obrigatório")
        return nome

    @field_validator("descricao")
    @classmethod
    def strip_descricao(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class SaasModuloRead(BaseModel):
    id: int
    codigo: str
    nome: str
    descricao: str | None = None
    preco_mensal: float | None = None
    ativo: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SaasPlanoCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=80)
    nome: str = Field(..., min_length=1, max_length=120)
    descricao: str | None = None
    ordem: int = 0
    usuarios_inclusos: int | None = Field(3, ge=0)
    preco_usuario_extra: float | None = Field(10, ge=0)
    max_usuarios: int | None = Field(None, ge=0)
    modulo_ids: list[int] = Field(default_factory=list)

    @field_validator("codigo")
    @classmethod
    def normalize_codigo(cls, v: str) -> str:
        return _validar_codigo(v)

    @field_validator("nome")
    @classmethod
    def strip_nome(cls, v: str) -> str:
        nome = (v or "").strip()
        if not nome:
            raise ValueError("Nome é obrigatório")
        return nome

    @field_validator("descricao")
    @classmethod
    def strip_descricao(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class SaasPlanoUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=120)
    descricao: str | None = None
    ordem: int | None = None
    usuarios_inclusos: int | None = Field(None, ge=0)
    preco_usuario_extra: float | None = Field(None, ge=0)
    max_usuarios: int | None = Field(None, ge=0)
    modulo_ids: list[int] | None = None

    @field_validator("nome")
    @classmethod
    def strip_nome(cls, v: str | None) -> str | None:
        if v is None:
            return None
        nome = v.strip()
        if not nome:
            raise ValueError("Nome é obrigatório")
        return nome

    @field_validator("descricao")
    @classmethod
    def strip_descricao(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class SaasPlanoRead(BaseModel):
    id: int
    codigo: str
    nome: str
    descricao: str | None = None
    ativo: bool = True
    ordem: int = 0
    preco_mensal: float | None = None
    usuarios_inclusos: int = 3
    preco_usuario_extra: float | None = 10
    max_postos: int | None = None
    max_usuarios: int | None = None
    modulos: list[SaasModuloBrief] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SaasPrecoEstimativa(BaseModel):
    preco_modulos: float = 0
    preco_usuarios_extra: float = 0
    preco_mensal_total: float = 0
    usuarios_inclusos: int = 3
    preco_usuario_extra: float = 10
    usuarios_contratados: int | None = None
    modulos: list[SaasModuloBrief] = Field(default_factory=list)
