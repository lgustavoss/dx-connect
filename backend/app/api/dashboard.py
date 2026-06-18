from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Ticket, StatusTicket, Empresa
from app.models.atendente import Atendente
from app.schemas.dashboard import DashboardGeralResponse, DashboardResponse, DashboardResumo, StatusCount
from app.services.dashboard_geral import obter_dashboard_geral as montar_dashboard_geral
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

    return DashboardResponse(resumo=resumo, ultimos_tickets=ultimos_tickets)


@router.get("/geral", response_model=DashboardGeralResponse)
def obter_dashboard_geral(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return montar_dashboard_geral(db, atendente)
