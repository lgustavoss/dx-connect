import json
import re
from datetime import datetime, timezone
from urllib import error, request

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Ticket, TicketMensagem
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage


def normalize_phone(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_conversation(
    db: Session,
    *,
    wa_id: str,
    profile_name: str | None,
    phone_number: str,
) -> WhatsAppConversation:
    normalized = normalize_phone(phone_number) or normalize_phone(wa_id)
    conv = db.query(WhatsAppConversation).filter(WhatsAppConversation.wa_id == wa_id).first()
    if conv:
        changed = False
        if profile_name and conv.profile_name != profile_name:
            conv.profile_name = profile_name
            changed = True
        if normalized and conv.phone_number != normalized:
            conv.phone_number = normalized
            changed = True
        if changed:
            conv.updated_at = utcnow()
        return conv
    conv = WhatsAppConversation(
        wa_id=wa_id,
        profile_name=profile_name,
        phone_number=normalized or wa_id,
        status="open",
        ai_enabled=False,
        ai_mode="assist",
        last_message_at=utcnow(),
    )
    db.add(conv)
    db.flush()
    return conv


def serialize_payload(data: dict | list | None) -> str | None:
    if data is None:
        return None
    return json.dumps(data, ensure_ascii=True)


def create_inbound_message(
    db: Session,
    *,
    conversation: WhatsAppConversation,
    ticket: Ticket | None,
    wa_message_id: str | None,
    sender_phone: str | None,
    recipient_phone: str | None,
    message_type: str,
    body: str | None,
    media_url: str | None = None,
    mime_type: str | None = None,
    filename: str | None = None,
    payload: dict | list | None = None,
    created_at: datetime | None = None,
) -> WhatsAppMessage:
    if wa_message_id:
        existing = db.query(WhatsAppMessage).filter(WhatsAppMessage.wa_message_id == wa_message_id).first()
        if existing:
            return existing
    msg = WhatsAppMessage(
        conversation_id=conversation.id,
        ticket_id=ticket.id if ticket else None,
        wa_message_id=wa_message_id,
        direction="inbound",
        sender_phone=normalize_phone(sender_phone),
        recipient_phone=normalize_phone(recipient_phone),
        message_type=message_type,
        body=body,
        media_url=media_url,
        mime_type=mime_type,
        filename=filename,
        status="received",
        payload_json=serialize_payload(payload),
        created_at=created_at or utcnow(),
    )
    db.add(msg)
    conversation.last_message_at = msg.created_at
    conversation.updated_at = utcnow()
    db.flush()
    if ticket and body and body.strip():
        db.add(
            TicketMensagem(
                ticket_id=ticket.id,
                atendente_id=None,
                tipo="cliente",
                corpo=body.strip(),
                created_at=msg.created_at,
            )
        )
    return msg


def create_outbound_message(
    db: Session,
    *,
    conversation: WhatsAppConversation,
    ticket: Ticket | None,
    body: str,
    wa_message_id: str | None,
    status: str,
    payload: dict | list | None = None,
    auto_generated: bool = False,
) -> WhatsAppMessage:
    msg = WhatsAppMessage(
        conversation_id=conversation.id,
        ticket_id=ticket.id if ticket else None,
        wa_message_id=wa_message_id,
        direction="outbound",
        sender_phone=normalize_phone(settings.WHATSAPP_BUSINESS_PHONE),
        recipient_phone=conversation.phone_number,
        message_type="text",
        body=body,
        status=status,
        payload_json=serialize_payload(payload),
        created_at=utcnow(),
    )
    db.add(msg)
    conversation.last_message_at = msg.created_at
    conversation.updated_at = utcnow()
    db.flush()
    if ticket:
        prefix = "[IA] " if auto_generated else ""
        db.add(
            TicketMensagem(
                ticket_id=ticket.id,
                atendente_id=None,
                tipo="publico",
                corpo=f"{prefix}{body}",
                created_at=msg.created_at,
            )
        )
    return msg


def update_message_status(db: Session, wa_message_id: str, status_value: str) -> None:
    msg = db.query(WhatsAppMessage).filter(WhatsAppMessage.wa_message_id == wa_message_id).first()
    if msg:
        msg.status = status_value
        msg.updated_at = utcnow()


def whatsapp_configured() -> bool:
    return bool(
        settings.WHATSAPP_ACCESS_TOKEN
        and settings.WHATSAPP_PHONE_NUMBER_ID
        and settings.WHATSAPP_VERIFY_TOKEN
    )


def send_whatsapp_text(to_phone: str, body: str) -> tuple[str | None, dict]:
    api_version = settings.WHATSAPP_API_VERSION
    phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
    if not settings.WHATSAPP_ACCESS_TOKEN or not phone_id:
        raise RuntimeError("WhatsApp nao configurado no servidor.")
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": normalize_phone(to_phone),
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    req = request.Request(
        url=f"https://graph.facebook.com/{api_version}/{phone_id}/messages",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = "Erro ao enviar mensagem pelo WhatsApp."
        try:
            payload_err = json.loads(exc.read().decode("utf-8"))
            detail = payload_err.get("error", {}).get("message") or detail
        except Exception:
            pass
        raise RuntimeError(detail) from exc
    except Exception as exc:
        raise RuntimeError("Falha ao comunicar com a API do WhatsApp.") from exc
    message_id = None
    contacts_messages = data.get("messages") or []
    if contacts_messages:
        message_id = contacts_messages[0].get("id")
    return message_id, data


def render_conversation_read(conv: WhatsAppConversation) -> dict:
    return {
        "id": conv.id,
        "wa_id": conv.wa_id,
        "profile_name": conv.profile_name,
        "phone_number": conv.phone_number,
        "status": conv.status,
        "ai_enabled": bool(conv.ai_enabled),
        "ai_mode": conv.ai_mode,
        "last_message_at": conv.last_message_at,
        "linked_ticket_id": conv.linked_ticket_id,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "linked_ticket_protocolo": conv.linked_ticket.protocolo if conv.linked_ticket else None,
        "linked_ticket_assunto": conv.linked_ticket.assunto if conv.linked_ticket else None,
        "linked_ticket_empresa_nome": conv.linked_ticket.empresa.nome if conv.linked_ticket and conv.linked_ticket.empresa else None,
        "messages": [
            {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "ticket_id": msg.ticket_id,
                "wa_message_id": msg.wa_message_id,
                "direction": msg.direction,
                "sender_phone": msg.sender_phone,
                "recipient_phone": msg.recipient_phone,
                "message_type": msg.message_type,
                "body": msg.body,
                "media_url": msg.media_url,
                "mime_type": msg.mime_type,
                "filename": msg.filename,
                "status": msg.status,
                "created_at": msg.created_at,
            }
            for msg in conv.messages
        ],
    }


def get_conversation_with_messages(db: Session, conversation_id: int) -> WhatsAppConversation | None:
    return (
        db.query(WhatsAppConversation)
        .options(
            joinedload(WhatsAppConversation.linked_ticket).joinedload(Ticket.empresa),
            joinedload(WhatsAppConversation.linked_ticket).joinedload(Ticket.setor),
            joinedload(WhatsAppConversation.linked_ticket).joinedload(Ticket.status),
            joinedload(WhatsAppConversation.messages),
        )
        .filter(WhatsAppConversation.id == conversation_id)
        .first()
    )
