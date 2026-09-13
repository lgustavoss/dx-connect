"""Schemas — alertas operacionais SaaS Ops (#1036)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Severidade = Literal["amarelo", "vermelho"]
Estado = Literal["ativo", "mitigado", "resolvido"]


class SaasAlertaOpsEventoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    mensagem: str
    payload: dict[str, Any] | None = None
    created_at: datetime


class SaasAlertaOpsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_saas_id: int
    cliente_nome: str | None = None
    cliente_slug: str | None = None
    codigo_sinal: str
    modulo: str
    severidade: Severidade
    estado: Estado
    ciclo_id: int
    titulo: str
    started_at: datetime
    mitigated_at: datetime | None = None
    resolved_at: datetime | None = None
    last_seen_at: datetime
    evidencia: dict[str, Any] | None = None
    eventos: list[SaasAlertaOpsEventoRead] = Field(default_factory=list)


class SaasAlertaOpsLista(BaseModel):
    items: list[SaasAlertaOpsRead]
    total: int


class SaasAlertaOpsModuloCount(BaseModel):
    modulo: str
    total: int


class SaasAlertaOpsResumo(BaseModel):
    alertas_ativos: int
    por_severidade: dict[str, int]
    instancias_afetadas: int
    modulos_mais_incidentes: list[SaasAlertaOpsModuloCount]


class SaasAlertaOpsMitigar(BaseModel):
    mensagem: str | None = Field(default=None, max_length=500)
