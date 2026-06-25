"""Motor de cálculo SLA: estados, violações e primeira resposta (#278)."""

from __future__ import annotations

import enum
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.business_calendar import (
    CalendarConfig,
    add_business_minutes,
    business_minutes_between,
    calendar_config_from_model,
    ensure_utc,
)
from app.models.sla_policy import SlaPolicy
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket, TicketHistorico, TicketMensagem
from app.services.sla_policy import carregar_calendario_policy

logger = logging.getLogger(__name__)

SLA_RISCO_PERCENT = 80


class SlaMetaEstado(str, enum.Enum):
    sem_meta = "sem_meta"
    dentro = "dentro"
    em_risco = "em_risco"
    violado = "violado"
    cumprido = "cumprido"


def calendar_config_para_ticket(db: Session, ticket: Ticket) -> CalendarConfig | None:
    if not ticket.sla_policy_id:
        return None
    policy = db.query(SlaPolicy).filter(SlaPolicy.id == ticket.sla_policy_id).first()
    if not policy:
        return None
    cal = carregar_calendario_policy(db, policy)
    if not cal:
        return None
    return calendar_config_from_model(cal)


def compute_deadline(
    base: datetime,
    minutes: int,
    calendar: CalendarConfig | None,
) -> datetime:
    base_u = ensure_utc(base)
    if calendar is None:
        from datetime import timedelta

        return base_u + timedelta(minutes=minutes)
    return add_business_minutes(base_u, minutes, calendar)


