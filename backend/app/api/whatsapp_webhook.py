import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem, WhatsappSettings
from app.services.evolution_inbound import iter_inbound_text_messages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _webhook_autorizado(request: Request, secret: str | None) -> bool:
    if not secret or not str(secret).strip():
        return True
    s = str(secret).strip()
    h = request.headers.get("X-Dx-Webhook-Secret") or request.headers.get("x-dx-webhook-secret")
    if h and h.strip() == s:
        return True
    api = request.headers.get("apikey") or request.headers.get("Apikey")
    return bool(api and api.strip() == s)


def _get_settings(db: Session) -> WhatsappSettings | None:
    return db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()


def _protocolo_proximo_chat(db: Session) -> str:
    r = db.query(func.max(WhatsappChat.id)).scalar() or 0
    return f"WCH-{20000 + int(r) + 1}"


def _chat_aberto_por_wa_id(db: Session, wa_id: str) -> WhatsappChat | None:
    return (
        db.query(WhatsappChat)
        .filter(WhatsappChat.wa_id == wa_id, WhatsappChat.estado != "encerrado")
        .order_by(WhatsappChat.id.desc())
        .first()
    )


@router.post("/evolution")
def evolution_webhook(
    request: Request,
    db: Session = Depends(get_db),
    body: dict = Body(...),
):
    st = _get_settings(db)
    secret = st.webhook_secret if st else None
    if not _webhook_autorizado(request, secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook não autorizado")

    processados = 0
    for item in iter_inbound_text_messages(body):
        wa_id = item["wa_id"]
        text = item["text"]
        wa_mid = item.get("wa_message_id")
        push = item.get("push_name")

        chat = _chat_aberto_por_wa_id(db, wa_id)
        if not chat:
            chat = WhatsappChat(
                protocolo=_protocolo_proximo_chat(db),
                wa_id=wa_id,
                cliente_nome=push,
                estado="aguardando_atendente",
            )
            db.add(chat)
            db.flush()

        msg = WhatsappMensagem(
            chat_id=chat.id,
            direcao="inbound",
            corpo=text,
            wa_message_id=wa_mid,
            atendente_id=None,
        )
        db.add(msg)
        if push and not chat.cliente_nome:
            chat.cliente_nome = push
        try:
            db.commit()
            processados += 1
        except IntegrityError:
            db.rollback()
            logger.info("Webhook Evolution: mensagem duplicada ignorada (wa_message_id=%s)", wa_mid)
        except Exception:
            db.rollback()
            raise

    return {"ok": True, "processados": processados}
