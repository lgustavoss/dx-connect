"""Atendimento anterior do mesmo cliente na conversa WhatsApp (#1105)."""

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models.whatsapp_chat import WhatsappChat


def candidatos_chat_anterior(db: Session, chat: WhatsappChat, *, limite: int = 30) -> list[WhatsappChat]:
    """Chats anteriores do mesmo contato, do mais recente ao mais antigo.

    A ordem é o id (criação). Comparar data no SQL falha no SQLite de teste
    quando o fuso do encerramento não casa com o `created_at`.
    """
    identidade = []
    if chat.funcionario_rede_id:
        identidade.append(WhatsappChat.funcionario_rede_id == chat.funcionario_rede_id)
    wa = (chat.wa_id or "").strip()
    if wa:
        identidade.append(WhatsappChat.wa_id == wa)
    if not identidade:
        return []
    return (
        db.query(WhatsappChat)
        .filter(WhatsappChat.id < chat.id, or_(*identidade))
        .order_by(desc(WhatsappChat.id))
        .limit(limite)
        .all()
    )
