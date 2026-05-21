"""
Índice global Message-ID → ticket (threading e-mail ↔ ticket, #165).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ticket_email_message_id import TicketEmailMessageId
from app.services.email_inbound_parse import normalize_message_id


def registar_message_id_para_ticket(
    db: Session,
    *,
    ticket_id: int,
    message_id: str | None,
    source: str,
) -> bool:
    """
    Regista um Message-ID no índice do ticket (idempotente por ``message_id`` global).

    Devolve ``True`` se criou um registo novo; ``False`` se o ID era inválido ou já existia.
    """
    mid = normalize_message_id(message_id)
    if not mid:
        s = (message_id or "").strip().strip("<>")
        mid = s[:998] if s else ""
    if not mid:
        return False
    exists = db.query(TicketEmailMessageId.id).filter(TicketEmailMessageId.message_id_normalized == mid).first()
    if exists:
        return False
    db.add(TicketEmailMessageId(message_id_normalized=mid, ticket_id=ticket_id, source=source))
    return True
