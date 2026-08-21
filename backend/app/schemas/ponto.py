"""Schemas de controle de ponto (#761+)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoBatida = Literal["entrada", "saida", "pausa_inicio", "pausa_fim"]


class PontoBaterRequest(BaseModel):
    tipo: TipoBatida
    origem: Literal["web", "mobile"] | None = "web"


class PontoBatidaRead(BaseModel):
    id: int
    atendente_id: int
    tipo: str
    registrado_em: datetime
    origem: str | None = None
    anulada: bool = False

    model_config = ConfigDict(from_attributes=True)


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
    jornada_diaria_minutos: int = 480

    model_config = ConfigDict(from_attributes=True)


class PontoSettingsUpdate(BaseModel):
    usar_feriados_nacionais: bool | None = None
    fecho_automatico_ativo: bool | None = None
    fecho_apos_horas: int | None = Field(default=None, ge=4, le=48)
    jornada_diaria_minutos: int | None = Field(default=None, ge=60, le=1440)


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
    """Lembretes ao utilizador — sem batida automática (#773 / #769)."""

    sem_entrada_em_dia_escala: bool = False
    online_sem_ponto: bool = False
    jornada_aberta_longa: bool = False
    horas_jornada_aberta: float | None = None
    mensagens: list[str] = []


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
