"""Schemas do portal do cliente (funcionário da rede)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PortalLogin(BaseModel):
    email: EmailStr
    senha: str = Field(..., min_length=1, max_length=128)


class PortalToken(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    must_change_password: bool = False


class PortalRefreshRequest(BaseModel):
    refresh_token: str


class PortalTrocarSenha(BaseModel):
    senha_atual: str = Field(..., min_length=1, max_length=128)
    senha_nova: str = Field(..., min_length=8, max_length=128)


class PortalPreferenciasUpdate(BaseModel):
    notificar_email_portal: bool | None = None


class PortalEmpresaRead(BaseModel):
    id: int
    nome: str
    rede_id: int

    model_config = ConfigDict(from_attributes=True)


class PortalSetorRead(BaseModel):
    id: int
    nome: str
    slug: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PortalPdvRead(BaseModel):
    id: int
    codigo: str
    papel: str | None = None
    ativo: bool = True


class PortalMe(BaseModel):
    id: int
    nome: str
    email: str
    tipo: str
    rede_id: int | None = None
    empresas: list[PortalEmpresaRead] = []
    must_change_password: bool = False
    notificar_email_portal: bool = True


class PortalTicketCreate(BaseModel):
    empresa_id: int
    setor_id: int | None = None
    assunto: str = Field(..., min_length=3, max_length=255)
    descricao: str | None = Field(None, max_length=20000)
    pdv_codigo: str | None = Field(None, max_length=64)
    motivo_id: int | None = None
    motivo_outro_texto: str | None = Field(None, max_length=500)


class PortalTicketMensagemCreate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=20000)


class PortalAnexoRead(BaseModel):
    id: int
    nome_original: str
    content_type: str | None = None
    tamanho_bytes: int
    mensagem_id: int | None = None
    created_at: datetime | None = None
    download_url: str


class PortalMensagemRead(BaseModel):
    id: int
    tipo: str
    corpo: str
    autor_nome: str | None = None
    autor_papel: Literal["equipe", "voce", "sistema"] = "sistema"
    created_at: datetime | None = None
    anexos: list[PortalAnexoRead] = []


class PortalTicketListItem(BaseModel):
    id: int
    protocolo: str
    assunto: str
    status_nome: str | None = None
    status_slug: str | None = None
    empresa_id: int | None = None
    empresa_nome: str | None = None
    setor_nome: str | None = None
    prioridade: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    fechado_em: datetime | None = None
    ultima_mensagem_em: datetime | None = None


class PortalTicketDetail(PortalTicketListItem):
    descricao: str | None = None
    pode_responder: bool = True
    csat_token: str | None = None
    csat_pendente: bool = False


class PortalMensagemOk(BaseModel):
    detail: str = "ok"
