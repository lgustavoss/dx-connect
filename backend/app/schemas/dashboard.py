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
    sla_em_risco_abertas: int = Field(ge=0)
    de: date
    ate: date
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


class DemandaEmpresaRanking(BaseModel):
    empresa_id: int | None = None
    empresa_nome: str
    total: int = Field(ge=0)
    natureza_dominante_id: int | None = None
    natureza_dominante_nome: str | None = None
    natureza_dominante_slug: str | None = None


class DemandaInsight(BaseModel):
    tipo: str
    titulo: str
    detalhe: str
    natureza_id: int | None = None
    motivo_id: int | None = None
    total: int = Field(ge=0)
    limiar: int = Field(ge=1)


class SugestaoMotivoOutros(BaseModel):
    natureza_id: int
    natureza_nome: str
    texto_normalizado: str
    texto_exemplo: str
    ocorrencias: int = Field(ge=0)
    limiar: int = Field(ge=1)


class DemandaDrillItem(BaseModel):
    demanda_id: int
    chat_id: int
    protocolo: str
    cliente_nome: str | None = None
    empresa_id: int | None = None
    empresa_nome: str | None = None
    natureza_id: int
    natureza_nome: str
    motivo_id: int | None = None
    motivo_nome: str | None = None
    desfecho: str
    descricao_curta: str | None = None
    created_at: datetime


class SugestaoMotivoOutrosAcao(BaseModel):
    natureza_id: int = Field(ge=1)
    texto_normalizado: str = Field(min_length=1, max_length=500)
    nome: str | None = Field(None, min_length=1, max_length=120)
    slug: str | None = Field(None, min_length=1, max_length=50)
    texto_exemplo: str | None = Field(None, max_length=500)


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
    demandas_por_natureza: list[ContagemIdNome] = Field(default_factory=list)
    demandas_por_motivo: list[ContagemIdNome] = Field(default_factory=list)
    demandas_por_empresa: list[DemandaEmpresaRanking] = Field(default_factory=list)
    demanda_maior: ContagemIdNome | None = None
    insights_demandas: list[DemandaInsight] = Field(default_factory=list)
    sugestoes_motivo_outros: list[SugestaoMotivoOutros] = Field(default_factory=list)
    snapshot: SnapshotCanais
    gerado_em: datetime
    cache_ttl_segundos: int = Field(ge=0)
