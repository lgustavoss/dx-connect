"""Resumo e itens de pendências (fila + mensagens não lidas)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Ticket, TicketMensagem, Atendente
from app.models.ticket_read import TicketRead
from app.schemas.notificacoes import NotificacaoResumo, NotificacaoItem, NotificacaoItensResponse
from app.core.auth import obter_atendente_atual
from app.core.setor_scope import ids_setores_visiveis_atendente
from app.api.tickets import _pode_ver_ticket

router = APIRouter(prefix="/notificacoes", tags=["notificacoes"])


def _last_seen_scalar_subq(atendente_id: int):
    return (
        select(TicketRead.last_seen_at)
        .where(
            TicketRead.ticket_id == Ticket.id,
            TicketRead.atendente_id == atendente_id,
        )
        .limit(1)
        .scalar_subquery()
    )


def _effective_last_seen_expr(atendente_id: int):
    return func.coalesce(_last_seen_scalar_subq(atendente_id), Ticket.created_at)


def _exists_mensagem_nao_lida(atendente_id: int):
    eff = _effective_last_seen_expr(atendente_id)
    return exists(
        select(TicketMensagem.id).where(
            TicketMensagem.ticket_id == Ticket.id,
            TicketMensagem.created_at > eff,
        )
    )


def _count_sem_responsavel(db: Session, atendente: Atendente) -> int:
    stmt = (
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.fechado_em.is_(None),
            Ticket.atendente_id.is_(None),
        )
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(Ticket.setor_id.in_(vis))
    return int(db.execute(stmt).scalar_one())


def _count_tickets_com_nao_lidas(db: Session, atendente: Atendente) -> int:
    stmt = select(func.count()).select_from(Ticket).where(
        Ticket.fechado_em.is_(None),
        Ticket.atendente_id.isnot(None),
        _exists_mensagem_nao_lida(atendente.id),
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(Ticket.setor_id.in_(vis), Ticket.atendente_id == atendente.id)
    return int(db.execute(stmt).scalar_one())


def _unread_count_for_ticket(db: Session, ticket: Ticket, atendente_id: int) -> int:
    ls = (
        db.query(TicketRead.last_seen_at)
        .filter(
            TicketRead.ticket_id == ticket.id,
            TicketRead.atendente_id == atendente_id,
        )
        .scalar()
    )
    eff = ls if ls is not None else ticket.created_at
    n = (
        db.query(func.count(TicketMensagem.id))
        .filter(
            TicketMensagem.ticket_id == ticket.id,
            TicketMensagem.created_at > eff,
        )
        .scalar()
    )
    return int(n or 0)


@router.get("/resumo", response_model=NotificacaoResumo)
def resumo(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    sem = _count_sem_responsavel(db, atendente)
    nao = _count_tickets_com_nao_lidas(db, atendente)
    return NotificacaoResumo(
        sem_responsavel_count=sem,
        nao_lidas_count=nao,
        total_pendencias=sem + nao,
    )


@router.get("/itens", response_model=NotificacaoItensResponse)
def itens(
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    out: list[NotificacaoItem] = []

    sem = _count_sem_responsavel(db, atendente)
    if sem > 0:
        out.append(
            NotificacaoItem(
                tipo="fila_sem_responsavel",
                ticket_id=None,
                titulo="Tickets na fila",
                descricao="Sem responsável — em aberto",
                count=sem,
                href="/tickets?sem_responsavel=1",
                created_at=datetime.now(timezone.utc),
            )
        )

    stmt = (
        select(Ticket)
        .where(
            Ticket.fechado_em.is_(None),
            Ticket.atendente_id.isnot(None),
            _exists_mensagem_nao_lida(atendente.id),
        )
        .options(
            joinedload(Ticket.empresa),
            joinedload(Ticket.setor),
        )
        .order_by(Ticket.updated_at.desc().nulls_last(), Ticket.id.desc())
        .limit(limit)
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(Ticket.setor_id.in_(vis), Ticket.atendente_id == atendente.id)

    rows = db.execute(stmt).unique().scalars().all()

    for t in rows:
        uc = _unread_count_for_ticket(db, t, atendente.id)
        if uc <= 0:
            continue
        emp = t.empresa.nome if t.empresa else "—"
        setor = t.setor.nome if t.setor else "—"
        out.append(
            NotificacaoItem(
                tipo="mensagens_nao_lidas",
                ticket_id=t.id,
                titulo=f"{t.protocolo} — {t.assunto[:80]}{'…' if len(t.assunto) > 80 else ''}",
                descricao=f"{emp} · {setor}",
                count=uc,
                href=f"/tickets/{t.id}",
                created_at=t.updated_at or t.created_at,
            )
        )

    return NotificacaoItensResponse(itens=out)


@router.post("/tickets/{ticket_id}/visto", status_code=204)
def marcar_visto(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")

    now = datetime.now(timezone.utc)
    row = (
        db.query(TicketRead)
        .filter(
            TicketRead.ticket_id == ticket_id,
            TicketRead.atendente_id == atendente.id,
        )
        .first()
    )
    if row:
        row.last_seen_at = now
    else:
        db.add(
            TicketRead(
                atendente_id=atendente.id,
                ticket_id=ticket_id,
                last_seen_at=now,
            )
        )
    db.commit()
    return None
