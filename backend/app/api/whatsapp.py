from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session, joinedload

from app.api.chat_assistant import generate_chat_reply
from app.config import settings
from app.core.auth import obter_atendente_atual
from app.database import get_db
from app.models import Atendente, Ticket
from app.models.whatsapp import WhatsAppConversation
from app.schemas.chat_assistant import ChatAssistantSuggestRequest
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.whatsapp import (
    WhatsAppAiAssistRequest,
    WhatsAppAiAssistResponse,
    WhatsAppConversationRead,
    WhatsAppConversationUpdate,
    WhatsAppOutboundMessageCreate,
)
from app.services.whatsapp import (
    create_inbound_message,
    create_outbound_message,
    ensure_conversation,
    get_conversation_with_messages,
    normalize_phone,
    render_conversation_read,
    send_whatsapp_text,
    update_message_status,
)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _conversation_query(db: Session):
    return db.query(WhatsAppConversation).options(
        joinedload(WhatsAppConversation.linked_ticket).joinedload(Ticket.empresa),
        joinedload(WhatsAppConversation.linked_ticket).joinedload(Ticket.setor),
        joinedload(WhatsAppConversation.linked_ticket).joinedload(Ticket.status),
        joinedload(WhatsAppConversation.messages),
    )


def _get_ticket_or_none(db: Session, ticket_id: int | None) -> Ticket | None:
    if ticket_id is None:
        return None
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def _build_ai_payload(conv: WhatsAppConversation, objective: str | None) -> ChatAssistantSuggestRequest:
    ticket = conv.linked_ticket
    recent = conv.messages[-12:]
    conversation = []
    for message in recent:
        role = "customer" if message.direction == "inbound" else "agent"
        if message.direction == "system":
            role = "internal"
        if message.body:
            conversation.append(
                {
                    "role": role,
                    "content": message.body,
                    "created_at": message.created_at,
                }
            )
    assunto = ticket.assunto if ticket else "Atendimento via WhatsApp"
    return ChatAssistantSuggestRequest(
        ticket={
            "protocolo": ticket.protocolo if ticket else f"WA-{conv.id}",
            "assunto": assunto,
            "empresa_nome": ticket.empresa.nome if ticket and ticket.empresa else conv.profile_name,
            "setor_nome": ticket.setor.nome if ticket and ticket.setor else "Atendimento inicial",
            "status_nome": ticket.status.nome if ticket and ticket.status else conv.status,
        },
        conversation=conversation,
        objective=objective or "Responder o cliente no WhatsApp com o proximo passo mais util.",
        tone="consultivo",
    )


def _fallback_ai_reply(conv: WhatsAppConversation) -> str:
    base_name = conv.profile_name or "cliente"
    if conv.linked_ticket:
        return (
            f"Ola, {base_name}. Recebemos sua mensagem e seguimos acompanhando pelo ticket "
            f"{conv.linked_ticket.protocolo}. Se puder, envie mais detalhes do que apareceu na tela "
            "e o horario da ocorrencia para acelerarmos a tratativa."
        )
    return (
        f"Ola, {base_name}. Recebemos sua mensagem no WhatsApp do suporte. "
        "Para eu te ajudar melhor, me envie a unidade/posto, o que aconteceu e qual o impacto na operacao."
    )


