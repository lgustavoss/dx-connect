from datetime import date, datetime

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


class ChatEstadoCount(BaseModel):
    estado: str
    rotulo: str
    total: int = Field(ge=0)


class DashboardChatsResumo(BaseModel):
    total_chats: int = Field(ge=0)
    iniciados_hoje: int = Field(ge=0)
    por_estado: list[ChatEstadoCount]


class ChatRecenteResumo(BaseModel):
    id: int
    protocolo: str
    cliente_nome: str | None = None
    estado: str
    created_at: datetime


class DashboardResponse(BaseModel):
    resumo: DashboardResumo
    resumo_chats: DashboardChatsResumo
    ultimos_tickets: list[TicketRead]
    ultimos_chats: list[ChatRecenteResumo]


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
    sla_violacoes_abertas: int = Field(ge=0)
    gerado_em: datetime
    cache_ttl_segundos: int = Field(ge=0)


class SerieVolumeDia(BaseModel):
    dia: date
    abertos: int = Field(ge=0)
    fechados: int = Field(ge=0)


class ContagemIdNome(BaseModel):
    id: int
    nome: str
    total: int = Field(ge=0)


class ContagemPrioridade(BaseModel):
    prioridade: str
    total: int = Field(ge=0)


class ContagemRotulo(BaseModel):
    chave: str | None = None
    rotulo: str
    total: int = Field(ge=0)


class ContagemCanal(BaseModel):
    canal: str
    rotulo: str
    total: int = Field(ge=0)


class CsatDistribuicaoTickets(BaseModel):
    media: float | None = None
    total_avaliacoes: int = Field(ge=0)
    por_nota: dict[int, int] = Field(default_factory=dict)


class DashboardTicketsResponse(BaseModel):
    de: date
    ate: date
    volume_por_dia: list[SerieVolumeDia]
    por_status: list[ContagemIdNome]
    por_prioridade: list[ContagemPrioridade]
    por_motivo: list[ContagemIdNome]
    por_rede: list[ContagemIdNome]
    por_empresa: list[ContagemIdNome]
    mttr_horas: float | None = None
    fila_tempo_medio_horas: float | None = None
    csat: CsatDistribuicaoTickets
    por_canal: list[ContagemCanal]
    por_atendente: list[ContagemIdNome]
    gerado_em: datetime
    cache_ttl_segundos: int = Field(ge=0)


class ContagemEncerramentoChat(BaseModel):
    tipo: str
    rotulo: str
    total: int = Field(ge=0)


class SnapshotCanais(BaseModel):
    tickets_abertos: int = Field(ge=0)
    tickets_sem_responsavel: int = Field(ge=0)
    chats_aguardando: int = Field(ge=0)
    chats_em_atendimento: int = Field(ge=0)


class DashboardChatsResponse(BaseModel):
    de: date
    ate: date
    volume_por_dia: list[SerieVolumeDia]
    tempo_espera_medio_horas: float | None = None
    tempo_atendimento_medio_horas: float | None = None
    avaliacoes: CsatDistribuicaoTickets
    encerramentos: list[ContagemEncerramentoChat]
    pct_com_ticket_vinculado: float | None = None
    por_atendente: list[ContagemIdNome]
    por_estado_atual: list[ContagemRotulo]
    snapshot: SnapshotCanais
    gerado_em: datetime
    cache_ttl_segundos: int = Field(ge=0)
