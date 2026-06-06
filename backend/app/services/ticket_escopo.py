"""Escopo de ticket: empresa, coordenação de rede ou triagem (sem empresa/rede)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.ticket import Ticket


def validar_escopo_criacao_manual(
    *,
    empresa_id: int | None,
    rede_id: int | None,
    parent_ticket_id: int | None,
) -> str:
    """Retorna 'empresa' ou 'coordenacao'. Levanta ValueError se inválido."""
    if empresa_id is not None and rede_id is not None:
        raise ValueError("Informe a empresa ou a rede (coordenação), não ambos.")
    if empresa_id is None and rede_id is None:
        raise ValueError("Informe a empresa ou a rede (ticket de coordenação).")
    if parent_ticket_id is not None and empresa_id is None:
        raise ValueError("Ticket filho exige empresa vinculada.")
    if empresa_id is not None:
        return "empresa"
    return "coordenacao"


def rede_id_de_empresa(db: Session, empresa_id: int, *, tenant_id: int) -> int | None:
    return (
        db.query(Empresa.rede_id)
        .filter(Empresa.id == empresa_id, Empresa.tenant_id == tenant_id)
        .scalar()
    )


def rede_id_efetivo_ticket(db: Session, ticket: Ticket) -> int | None:
    if ticket.rede_id is not None:
        return ticket.rede_id
    if ticket.empresa is not None and ticket.empresa.rede_id is not None:
        return ticket.empresa.rede_id
    if ticket.empresa_id is None:
        return None
    return rede_id_de_empresa(db, ticket.empresa_id, tenant_id=ticket.tenant_id)


def ticket_e_coordenacao_rede(ticket: Ticket) -> bool:
    return ticket.empresa_id is None and ticket.rede_id is not None
