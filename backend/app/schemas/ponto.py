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


class PontoCalendarioDia(BaseModel):
    data: date
    esperado: bool
    tem_entrada: bool
    tem_saida: bool
    status: Literal["ok", "falta", "parcial", "folga", "folga_com_ponto", "livre"]


class PontoCalendarioRead(BaseModel):
    atendente_id: int
    ano: int
    mes: int
    usa_escala: bool
    escala_rotulo: str | None = None
    dias: list[PontoCalendarioDia]


class PontoHojeItem(BaseModel):
    atendente_id: int
    nome: str
    esperado: bool
    em_jornada: bool
    em_pausa: bool = False
    entrada_em: datetime | None = None
    status: Literal["ok", "falta", "parcial", "folga", "folga_com_ponto", "livre"]
    online: bool = False
    online_sem_ponto: bool = False


class PontoHojeRead(BaseModel):
    data: date
    itens: list[PontoHojeItem]


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
