"""Jornada esperada: ciclo X×Y ou escala semanal (#770 / #959/#960)."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.core.business_calendar import WEEKDAY_KEYS, horario_semana_from_json, parse_hhmm
from app.models.atendente import Atendente

PONTO_TZ = ZoneInfo("America/Sao_Paulo")

MODOS_JORNADA = frozenset({"nenhum", "semanal", "ciclo"})


def rotulo_escala(horas_trabalho: int | None, horas_folga: int | None) -> str | None:
    if not horas_trabalho or not horas_folga:
        return None
    return f"{horas_trabalho}×{horas_folga}"


def modo_jornada(atendente: Atendente) -> str:
    raw = (getattr(atendente, "modo_jornada", None) or "").strip().lower()
    if raw == "semanal":
        return "semanal"
    if raw == "ciclo":
        return "ciclo"
    # nenhum / vazio / legado: usa_escala + ciclo X×Y ainda conta como ciclo
    if getattr(atendente, "usa_escala", False) and _ciclo_campos_ok(atendente):
        return "ciclo"
    return "nenhum"


def _ciclo_campos_ok(atendente: Atendente) -> bool:
    return bool(
        atendente.escala_horas_trabalho
        and atendente.escala_horas_folga
        and atendente.escala_inicio_em
    )


def horario_semana_dict(atendente: Atendente) -> dict[str, dict[str, Any]] | None:
    return horario_semana_from_json(getattr(atendente, "horario_semana_json", None))


def _semanal_configurado(atendente: Atendente) -> bool:
    hs = horario_semana_dict(atendente)
    if not hs:
        return False
    for k in WEEKDAY_KEYS:
        cfg = hs.get(k)
        if not isinstance(cfg, dict) or not bool(cfg.get("ativo")):
            continue
        ini = parse_hhmm(cfg.get("inicio"))
        fim = parse_hhmm(cfg.get("fim"))
        if ini and fim and (ini[0], ini[1]) < (fim[0], fim[1]):
            return True
    return False


def ciclo_configurado(atendente: Atendente) -> bool:
    return modo_jornada(atendente) == "ciclo" and _ciclo_campos_ok(atendente)


def escala_configurada(atendente: Atendente) -> bool:
    """True se há jornada esperada (semanal ou ciclo) — gera falta/meta/avisos."""
    m = modo_jornada(atendente)
    if m == "ciclo":
        return _ciclo_campos_ok(atendente)
    if m == "semanal":
        return _semanal_configurado(atendente)
    return False


def _inicio_ciclo_local(atendente: Atendente) -> datetime:
    assert atendente.escala_inicio_em is not None
    return datetime.combine(atendente.escala_inicio_em, time.min, tzinfo=PONTO_TZ)


def em_periodo_trabalho(atendente: Atendente, when: datetime) -> bool:
    """True se o instante cair na janela de trabalho do ciclo X×Y."""
    if not ciclo_configurado(atendente):
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
    """Dia esperado de trabalho conforme o modo de jornada."""
    m = modo_jornada(atendente)
    if m == "ciclo":
        if not _ciclo_campos_ok(atendente):
            return False
        for hour in range(24):
            moment = datetime.combine(dia, time(hour=hour, minute=0), tzinfo=PONTO_TZ)
            if em_periodo_trabalho(atendente, moment):
                return True
        return False
    if m == "semanal":
        hs = horario_semana_dict(atendente)
        if not hs:
            return False
        k = WEEKDAY_KEYS[dia.weekday()]
        cfg = hs.get(k)
        return bool(isinstance(cfg, dict) and cfg.get("ativo"))
    return False


def horario_previsto_do_dia(
    atendente: Atendente, dia: date
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Retorna ((h,m) inicio, (h,m) fim) do dia, ou None se não houver janela."""
    m = modo_jornada(atendente)
    if m == "semanal":
        hs = horario_semana_dict(atendente)
        if not hs:
            return None
        k = WEEKDAY_KEYS[dia.weekday()]
        cfg = hs.get(k)
        if not isinstance(cfg, dict) or not cfg.get("ativo"):
            return None
        ini = parse_hhmm(cfg.get("inicio"))
        fim = parse_hhmm(cfg.get("fim"))
        if ini and fim:
            return ini, fim
        return None
    if m == "ciclo":
        if not eh_dia_de_trabalho(atendente, dia):
            return None
        pe = parse_hhmm(getattr(atendente, "horario_previsto_entrada", None))
        ps = parse_hhmm(getattr(atendente, "horario_previsto_saida", None))
        if pe and ps:
            return pe, ps
        return None
    return None


def dias_do_mes(ano: int, mes: int) -> list[date]:
    d = date(ano, mes, 1)
    out: list[date] = []
    while d.month == mes:
        out.append(d)
        d += timedelta(days=1)
    return out


def _validar_horario_semana_payload(hs: dict[str, Any] | None) -> None:
    if not hs or not isinstance(hs, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o horário semanal (dias ativos com início e fim).",
        )
    ativos = 0
    for k in WEEKDAY_KEYS:
        cfg = hs.get(k)
        if not isinstance(cfg, dict):
            continue
        if not bool(cfg.get("ativo")):
            continue
        ini = parse_hhmm(cfg.get("inicio"))
        fim = parse_hhmm(cfg.get("fim"))
        if not ini or not fim:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Horário inválido em {k} (use HH:MM).",
            )
        if (ini[0], ini[1]) >= (fim[0], fim[1]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Em {k}, o início deve ser anterior ao fim.",
            )
        ativos += 1
    if ativos < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Marque pelo menos um dia ativo na escala semanal.",
        )


