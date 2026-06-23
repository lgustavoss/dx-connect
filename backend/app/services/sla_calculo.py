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
from app.models.ticket import Ticket, TicketMensagem
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


def avaliar_meta(
    *,
    inicio: datetime,
    vence_em: datetime | None,
    cumprido_em: datetime | None,
    meta_min: int | None,
    now: datetime,
    calendar: CalendarConfig | None,
) -> tuple[SlaMetaEstado, float | None]:
    if not meta_min or meta_min <= 0 or not vence_em:
        return SlaMetaEstado.sem_meta, None

    vence_u = ensure_utc(vence_em)
    now_u = ensure_utc(now)

    if cumprido_em is not None:
        cumprido_u = ensure_utc(cumprido_em)
        if cumprido_u <= vence_u:
            return SlaMetaEstado.cumprido, 100.0
        return SlaMetaEstado.violado, 100.0

    if now_u > vence_u:
        return SlaMetaEstado.violado, 100.0

    decorridos = elapsed_minutes(inicio, now_u, calendar)
    pct = min(99.9, (decorridos / meta_min) * 100) if meta_min > 0 else 0.0
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

    estado_primeira, pct_primeira = avaliar_meta(
        inicio=inicio,
        vence_em=ticket.sla_primeira_resposta_vence_em,
        cumprido_em=ticket.sla_primeira_resposta_em,
        meta_min=ticket.sla_meta_primeira_resposta_min,
        now=now_u,
        calendar=calendar,
    )
    estado_resolucao, pct_resolucao = avaliar_meta(
        inicio=inicio,
        vence_em=ticket.sla_resolucao_vence_em,
        cumprido_em=ticket.fechado_em,
        meta_min=ticket.sla_meta_resolucao_min,
        now=now_u,
        calendar=calendar,
    )

    return {
        "ticket_id": ticket.id,
        "sla_policy_id": ticket.sla_policy_id,
        "sla_violado": bool(ticket.sla_violado),
        "inicio_em": inicio,
        "usa_horario_comercial": calendar is not None,
        "primeira_resposta": {
            "meta_minutos": ticket.sla_meta_primeira_resposta_min,
            "vence_em": ticket.sla_primeira_resposta_vence_em,
            "cumprido_em": ticket.sla_primeira_resposta_em,
            "estado": estado_primeira.value,
            "percentual_decorrido": pct_primeira,
        },
        "resolucao": {
            "meta_minutos": ticket.sla_meta_resolucao_min,
            "vence_em": ticket.sla_resolucao_vence_em,
            "cumprido_em": ticket.fechado_em,
            "estado": estado_resolucao.value,
            "percentual_decorrido": pct_resolucao,
        },
    }


def sla_estado_resumido(
    ticket: Ticket,
    *,
    now: datetime | None = None,
    calendar: CalendarConfig | None = None,
) -> str | None:
    """Pior estado SLA entre primeira resposta e resolução (para listagem, sem query extra)."""
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


def filtro_sql_sla_em_risco():
    """Expressão SQL para tickets com alguma meta em risco (aprox. relógio contínuo)."""
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
