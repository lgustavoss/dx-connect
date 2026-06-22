"""Relatório tabular de chats WhatsApp (#285 / D-F4)."""

from __future__ import annotations

import csv
import io
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.models.whatsapp_chat import WhatsappChat
from app.schemas.relatorio import RelatorioChatLinha, RelatorioChatsResponse
from app.services.chat_dashboard_filters import (
    apply_chat_dashboard_filters,
    period_bounds,
    resolve_period,
)

MAX_EXPORT_ROWS = 50_000
PREVIEW_LIMIT = 50

_CSV_HEADERS = (
    "protocolo",
    "cliente_nome",
    "wa_id",
    "estado",
    "setor",
    "atendente",
    "empresa",
    "aberto_em",
    "inicio_atendimento",
    "encerrado_em",
    "avaliacao_nota",
)

_ESTADO_ROTULOS = {
    "aguardando_atendente": "Aguardando atendente",
    "em_atendimento": "Em atendimento",
    "aguardando_avaliacao": "Aguardando avaliação",
    "encerrado": "Encerrado",
}


def _estado_rotulo(estado: str) -> str:
    return _ESTADO_ROTULOS.get(estado, estado.replace("_", " ").title())


def _chat_para_linha(chat: WhatsappChat) -> RelatorioChatLinha:
    return RelatorioChatLinha(
        protocolo=chat.protocolo,
        cliente_nome=chat.cliente_nome,
        wa_id=chat.wa_id,
        estado=chat.estado,
        estado_rotulo=_estado_rotulo(chat.estado),
        setor_nome=chat.setor.nome if chat.setor else "",
        atendente_nome=chat.atendente.nome if chat.atendente else "",
        empresa_nome=chat.empresa.nome if chat.empresa else "",
        aberto_em=chat.created_at,
        inicio_atendimento=chat.atendimento_inicio_at,
        encerrado_em=chat.encerramento_at,
        avaliacao_nota=chat.avaliacao_nota,
    )


def _load_options(stmt):
    return stmt.options(
        joinedload(WhatsappChat.setor),
        joinedload(WhatsappChat.atendente),
        joinedload(WhatsappChat.empresa),
    )


def listar_relatorio_chats(
    db: Session,
    atendente: Atendente,
    *,
    de: date | None = None,
    ate: date | None = None,
    setor_id: int | None = None,
    atendente_filtro_id: int | None = None,
    offset: int = 0,
    limit: int = PREVIEW_LIMIT,
) -> RelatorioChatsResponse:
    inicio, fim = resolve_period(de, ate)
    de_dt, ate_dt = period_bounds(inicio, fim)
    filtros = {
        "setor_id": setor_id,
        "atendente_id": atendente_filtro_id,
    }

    count_stmt = select(func.count()).select_from(WhatsappChat).where(
        WhatsappChat.created_at >= de_dt,
        WhatsappChat.created_at < ate_dt,
    )
    count_stmt = apply_chat_dashboard_filters(count_stmt, db, atendente, **filtros)
    total = int(db.execute(count_stmt).scalar_one())

    stmt = (
        select(WhatsappChat)
        .where(WhatsappChat.created_at >= de_dt, WhatsappChat.created_at < ate_dt)
        .order_by(WhatsappChat.created_at.desc(), WhatsappChat.id.desc())
    )
    stmt = apply_chat_dashboard_filters(stmt, db, atendente, **filtros)
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
    return RelatorioChatsResponse(
        de=inicio,
        ate=fim,
        total=total,
        offset=max(0, offset),
        limit=min(max(1, limit), PREVIEW_LIMIT),
        itens=[_chat_para_linha(c) for c in rows],
    )


def exportar_relatorio_chats_csv(
    db: Session,
    atendente: Atendente,
    *,
    de: date | None = None,
    ate: date | None = None,
    setor_id: int | None = None,
    atendente_filtro_id: int | None = None,
) -> str:
    inicio, fim = resolve_period(de, ate)
    de_dt, ate_dt = period_bounds(inicio, fim)
    filtros = {
        "setor_id": setor_id,
        "atendente_id": atendente_filtro_id,
    }
    stmt = (
        select(WhatsappChat)
        .where(WhatsappChat.created_at >= de_dt, WhatsappChat.created_at < ate_dt)
        .order_by(WhatsappChat.created_at.desc(), WhatsappChat.id.desc())
        .limit(MAX_EXPORT_ROWS)
    )
    stmt = apply_chat_dashboard_filters(stmt, db, atendente, **filtros)
    chats = db.execute(_load_options(stmt)).unique().scalars().all()

    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(_CSV_HEADERS)
    for chat in chats:
        linha = _chat_para_linha(chat)
        writer.writerow(
            [
                linha.protocolo,
                linha.cliente_nome or "",
                linha.wa_id,
                linha.estado_rotulo,
                linha.setor_nome,
                linha.atendente_nome,
                linha.empresa_nome,
                linha.aberto_em.isoformat() if linha.aberto_em else "",
                linha.inicio_atendimento.isoformat() if linha.inicio_atendimento else "",
                linha.encerrado_em.isoformat() if linha.encerrado_em else "",
                linha.avaliacao_nota if linha.avaliacao_nota is not None else "",
            ]
        )
    return buffer.getvalue()