def horario_semana_para_json(hs: dict[str, Any] | None) -> str | None:
    if not hs:
        return None
    return json.dumps(hs, ensure_ascii=False)


def validar_campos_jornada(
    *,
    modo: str,
    escala_horas_trabalho: int | None,
    escala_horas_folga: int | None,
    escala_inicio_em: date | None,
    horario_semana: dict[str, Any] | None,
) -> None:
    """Valida campos do modo de jornada; levanta HTTP 400 se inválido."""
    m = (modo or "nenhum").strip().lower()
    if m not in MODOS_JORNADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="modo_jornada deve ser nenhum, semanal ou ciclo.",
        )
    if m == "nenhum":
        return
    if m == "ciclo":
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
        return
    # semanal
    _validar_horario_semana_payload(horario_semana)


def validar_campos_escala(
    *,
    usa_escala: bool,
    escala_horas_trabalho: int | None,
    escala_horas_folga: int | None,
    escala_inicio_em: date | None,
) -> None:
    """Compat legado: usa_escala True ≡ ciclo."""
    validar_campos_jornada(
        modo="ciclo" if usa_escala else "nenhum",
        escala_horas_trabalho=escala_horas_trabalho,
        escala_horas_folga=escala_horas_folga,
        escala_inicio_em=escala_inicio_em,
        horario_semana=None,
    )


def validar_horario_previsto(entrada: str | None, saida: str | None) -> None:
    for label, val in (("entrada", entrada), ("saída", saida)):
        if val is None or not str(val).strip():
            continue
        if parse_hhmm(val) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Horário previsto de {label} inválido (use HH:MM).",
            )


def segundos_esperados_dia(atendente: Atendente, dia: date | None = None) -> int:
    """Duração esperada de um dia de trabalho."""
    d = dia or datetime.now(PONTO_TZ).date()
    janela = horario_previsto_do_dia(atendente, d)
    if janela:
        pe, ps = janela
        ini = pe[0] * 3600 + pe[1] * 60
        fim = ps[0] * 3600 + ps[1] * 60
        if fim > ini:
            return fim - ini
    if ciclo_configurado(atendente) and atendente.escala_horas_trabalho:
        return int(atendente.escala_horas_trabalho) * 3600
    return 0


def liberacao_entrada_em(atendente: Atendente, dia: date) -> datetime | None:
    """Primeiro instante em que a entrada é permitida (inicio − tolerância)."""
    janela = horario_previsto_do_dia(atendente, dia)
    if not janela:
        return None
    pe, _ = janela
    tol = int(getattr(atendente, "tolerancia_atraso_minutos", 0) or 0)
    return datetime.combine(dia, time(hour=pe[0], minute=pe[1]), tzinfo=PONTO_TZ) - timedelta(
        minutes=tol
    )


def limite_atraso_em(atendente: Atendente, dia: date) -> datetime | None:
    """Após este instante a entrada conta como atraso (inicio + tolerância)."""
    janela = horario_previsto_do_dia(atendente, dia)
    if not janela:
        return None
    pe, _ = janela
    tol = int(getattr(atendente, "tolerancia_atraso_minutos", 0) or 0)
    return datetime.combine(dia, time(hour=pe[0], minute=pe[1]), tzinfo=PONTO_TZ) + timedelta(
        minutes=tol
    )


def saida_prevista_em(atendente: Atendente, dia: date) -> datetime | None:
    janela = horario_previsto_do_dia(atendente, dia)
    if not janela:
        return None
    _, ps = janela
    return datetime.combine(dia, time(hour=ps[0], minute=ps[1]), tzinfo=PONTO_TZ)


def validar_janela_entrada(atendente: Atendente, when: datetime) -> None:
    """Bloqueia entrada antes de inicio−tolerância (#964). Admin/sistema não chamam isto."""
    if not escala_configurada(atendente):
        return
    if when.tzinfo is None:
        when = when.replace(tzinfo=PONTO_TZ)
    else:
        when = when.astimezone(PONTO_TZ)
    dia = when.date()
    if not eh_dia_de_trabalho(atendente, dia):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hoje não é dia de trabalho na sua jornada.",
        )
    liberacao = liberacao_entrada_em(atendente, dia)
    if liberacao is None:
        return
    if when < liberacao:
        tol = int(getattr(atendente, "tolerancia_atraso_minutos", 0) or 0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Entrada liberada a partir de {liberacao.strftime('%H:%M')} "
                f"(tolerância de {tol} min antes do horário)."
            ),
        )


def rotulo_jornada(atendente: Atendente) -> str | None:
    m = modo_jornada(atendente)
    if m == "ciclo":
        return rotulo_escala(atendente.escala_horas_trabalho, atendente.escala_horas_folga)
    if m == "semanal" and _semanal_configurado(atendente):
        hs = horario_semana_dict(atendente) or {}
        ativos = [k for k in WEEKDAY_KEYS if isinstance(hs.get(k), dict) and hs[k].get("ativo")]
        if not ativos:
            return "semanal"
        return f"semanal ({', '.join(ativos)})"
    return None
