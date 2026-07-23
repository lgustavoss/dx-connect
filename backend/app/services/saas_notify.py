"""Notificações internas da equipe DeskRudder (control-plane SaaS)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.services.email_send_sistema import enviar_mensagem_texto_sistema

logger = logging.getLogger(__name__)


def notificar_equipe_saas(db: Session, *, subject: str, body: str) -> bool:
    """Envia e-mail à caixa SAAS_NOTIFY_EMAIL. Retorna False se não configurado / falhou."""
    to_addr = (settings.SAAS_NOTIFY_EMAIL or "").strip()
    if not to_addr:
        logger.info("SAAS_NOTIFY_EMAIL não definido — notificação ignorada: %s", subject)
        return False
    try:
        enviar_mensagem_texto_sistema(db, to_addr=to_addr, subject=subject, body=body)
        return True
    except Exception as e:
        logger.warning("Falha ao notificar equipe SaaS (%s): %s", subject, e)
        return False
