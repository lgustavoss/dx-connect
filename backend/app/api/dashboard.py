from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, cast, Date, or_, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Ticket, StatusTicket, Empresa
from app.models.atendente import Atendente
from app.models.whatsapp_chat import WhatsappChat
from app.schemas.dashboard import (
    ChatEstadoCount,
    ChatRecenteResumo,
    DashboardChatsResumo,
    DashboardGeralResponse,
    DashboardResponse,
    DashboardResumo,
    DashboardTicketsResponse,
    DashboardChatsResponse,
    StatusCount,
)
from app.services.dashboard_geral import obter_dashboard_geral as montar_dashboard_geral
from app.services.dashboard_tickets import obter_dashboard_tickets as montar_dashboard_tickets
from app.services.dashboard_chats import obter_dashboard_chats as montar_dashboard_chats
from app.services.ticket_dashboard_filters import normalizar_prioridade
from app.schemas.ticket import TicketRead
from app.core.auth import obter_atendente_atual
from app.api.tickets import _ticket_para_read
from app.core.setor_scope import ids_setores_visiveis_atendente

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _filtro_setor_atendente(db: Session, q, atendente: Atendente):
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        return q.filter(Ticket.setor_id.in_(vis))
    return q


def _filtro_whatsapp_scope(db: Session, q, atendente: Atendente):
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        return q.filter(or_(WhatsappChat.setor_id.is_(None), WhatsappChat.setor_id.in_(vis)))
    return q


_CHAT_ESTADO_ROTULO = {
    "aguardando_atendente": "Aguardando atendente",
    "em_atendimento": "Em atendimento",
    "aguardando_avaliacao": "Aguardando avaliação",
    "encerrado": "Encerrado",
}


