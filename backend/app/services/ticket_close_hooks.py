"""Hooks executados quando um ticket é fechado (CSAT, webhook externo, …)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.ticket_closed_webhook import enfileirar_webhook_ticket_fechado
from app.services.ticket_csat import processar_convite_csat_ao_fechar


def processar_hooks_ao_fechar_ticket(db: Session, ticket_id: int) -> None:
    processar_convite_csat_ao_fechar(db, ticket_id)
    enfileirar_webhook_ticket_fechado(db, ticket_id)
