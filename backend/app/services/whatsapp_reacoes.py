"""Reações em mensagens WhatsApp do chat com o cliente (#630 lote 2)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.whatsapp_chat import WhatsappMensagem, WhatsappMensagemReacao

ORIGEM_CLIENTE = "cliente"
ORIGEM_ATENDENTE = "atendente"
EMOJIS_REACAO_PERMITIDOS = frozenset({"👍", "❤️", "😂", "😮", "😢", "🙏"})


class WhatsappReacaoErro(ValueError):
    """Validação de reação WhatsApp."""


@dataclass
class ReacaoAgregada:
    emoji: str
    count: int
    reagiu_eu: bool
    atendente_ids: list[int]
    tem_cliente: bool


def validar_emoji_reacao(emoji: str) -> str:
    valor = (emoji or "").strip()
    if valor not in EMOJIS_REACAO_PERMITIDOS:
        raise WhatsappReacaoErro("Emoji de reação inválido.")
    return valor


def aplicar_reacao(
    db: Session,
    mensagem: WhatsappMensagem,
    *,
    origem: str,
    emoji: str | None,
    atendente_id: int | None = None,
) -> WhatsappMensagem:
    """Upsert ou remove reação da origem. emoji None/'' remove."""
    if origem not in (ORIGEM_CLIENTE, ORIGEM_ATENDENTE):
        raise WhatsappReacaoErro("Origem de reação inválida.")
    if mensagem.evento_sistema:
        raise WhatsappReacaoErro("Não é possível reagir a mensagem de sistema.")

    row = (
        db.query(WhatsappMensagemReacao)
        .filter(
            WhatsappMensagemReacao.mensagem_id == mensagem.id,
            WhatsappMensagemReacao.origem == origem,
        )
        .first()
    )
    texto = (emoji or "").strip()
    if not texto:
        if row:
            db.delete(row)
            db.flush()
        db.refresh(mensagem)
        return mensagem

    if origem == ORIGEM_ATENDENTE:
        texto = validar_emoji_reacao(texto)
    # Cliente: aceitar qualquer emoji Unicode curto (WhatsApp livre)
    elif len(texto) > 16:
        texto = texto[:16]

    if row:
        row.emoji = texto
        row.atendente_id = atendente_id if origem == ORIGEM_ATENDENTE else None
    else:
        db.add(
            WhatsappMensagemReacao(
                mensagem_id=mensagem.id,
                origem=origem,
                emoji=texto,
                atendente_id=atendente_id if origem == ORIGEM_ATENDENTE else None,
            )
        )
    db.flush()
    db.refresh(mensagem)
    return mensagem


def agregar_reacoes(
    mensagem: WhatsappMensagem,
    viewer_id: int | None = None,
) -> list[ReacaoAgregada]:
    rows = list(getattr(mensagem, "reacoes", None) or [])
    por_emoji: dict[str, dict] = {}
    for row in rows:
        bucket = por_emoji.setdefault(
            row.emoji,
            {"count": 0, "reagiu_eu": False, "atendente_ids": [], "tem_cliente": False},
        )
        bucket["count"] = int(bucket["count"]) + 1
        if row.origem == ORIGEM_CLIENTE:
            bucket["tem_cliente"] = True
        if row.origem == ORIGEM_ATENDENTE and row.atendente_id is not None:
            bucket["atendente_ids"].append(int(row.atendente_id))
            if viewer_id is not None and row.atendente_id == viewer_id:
                bucket["reagiu_eu"] = True
    return [
        ReacaoAgregada(
            emoji=emoji,
            count=int(data["count"]),
            reagiu_eu=bool(data["reagiu_eu"]),
            atendente_ids=list(data["atendente_ids"]),
            tem_cliente=bool(data["tem_cliente"]),
        )
        for emoji, data in sorted(por_emoji.items(), key=lambda item: (-int(item[1]["count"]), item[0]))
    ]
