"""Contagem de inbound não lido e cursor de leitura por atendente (#951 / #S202608-0010)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.setor_scope import ids_setores_visiveis_atendente
from app.models.atendente import Atendente
from app.models.portal_chat import PortalChat, PortalChatRead as PortalChatReadModel, PortalMensagem
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem
from app.models.whatsapp_chat_read import WhatsappChatRead as WhatsappChatReadModel


# --- WhatsApp: expressões SQL reutilizáveis ---


def wpp_seen_msg_id_subq(atendente_id: int):
    return (
        select(WhatsappChatReadModel.last_seen_mensagem_id)
        .where(
            WhatsappChatReadModel.chat_id == WhatsappChat.id,
            WhatsappChatReadModel.atendente_id == atendente_id,
        )
        .limit(1)
        .scalar_subquery()
    )


def wpp_seen_at_subq(atendente_id: int):
    return (
        select(WhatsappChatReadModel.last_seen_at)
        .where(
            WhatsappChatReadModel.chat_id == WhatsappChat.id,
            WhatsappChatReadModel.atendente_id == atendente_id,
        )
        .limit(1)
        .scalar_subquery()
    )


def wpp_eff_seen_ts(atendente_id: int):
    return func.coalesce(
        wpp_seen_at_subq(atendente_id),
        WhatsappChat.atendimento_inicio_at,
        WhatsappChat.created_at,
    )


def _wpp_inbound_contavel_filters():
    return (
        WhatsappMensagem.direcao == "inbound",
        or_(WhatsappMensagem.evento_sistema.is_(None), WhatsappMensagem.evento_sistema == ""),
        WhatsappMensagem.apagada_em.is_(None),
    )


def _wpp_inbound_apos_cursor_clause(atendente_id: int):
    seen_msg_id = wpp_seen_msg_id_subq(atendente_id)
    eff_ts = wpp_eff_seen_ts(atendente_id)
    return or_(
        and_(seen_msg_id.isnot(None), WhatsappMensagem.id > seen_msg_id),
        and_(seen_msg_id.is_(None), WhatsappMensagem.created_at > eff_ts),
    )


def exists_wpp_inbound_nao_lido(atendente_id: int):
    return exists(
        select(WhatsappMensagem.id).where(
            WhatsappMensagem.chat_id == WhatsappChat.id,
            *_wpp_inbound_contavel_filters(),
            _wpp_inbound_apos_cursor_clause(atendente_id),
        )
    )


def wpp_ultima_nao_lida_at_subq(atendente_id: int):
    return (
        select(func.max(WhatsappMensagem.created_at))
        .where(
            WhatsappMensagem.chat_id == WhatsappChat.id,
            *_wpp_inbound_contavel_filters(),
            _wpp_inbound_apos_cursor_clause(atendente_id),
        )
        .scalar_subquery()
    )


def _ler_cursor_whatsapp(
    db: Session, chat_id: int, atendente_id: int
) -> tuple[datetime | None, int | None]:
    row = (
        db.query(WhatsappChatReadModel.last_seen_at, WhatsappChatReadModel.last_seen_mensagem_id)
        .filter(
            WhatsappChatReadModel.chat_id == chat_id,
            WhatsappChatReadModel.atendente_id == atendente_id,
        )
        .first()
    )
    if not row:
        return None, None
    return row[0], row[1]


def contar_nao_lidas_whatsapp(
    db: Session, c: WhatsappChat, atendente_id: int
) -> tuple[int, datetime | None, int | None]:
    """Inbound contável após o cursor de leitura do atendente."""
    ls, cursor_id = _ler_cursor_whatsapp(db, c.id, atendente_id)
    q = db.query(func.count(WhatsappMensagem.id)).filter(
        WhatsappMensagem.chat_id == c.id,
        *_wpp_inbound_contavel_filters(),
    )
    if cursor_id is not None:
        q = q.filter(WhatsappMensagem.id > cursor_id)
    else:
        eff = ls if ls is not None else (c.atendimento_inicio_at or c.created_at)
        if eff is None:
            return 0, ls, cursor_id
        q = q.filter(WhatsappMensagem.created_at > eff)
    return int(q.scalar() or 0), ls, cursor_id


def contar_nao_lidas_whatsapp_por_id(db: Session, chat_id: int, atendente_id: int) -> int:
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        return 0
    n, _, _ = contar_nao_lidas_whatsapp(db, c, atendente_id)
    return n


def marcar_leitura_whatsapp(
    db: Session,
    chat_id: int,
    atendente_id: int,
    *,
    now: datetime | None = None,
) -> None:
    ts = now or datetime.now(timezone.utc)
    max_msg_id = (
        db.query(func.max(WhatsappMensagem.id)).filter(WhatsappMensagem.chat_id == chat_id).scalar()
    )
    row = (
        db.query(WhatsappChatReadModel)
        .filter(
            WhatsappChatReadModel.chat_id == chat_id,
            WhatsappChatReadModel.atendente_id == atendente_id,
        )
        .first()
    )
    if row:
        row.last_seen_at = ts
        row.last_seen_mensagem_id = max_msg_id
    else:
        db.add(
            WhatsappChatReadModel(
                chat_id=chat_id,
                atendente_id=atendente_id,
                last_seen_at=ts,
                last_seen_mensagem_id=max_msg_id,
            )
        )


def count_wpp_respostas_pendentes(db: Session, atendente: Atendente) -> int:
    stmt = (
        select(func.count())
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.estado == "em_atendimento",
            WhatsappChat.atendente_id == atendente.id,
            exists_wpp_inbound_nao_lido(atendente.id),
        )
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(or_(WhatsappChat.setor_id.is_(None), WhatsappChat.setor_id.in_(vis)))
    return int(db.execute(stmt).scalar_one())


# --- Portal ---


def portal_seen_msg_id_subq(atendente_id: int):
    return (
        select(PortalChatReadModel.last_seen_mensagem_id)
        .where(
            PortalChatReadModel.chat_id == PortalChat.id,
            PortalChatReadModel.atendente_id == atendente_id,
        )
        .limit(1)
        .scalar_subquery()
    )


def portal_seen_at_subq(atendente_id: int):
    return (
        select(PortalChatReadModel.last_seen_at)
        .where(
            PortalChatReadModel.chat_id == PortalChat.id,
            PortalChatReadModel.atendente_id == atendente_id,
        )
        .limit(1)
        .scalar_subquery()
    )


def portal_eff_seen_ts(atendente_id: int):
    return func.coalesce(
        portal_seen_at_subq(atendente_id),
        PortalChat.atendimento_inicio_at,
        PortalChat.created_at,
    )


def _portal_inbound_contavel_filters():
    return (
        PortalMensagem.direcao == "inbound",
        or_(PortalMensagem.evento_sistema.is_(None), PortalMensagem.evento_sistema == ""),
    )


def _portal_inbound_apos_cursor_clause(atendente_id: int):
    seen_msg_id = portal_seen_msg_id_subq(atendente_id)
    eff_ts = portal_eff_seen_ts(atendente_id)
    return or_(
        and_(seen_msg_id.isnot(None), PortalMensagem.id > seen_msg_id),
        and_(seen_msg_id.is_(None), PortalMensagem.created_at > eff_ts),
    )


def exists_portal_inbound_nao_lido(atendente_id: int):
    return exists(
        select(PortalMensagem.id).where(
            PortalMensagem.chat_id == PortalChat.id,
            *_portal_inbound_contavel_filters(),
            _portal_inbound_apos_cursor_clause(atendente_id),
        )
    )


def contar_nao_lidas_portal(
    db: Session, c: PortalChat, atendente_id: int
) -> tuple[int, datetime | None, int | None]:
    row = (
        db.query(PortalChatReadModel.last_seen_at, PortalChatReadModel.last_seen_mensagem_id)
        .filter(
            PortalChatReadModel.chat_id == c.id,
            PortalChatReadModel.atendente_id == atendente_id,
        )
        .first()
    )
    ls = row[0] if row else None
    cursor_id = row[1] if row else None
    q = db.query(func.count(PortalMensagem.id)).filter(
        PortalMensagem.chat_id == c.id,
        *_portal_inbound_contavel_filters(),
    )
    if cursor_id is not None:
        q = q.filter(PortalMensagem.id > cursor_id)
    else:
        eff = ls if ls is not None else (c.atendimento_inicio_at or c.created_at)
        if eff is None:
            return 0, ls, cursor_id
        q = q.filter(PortalMensagem.created_at > eff)
    return int(q.scalar() or 0), ls, cursor_id


def count_portal_respostas_pendentes(db: Session, atendente: Atendente) -> int:
    stmt = (
        select(func.count())
        .select_from(PortalChat)
        .where(
            PortalChat.estado == "em_atendimento",
            PortalChat.atendente_id == atendente.id,
            exists_portal_inbound_nao_lido(atendente.id),
        )
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        stmt = stmt.where(or_(PortalChat.setor_id.is_(None), PortalChat.setor_id.in_(vis)))
    return int(db.execute(stmt).scalar_one())
