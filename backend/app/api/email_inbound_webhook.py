"""
Webhook público (segredo em cabeçalho) para ingestão de e-mail → ticket (v1).

Compatível com formulário estilo SendGrid (from, subject, text, headers, email)
ou JSON de teste: ``{"rfc822": "..."}`` com mensagem MIME completa.
"""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.email_inbound import EmailInboundWebhookResponse
from app.services.email_inbound_dispatch import dispatch_parsed_inbound
from app.services.email_inbound_parse import parse_from_rfc822_bytes, parse_from_sendgrid_like_form

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks-email"])


def _check_secret(request: Request) -> None:
    secret = (settings.EMAIL_INBOUND_WEBHOOK_SECRET or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestão por webhook não está configurada (defina EMAIL_INBOUND_WEBHOOK_SECRET).",
        )
    hdr = (request.headers.get("X-Dx-Email-Webhook-Secret") or "").strip()
    if not hdr or len(hdr) != len(secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado.")
    if not secrets.compare_digest(hdr, secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado.")


async def _form_dict(request: Request) -> dict[str, str]:
    form = await request.form()
    out: dict[str, str] = {}
    for key, val in form.multi_items():
        if hasattr(val, "read"):
            raw = await val.read()  # type: ignore[union-attr]
            out[str(key)] = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        else:
            out[str(key)] = str(val)
    return out


@router.post(
    "/email-inbound",
    response_model=EmailInboundWebhookResponse,
    summary="Ingestão de e-mail (webhook)",
    description=(
        "Recebe MIME (JSON `rfc822`) ou formulário estilo SendGrid. "
        "Autenticação por cabeçalho `X-Dx-Email-Webhook-Secret`. "
        "Requer variáveis de ambiente `EMAIL_INBOUND_*` (ver documentação do projeto)."
    ),
)
async def post_email_inbound(request: Request, db: Session = Depends(get_db)):
    _check_secret(request)

    ct = (request.headers.get("content-type") or "").lower()
    try:
        if "application/json" in ct:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("JSON inválido.")
            raw = body.get("rfc822")
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError('Corpo JSON deve incluir a string "rfc822" com a mensagem MIME completa.')
            parsed = parse_from_rfc822_bytes(raw.encode("utf-8", errors="replace"))
        else:
            fields = await _form_dict(request)
            parsed = parse_from_sendgrid_like_form(fields)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.warning("Falha ao interpretar e-mail inbound: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível interpretar a mensagem (formato inválido).",
        ) from e

    try:
        return dispatch_parsed_inbound(db, parsed)
    except ValueError as e:
        detail = str(e)
        if "Configure EMAIL_INBOUND" in detail:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from e
