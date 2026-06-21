"""Filtros compartilhados do dashboard analítico de chats WhatsApp."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.setor_scope import ids_setores_visiveis_atendente
from app.models.atendente import Atendente
from app.models.whatsapp_chat import WhatsappChat

from app.services.ticket_dashboard_filters import (
    DEFAULT_PERIOD_DAYS,
    MAX_PERIOD_DAYS,
    period_bounds,
    resolve_period,
)

__all__ = [
    "DEFAULT_PERIOD_DAYS",
    "MAX_PERIOD_DAYS",
    "apply_chat_dashboard_filters",
    "period_bounds",
    "resolve_period",
]


def apply_chat_dashboard_filters(
    stmt,
    db: Session,
    atendente: Atendente,
    *,
    setor_id: int | None = None,
    atendente_id: int | None = None,
):
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(or_(WhatsappChat.setor_id.is_(None), WhatsappChat.setor_id.in_(vis)))
    if setor_id is not None:
        if atendente.role != "admin":
            vis = ids_setores_visiveis_atendente(db, atendente)
            if setor_id not in vis:
                return stmt.where(WhatsappChat.id == -1)
        stmt = stmt.where(WhatsappChat.setor_id == setor_id)
    if atendente_id is not None:
        stmt = stmt.where(WhatsappChat.atendente_id == atendente_id)
    return stmt


def apply_chat_drill_to_stmt(stmt, drill, *, exclude: str | None = None):
    from app.services.dashboard_drilldown import ChatDrillDown, apply_chat_drill_down

    active = drill.without(exclude) if isinstance(drill, ChatDrillDown) and exclude else drill
    return apply_chat_drill_down(stmt, active)
