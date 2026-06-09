"""Regras de classificação (natureza/motivo) e prioridade de tickets."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.ticket_prioridade import PrioridadeTicket
from app.models.ticket import Ticket
from app.models.ticket_classificacao import TicketMotivo

MOTIVO_OUTROS_SLUG = "outros"


def normalizar_motivo_outro_texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    t = valor.strip()
    return t or None


def obter_motivo_ativo(db: Session, motivo_id: int) -> TicketMotivo | None:
    return (
        db.query(TicketMotivo)
        .options(joinedload(TicketMotivo.natureza))
        .filter(TicketMotivo.id == motivo_id)
        .first()
    )


def validar_classificacao(
    db: Session,
    *,
    motivo_id: int | None,
    motivo_outro_texto: str | None,
    obrigatorio: bool,
) -> tuple[int | None, str | None]:
    outro = normalizar_motivo_outro_texto(motivo_outro_texto)
    if motivo_id is None:
        if obrigatorio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe o motivo do atendimento para encerrar o ticket.",
            )
        if outro:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O texto complementar exige um motivo do tipo Outros.",
            )
        return None, None

    motivo = obter_motivo_ativo(db, motivo_id)
    if motivo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Motivo não encontrado.")
    if not motivo.ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Motivo inativo não pode ser selecionado.",
        )
    slug = (motivo.slug or "").lower()
    if slug == MOTIVO_OUTROS_SLUG:
        if not outro:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Descreva o atendimento quando o motivo for Outros.",
            )
    elif outro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Texto complementar só é permitido para o motivo Outros.",
        )
    return motivo_id, outro


def motivo_efetivo_no_ticket(ticket: Ticket, update: dict) -> tuple[int | None, str | None]:
    mid = update["motivo_id"] if "motivo_id" in update else ticket.motivo_id
    if "motivo_outro_texto" in update:
        outro = normalizar_motivo_outro_texto(update["motivo_outro_texto"])
    else:
        outro = normalizar_motivo_outro_texto(ticket.motivo_outro_texto)
    return mid, outro


def validar_prioridade(valor: str | PrioridadeTicket) -> PrioridadeTicket:
    if isinstance(valor, PrioridadeTicket):
        return valor
    try:
        return PrioridadeTicket(valor)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prioridade inválida. Use: baixa, normal, alta ou urgente.",
        ) from e