@router.get("", response_model=DashboardResponse)
def obter_dashboard(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    hoje = date.today()

    # Total de tickets
    q_total = db.query(func.count(Ticket.id)).select_from(Ticket)
    q_total = _filtro_setor_atendente(db, q_total, atendente)
    total_tickets = q_total.scalar() or 0

    # Tickets abertos hoje
    q_hoje = (
        db.query(func.count(Ticket.id))
        .select_from(Ticket)
        .filter(cast(Ticket.created_at, Date) == hoje)
    )
    q_hoje = _filtro_setor_atendente(db, q_hoje, atendente)
    abertos_hoje = q_hoje.scalar() or 0

    # Contagem por status
    q_status = (
        db.query(Ticket.status_id, StatusTicket.nome, func.count(Ticket.id).label("total"))
        .join(StatusTicket, Ticket.status_id == StatusTicket.id)
        .group_by(Ticket.status_id, StatusTicket.nome)
    )
    q_status = _filtro_setor_atendente(db, q_status, atendente)
    rows_status = q_status.all()
    por_status = [
        StatusCount(status_id=sid, status_nome=nome, total=tot)
        for sid, nome, tot in rows_status
    ]

    resumo = DashboardResumo(
        total_tickets=total_tickets,
        abertos_hoje=abertos_hoje,
        por_status=por_status,
    )

    q_chats_total = db.query(func.count(WhatsappChat.id)).select_from(WhatsappChat)
    q_chats_total = _filtro_whatsapp_scope(db, q_chats_total, atendente)
    total_chats = q_chats_total.scalar() or 0

    q_chats_hoje = (
        db.query(func.count(WhatsappChat.id))
        .select_from(WhatsappChat)
        .filter(cast(WhatsappChat.created_at, Date) == hoje)
    )
    q_chats_hoje = _filtro_whatsapp_scope(db, q_chats_hoje, atendente)
    chats_hoje = q_chats_hoje.scalar() or 0

    q_estados = (
        db.query(WhatsappChat.estado, func.count(WhatsappChat.id))
        .select_from(WhatsappChat)
        .group_by(WhatsappChat.estado)
    )
    q_estados = _filtro_whatsapp_scope(db, q_estados, atendente)
    por_estado = [
        ChatEstadoCount(
            estado=estado,
            rotulo=_CHAT_ESTADO_ROTULO.get(estado, estado),
            total=int(total),
        )
        for estado, total in q_estados.all()
        if estado in _CHAT_ESTADO_ROTULO
    ]

    resumo_chats = DashboardChatsResumo(
        total_chats=total_chats,
        iniciados_hoje=chats_hoje,
        por_estado=por_estado,
    )

    # Últimos tickets
    q_ultimos = (
        db.query(Ticket)
        .outerjoin(Ticket.empresa)
        .join(Ticket.setor)
        .join(Ticket.status)
        .outerjoin(Ticket.atendente)
    )
    q_ultimos = _filtro_setor_atendente(db, q_ultimos, atendente)
    ultimos = (
        q_ultimos.options(
            joinedload(Ticket.empresa).joinedload(Empresa.rede),
            joinedload(Ticket.setor),
            joinedload(Ticket.status),
            joinedload(Ticket.atendente),
        )
        .order_by(Ticket.created_at.desc())
        .limit(10)
        .all()
    )
    ultimos_tickets = [_ticket_para_read(t) for t in ultimos]

    q_ultimos_chats = db.query(WhatsappChat)
    q_ultimos_chats = _filtro_whatsapp_scope(db, q_ultimos_chats, atendente)
    ultimos_chats_rows = q_ultimos_chats.order_by(WhatsappChat.created_at.desc()).limit(10).all()
    ultimos_chats = [
        ChatRecenteResumo(
            id=c.id,
            protocolo=c.protocolo,
            cliente_nome=c.cliente_nome,
            estado=c.estado,
            created_at=c.created_at,
        )
        for c in ultimos_chats_rows
    ]

    return DashboardResponse(
        resumo=resumo,
        resumo_chats=resumo_chats,
        ultimos_tickets=ultimos_tickets,
        ultimos_chats=ultimos_chats,
    )


@router.get("/geral", response_model=DashboardGeralResponse)
def obter_dashboard_geral(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return montar_dashboard_geral(db, atendente)


@router.get(
    "/tickets",
    response_model=DashboardTicketsResponse,
    summary="Dashboard analítico de tickets",
    description="Métricas consolidadas do canal ticket no período informado (default: últimos 30 dias). "
    "Atendentes veem apenas setores vinculados.",
)
def obter_dashboard_tickets(
    de: date | None = Query(None, description="Início do período (default: 30 dias antes de ate)"),
    ate: date | None = Query(None, description="Fim do período (default: hoje)"),
    rede_id: int | None = Query(None, ge=1),
    setor_id: int | None = Query(None, ge=1),
    prioridade: str | None = Query(
        None,
        description="Filtrar por prioridade: baixa, normal, alta, urgente",
    ),
    atendente_filtro_id: int | None = Query(None, ge=1, description="Drill-down por atendente responsável (legado)"),
    drill_tipo: str | None = Query(None, description="Tipo do drill-down cross-filter (ex.: empresa, atendente)"),
    drill_valor: str | None = Query(None, description="Valor do drill-down (id ou código conforme o tipo)"),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    prio = None
    if prioridade is not None:
        try:
            prio = normalizar_prioridade(prioridade)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return montar_dashboard_tickets(
        db,
        atendente,
        de=de,
        ate=ate,
        rede_id=rede_id,
        setor_id=setor_id,
        prioridade=prio,
        drill_tipo=drill_tipo,
        drill_valor=drill_valor,
        atendente_filtro_id=atendente_filtro_id,
    )


@router.get(
    "/chats",
    response_model=DashboardChatsResponse,
    summary="Dashboard analítico de chats WhatsApp",
    description="Métricas consolidadas do canal WhatsApp no período informado (default: últimos 30 dias). "
    "Atendentes veem apenas setores vinculados.",
)
def obter_dashboard_chats(
    de: date | None = Query(None, description="Início do período (default: 30 dias antes de ate)"),
    ate: date | None = Query(None, description="Fim do período (default: hoje)"),
    setor_id: int | None = Query(None, ge=1),
    atendente_filtro_id: int | None = Query(None, ge=1, description="Drill-down por atendente responsável (legado)"),
    drill_tipo: str | None = Query(None, description="Tipo do drill-down cross-filter (ex.: estado, atendente)"),
    drill_valor: str | None = Query(None, description="Valor do drill-down (id ou código conforme o tipo)"),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return montar_dashboard_chats(
        db,
        atendente,
        de=de,
        ate=ate,
        setor_id=setor_id,
        drill_tipo=drill_tipo,
        drill_valor=drill_valor,
        atendente_filtro_id=atendente_filtro_id,
    )
