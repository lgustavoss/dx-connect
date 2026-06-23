"""Calendário comercial compartilhado (feriados BR + helpers de horário)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def easter_date_gregorian(year: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def is_feriado_nacional_br(d: date) -> bool:
    fixos = {
        (1, 1),
        (4, 21),
        (5, 1),
        (9, 7),
        (10, 12),
        (11, 2),
        (11, 15),
        (11, 20),
        (12, 25),
    }
    if (d.month, d.day) in fixos:
        return True
    easter = easter_date_gregorian(d.year)
    carnaval_seg = easter - timedelta(days=48)
    carnaval_ter = easter - timedelta(days=47)
    sexta_santa = easter - timedelta(days=2)
    corpus_christi = easter + timedelta(days=60)
    return d in (carnaval_seg, carnaval_ter, sexta_santa, corpus_christi)


def parse_hhmm(value: str | None) -> tuple[int, int] | None:
    if not value or not str(value).strip():
        return None
    parts = str(value).strip().split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return h, m


def horario_semana_from_json(raw: str | None) -> dict[str, dict[str, Any]] | None:
    if not raw or not str(raw).strip():
        return None
    try:
        v = json.loads(str(raw))
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def esta_em_horario_comercial(
    *,
    timezone_name: str,
    horario_inicio: str | None,
    horario_fim: str | None,
    horario_semana_json: str | None,
    usar_feriados_nacionais: bool,
    moment: datetime | None = None,
) -> bool:
    tzname = (timezone_name or "America/Sao_Paulo").strip() or "America/Sao_Paulo"
    try:
        tz = ZoneInfo(tzname)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("America/Sao_Paulo")
    now = moment.astimezone(tz) if moment is not None else datetime.now(tz)
    today = now.date()

    if usar_feriados_nacionais and is_feriado_nacional_br(today):
        return False

    hs = horario_semana_from_json(horario_semana_json)
    if hs:
        keys = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
        k = keys[now.weekday()]
        cfg = hs.get(k) if isinstance(hs, dict) else None
        if isinstance(cfg, dict):
            if not bool(cfg.get("ativo", True)):
                return False
            ini = parse_hhmm(cfg.get("inicio"))
            fim = parse_hhmm(cfg.get("fim"))
            if not ini or not fim:
                return True
            m = now.hour * 60 + now.minute
            a = ini[0] * 60 + ini[1]
            b = fim[0] * 60 + fim[1]
            if a == b:
                return True
            if a < b:
                return a <= m < b
            return m >= a or m < b

    ini = parse_hhmm(horario_inicio)
    fim = parse_hhmm(horario_fim)
    if not ini or not fim:
        return True
    m = now.hour * 60 + now.minute
    a = ini[0] * 60 + ini[1]
    b = fim[0] * 60 + fim[1]
    if a == b:
        return True
    if a < b:
        return a <= m < b
    return m >= a or m < b
