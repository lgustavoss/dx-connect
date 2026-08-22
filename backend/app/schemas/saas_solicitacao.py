"""Schemas da fila SaaS de solicitações de produto (#855)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoSolicitacao = Literal["sugestao", "problema"]


class SaasSolicitacaoIngest(BaseModel):
    instance_slug: str = Field(..., min_length=1, max_length=80)
    origem_solicitacao_id: int = Field(..., ge=1)
    tipo: TipoSolicitacao
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: str = Field(..., min_length=1, max_length=20000)
    status: str = Field("aberta", max_length=40)
    versao_contexto: str | None = Field(None, max_length=64)
    autor_nome: str | None = Field(None, max_length=255)
    created_at: datetime | None = None


class SaasSolicitacaoListaItem(BaseModel):
    id: int
    cliente_saas_id: int | None
    cliente_nome: str | None
    instance_slug: str
    origem_solicitacao_id: int
    tipo: str
    titulo: str
    status: str
    status_rotulo: str
    versao_contexto: str | None
    autor_nome: str | None
    created_at_origem: datetime | None
    ingested_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SaasSolicitacaoComentarioRead(BaseModel):
    id: int
    corpo: str
    publico_cliente: bool
    autor_nome: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SaasSolicitacaoAnexoRead(BaseModel):
    id: int
    papel: str
    nome_original: str
    content_type: str | None
    tamanho_bytes: int
    url: str


class SaasSolicitacaoDetalhe(SaasSolicitacaoListaItem):
    descricao: str
    motivo_nao_desenvolvimento: str | None = None
    triagem_atualizada_em: datetime | None = None
    comentarios: list[SaasSolicitacaoComentarioRead] = Field(default_factory=list)
    anexos: list[SaasSolicitacaoAnexoRead] = Field(default_factory=list)


class SaasSolicitacaoStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=40)
    motivo_nao_desenvolvimento: str | None = Field(None, max_length=4000)


class SaasSolicitacaoComentarioCreate(BaseModel):
    corpo: str = Field(..., min_length=1, max_length=8000)
    publico_cliente: bool = True


class SaasSolicitacaoSyncComentario(BaseModel):
    id: int
    corpo: str
    autor_nome: str | None
    created_at: datetime


class SaasSolicitacaoSyncItem(BaseModel):
    origem_solicitacao_id: int
    status: str
    motivo_nao_desenvolvimento: str | None = None
    comentarios_publicos: list[SaasSolicitacaoSyncComentario] = Field(default_factory=list)


class SaasSolicitacaoSyncResponse(BaseModel):
    items: list[SaasSolicitacaoSyncItem] = Field(default_factory=list)


class ClienteSaaSIngestTokenRead(BaseModel):
    slug: str
    token: str
    ingest_url: str
    ingest_token_configurado: bool = True
