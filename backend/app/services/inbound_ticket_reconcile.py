"""Reconcilia tickets inbound após cadastro do remetente (#388)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.email_inbound_received import EmailInboundReceived
from app.models.ticket import Ticket
from app.services.funcionario_rede_resolver import RemetenteFuncionarioResolve, resolver_remetente_por_email
from app.services.ticket_client_email import extrair_email_de_from_address


def aplicar_reconciliacao_remetente(
    db: Session,
    ticket: Ticket,
    rem: RemetenteFuncionarioResolve,
) -> bool:
    if rem.requer_cadastro or rem.funcionario_id is None:
        return False
    changed = False
    if ticket.aberto_por_id is None:
        ticket.aberto_por_id = rem.funcionario_id
        changed = True
    if rem.rede_id is not None and ticket.rede_id is None:
        ticket.rede_id = rem.rede_id
        changed = True
    if rem.empresa_id is not None and ticket.empresa_id is None:
        ticket.empresa_id = rem.empresa_id
        changed = True
    return changed


def reconciliar_tickets_pendentes_por_email(db: Session, email_raw: str | None) -> int:
    email = (email_raw or "").strip().lower()
    if not email:
        return 0
    rem = resolver_remetente_por_email(db, email)
    if rem.requer_cadastro:
        return 0

    rows = (
        db.query(EmailInboundReceived)
        .join(Ticket, Ticket.id == EmailInboundReceived.ticket_id)
        .filter(Ticket.empresa_id.is_(None))
        .all()
    )
    alterados = 0
    vistos: set[int] = set()
    for row in rows:
        row_email = extrair_email_de_from_address(row.from_address)
        if row_email != email:
            continue
        ticket = row.ticket
        if ticket.id in vistos:
            continue
        vistos.add(ticket.id)
        if aplicar_reconciliacao_remetente(db, ticket, rem):
            alterados += 1
    if alterados:
        db.flush()
    return alterados
