"""Relatório tabular de tickets — export CSV (#287 → D-08, base para #285)."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Ticket
from app.models.atendente import Atendente
from app.schemas.relatorio import RelatorioTicketLinha, RelatorioTicketsResponse
from app.services.ticket_dashboard_filters import (
    apply_ticket_dashboard_filters,
    period_bounds,
    resolve_period,
)

MAX_EXPORT_ROWS = 50_000
PREVIEW_LIMIT = 50

_CSV_HEADERS = (
    "protocolo",
    "assunto",
    "status",
    "prioridade",
    "rede",
    "empresa",
    "setor",
    "aberto_em",
    "fechado_em",
    "responsavel",
    "canal",
)


def _canal_rotulo(ticket: Ticket) -> str:
    if ticket.parent_ticket_id is not None:
        return "Filho em massa"
    if any(getattr(m, "tipo", None) == "email_cliente" for m in (ticket.mensagens or [])):
        return "E-mail"
    return "Manual"


def _ticket_para_linha(ticket: Ticket) -> RelatorioTicketLinha:
    return RelatorioTicketLinha(
        protocolo=ticket.protocolo,
        assunto=ticket.assunto,
        status_nome=ticket.status.nome if ticket.status else "",
        prioridade=str(ticket.prioridade),
        rede_nome=ticket.rede.nome if ticket.rede else "",
        empresa_nome=ticket.empresa.nome if ticket.empresa else "",
        setor_nome=ticket.setor.nome if ticket.setor else "",
        aberto_em=ticket.created_at,
        fechado_em=ticket.fechado_em,
        responsavel_nome=ticket.atendente.nome if ticket.atendente else "",
        canal=_canal_rotulo(ticket),
    )


def _load_options(stmt):
    return stmt.options(
        joinedload(Ticket.status),
        joinedload(Ticket.rede),
        joinedload(Ticket.empresa),
        joinedload(Ticket.setor),
        joinedload(Ticket.atendente),
        joinedload(Ticket.mensagens),
    )


def listar_relatorio_tickets(
    db: Session,
    atendente: Atendente,
    *,
    de: date | None = None,
    ate: date | None = None,
    rede_id: int | None = None,
    setor_id: int | None = None,
    prioridade: str | None = None,
    offset: int = 0,
    limit: int = PREVIEW_LIMIT,
) -> RelatorioTicketsResponse:
    inicio, fim = resolve_period(de, ate)
    de_dt, ate_dt = period_bounds(inicio, fim)
    filtros = {
        "rede_id": rede_id,
        "setor_id": setor_id,
        "prioridade": prioridade,
    }

    count_stmt = select(func.count()).select_from(Ticket).where(
        Ticket.created_at >= de_dt,
        Ticket.created_at < ate_dt,
    )
    count_stmt = apply_ticket_dashboard_filters(count_stmt, db, atendente, **filtros)
    total = int(db.execute(count_stmt).scalar_one())

    stmt = (
        select(Ticket)
        .where(Ticket.created_at >= de_dt, Ticket.created_at < ate_dt)
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
    )
    stmt = apply_ticket_dashboard_filters(stmt, db, atendente, **filtros)
    rows = (
        db.execute(
            _load_options(stmt)
            .offset(max(0, offset))
            .limit(min(max(1, limit), PREVIEW_LIMIT))
        )
        .unique()
        .scalars()
        .all()
    )
    return RelatorioTicketsResponse(
        de=inicio,
        ate=fim,
        total=total,
        offset=max(0, offset),
        limit=min(max(1, limit), PREVIEW_LIMIT),
        itens=[_ticket_para_linha(t) for t in rows],
    )


def exportar_relatorio_tickets_csv(
    db: Session,
    atendente: Atendente,
    *,
    de: date | None = None,
    ate: date | None = None,
    rede_id: int | None = None,
    setor_id: int | None = None,
    prioridade: str | None = None,
) -> str:
    inicio, fim = resolve_period(de, ate)
    de_dt, ate_dt = period_bounds(inicio, fim)
    filtros = {
        "rede_id": rede_id,
        "setor_id": setor_id,
        "prioridade": prioridade,
    }
    stmt = (
        select(Ticket)
        .where(Ticket.created_at >= de_dt, Ticket.created_at < ate_dt)
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .limit(MAX_EXPORT_ROWS)
    )
    stmt = apply_ticket_dashboard_filters(stmt, db, atendente, **filtros)
    tickets = db.execute(_load_options(stmt)).unique().scalars().all()

    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(_CSV_HEADERS)
    for ticket in tickets:
        linha = _ticket_para_linha(ticket)
        writer.writerow(
            [
                linha.protocolo,
                linha.assunto,
                linha.status_nome,
                linha.prioridade,
                linha.rede_nome,
                linha.empresa_nome,
                linha.setor_nome,
                linha.aberto_em.isoformat() if linha.aberto_em else "",
                linha.fechado_em.isoformat() if linha.fechado_em else "",
                linha.responsavel_nome,
                linha.canal,
            ]
        )
    return buffer.getvalue()
