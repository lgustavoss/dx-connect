"""Filtros compartilhados entre dashboard e relatórios de tickets."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.setor_scope import ids_setores_visiveis_atendente
from app.core.ticket_prioridade import PrioridadeTicket
from app.models import Ticket
from app.models.atendente import Atendente

DEFAULT_PERIOD_DAYS = 30
MAX_PERIOD_DAYS = 366

# Presets de calendário (#599). Semana = segunda → domingo (ISO weekday).
PRESET_HOJE = "hoje"
PRESET_ESTA_SEMANA = "esta_semana"
PRESET_ESTE_MES = "este_mes"
PRESET_MES_PASSADO = "mes_passado"


def period_bounds(de: date, ate: date) -> tuple[datetime, datetime]:
    de_dt = datetime.combine(de, time.min, tzinfo=timezone.utc)
    ate_dt = datetime.combine(ate + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return de_dt, ate_dt


def resolve_period(de: date | None, ate: date | None) -> tuple[date, date]:
    fim = ate or date.today()
    inicio = de or (fim - timedelta(days=DEFAULT_PERIOD_DAYS))
    if inicio > fim:
        inicio, fim = fim, inicio
    if (fim - inicio).days > MAX_PERIOD_DAYS:
        inicio = fim - timedelta(days=MAX_PERIOD_DAYS)
    return inicio, fim


def bounds_hoje(ref: date | None = None) -> tuple[date, date]:
    d = ref or date.today()
    return d, d


def bounds_esta_semana(ref: date | None = None) -> tuple[date, date]:
    """Segunda → domingo; se a semana ainda não acabou, o fim é `ref` (hoje)."""
    d = ref or date.today()
    inicio = d - timedelta(days=d.weekday())
    fim_semana = inicio + timedelta(days=6)
    fim = min(fim_semana, d)
    return inicio, fim


def bounds_este_mes(ref: date | None = None) -> tuple[date, date]:
    d = ref or date.today()
    return d.replace(day=1), d


def bounds_mes_passado(ref: date | None = None) -> tuple[date, date]:
    d = ref or date.today()
    primeiro_este = d.replace(day=1)
    ultimo_passado = primeiro_este - timedelta(days=1)
    return ultimo_passado.replace(day=1), ultimo_passado


def bounds_for_preset(preset: str, ref: date | None = None) -> tuple[date, date]:
    """Calcula `de`/`ate` para presets de calendário (#599)."""
    key = (preset or "").strip().lower()
    if key == PRESET_HOJE:
        return bounds_hoje(ref)
    if key == PRESET_ESTA_SEMANA:
        return bounds_esta_semana(ref)
    if key == PRESET_ESTE_MES:
        return bounds_este_mes(ref)
    if key == PRESET_MES_PASSADO:
        return bounds_mes_passado(ref)
    raise ValueError(f"preset de período inválido: {preset}")


def period_days_inclusive(de: date, ate: date) -> int:
    return (ate - de).days + 1


def normalizar_prioridade(prioridade: str | None) -> str | None:
    if prioridade is None or prioridade == "":
        return None
    valor = prioridade.strip().lower()
    if valor not in {p.value for p in PrioridadeTicket}:
        raise ValueError(f"prioridade inválida: {prioridade}")
    return valor


def apply_ticket_dashboard_filters(
    stmt,
    db: Session,
    atendente: Atendente,
    *,
    rede_id: int | None = None,
    setor_id: int | None = None,
    prioridade: str | None = None,
    atendente_id: int | None = None,
):
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(Ticket.setor_id.in_(vis))
    if rede_id is not None:
        stmt = stmt.where(Ticket.rede_id == rede_id)
    if setor_id is not None:
        if atendente.role != "admin":
            vis = ids_setores_visiveis_atendente(db, atendente)
            if setor_id not in vis:
                return stmt.where(Ticket.id == -1)
        stmt = stmt.where(Ticket.setor_id == setor_id)
    if prioridade is not None:
        stmt = stmt.where(Ticket.prioridade == prioridade)
    if atendente_id is not None:
        stmt = stmt.where(Ticket.atendente_id == atendente_id)
    return stmt


def apply_ticket_drill_to_stmt(stmt, drill, *, canal_expr=None, exclude: str | None = None):
    from app.services.dashboard_drilldown import TicketDrillDown, apply_ticket_drill_down

    active = drill.without(exclude) if isinstance(drill, TicketDrillDown) and exclude else drill
    return apply_ticket_drill_down(stmt, active, canal_expr=canal_expr)
