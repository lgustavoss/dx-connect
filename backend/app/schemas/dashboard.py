from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.ticket import TicketRead


class StatusCount(BaseModel):
    status_id: int
    status_nome: str
    total: int


class DashboardResumo(BaseModel):
    total_tickets: int
    abertos_hoje: int
    por_status: list[StatusCount]


class DashboardResponse(BaseModel):
    resumo: DashboardResumo
    ultimos_tickets: list[TicketRead]


class CsAtMediaResumo(BaseModel):
    media: float | None = None
    total_avaliacoes: int = Field(ge=0)
    periodo_dias: int = Field(ge=1)


class DashboardGeralResponse(BaseModel):
    tickets_abertos: int = Field(ge=0)
    tickets_sem_responsavel: int = Field(ge=0)
    chats_aguardando_atendente: int = Field(ge=0)
    chats_em_atendimento: int = Field(ge=0)
    csat_tickets: CsAtMediaResumo
    csat_chats: CsAtMediaResumo
    sla_violacoes_abertas: int | None = None
    gerado_em: datetime
    cache_ttl_segundos: int = Field(ge=0)
