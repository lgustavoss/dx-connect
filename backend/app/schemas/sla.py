from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.ticket_prioridade import PRIORIDADES_TICKET, PrioridadeTicket


class BusinessCalendarBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    setor_id: int | None = None
    horario_timezone: str = Field(default="America/Sao_Paulo", max_length=64)
    horario_inicio: str | None = Field(default=None, max_length=5)
    horario_fim: str | None = Field(default=None, max_length=5)
    horario_semana: dict[str, Any] | None = None
    usar_feriados_nacionais: bool = False
    ativo: bool = True


class BusinessCalendarCreate(BusinessCalendarBase):
    pass


class BusinessCalendarUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    setor_id: int | None = None
    horario_timezone: str | None = Field(default=None, max_length=64)
    horario_inicio: str | None = Field(default=None, max_length=5)
    horario_fim: str | None = Field(default=None, max_length=5)
    horario_semana: dict[str, Any] | None = None
    usar_feriados_nacionais: bool | None = None
    ativo: bool | None = None


class BusinessCalendarRead(BusinessCalendarBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_row(cls, row) -> "BusinessCalendarRead":
        import json

        horario_semana = None
        raw = getattr(row, "horario_semana_json", None)
        if raw:
            try:
                horario_semana = json.loads(str(raw))
            except Exception:
                horario_semana = None
        return cls(
            id=row.id,
            nome=row.nome,
            setor_id=row.setor_id,
            horario_timezone=row.horario_timezone,
            horario_inicio=row.horario_inicio,
            horario_fim=row.horario_fim,
            horario_semana=horario_semana,
            usar_feriados_nacionais=row.usar_feriados_nacionais,
            ativo=row.ativo,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class SlaPolicyBase(BaseModel):
    setor_id: int
    prioridade: PrioridadeTicket | None = Field(
        default=None,
        description="Nulo = política padrão do setor (qualquer prioridade sem regra específica).",
    )
    business_calendar_id: int | None = None
    meta_primeira_resposta_min: int | None = Field(default=None, ge=1)
    meta_resolucao_min: int | None = Field(default=None, ge=1)
    ativo: bool = True

    @field_validator("prioridade", mode="before")
    @classmethod
    def _empty_prioridade_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class SlaPolicyCreate(SlaPolicyBase):
    pass


class SlaPolicyUpdate(BaseModel):
    setor_id: int | None = None
    prioridade: PrioridadeTicket | None = None
    business_calendar_id: int | None = None
    meta_primeira_resposta_min: int | None = Field(default=None, ge=1)
    meta_resolucao_min: int | None = Field(default=None, ge=1)
    ativo: bool | None = None

    @field_validator("prioridade", mode="before")
    @classmethod
    def _empty_prioridade_none(cls, v):
        if v == "":
            return None
        return v


class SlaPolicyRead(SlaPolicyBase):
    id: int
    setor_nome: str | None = None
    business_calendar_nome: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_row(cls, row, *, setor_nome: str | None = None, calendar_nome: str | None = None) -> "SlaPolicyRead":
        prio = row.prioridade
        prioridade = PrioridadeTicket(prio) if prio else None
        return cls(
            id=row.id,
            setor_id=row.setor_id,
            prioridade=prioridade,
            business_calendar_id=row.business_calendar_id,
            meta_primeira_resposta_min=row.meta_primeira_resposta_min,
            meta_resolucao_min=row.meta_resolucao_min,
            ativo=row.ativo,
            setor_nome=setor_nome,
            business_calendar_nome=calendar_nome,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class SlaPrioridadesDisponiveis(BaseModel):
    prioridades: list[str] = list(PRIORIDADES_TICKET)


class SlaMetaDetalheRead(BaseModel):
    meta_minutos: int | None = None
    vence_em: datetime | None = None
    cumprido_em: datetime | None = None
    estado: str
    percentual_decorrido: float | None = None


class TicketSlaRead(BaseModel):
    ticket_id: int
    sla_policy_id: int | None = None
    sla_violado: bool = False
    inicio_em: datetime
    usa_horario_comercial: bool = False
    pausado_agora: bool = False
    minutos_pausados: int = 0
    primeira_resposta: SlaMetaDetalheRead
    resolucao: SlaMetaDetalheRead
