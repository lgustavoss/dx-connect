"""Métricas consolidadas do dashboard geral (#282)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.setor_scope import ids_setores_visiveis_atendente
from app.models import Ticket
from app.models.atendente import Atendente
from app.models.ticket_avaliacao import TicketAvaliacao
from app.models.whatsapp_chat import WhatsappChat
from app.schemas.dashboard import CsAtMediaResumo, DashboardGeralResponse

CACHE_TTL_SECONDS = 60
CSAT_PERIOD_DAYS = 7

_cache: dict[tuple[int, str], tuple[datetime, DashboardGeralResponse]] = {}


def clear_dashboard_geral_cache() -> None:
    _cache.clear()


def _ticket_scope(stmt, db: Session, atendente: Atendente):
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        return stmt.where(Ticket.setor_id.in_(vis))
    return stmt


def _whatsapp_scope(stmt, db: Session, atendente: Atendente):
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        return stmt.where(or_(WhatsappChat.setor_id.is_(None), WhatsappChat.setor_id.in_(vis)))
    return stmt


def _count_tickets_abertos(db: Session, atendente: Atendente) -> int:
    stmt = select(func.count()).select_from(Ticket).where(Ticket.fechado_em.is_(None))
    stmt = _ticket_scope(stmt, db, atendente)
    return int(db.execute(stmt).scalar_one())


def _count_tickets_sem_responsavel(db: Session, atendente: Atendente) -> int:
    stmt = (
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.fechado_em.is_(None),
            Ticket.atendente_id.is_(None),
        )
    )
    stmt = _ticket_scope(stmt, db, atendente)
    return int(db.execute(stmt).scalar_one())


def _count_sla_violacoes_abertas(db: Session, atendente: Atendente) -> int:
    stmt = (
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.fechado_em.is_(None),
            Ticket.sla_violado.is_(True),
        )
    )
    stmt = _ticket_scope(stmt, db, atendente)
    return int(db.execute(stmt).scalar_one())


def _count_sla_em_risco_abertas(db: Session, atendente: Atendente) -> int:
    from app.services.sla_calculo import filtro_sql_sla_em_risco

    stmt = select(func.count()).select_from(Ticket).where(filtro_sql_sla_em_risco())
    stmt = _ticket_scope(stmt, db, atendente)
    return int(db.execute(stmt).scalar_one())


def _count_chats_por_estado(db: Session, atendente: Atendente, estado: str) -> int:
    stmt = select(func.count()).select_from(WhatsappChat).where(WhatsappChat.estado == estado)
    stmt = _whatsapp_scope(stmt, db, atendente)
    return int(db.execute(stmt).scalar_one())


def _csat_tickets(db: Session, atendente: Atendente, desde: datetime) -> CsAtMediaResumo:
    stmt = (
        select(
            func.avg(TicketAvaliacao.nota),
            func.count(TicketAvaliacao.id),
        )
        .select_from(TicketAvaliacao)
        .join(Ticket, Ticket.id == TicketAvaliacao.ticket_id)
        .where(TicketAvaliacao.respondida_em >= desde)
    )
    stmt = _ticket_scope(stmt, db, atendente)
    media, total = db.execute(stmt).one()
    total_int = int(total or 0)
    return CsAtMediaResumo(
        media=round(float(media), 2) if media is not None and total_int > 0 else None,
        total_avaliacoes=total_int,
        periodo_dias=CSAT_PERIOD_DAYS,
    )


def _csat_chats(db: Session, atendente: Atendente, desde: datetime) -> CsAtMediaResumo:
    stmt = (
        select(
            func.avg(WhatsappChat.avaliacao_nota),
            func.count(WhatsappChat.id),
        )
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.avaliacao_nota.isnot(None),
            WhatsappChat.avaliacao_respondida_at.isnot(None),
            WhatsappChat.avaliacao_respondida_at >= desde,
        )
    )
    stmt = _whatsapp_scope(stmt, db, atendente)
    media, total = db.execute(stmt).one()
    total_int = int(total or 0)
    return CsAtMediaResumo(
        media=round(float(media), 2) if media is not None and total_int > 0 else None,
        total_avaliacoes=total_int,
        periodo_dias=CSAT_PERIOD_DAYS,
    )


def _compute_dashboard_geral(db: Session, atendente: Atendente) -> DashboardGeralResponse:
    agora = datetime.now(timezone.utc)
    desde = agora - timedelta(days=CSAT_PERIOD_DAYS)
    return DashboardGeralResponse(
        tickets_abertos=_count_tickets_abertos(db, atendente),
        tickets_sem_responsavel=_count_tickets_sem_responsavel(db, atendente),
        chats_aguardando_atendente=_count_chats_por_estado(db, atendente, "aguardando_atendente"),
        chats_em_atendimento=_count_chats_por_estado(db, atendente, "em_atendimento"),
        csat_tickets=_csat_tickets(db, atendente, desde),
        csat_chats=_csat_chats(db, atendente, desde),
        sla_violacoes_abertas=_count_sla_violacoes_abertas(db, atendente),
        sla_em_risco_abertas=_count_sla_em_risco_abertas(db, atendente),
        gerado_em=agora,
        cache_ttl_segundos=CACHE_TTL_SECONDS,
    )


def obter_dashboard_geral(db: Session, atendente: Atendente) -> DashboardGeralResponse:
    chave = (atendente.id, atendente.role)
    agora = datetime.now(timezone.utc)
    em_cache = _cache.get(chave)
    if em_cache is not None:
        gerado_em, resposta = em_cache
        if (agora - gerado_em).total_seconds() < CACHE_TTL_SECONDS:
            return resposta
    resposta = _compute_dashboard_geral(db, atendente)
    _cache[chave] = (agora, resposta)
    return resposta
