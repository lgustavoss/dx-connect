"""Resolução de policy SLA e snapshot na criação do ticket (#277)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.ticket_prioridade import PrioridadeTicket
from app.models.business_calendar import BusinessCalendar
from app.models.sla_policy import SlaPolicy
from app.models.ticket import Ticket


def _prioridade_valor(prioridade) -> str:
    if isinstance(prioridade, PrioridadeTicket):
        return prioridade.value
    return str(prioridade or PrioridadeTicket.normal.value)


def resolve_sla_policy(
    db: Session,
    *,
    tenant_id: int,
    setor_id: int,
    prioridade,
) -> SlaPolicy | None:
    prio_val = _prioridade_valor(prioridade)
    base_q = db.query(SlaPolicy).filter(
        SlaPolicy.tenant_id == tenant_id,
        SlaPolicy.setor_id == setor_id,
        SlaPolicy.ativo.is_(True),
    )
    specific = base_q.filter(SlaPolicy.prioridade == prio_val).first()
    if specific:
        return specific
    return base_q.filter(SlaPolicy.prioridade.is_(None)).first()


def _deadline_wall_clock(base: datetime, minutes: int) -> datetime:
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base + timedelta(minutes=minutes)


def aplicar_sla_snapshot_ao_ticket(
    db: Session,
    ticket: Ticket,
    *,
    base_time: datetime | None = None,
) -> SlaPolicy | None:
    """Grava metas e prazos iniciais no ticket (relógio corrido em S-01; calendário em S-02)."""
    prioridade = ticket.prioridade
    if prioridade is None:
        prioridade = PrioridadeTicket.normal
    policy = resolve_sla_policy(
        db,
        tenant_id=ticket.tenant_id,
        setor_id=ticket.setor_id,
        prioridade=prioridade,
    )
    if not policy:
        return None

    base = base_time or ticket.created_at or datetime.now(timezone.utc)

    ticket.sla_policy_id = policy.id
    ticket.sla_meta_primeira_resposta_min = policy.meta_primeira_resposta_min
    ticket.sla_meta_resolucao_min = policy.meta_resolucao_min
    ticket.sla_violado = False

    if policy.meta_primeira_resposta_min and policy.meta_primeira_resposta_min > 0:
        ticket.sla_primeira_resposta_vence_em = _deadline_wall_clock(
            base, policy.meta_primeira_resposta_min
        )
    else:
        ticket.sla_primeira_resposta_vence_em = None

    if policy.meta_resolucao_min and policy.meta_resolucao_min > 0:
        ticket.sla_resolucao_vence_em = _deadline_wall_clock(base, policy.meta_resolucao_min)
    else:
        ticket.sla_resolucao_vence_em = None

    return policy


def validar_metas_sla(
    *,
    meta_primeira_resposta_min: int | None,
    meta_resolucao_min: int | None,
) -> None:
    primeira = meta_primeira_resposta_min
    resolucao = meta_resolucao_min
    if primeira is None and resolucao is None:
        raise ValueError("Informe ao menos uma meta (primeira resposta ou resolução).")
    for label, valor in (
        ("meta_primeira_resposta_min", primeira),
        ("meta_resolucao_min", resolucao),
    ):
        if valor is None:
            continue
        if valor <= 0:
            raise ValueError(f"{label} deve ser maior que zero.")


def carregar_calendario_policy(db: Session, policy: SlaPolicy) -> BusinessCalendar | None:
    if not policy.business_calendar_id:
        return None
    return (
        db.query(BusinessCalendar)
        .filter(
            BusinessCalendar.id == policy.business_calendar_id,
            BusinessCalendar.tenant_id == policy.tenant_id,
            BusinessCalendar.ativo.is_(True),
        )
        .first()
    )
