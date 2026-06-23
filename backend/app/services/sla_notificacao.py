"""Alertas SLA in-app (SSE) e e-mail (#279)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.atendente import Atendente
from app.models.sla_alerta_emitido import SlaAlertaEmitido
from app.models.ticket import Ticket
from app.services.realtime_emit import emit_ticket_sla_alerta, ids_atendentes_sla_ticket
from app.services.sla_calculo import SlaMetaEstado, build_ticket_sla_read
from app.services.notificacao_atendente_email import notificar_sla_alerta_email

logger = logging.getLogger(__name__)

META_PRIMEIRA = "primeira_resposta"
META_RESOLUCAO = "resolucao"
EVENTO_EM_RISCO = "em_risco"
EVENTO_VIOLADO = "violado"

_META_LABELS = {
    META_PRIMEIRA: "Primeira resposta",
    META_RESOLUCAO: "Resolução",
}


def _ja_emitido(db: Session, *, ticket_id: int, meta: str, evento: str) -> bool:
    return (
        db.query(SlaAlertaEmitido.id)
        .filter(
            SlaAlertaEmitido.ticket_id == ticket_id,
            SlaAlertaEmitido.meta == meta,
            SlaAlertaEmitido.evento == evento,
        )
        .first()
        is not None
    )


def _marcar_emitido(db: Session, *, ticket_id: int, meta: str, evento: str) -> None:
    if _ja_emitido(db, ticket_id=ticket_id, meta=meta, evento=evento):
        return
    db.add(SlaAlertaEmitido(ticket_id=ticket_id, meta=meta, evento=evento))
    db.flush()


def _disparar_alerta(
    db: Session,
    *,
    ticket: Ticket,
    meta: str,
    evento: str,
) -> None:
    recipients = ids_atendentes_sla_ticket(db, ticket)
    if not recipients:
        return

    meta_label = _META_LABELS.get(meta, meta)
    evento_label = "em risco" if evento == EVENTO_EM_RISCO else "violado"

    for aid in recipients:
        atendente = db.query(Atendente).filter(Atendente.id == aid, Atendente.ativo.is_(True)).first()
        if not atendente:
            continue
        try:
            notificar_sla_alerta_email(
                db,
                atendente=atendente,
                ticket=ticket,
                meta=meta,
                evento=evento,
                meta_label=meta_label,
                evento_label=evento_label,
            )
        except Exception:
            logger.exception("Falha ao enfileirar e-mail SLA (ticket %s)", ticket.id)

    try:
        emit_ticket_sla_alerta(
            db,
            ticket,
            meta=meta,
            evento=evento,
            meta_label=meta_label,
            evento_label=evento_label,
            atendente_ids=recipients,
        )
    except Exception:
        logger.exception("Falha ao emitir SSE SLA (ticket %s)", ticket.id)

    _marcar_emitido(db, ticket_id=ticket.id, meta=meta, evento=evento)


def processar_alertas_sla(db: Session, *, limit: int = 200) -> int:
    """Avalia tickets abertos com SLA e dispara alertas ``em_risco`` / ``violado`` (uma vez cada)."""
    from datetime import datetime, timezone

    from app.services.sla_calculo import processar_sla_tickets_abertos

    processar_sla_tickets_abertos(db, limit=limit)

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
    disparados = 0
    for ticket in tickets:
        dados = build_ticket_sla_read(db, ticket, now=now)
        pares = (
            (META_PRIMEIRA, dados["primeira_resposta"]["estado"]),
            (META_RESOLUCAO, dados["resolucao"]["estado"]),
        )
        for meta, estado in pares:
            if estado == SlaMetaEstado.em_risco.value:
                if not _ja_emitido(db, ticket_id=ticket.id, meta=meta, evento=EVENTO_EM_RISCO):
                    _disparar_alerta(db, ticket=ticket, meta=meta, evento=EVENTO_EM_RISCO)
                    disparados += 1
            elif estado == SlaMetaEstado.violado.value:
                if not _ja_emitido(db, ticket_id=ticket.id, meta=meta, evento=EVENTO_VIOLADO):
                    _disparar_alerta(db, ticket=ticket, meta=meta, evento=EVENTO_VIOLADO)
                    disparados += 1
    return disparados
