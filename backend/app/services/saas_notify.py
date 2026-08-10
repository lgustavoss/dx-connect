"""Notificações internas da equipe DeskRudder (control-plane SaaS)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.cliente_saas import ClienteSaaS
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


def notificar_contacto_entrega(
    db: Session,
    row: ClienteSaaS,
    *,
    forcar: bool = False,
) -> bool:
    """Avisa o contacto da licença de que a instância está pronta (pós-health)."""
    to_addr = (row.contato_email or "").strip()
    if not to_addr:
        logger.info("Sem contato_email — entrega ignorada para slug=%s", row.slug)
        return False
    if row.entrega_notificada_em is not None and not forcar:
        logger.info("Entrega já notificada em %s — slug=%s", row.entrega_notificada_em, row.slug)
        return False

    url = (row.instancia_url or "").strip() or f"(URL pendente — slug {row.slug})"
    if url and "://" not in url and not url.startswith("("):
        url = f"https://{url}"
    nome = (row.contato_nome or row.nome or "olá").strip()
    subject = f"DeskRudder — ambiente pronto ({row.nome})"
    body = (
        f"Olá {nome},\n\n"
        f"O ambiente DeskRudder de «{row.nome}» está disponível.\n\n"
        f"Acesso: {url}\n"
        f"Login da equipa: {url.rstrip('/')}/login\n\n"
        "As credenciais iniciais (admin) são as definidas no provisionamento; "
        "se ainda não as recebeu, a equipa DeskRudder envia-as em seguida.\n\n"
        "— Equipa DeskRudder\n"
    )
    try:
        enviar_mensagem_texto_sistema(db, to_addr=to_addr, subject=subject, body=body)
        row.entrega_notificada_em = datetime.now(timezone.utc)
        db.flush()
        notificar_equipe_saas(
            db,
            subject=f"[DeskRudder] Entrega enviada — {row.slug}",
            body=f"Contacto notificado: {to_addr}\nURL: {url}\n",
        )
        return True
    except Exception as e:
        logger.warning("Falha ao notificar contacto de entrega (%s): %s", row.slug, e)
        return False
