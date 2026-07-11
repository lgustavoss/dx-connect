"""Resumo e itens de pendências (fila + mensagens não lidas)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, func, select, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Ticket, TicketMensagem, Atendente
from app.models.ticket_read import TicketRead
from app.models.whatsapp_chat_read import WhatsappChatRead
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem
from app.schemas.notificacoes import NotificacaoResumo, NotificacaoItem, NotificacaoItensResponse
from app.schemas.atendente_notificacao import NotificacaoPreferenciasRead, NotificacaoPreferenciasUpdate
from app.core.auth import obter_atendente_atual
from app.services.notificacao_atendente_email import (
    atualizar_preferencias,
    obter_ou_criar_preferencias,
    preferencias_para_dict,
)
from app.services import chat_interno as chat_interno_svc
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
            Ticket.tenant_id == atendente.tenant_id,
            Ticket.fechado_em.is_(None),
            Ticket.atendente_id.is_(None),
        )
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(Ticket.setor_id.in_(vis))
    return int(db.execute(stmt).scalar_one())


def _apply_escopo_tickets_nao_lidos(stmt, db: Session, atendente: Atendente):
    """Tickets abertos atribuídos ao atendente com mensagens não lidas (mesmo escopo em resumo e itens)."""
    stmt = stmt.where(
        Ticket.tenant_id == atendente.tenant_id,
        Ticket.fechado_em.is_(None),
        Ticket.atendente_id == atendente.id,
        _exists_mensagem_nao_lida(atendente.id),
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(Ticket.setor_id.in_(vis))
    return stmt


def _count_tickets_com_nao_lidas(db: Session, atendente: Atendente) -> int:
    stmt = _apply_escopo_tickets_nao_lidos(select(func.count()).select_from(Ticket), db, atendente)
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


def _last_unread_message_at_subq(atendente_id: int):
    eff = _effective_last_seen_expr(atendente_id)
    return (
        select(func.max(TicketMensagem.created_at))
        .where(
            TicketMensagem.ticket_id == Ticket.id,
            TicketMensagem.created_at > eff,
        )
        .scalar_subquery()
    )


def _wpp_resposta_pendente_exprs(atendente_id: int):
    seen_at = (
        select(WhatsappChatRead.last_seen_at)
        .where(
            WhatsappChatRead.chat_id == WhatsappChat.id,
            WhatsappChatRead.atendente_id == atendente_id,
        )
        .limit(1)
        .scalar_subquery()
    )
    inbound_last = (
        select(func.max(WhatsappMensagem.created_at))
        .where(
            WhatsappMensagem.chat_id == WhatsappChat.id,
            WhatsappMensagem.direcao == "inbound",
        )
        .scalar_subquery()
    )
    eff_seen = func.coalesce(seen_at, WhatsappChat.atendimento_inicio_at, WhatsappChat.created_at)
    return inbound_last, eff_seen


def _preview_ultima_nao_lida(db: Session, ticket: Ticket, atendente_id: int) -> str | None:
    ls = (
        db.query(TicketRead.last_seen_at)
        .filter(
            TicketRead.ticket_id == ticket.id,
            TicketRead.atendente_id == atendente_id,
        )
        .scalar()
    )
    eff = ls if ls is not None else ticket.created_at
    corpo = (
        db.query(TicketMensagem.corpo)
        .filter(
            TicketMensagem.ticket_id == ticket.id,
            TicketMensagem.created_at > eff,
        )
        .order_by(TicketMensagem.created_at.desc())
        .limit(1)
        .scalar()
    )
    if not corpo:
        return None
    texto = corpo.strip()
    if len(texto) > 60:
        return texto[:60] + "…"
    return texto


def _count_wpp_fila(db: Session, atendente: Atendente) -> int:
    stmt = (
        select(func.count())
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.estado == "aguardando_atendente",
        )
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(or_(WhatsappChat.setor_id.is_(None), WhatsappChat.setor_id.in_(vis)))
    return int(db.execute(stmt).scalar_one())


def _count_wpp_respostas_pendentes(db: Session, atendente: Atendente) -> int:
    inbound_last, eff_seen = _wpp_resposta_pendente_exprs(atendente.id)
    stmt = (
        select(func.count())
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.estado == "em_atendimento",
            WhatsappChat.atendente_id == atendente.id,
            inbound_last.isnot(None),
            eff_seen < inbound_last,
        )
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(or_(WhatsappChat.setor_id.is_(None), WhatsappChat.setor_id.in_(vis)))
    return int(db.execute(stmt).scalar_one())


def _wpp_unread_count_for_chat(db: Session, chat_id: int, atendente_id: int) -> int:
    c = db.query(WhatsappChat.id, WhatsappChat.created_at, WhatsappChat.atendimento_inicio_at).filter(WhatsappChat.id == chat_id).first()
    if not c:
        return 0
    ls = (
        db.query(WhatsappChatRead.last_seen_at)
        .filter(WhatsappChatRead.chat_id == chat_id, WhatsappChatRead.atendente_id == atendente_id)
        .scalar()
    )
    eff = ls if ls is not None else (c.atendimento_inicio_at or c.created_at)
    n = (
        db.query(func.count(WhatsappMensagem.id))
        .filter(
            WhatsappMensagem.chat_id == chat_id,
            WhatsappMensagem.direcao == "inbound",
            WhatsappMensagem.created_at > eff,
        )
        .scalar()
    )
    return int(n or 0)


def build_notificacao_itens(
    db: Session,
    atendente: Atendente,
    *,
    limit: int = 15,
) -> list[NotificacaoItem]:
    """Lista de pendências navegáveis (paridade com build_notificacao_resumo)."""
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

    wpp_fila = _count_wpp_fila(db, atendente)
    if wpp_fila > 0:
        out.append(
            NotificacaoItem(
                tipo="wpp_chats_na_fila",
                ticket_id=None,
                titulo="Chats na fila",
                descricao="WhatsApp — aguardando atendimento",
                count=wpp_fila,
                href="/whatsapp/atendendo",
                created_at=datetime.now(timezone.utc),
            )
        )

    inbound_last, eff_seen = _wpp_resposta_pendente_exprs(atendente.id)
    stmt_wpp = (
        select(WhatsappChat)
        .where(
            WhatsappChat.estado == "em_atendimento",
            WhatsappChat.atendente_id == atendente.id,
            inbound_last.isnot(None),
            eff_seen < inbound_last,
        )
        .order_by(inbound_last.desc(), WhatsappChat.id.desc())
        .limit(limit)
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt_wpp = stmt_wpp.where(or_(WhatsappChat.setor_id.is_(None), WhatsappChat.setor_id.in_(vis)))
    chats = db.execute(stmt_wpp).scalars().all()
    for c in chats:
        uc = _wpp_unread_count_for_chat(db, c.id, atendente.id)
        if uc <= 0:
            uc = 1
        nome = (c.cliente_nome or "").strip() or c.wa_id
        out.append(
            NotificacaoItem(
                tipo="wpp_chats_com_resposta",
                ticket_id=None,
                titulo=f"{c.protocolo} — {nome}",
                descricao="WhatsApp — cliente respondeu",
                count=uc,
                href=f"/whatsapp/c/{c.id}",
                created_at=datetime.now(timezone.utc),
            )
        )

    last_unread_at = _last_unread_message_at_subq(atendente.id)
    stmt = _apply_escopo_tickets_nao_lidos(
        select(Ticket)
        .options(
            joinedload(Ticket.empresa),
            joinedload(Ticket.setor),
        )
        .order_by(last_unread_at.desc(), Ticket.id.desc())
        .limit(limit),
        db,
        atendente,
    )
    rows = db.execute(stmt).unique().scalars().all()

    for t in rows:
        uc = _unread_count_for_ticket(db, t, atendente.id)
        if uc <= 0:
            uc = 1
        emp = t.empresa.nome if t.empresa else "—"
        setor = t.setor.nome if t.setor else "—"
        assunto = (t.assunto or "").strip() or "—"
        preview = _preview_ultima_nao_lida(db, t, atendente.id)
        descricao = f"Nova resposta do cliente — {preview}" if preview else f"{emp} · {setor}"
        out.append(
            NotificacaoItem(
                tipo="mensagens_nao_lidas",
                ticket_id=t.id,
                titulo=f"{t.protocolo} — {assunto[:80]}{'…' if len(assunto) > 80 else ''}",
                descricao=descricao,
                count=uc,
                href=f"/tickets/{t.id}",
                created_at=t.updated_at or t.created_at,
            )
        )

    for resumo in chat_interno_svc.listar_conversas_com_nao_lidas(db, atendente, limit=limit):
        preview = resumo.ultima_mensagem_corpo
        descricao = (
            f"Chat interno — {chat_interno_svc.preview_corpo(preview)}"
            if preview
            else "Chat interno — nova mensagem"
        )
        out.append(
            NotificacaoItem(
                tipo="chat_interno",
                conversa_id=resumo.conversa.id,
                titulo=resumo.titulo,
                descricao=descricao,
                count=resumo.nao_lidas_count,
                href=f"/chat-interno/{resumo.conversa.id}",
                created_at=resumo.ultima_mensagem_em or resumo.conversa.created_at,
            )
        )

    return out


def build_notificacao_resumo(db: Session, atendente: Atendente) -> NotificacaoResumo:
    """Contadores de pendências para um atendente (reutilizado por API e SSE)."""
    sem = _count_sem_responsavel(db, atendente)
    nao = _count_tickets_com_nao_lidas(db, atendente)
    wpp_fila = _count_wpp_fila(db, atendente)
    wpp_resp = _count_wpp_respostas_pendentes(db, atendente)
    chat_interno = chat_interno_svc.contar_total_nao_lidas_atendente(db, atendente)
    return NotificacaoResumo(
        sem_responsavel_count=sem,
        nao_lidas_count=nao,
        wpp_fila_count=wpp_fila,
        wpp_respostas_count=wpp_resp,
        chat_interno_nao_lidas_count=chat_interno,
        total_pendencias=sem + nao + wpp_fila + wpp_resp + chat_interno,
    )


@router.get("/resumo", response_model=NotificacaoResumo)
def resumo(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return build_notificacao_resumo(db, atendente)


@router.get("/itens", response_model=NotificacaoItensResponse)
def itens(
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return NotificacaoItensResponse(itens=build_notificacao_itens(db, atendente, limit=limit))


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
    from app.services.realtime_emit import emit_notificacao_contagem

    emit_notificacao_contagem(db, [atendente.id])
    return None


@router.get("/preferencias", response_model=NotificacaoPreferenciasRead)
def obter_preferencias(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    prefs = obter_ou_criar_preferencias(db, atendente.id)
    db.commit()
    return NotificacaoPreferenciasRead(**preferencias_para_dict(prefs))


@router.patch("/preferencias", response_model=NotificacaoPreferenciasRead)
def atualizar_preferencias_endpoint(
    data: NotificacaoPreferenciasUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    payload = data.model_dump(exclude_unset=True)
    if not payload:
        prefs = obter_ou_criar_preferencias(db, atendente.id)
        db.commit()
        return NotificacaoPreferenciasRead(**preferencias_para_dict(prefs))
    prefs = atualizar_preferencias(db, atendente.id, payload)
    return NotificacaoPreferenciasRead(**preferencias_para_dict(prefs))
