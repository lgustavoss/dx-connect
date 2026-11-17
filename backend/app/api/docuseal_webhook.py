"""Webhook público do DocuSeal — conclusão/recusa de assinatura (#1380)."""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.contrato_assinatura import ContratoAssinaturaWebhookAck
from app.services import contrato_assinatura as assinatura_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks-docuseal"])


def _check_secret(request: Request) -> None:
    secret = (settings.DOCUSEAL_WEBHOOK_SECRET or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook DocuSeal não está configurado (defina DOCUSEAL_WEBHOOK_SECRET).",
        )
    hdr = (
        request.headers.get("X-Docuseal-Secret")
        or request.headers.get("X-Dx-Docuseal-Webhook-Secret")
        or ""
    ).strip()
    if not hdr or len(hdr) != len(secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado.")
    if not secrets.compare_digest(hdr, secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado.")


@router.post(
    "/docuseal",
    response_model=ContratoAssinaturaWebhookAck,
    summary="Webhook DocuSeal (assinatura de contrato)",
)
async def post_docuseal(request: Request, db: Session = Depends(get_db)):
    _check_secret(request)
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON inválido.") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON inválido.")

    env = assinatura_svc.processar_webhook_docuseal(db, body)
    db.commit()
    if env is None:
        return ContratoAssinaturaWebhookAck(ok=True)
    return ContratoAssinaturaWebhookAck(
        ok=True,
        contrato_id=env.contrato_id,
        assinatura_id=env.id,
        status=env.status,
    )
