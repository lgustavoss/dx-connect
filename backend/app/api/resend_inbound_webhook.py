"""
Webhook Resend ``email.received`` → ticket.

Configurar na Resend: evento ``email.received``, URL
``POST /v1/webhooks/resend-inbound``, segredo em ``RESEND_WEBHOOK_SECRET``.
Requer ``INBOUND_EMAIL_DOMAIN`` (ex.: ``notify.duplexsoft.com.br``) com **Receiving** activo na Resend.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.email_inbound import EmailInboundWebhookResponse
from app.services.email_inbound_dispatch import dispatch_parsed_inbound
from app.services.email_resend_receiving import (
    fetch_received_email_with_retry,
    parsed_from_resend_received,
    parsed_from_resend_webhook_data,
    resend_api_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks-email"])


def _verify_svix(request: Request, body: bytes) -> None:
    secret = (settings.RESEND_WEBHOOK_SECRET or "").strip()
    if not secret:
        logger.warning("RESEND_WEBHOOK_SECRET ausente: webhook Resend inbound aceite sem verificação Svix.")
        return
    try:
        from svix.webhooks import Webhook
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pacote svix não instalado (necessário para verificar webhooks Resend).",
        ) from e

    wh = Webhook(secret)
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }
    try:
        wh.verify(body.decode("utf-8") if isinstance(body, bytes) else body, headers)
    except Exception as e:
        logger.warning("Assinatura Svix inválida no webhook Resend: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook não autorizado.") from e


@router.post(
    "/resend-inbound",
    response_model=EmailInboundWebhookResponse,
    summary="Ingestão Resend (email.received)",
    description=(
        "Recebe eventos Resend ``email.received``, obtém o MIME via API e abre/anexa ticket. "
        "Requer ``RESEND_API_KEY``, domínio inbound com recepção e ``RESEND_WEBHOOK_SECRET`` (recomendado)."
    ),
    responses={
        200: {"description": "Evento ignorado (não é email.received) — corpo vazio ou mensagem simples"},
    },
)
async def post_resend_inbound(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    _verify_svix(request, body)

    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido.") from e

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido.")

    event_type = (payload.get("type") or "").strip()
    if event_type != "email.received":
        return JSONResponse({"ignored": True, "type": event_type or None})

    data = payload.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campo data ausente.")

    email_id = (data.get("email_id") or data.get("id") or "").strip()
    if not email_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email_id ausente no evento.")

    try:
        api_key = resend_api_key()
        parsed = None
        try:
            received = fetch_received_email_with_retry(email_id, api_key=api_key)
            parsed = parsed_from_resend_received(received, fallback_email_id=email_id)
        except ValueError as fetch_err:
            logger.warning(
                "GET Resend receiving para %s falhou (%s); usa payload do webhook.",
                email_id,
                fetch_err,
            )
            parsed = parsed_from_resend_webhook_data(data, fallback_email_id=email_id)
        return dispatch_parsed_inbound(db, parsed)
    except ValueError as e:
        detail = str(e)
        if "Configure EMAIL_INBOUND_DEFAULT_SETOR_ID" in detail:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Falha ao processar webhook Resend inbound: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível processar o e-mail recebido via Resend.",
        ) from e