@router.get("/webhook")
def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    verify_token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
):
    if not settings.WHATSAPP_VERIFY_TOKEN or verify_token != settings.WHATSAPP_VERIFY_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token de verificacao invalido")
    if mode != "subscribe":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Modo de webhook invalido")
    return Response(content=challenge, media_type="text/plain")


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.json()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            metadata = value.get("metadata") or {}
            recipient_phone = metadata.get("display_phone_number") or metadata.get("phone_number_id")
            contacts = value.get("contacts") or []
            contact_map = {
                item.get("wa_id"): (item.get("profile") or {}).get("name")
                for item in contacts
                if item.get("wa_id")
            }

            for status_item in value.get("statuses") or []:
                if status_item.get("id") and status_item.get("status"):
                    update_message_status(db, status_item["id"], status_item["status"])

            for message in value.get("messages") or []:
                from_phone = normalize_phone(message.get("from"))
                profile_name = contact_map.get(message.get("from"))
                conv = ensure_conversation(
                    db,
                    wa_id=message.get("from") or from_phone,
                    profile_name=profile_name,
                    phone_number=from_phone,
                )
                ticket = _get_ticket_or_none(db, conv.linked_ticket_id)
                message_type = message.get("type") or "text"
                body = None
                media_url = None
                mime_type = None
                filename = None

                if message_type == "text":
                    body = (message.get("text") or {}).get("body")
                elif message_type == "button":
                    body = (message.get("button") or {}).get("text")
                elif message_type == "interactive":
                    interactive = message.get("interactive") or {}
                    body = (
                        ((interactive.get("button_reply") or {}).get("title"))
                        or ((interactive.get("list_reply") or {}).get("title"))
                        or "Interacao recebida"
                    )
                else:
                    media = message.get(message_type) or {}
                    body = media.get("caption") or f"Mensagem recebida ({message_type})"
                    media_url = media.get("id")
                    mime_type = media.get("mime_type")
                    filename = media.get("filename")

                timestamp = message.get("timestamp")
                created_at = None
                if timestamp:
                    try:
                        created_at = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                    except Exception:
                        created_at = None
                create_inbound_message(
                    db,
                    conversation=conv,
                    ticket=ticket,
                    wa_message_id=message.get("id"),
                    sender_phone=from_phone,
                    recipient_phone=recipient_phone,
                    message_type=message_type,
                    body=body,
                    media_url=media_url,
                    mime_type=mime_type,
                    filename=filename,
                    payload=message,
                    created_at=created_at,
                )
                db.flush()
                if conv.ai_enabled:
                    assist = _fallback_ai_reply(conv)
                    try:
                        ai_response = generate_chat_reply(_build_ai_payload(conv, None))
                        assist = ai_response.reply
                        source = "openai"
                    except Exception:
                        source = "fallback"
                    try:
                        message_id, raw = send_whatsapp_text(conv.phone_number, assist)
                        create_outbound_message(
                            db,
                            conversation=conv,
                            ticket=ticket,
                            body=assist,
                            wa_message_id=message_id,
                            status="sent",
                            payload={"provider": source, "response": raw},
                            auto_generated=True,
                        )
                    except Exception:
                        pass
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/conversations", response_model=ListaPaginada[WhatsAppConversationRead])
def list_conversations(
    busca: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
):
    q = _conversation_query(db)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(
            (WhatsAppConversation.profile_name.ilike(term))
            | (WhatsAppConversation.phone_number.ilike(term))
        )
    total = q.count()
    rows = q.order_by(WhatsAppConversation.last_message_at.desc().nullslast(), WhatsAppConversation.id.desc()).offset(offset).limit(limit).all()
    return ListaPaginada(items=[render_conversation_read(row) for row in rows], total=total)


@router.get("/conversations/{conversation_id}", response_model=WhatsAppConversationRead)
def get_conversation(
    conversation_id: int,
    _: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
):
    conv = get_conversation_with_messages(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa nao encontrada")
    return render_conversation_read(conv)


@router.patch("/conversations/{conversation_id}", response_model=WhatsAppConversationRead)
def update_conversation(
    conversation_id: int,
    data: WhatsAppConversationUpdate,
    _: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
):
    conv = get_conversation_with_messages(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa nao encontrada")
    patch = data.model_dump(exclude_unset=True)
    if "linked_ticket_id" in patch and patch["linked_ticket_id"] is not None:
        ticket = db.query(Ticket).filter(Ticket.id == patch["linked_ticket_id"]).first()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket nao encontrado")
        conv.linked_ticket_id = ticket.id
    elif "linked_ticket_id" in patch:
        conv.linked_ticket_id = None
    for field in ("ai_enabled", "ai_mode", "status", "profile_name"):
        if field in patch:
            setattr(conv, field, patch[field])
    db.commit()
    conv = get_conversation_with_messages(db, conversation_id)
    assert conv is not None
    return render_conversation_read(conv)


@router.post("/conversations/{conversation_id}/messages", response_model=WhatsAppConversationRead)
def send_message(
    conversation_id: int,
    data: WhatsAppOutboundMessageCreate,
    _: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
):
    conv = get_conversation_with_messages(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa nao encontrada")
    ticket = _get_ticket_or_none(db, conv.linked_ticket_id)
    try:
        message_id, raw = send_whatsapp_text(conv.phone_number, data.body.strip())
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    create_outbound_message(
        db,
        conversation=conv,
        ticket=ticket,
        body=data.body.strip(),
        wa_message_id=message_id,
        status="sent",
        payload=raw,
        auto_generated=data.auto_generated,
    )
    db.commit()
    conv = get_conversation_with_messages(db, conversation_id)
    assert conv is not None
    return render_conversation_read(conv)


@router.post("/conversations/{conversation_id}/assist", response_model=WhatsAppAiAssistResponse)
def assist_customer(
    conversation_id: int,
    data: WhatsAppAiAssistRequest,
    _: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
):
    conv = get_conversation_with_messages(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa nao encontrada")
    source = "openai"
    try:
        ai = generate_chat_reply(_build_ai_payload(conv, data.objective))
        reply = ai.reply
    except Exception:
        source = "fallback"
        reply = _fallback_ai_reply(conv)

    sent = False
    if data.auto_send:
        try:
            message_id, raw = send_whatsapp_text(conv.phone_number, reply)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        create_outbound_message(
            db,
            conversation=conv,
            ticket=_get_ticket_or_none(db, conv.linked_ticket_id),
            body=reply,
            wa_message_id=message_id,
            status="sent",
            payload=raw,
            auto_generated=True,
        )
        db.commit()
        sent = True
    return WhatsAppAiAssistResponse(reply=reply, sent=sent, source=source)  # type: ignore[arg-type]