def elapsed_minutes(
    inicio: datetime,
    fim: datetime,
    calendar: CalendarConfig | None,
) -> int:
    if calendar is None:
        return max(0, int((ensure_utc(fim) - ensure_utc(inicio)).total_seconds() // 60))
    return business_minutes_between(inicio, fim, calendar)


def _parse_status_id(valor: str | None) -> int | None:
    if valor is None or valor == "":
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _timeline_status_segments(
    ticket: Ticket,
    historico: list[TicketHistorico],
    ate: datetime,
) -> list[tuple[int | None, datetime, datetime]]:
    """Intervalos (status_id, início, fim) cobrindo a vida do ticket até ``ate``."""
    inicio = ensure_utc(ticket.created_at or ate)
    ate_u = ensure_utc(ate)
    if ate_u < inicio:
        ate_u = inicio

    if not historico:
        return [(ticket.status_id, inicio, ate_u)]

    cur_status = _parse_status_id(historico[0].valor_antigo) or ticket.status_id
    cur_inicio = inicio
    segments: list[tuple[int | None, datetime, datetime]] = []

    for h in historico:
        h_at = ensure_utc(h.created_at or ate_u)
        if h_at <= cur_inicio:
            novo = _parse_status_id(h.valor_novo)
            if novo is not None:
                cur_status = novo
            continue
        segments.append((cur_status, cur_inicio, min(h_at, ate_u)))
        cur_inicio = h_at
        novo = _parse_status_id(h.valor_novo)
        if novo is not None:
            cur_status = novo

    if cur_inicio < ate_u:
        segments.append((cur_status, cur_inicio, ate_u))
    return segments


def _status_ids_com_pausa_sla(db: Session, status_ids: set[int]) -> set[int]:
    if not status_ids:
        return set()
    rows = (
        db.query(StatusTicket.id)
        .filter(StatusTicket.id.in_(status_ids), StatusTicket.pausa_sla.is_(True))
        .all()
    )
    return {int(r[0]) for r in rows}


def minutos_pausa_sla(
    db: Session,
    ticket: Ticket,
    *,
    ate: datetime,
    calendar: CalendarConfig | None,
    historico: list[TicketHistorico] | None = None,
    pausa_status_ids: set[int] | None = None,
) -> int:
    """Minutos em que o relógio SLA ficou pausado (status com ``pausa_sla``)."""
    if historico is None:
        historico = (
            db.query(TicketHistorico)
            .filter(TicketHistorico.ticket_id == ticket.id, TicketHistorico.campo == "status_id")
            .order_by(TicketHistorico.created_at.asc(), TicketHistorico.id.asc())
            .all()
        )
    segments = _timeline_status_segments(ticket, historico, ate)
    status_ids = {sid for sid, _, _ in segments if sid is not None}
    if pausa_status_ids is None:
        pausa_status_ids = _status_ids_com_pausa_sla(db, status_ids)
    if not pausa_status_ids:
        return 0
    total = 0
    for status_id, seg_inicio, seg_fim in segments:
        if status_id in pausa_status_ids and seg_fim > seg_inicio:
            total += elapsed_minutes(seg_inicio, seg_fim, calendar)
    return total


def status_atual_pausa_sla(db: Session, ticket: Ticket) -> bool:
    if not ticket.status_id:
        return False
    row = db.query(StatusTicket.pausa_sla).filter(StatusTicket.id == ticket.status_id).first()
    return bool(row and row[0])


def preload_minutos_pausa_sla(
    db: Session,
    tickets: list[Ticket],
    *,
    ate: datetime,
    cal_map: dict[int, CalendarConfig | None],
) -> dict[int, int]:
    if not tickets:
        return {}
    ticket_ids = [t.id for t in tickets]
    historicos = (
        db.query(TicketHistorico)
        .filter(TicketHistorico.ticket_id.in_(ticket_ids), TicketHistorico.campo == "status_id")
        .order_by(TicketHistorico.ticket_id.asc(), TicketHistorico.created_at.asc(), TicketHistorico.id.asc())
        .all()
    )
    hist_by_ticket: dict[int, list[TicketHistorico]] = {}
    status_ids: set[int] = set()
    for h in historicos:
        hist_by_ticket.setdefault(h.ticket_id, []).append(h)
        sid = _parse_status_id(h.valor_antigo)
        if sid is not None:
            status_ids.add(sid)
        sid = _parse_status_id(h.valor_novo)
        if sid is not None:
            status_ids.add(sid)
    for t in tickets:
        if t.status_id:
            status_ids.add(t.status_id)
    pausa_ids = _status_ids_com_pausa_sla(db, status_ids)
    if not pausa_ids:
        return {t.id: 0 for t in tickets}

    ate_u = ensure_utc(ate)
    out: dict[int, int] = {}
    for t in tickets:
        calendar = cal_map.get(t.sla_policy_id) if t.sla_policy_id else None
        out[t.id] = minutos_pausa_sla(
            db,
            t,
            ate=ate_u,
            calendar=calendar,
            historico=hist_by_ticket.get(t.id, []),
            pausa_status_ids=pausa_ids,
        )
    return out


def avaliar_meta(
    *,
    inicio: datetime,
    vence_em: datetime | None,
    cumprido_em: datetime | None,
    meta_min: int | None,
    now: datetime,
    calendar: CalendarConfig | None,
    minutos_pausados: int = 0,
) -> tuple[SlaMetaEstado, float | None]:
    if not meta_min or meta_min <= 0 or not vence_em:
        return SlaMetaEstado.sem_meta, None

    now_u = ensure_utc(now)

    if cumprido_em is not None:
        cumprido_u = ensure_utc(cumprido_em)
        decorridos = max(0, elapsed_minutes(inicio, cumprido_u, calendar) - minutos_pausados)
        pct = min(100.0, (decorridos / meta_min) * 100) if meta_min > 0 else 100.0
        if decorridos <= meta_min:
            return SlaMetaEstado.cumprido, pct
        return SlaMetaEstado.violado, pct

    decorridos = max(0, elapsed_minutes(inicio, now_u, calendar) - minutos_pausados)
    pct = min(99.9, (decorridos / meta_min) * 100) if meta_min > 0 else 0.0
    if decorridos >= meta_min:
        return SlaMetaEstado.violado, 100.0
    if pct >= SLA_RISCO_PERCENT:
        return SlaMetaEstado.em_risco, pct
    return SlaMetaEstado.dentro, pct


def mensagem_conta_primeira_resposta(mensagem: TicketMensagem) -> bool:
    return mensagem.atendente_id is not None and mensagem.tipo in ("publico", "abertura")


def registrar_primeira_resposta_se_necessario(
    db: Session,
    ticket: Ticket,
    momento: datetime | None = None,
) -> bool:
    if ticket.sla_primeira_resposta_em is not None:
        return False
    if not ticket.sla_meta_primeira_resposta_min:
        return False
    ticket.sla_primeira_resposta_em = ensure_utc(momento or datetime.now(timezone.utc))
    sincronizar_sla_violado(db, ticket)
    return True


def build_ticket_sla_read(db: Session, ticket: Ticket, *, now: datetime | None = None) -> dict:
    now_u = ensure_utc(now or datetime.now(timezone.utc))
    inicio = ensure_utc(ticket.created_at or now_u)
    calendar = calendar_config_para_ticket(db, ticket)
    pausado_agora = status_atual_pausa_sla(db, ticket)
    minutos_pausados = minutos_pausa_sla(db, ticket, ate=now_u, calendar=calendar)
    pausa_primeira = (
        minutos_pausa_sla(db, ticket, ate=ticket.sla_primeira_resposta_em, calendar=calendar)
        if ticket.sla_primeira_resposta_em
        else minutos_pausados
    )
    pausa_resolucao = (
        minutos_pausa_sla(db, ticket, ate=ticket.fechado_em, calendar=calendar)
        if ticket.fechado_em
        else minutos_pausados
    )

    estado_primeira, pct_primeira = avaliar_meta(
        inicio=inicio,
        vence_em=ticket.sla_primeira_resposta_vence_em,
        cumprido_em=ticket.sla_primeira_resposta_em,
        meta_min=ticket.sla_meta_primeira_resposta_min,
        now=now_u,
        calendar=calendar,
        minutos_pausados=pausa_primeira,
    )
    estado_resolucao, pct_resolucao = avaliar_meta(
        inicio=inicio,
        vence_em=ticket.sla_resolucao_vence_em,
        cumprido_em=ticket.fechado_em,
        meta_min=ticket.sla_meta_resolucao_min,
        now=now_u,
        calendar=calendar,
        minutos_pausados=pausa_resolucao,
    )

    def _meta_block(
        *,
        meta_min: int | None,
        vence_em: datetime | None,
        cumprido_em: datetime | None,
        pausa_min: int,
        estado: SlaMetaEstado,
        pct: float | None,
    ) -> dict:
        vence_efetivo = None
        if meta_min and meta_min > 0 and cumprido_em is None:
            vence_efetivo = compute_deadline(inicio, meta_min + pausa_min, calendar)
        return {
            "meta_minutos": meta_min,
            "vence_em": vence_em,
            "vence_em_efetivo": vence_efetivo,
            "cumprido_em": cumprido_em,
            "estado": estado.value,
            "percentual_decorrido": pct,
        }

    return {
        "ticket_id": ticket.id,
        "sla_policy_id": ticket.sla_policy_id,
        "sla_violado": bool(ticket.sla_violado),
        "inicio_em": inicio,
        "usa_horario_comercial": calendar is not None,
        "pausado_agora": pausado_agora,
        "minutos_pausados": minutos_pausados,
        "primeira_resposta": _meta_block(
            meta_min=ticket.sla_meta_primeira_resposta_min,
            vence_em=ticket.sla_primeira_resposta_vence_em,
            cumprido_em=ticket.sla_primeira_resposta_em,
            pausa_min=pausa_primeira,
            estado=estado_primeira,
            pct=pct_primeira,
        ),
        "resolucao": _meta_block(
            meta_min=ticket.sla_meta_resolucao_min,
            vence_em=ticket.sla_resolucao_vence_em,
            cumprido_em=ticket.fechado_em,
            pausa_min=pausa_resolucao,
            estado=estado_resolucao,
            pct=pct_resolucao,
        ),
    }


def sla_estado_resumido(
    ticket: Ticket,
    *,
    now: datetime | None = None,
    calendar: CalendarConfig | None = None,
    minutos_pausados: int = 0,
) -> str | None:
    """Pior estado SLA entre primeira resposta e resolução (para listagem)."""
    if not ticket.sla_policy_id:
        return None
    now_u = ensure_utc(now or datetime.now(timezone.utc))
    inicio = ensure_utc(ticket.created_at or now_u)
    estados: list[SlaMetaEstado] = []
    if ticket.sla_meta_primeira_resposta_min:
        estado, _ = avaliar_meta(
            inicio=inicio,
            vence_em=ticket.sla_primeira_resposta_vence_em,
            cumprido_em=ticket.sla_primeira_resposta_em,
            meta_min=ticket.sla_meta_primeira_resposta_min,
            now=now_u,
            calendar=calendar,
            minutos_pausados=minutos_pausados,
        )
        estados.append(estado)
    if ticket.sla_meta_resolucao_min:
        estado, _ = avaliar_meta(
            inicio=inicio,
            vence_em=ticket.sla_resolucao_vence_em,
            cumprido_em=ticket.fechado_em,
            meta_min=ticket.sla_meta_resolucao_min,
            now=now_u,
            calendar=calendar,
            minutos_pausados=minutos_pausados,
        )
        estados.append(estado)
    if not estados:
        return None
    prioridade = {
        SlaMetaEstado.violado: 5,
        SlaMetaEstado.em_risco: 4,
        SlaMetaEstado.dentro: 3,
        SlaMetaEstado.cumprido: 2,
        SlaMetaEstado.sem_meta: 1,
    }
    pior = max(estados, key=lambda e: prioridade.get(e, 0))
    if pior in (SlaMetaEstado.sem_meta, SlaMetaEstado.cumprido) and ticket.fechado_em is not None:
        return pior.value
    if pior == SlaMetaEstado.sem_meta:
        return None
    if ticket.fechado_em is not None and pior == SlaMetaEstado.cumprido:
        return "cumprido"
    if ticket.fechado_em is not None and pior == SlaMetaEstado.violado:
        return "violado"
    if ticket.fechado_em is not None:
        return None
    return pior.value


def preload_sla_calendars(db: Session, tickets: list[Ticket]) -> dict[int, CalendarConfig | None]:
    """Mapa sla_policy_id → calendário (uma query por lote, evita N+1 na listagem)."""
    policy_ids = {t.sla_policy_id for t in tickets if t.sla_policy_id}
    if not policy_ids:
        return {}
    policies = db.query(SlaPolicy).filter(SlaPolicy.id.in_(policy_ids)).all()
    cal_ids = {p.business_calendar_id for p in policies if p.business_calendar_id}
    cal_by_id: dict[int, CalendarConfig] = {}
    if cal_ids:
        from app.models.business_calendar import BusinessCalendar

        for row in db.query(BusinessCalendar).filter(BusinessCalendar.id.in_(cal_ids)).all():
            cfg = calendar_config_from_model(row)
            if cfg:
                cal_by_id[row.id] = cfg
    out: dict[int, CalendarConfig | None] = {}
    for p in policies:
        out[p.id] = cal_by_id.get(p.business_calendar_id) if p.business_calendar_id else None
    return out


def selecionar_tickets_sla_em_risco(
    db: Session,
    tickets: list[Ticket],
    *,
    now: datetime | None = None,
) -> list[Ticket]:
    """Filtra tickets cujo pior estado SLA é ``em_risco`` (motor completo: calendário + pausa)."""
    if not tickets:
        return []
    now_u = ensure_utc(now or datetime.now(timezone.utc))
    cal_map = preload_sla_calendars(db, tickets)
    pausa_map = preload_minutos_pausa_sla(db, tickets, ate=now_u, cal_map=cal_map)
    em_risco: list[Ticket] = []
    for ticket in tickets:
        if not ticket.sla_policy_id or ticket.sla_violado or ticket.fechado_em is not None:
            continue
        estado = sla_estado_resumido(
            ticket,
            now=now_u,
            calendar=cal_map.get(ticket.sla_policy_id),
            minutos_pausados=pausa_map.get(ticket.id, 0),
        )
        if estado == "em_risco":
            em_risco.append(ticket)
    return em_risco


def contar_tickets_sla_em_risco(db: Session, atendente) -> int:
    from app.core.setor_scope import ids_setores_visiveis_atendente

    q = db.query(Ticket).filter(
        Ticket.fechado_em.is_(None),
        Ticket.sla_policy_id.isnot(None),
        Ticket.sla_violado.is_(False),
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter(Ticket.setor_id.in_(vis))
    return len(selecionar_tickets_sla_em_risco(db, q.all()))


def filtro_sql_sla_em_risco():
    """Pré-filtro SQL rápido (24×7). Preferir ``selecionar_tickets_sla_em_risco`` para precisão."""
    from sqlalchemy import and_, func, or_

    elapsed_min = (func.extract("epoch", func.now()) - func.extract("epoch", Ticket.created_at)) / 60.0
    primeira = and_(
        Ticket.sla_primeira_resposta_em.is_(None),
        Ticket.sla_meta_primeira_resposta_min.isnot(None),
        Ticket.sla_meta_primeira_resposta_min > 0,
        Ticket.sla_primeira_resposta_vence_em.isnot(None),
        Ticket.sla_primeira_resposta_vence_em > func.now(),
        elapsed_min >= Ticket.sla_meta_primeira_resposta_min * (SLA_RISCO_PERCENT / 100.0),
    )
    resolucao = and_(
        Ticket.fechado_em.is_(None),
        Ticket.sla_meta_resolucao_min.isnot(None),
        Ticket.sla_meta_resolucao_min > 0,
        Ticket.sla_resolucao_vence_em.isnot(None),
        Ticket.sla_resolucao_vence_em > func.now(),
        elapsed_min >= Ticket.sla_meta_resolucao_min * (SLA_RISCO_PERCENT / 100.0),
    )
    return and_(
        Ticket.sla_policy_id.isnot(None),
        Ticket.sla_violado.is_(False),
        Ticket.fechado_em.is_(None),
        or_(primeira, resolucao),
    )


def sincronizar_sla_violado(db: Session, ticket: Ticket, *, now: datetime | None = None) -> None:
    dados = build_ticket_sla_read(db, ticket, now=now)
    violado = (
        dados["primeira_resposta"]["estado"] == SlaMetaEstado.violado.value
        or dados["resolucao"]["estado"] == SlaMetaEstado.violado.value
    )
    ticket.sla_violado = violado


def processar_sla_tickets_abertos(db: Session, *, limit: int = 200) -> int:
    """Worker periódico: atualiza flag ``sla_violado`` em tickets abertos com SLA."""
    now = datetime.now(timezone.utc)
    tickets = (
        db.query(Ticket)
        .filter(
            Ticket.fechado_em.is_(None),
            Ticket.sla_policy_id.isnot(None),
        )
        .order_by(Ticket.id.asc())
        .limit(limit)
        .all()
    )
    atualizados = 0
    for ticket in tickets:
        antes = bool(ticket.sla_violado)
        sincronizar_sla_violado(db, ticket, now=now)
        if bool(ticket.sla_violado) != antes:
            atualizados += 1
    return atualizados
