"""Schemas de controle de ponto (#761)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PontoBaterRequest(BaseModel):
    tipo: Literal["entrada", "saida"]
    origem: Literal["web", "mobile"] | None = "web"


class PontoBatidaRead(BaseModel):
    id: int
    atendente_id: int
    tipo: str
    registrado_em: datetime
    origem: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PontoEstadoRead(BaseModel):
    em_jornada: bool
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
    aberto: bool = False


class PontoHistoricoRead(BaseModel):
    intervalos: list[PontoIntervaloRead]
    total_segundos_fechados: int
    total: int  # nº de intervalos (paginação)


class PontoBatidaAdminItem(BaseModel):
    id: int
    atendente_id: int
    atendente_nome: str
    tipo: str
    registrado_em: datetime
    origem: str | None = None


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
    entrada_em: datetime | None = None
    status: Literal["ok", "falta", "parcial", "folga", "folga_com_ponto", "livre"]


class PontoHojeRead(BaseModel):
    data: date
    itens: list[PontoHojeItem]


class EscalaCampos(BaseModel):
    """Campos de escala embutidos no atendente (create/update)."""

    usa_escala: bool = False
    escala_horas_trabalho: int | None = Field(default=None, ge=1, le=168)
    escala_horas_folga: int | None = Field(default=None, ge=1, le=336)
    escala_inicio_em: date | None = None
