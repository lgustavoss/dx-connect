"""Schemas de controle de ponto (#761+)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoBatida = Literal["entrada", "saida", "pausa_inicio", "pausa_fim"]


class PontoBaterRequest(BaseModel):
    tipo: TipoBatida
    origem: Literal["web", "mobile"] | None = "web"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_metros: float | None = Field(default=None, ge=0, le=100_000)


class PontoBatidaRead(BaseModel):
    id: int
    atendente_id: int
    tipo: str
    registrado_em: datetime
    origem: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    accuracy_metros: float | None = None
    fora_area: bool = False
    distancia_metros: float | None = None
    local_id: int | None = None
    anulada: bool = False

    model_config = ConfigDict(from_attributes=True)


PoliticaGeolocalizacao = Literal["opcional", "recomendada", "obrigatoria"]


class PontoSettingsPublicRead(BaseModel):
    politica_geolocalizacao: PoliticaGeolocalizacao = "opcional"
    tem_locais_ativos: bool = False


class PontoLocalCreate(BaseModel):
    atendente_id: int = Field(..., ge=1)
    nome: str = Field(..., min_length=1, max_length=255)
    endereco: str | None = Field(default=None, max_length=512)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    raio_metros: int = Field(default=200, ge=20, le=50_000)
    ativo: bool | None = True


class PontoLocalRead(BaseModel):
    id: int
    atendente_id: int | None = None
    nome: str
    endereco: str | None = None
    latitude: float
    longitude: float
    raio_metros: int
    ativo: bool = True

    model_config = ConfigDict(from_attributes=True)


class PontoLocalUpdate(BaseModel):
    atendente_id: int | None = Field(default=None, ge=1)
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    endereco: str | None = Field(default=None, max_length=512)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    raio_metros: int | None = Field(default=None, ge=20, le=50_000)
    ativo: bool | None = None


class PontoEstadoRead(BaseModel):
    em_jornada: bool
    em_pausa: bool = False
    entrada_aberta_em: datetime | None = None
    ultima_batida: PontoBatidaRead | None = None
    usa_escala: bool = False
    hoje_esperado: bool | None = None
    escala_rotulo: str | None = None


class PontoIntervaloRead(BaseModel):
    data: date
    entrada_em: datetime
    saida_em: datetime | None = None
    duracao_segundos: int | None = None
    segundos_pausa: int = 0
    aberto: bool = False
    entrada_latitude: float | None = None
    entrada_longitude: float | None = None
    entrada_fora_area: bool = False
    saida_latitude: float | None = None
    saida_longitude: float | None = None
    saida_fora_area: bool = False


class PontoHistoricoRead(BaseModel):
    intervalos: list[PontoIntervaloRead]
    total_segundos_fechados: int
    total_segundos_pausa: int = 0
    total: int


class PontoBatidaAdminItem(BaseModel):
    id: int
    atendente_id: int
    atendente_nome: str
    tipo: str
    registrado_em: datetime
    origem: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    accuracy_metros: float | None = None
    fora_area: bool = False
    distancia_metros: float | None = None
    local_id: int | None = None
    anulada: bool = False


StatusDiaPonto = Literal[
    "ok",
    "falta",
    "parcial",
    "folga",
    "folga_com_ponto",
    "livre",
    "atraso",
    "feriado",
]


class PontoCalendarioDia(BaseModel):
    data: date
    esperado: bool
    tem_entrada: bool
    tem_saida: bool
    status: StatusDiaPonto
    atrasado: bool = False
    feriado: bool = False
    # #842 — meta de jornada × realizado (cores do calendário)
    segundos_trabalhados: int = 0
    segundos_esperados: int = 0
    classe_visual: Literal["abaixo", "ok", "he", "feriado", "neutro"] = "neutro"


class PontoCalendarioRead(BaseModel):
    atendente_id: int
    ano: int
    mes: int
    usa_escala: bool
    escala_rotulo: str | None = None
    jornada_diaria_minutos: int = 480
    dias: list[PontoCalendarioDia]


class PontoHojeItem(BaseModel):
    atendente_id: int
    nome: str
    esperado: bool
    em_jornada: bool
    em_pausa: bool = False
    entrada_em: datetime | None = None
    status: StatusDiaPonto
    online: bool = False
    online_sem_ponto: bool = False
    atrasado: bool = False
    feriado: bool = False


class PontoHojeRead(BaseModel):
    data: date
    itens: list[PontoHojeItem]


class PontoBancoHorasRead(BaseModel):
    atendente_id: int
    atendente_nome: str | None = None
    desde: date
    ate: date
    segundos_esperados: int
    segundos_realizados: int
    saldo_segundos: int
    dias_escala: int
    dias_feriado: int = 0


class PontoDigestRead(BaseModel):
    data: date
    faltas: int
    atrasos: int
    jornadas_abertas: int
    online_sem_ponto: int
    justificativas_pendentes: int
    itens: list[PontoHojeItem]


class PontoSettingsRead(BaseModel):
    usar_feriados_nacionais: bool = True
    fecho_automatico_ativo: bool = False
    fecho_apos_horas: int = 14
    fecho_margem_pos_saida_minutos: int = 30
    jornada_diaria_minutos: int = 480
    politica_geolocalizacao: PoliticaGeolocalizacao = "opcional"

    model_config = ConfigDict(from_attributes=True)


class PontoSettingsUpdate(BaseModel):
    usar_feriados_nacionais: bool | None = None
    fecho_automatico_ativo: bool | None = None
    fecho_apos_horas: int | None = Field(default=None, ge=4, le=48)
    fecho_margem_pos_saida_minutos: int | None = Field(default=None, ge=0, le=240)
    jornada_diaria_minutos: int | None = Field(default=None, ge=60, le=1440)
    politica_geolocalizacao: PoliticaGeolocalizacao | None = None


class PontoFeriadoCreate(BaseModel):
    data: date
    nome: str = Field(..., min_length=1, max_length=255)
    ativo: bool | None = True


class PontoFeriadoRead(BaseModel):
    id: int
    data: date
    nome: str
    ativo: bool = True

    model_config = ConfigDict(from_attributes=True)


class PontoAjusteCreate(BaseModel):
    atendente_id: int
    tipo: TipoBatida
    registrado_em: datetime
    motivo: str = Field(..., min_length=3, max_length=500)


class PontoAjusteUpdate(BaseModel):
    tipo: TipoBatida | None = None
    registrado_em: datetime | None = None
    motivo: str = Field(..., min_length=3, max_length=500)


class PontoAnularBody(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)


class PontoAlertasMe(BaseModel):
    """Lembretes ao usuário — sem batida automática (#773 / #769 / #968)."""

    sem_entrada_em_dia_escala: bool = False
    online_sem_ponto: bool = False
    jornada_aberta_longa: bool = False
    horas_jornada_aberta: float | None = None
    lembrete_entrada_tolerancia: bool = False
    lembrete_saida_tolerancia: bool = False
    mensagens: list[str] = []


class PontoResumoSemanaRead(BaseModel):
    """Resumo semanal do colaborador (#972)."""

    desde: date
    ate: date
    segundos_esperados: int
    segundos_realizados: int
    saldo_segundos: int
    atrasos: int
    he_minutos: int
    dias_escala: int
    dias_feriado: int = 0


class PontoJustificativaCreate(BaseModel):
    data_ref: date
    tipo: Literal["falta", "esquecimento", "folga_com_ponto", "outro"]
    motivo: str = Field(..., min_length=3, max_length=1000)


class PontoJustificativaRead(BaseModel):
    id: int
    atendente_id: int
    atendente_nome: str | None = None
    data_ref: date
    tipo: str
    motivo: str
    estado: str
    decisao_motivo: str | None = None
    decidido_por_id: int | None = None
    decidido_em: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PontoJustificativaDecisao(BaseModel):
    estado: Literal["aprovada", "rejeitada"]
    decisao_motivo: str = Field(..., min_length=3, max_length=1000)

    class BatidaAplicar(BaseModel):
        tipo: TipoBatida
        registrado_em: datetime
        motivo: str = Field(..., min_length=3, max_length=500)

    aplicar_batidas: list[BatidaAplicar] | None = None


class PontoHoraExtraCreate(BaseModel):
    motivo: str | None = Field(default=None, max_length=1000)


class PontoHoraExtraRead(BaseModel):
    id: int
    atendente_id: int
    atendente_nome: str | None = None
    estado: str
    motivo: str | None = None
    modo: str | None = None
    ate_em: datetime | None = None
    origem: str = "solicitacao"
    decidido_por_id: int | None = None
    decidido_em: datetime | None = None
    decisao_motivo: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PontoHoraExtraDecisao(BaseModel):
    aprovar: bool
    modo: Literal["resto_do_dia", "ate_horario", "duracao"] | None = None
    ate_horario: str | None = Field(default=None, max_length=5, description="HH:MM se modo=ate_horario")
    duracao_minutos: int | None = Field(default=None, ge=15, le=24 * 60)
    decisao_motivo: str | None = Field(default=None, max_length=1000)


class PontoHoraExtraConceder(BaseModel):
    atendente_id: int = Field(..., ge=1)
    modo: Literal["resto_do_dia", "ate_horario", "duracao"]
    ate_horario: str | None = Field(default=None, max_length=5)
    duracao_minutos: int | None = Field(default=None, ge=15, le=24 * 60)
    motivo: str | None = Field(default=None, max_length=1000)


class PontoHoraExtraMeStatus(BaseModel):
    fora_da_jornada: bool
    pode_pegar_whatsapp: bool
    he_ativa: PontoHoraExtraRead | None = None
    pedido_pendente: PontoHoraExtraRead | None = None
    he_teto_minutos: int | None = None
    he_restante_minutos: int | None = None


class PontoCoberturaColega(BaseModel):
    id: int
    nome: str


class PontoCoberturaCreate(BaseModel):
    cobertor_id: int = Field(..., ge=1)
    data_ref: date
    motivo: str | None = Field(default=None, max_length=1000)


class PontoCoberturaConceder(BaseModel):
    solicitante_id: int = Field(..., ge=1)
    cobertor_id: int = Field(..., ge=1)
    data_ref: date
    motivo: str | None = Field(default=None, max_length=1000)


class PontoCoberturaResposta(BaseModel):
    aceitar: bool


class PontoCoberturaDecisao(BaseModel):
    aprovar: bool
    decisao_motivo: str | None = Field(default=None, max_length=1000)


class PontoCoberturaRead(BaseModel):
    id: int
    solicitante_id: int
    solicitante_nome: str | None = None
    cobertor_id: int
    cobertor_nome: str | None = None
    data_ref: date
    motivo: str | None = None
    estado: str
    origem: str = "solicitacao"
    resposta_cobertor: str | None = None
    respondido_em: datetime | None = None
    decidido_por_id: int | None = None
    decidido_em: datetime | None = None
    decisao_motivo: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PontoSetupItem(BaseModel):
    codigo: str
    titulo: str
    detalhe: str
    destino: str
    ok: bool
    informativo: bool = False


class PontoSetupStatus(BaseModel):
    defaults_fecho_off: bool
    tolerancia_sugerida_minutos: int = 15
    pendentes: int
    itens: list[PontoSetupItem]


class PontoCompetenciaRead(BaseModel):
    id: int
    ano: int
    mes: int
    fechada: bool
    fechado_em: datetime | None = None
    fechado_por_id: int | None = None
    fechado_por_nome: str | None = None
    reaberto_em: datetime | None = None
    reaberto_por_id: int | None = None
    reabrir_motivo: str | None = None


class PontoCompetenciaReabrir(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=1000)


class PontoCienciaMe(BaseModel):
    ano: int
    mes: int
    competencia_fechada: bool
    confirmada: bool
    confirmado_em: datetime | None = None
    pode_confirmar: bool


class PontoCienciaItem(BaseModel):
    atendente_id: int
    atendente_nome: str
    confirmada: bool
    confirmado_em: datetime | None = None
