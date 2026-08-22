"""Schemas de pré-ticket IA (#809 / #810)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PreTicketEstado = Literal["rascunho", "analisado", "aprovado", "publicado", "descartado"]
PreTicketClassificacao = Literal["bug", "melhoria", "spike", "infra", "documentacao", "duvida"]
PreTicketViabilidade = Literal["viavel", "nao_viavel", "precisa_contexto"]


class PreTicketSessaoCreate(BaseModel):
    contexto: str = Field(..., min_length=10, max_length=20000)
    problema: str = Field(..., min_length=10, max_length=20000)
    impacto: str | None = Field(None, max_length=10000)
    evidencias: str | None = Field(None, max_length=20000)
    urgencia: str | None = Field(None, max_length=200)
    ticket_id: int | None = None


class PreTicketRascunhoUpdate(BaseModel):
    rascunho_titulo: str | None = Field(None, max_length=255)
    rascunho_corpo: str | None = Field(None, max_length=50000)


class PreTicketAnalise(BaseModel):
    classificacao: PreTicketClassificacao
    lacunas_perguntas: list[str]
    riscos: list[str]
    viabilidade: PreTicketViabilidade
    titulo_sugerido: str
    criterios_aceite: list[str]
    corpo_sugerido: str
    dependencias: list[str]
    prompt_version: str


class PreTicketSessaoRead(BaseModel):
    id: int
    ticket_id: int | None
    contexto: str
    problema: str
    impacto: str | None
    evidencias: str | None
    urgencia: str | None
    estado: PreTicketEstado
    prompt_version: str | None
    analise: PreTicketAnalise | None
    rascunho_titulo: str | None
    rascunho_corpo: str | None
    rascunho_publicado_titulo: str | None = None
    rascunho_publicado_corpo: str | None = None
    github_repo: str | None
    github_issue_number: int | None
    github_issue_url: str | None
    github_last_error: str | None = None
    criado_por_nome: str | None
    aprovado_por_nome: str | None
    publicado_por_nome: str | None = None
    aprovado_em: datetime | None
    publicado_em: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class PreTicketHistoricoItem(BaseModel):
    id: int
    acao: str
    detalhe: str | None
    atendente_nome: str | None
    payload: dict | None = None
    created_at: datetime


class PreTicketMetricasAlerta(BaseModel):
    tipo: str
    nivel: str
    mensagem: str


class PreTicketMetricasRead(BaseModel):
    periodo: dict
    uso: dict
    tecnicas: dict
    custo: dict
    alertas: list[PreTicketMetricasAlerta]
    limites: dict


class PreTicketSessaoListaItem(BaseModel):
    id: int
    ticket_id: int | None
    estado: PreTicketEstado
    rascunho_titulo: str | None
    classificacao: PreTicketClassificacao | None
    criado_por_nome: str | None
    created_at: datetime
