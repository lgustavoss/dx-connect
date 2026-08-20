"""Regras de escala: ciclo horas trabalhadas × horas de folga (#770)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.models.atendente import Atendente

PONTO_TZ = ZoneInfo("America/Sao_Paulo")


def rotulo_escala(horas_trabalho: int | None, horas_folga: int | None) -> str | None:
    if not horas_trabalho or not horas_folga:
        return None
    return f"{horas_trabalho}×{horas_folga}"


def escala_configurada(atendente: Atendente) -> bool:
    return bool(
        getattr(atendente, "usa_escala", False)
        and atendente.escala_horas_trabalho
        and atendente.escala_horas_folga
        and atendente.escala_inicio_em
    )


def _inicio_ciclo_local(atendente: Atendente) -> datetime:
    assert atendente.escala_inicio_em is not None
    return datetime.combine(atendente.escala_inicio_em, time.min, tzinfo=PONTO_TZ)


def em_periodo_trabalho(atendente: Atendente, when: datetime) -> bool:
    """True se o instante cair na janela de trabalho do ciclo X×Y."""
    if not escala_configurada(atendente):
        return False
    h_trab = int(atendente.escala_horas_trabalho)  # type: ignore[arg-type]
    h_folga = int(atendente.escala_horas_folga)  # type: ignore[arg-type]
    ciclo = h_trab + h_folga
    if when.tzinfo is None:
        when = when.replace(tzinfo=PONTO_TZ)
    else:
        when = when.astimezone(PONTO_TZ)
    start = _inicio_ciclo_local(atendente)
    elapsed_h = (when - start).total_seconds() / 3600.0
    if elapsed_h < 0:
        return False
    return (elapsed_h % ciclo) < h_trab


def eh_dia_de_trabalho(atendente: Atendente, dia: date) -> bool:
    """Dia de trabalho se qualquer hora do dia (TZ negócio) cair no período de trabalho."""
    if not escala_configurada(atendente):
        return False
    for hour in range(24):
        moment = datetime.combine(dia, time(hour=hour, minute=0), tzinfo=PONTO_TZ)
        if em_periodo_trabalho(atendente, moment):
            return True
    return False


def dias_do_mes(ano: int, mes: int) -> list[date]:
    d = date(ano, mes, 1)
    out: list[date] = []
    while d.month == mes:
        out.append(d)
        d += timedelta(days=1)
    return out


def validar_campos_escala(
    *,
    usa_escala: bool,
    escala_horas_trabalho: int | None,
    escala_horas_folga: int | None,
    escala_inicio_em: date | None,
) -> None:
    """Valida campos; levanta HTTP 400 se inválido."""
    if not usa_escala:
        return
    if not escala_horas_trabalho or escala_horas_trabalho < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe as horas trabalhadas da escala (mínimo 1).",
        )
    if not escala_horas_folga or escala_horas_folga < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe as horas de folga da escala (mínimo 1).",
        )
    if escala_inicio_em is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe a data de início da escala.",
        )
