"""Calendário comercial compartilhado (feriados BR + helpers de horário)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEKDAY_KEYS = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")


@dataclass(frozen=True)
class CalendarConfig:
    timezone_name: str = "America/Sao_Paulo"
    horario_inicio: str | None = None
    horario_fim: str | None = None
    horario_semana_json: str | None = None
    usar_feriados_nacionais: bool = False


def calendar_config_from_model(cal) -> CalendarConfig:
    return CalendarConfig(
        timezone_name=cal.horario_timezone or "America/Sao_Paulo",
        horario_inicio=cal.horario_inicio,
        horario_fim=cal.horario_fim,
        horario_semana_json=cal.horario_semana_json,
        usar_feriados_nacionais=bool(cal.usar_feriados_nacionais),
    )


def resolve_timezone(config: CalendarConfig) -> ZoneInfo:
    tzname = (config.timezone_name or "America/Sao_Paulo").strip() or "America/Sao_Paulo"
    try:
        return ZoneInfo(tzname)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Sao_Paulo")


def ensure_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


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


def _day_schedule_for_date(d: date, config: CalendarConfig) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """Retorna (inicio, fim) em minutos desde meia-noite ou (None, None) se dia fechado."""
    if config.usar_feriados_nacionais and is_feriado_nacional_br(d):
        return None, None

    hs = horario_semana_from_json(config.horario_semana_json)
    if hs:
        k = WEEKDAY_KEYS[d.weekday()]
        cfg = hs.get(k) if isinstance(hs, dict) else None
        if isinstance(cfg, dict) and not bool(cfg.get("ativo", True)):
            return None, None
        ini = parse_hhmm(cfg.get("inicio") if isinstance(cfg, dict) else None)
        fim = parse_hhmm(cfg.get("fim") if isinstance(cfg, dict) else None)
        if ini is None:
            ini = parse_hhmm(config.horario_inicio)
        if fim is None:
            fim = parse_hhmm(config.horario_fim)
    else:
        ini = parse_hhmm(config.horario_inicio)
        fim = parse_hhmm(config.horario_fim)

    if not ini or not fim:
        return (0, 0), (23, 59)
    return ini, fim


def day_business_window(d: date, config: CalendarConfig, tz: ZoneInfo) -> tuple[datetime, datetime] | None:
    ini, fim = _day_schedule_for_date(d, config)
    if ini is None or fim is None:
        return None
    start = datetime.combine(d, time(ini[0], ini[1]), tzinfo=tz)
    end = datetime.combine(d, time(fim[0], fim[1]), tzinfo=tz)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def _start_of_next_business_moment(moment: datetime, config: CalendarConfig) -> datetime:
    tz = resolve_timezone(config)
    cur = moment.astimezone(tz)
    for _ in range(370):
        window = day_business_window(cur.date(), config, tz)
        if window is None:
            cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
            continue
        day_open, day_close = window
        if cur < day_open:
            return day_open
        if cur < day_close:
            return cur
        cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
    return moment


def add_business_minutes(start: datetime, minutes: int, config: CalendarConfig) -> datetime:
    if minutes <= 0:
        return ensure_utc(start)
    tz = resolve_timezone(config)
    cur = _start_of_next_business_moment(ensure_utc(start), config)
    remaining = minutes
    for _ in range(60 * 24 * 400):
        window = day_business_window(cur.date(), config, tz)
        if window is None:
            cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
            continue
        day_open, day_close = window
        if cur < day_open:
            cur = day_open
        if cur >= day_close:
            cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
            continue
        avail = max(0, int((day_close - cur).total_seconds() // 60))
        if avail == 0:
            cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
            continue
        take = min(remaining, avail)
        cur += timedelta(minutes=take)
        remaining -= take
        if remaining <= 0:
            return ensure_utc(cur)
    return ensure_utc(cur)


def business_minutes_between(start: datetime, end: datetime, config: CalendarConfig) -> int:
    start_u = ensure_utc(start)
    end_u = ensure_utc(end)
    if end_u <= start_u:
        return 0
    tz = resolve_timezone(config)
    cur = _start_of_next_business_moment(start_u, config)
    total = 0
    for _ in range(60 * 24 * 400):
        if cur >= end_u.astimezone(tz):
            break
        window = day_business_window(cur.date(), config, tz)
        if window is None:
            cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
            continue
        day_open, day_close = window
        if cur < day_open:
            cur = day_open
        segment_end = min(day_close, end_u.astimezone(tz))
        if segment_end <= cur:
            cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
            continue
        total += max(0, int((segment_end - cur).total_seconds() // 60))
        cur = day_close
        if cur >= end_u.astimezone(tz):
            break
        cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
    return total
