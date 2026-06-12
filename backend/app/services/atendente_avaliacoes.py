"""Métricas de avaliação (CSAT) por atendente."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ticket_avaliacao import TicketAvaliacao
from app.models.whatsapp_chat import WhatsappChat


def calcular_avaliacoes_atendente(db: Session, atendente_id: int) -> dict:
    wpp_row = (
        db.query(func.avg(WhatsappChat.avaliacao_nota), func.count(WhatsappChat.id))
        .filter(
            WhatsappChat.atendente_id == atendente_id,
            WhatsappChat.avaliacao_nota.isnot(None),
        )
        .one()
    )
    tkt_row = (
        db.query(func.avg(TicketAvaliacao.nota), func.count(TicketAvaliacao.id))
        .filter(TicketAvaliacao.atendente_id == atendente_id)
        .one()
    )
    wpp_media, wpp_total = wpp_row[0], int(wpp_row[1] or 0)
    tkt_media, tkt_total = tkt_row[0], int(tkt_row[1] or 0)

    soma = 0.0
    total_geral = 0
    if wpp_total and wpp_media is not None:
        soma += float(wpp_media) * wpp_total
        total_geral += wpp_total
    if tkt_total and tkt_media is not None:
        soma += float(tkt_media) * tkt_total
        total_geral += tkt_total
    geral_media = round(soma / total_geral, 2) if total_geral else None

    def pack(media, total: int) -> dict:
        return {"media": round(float(media), 2) if media is not None and total else None, "total": total}

    return {
        "geral": pack(geral_media, total_geral),
        "whatsapp": pack(wpp_media, wpp_total),
        "tickets": pack(tkt_media, tkt_total),
    }
