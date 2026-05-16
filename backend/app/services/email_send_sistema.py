"""
Envio de e-mail do sistema (tickets, alertas futuros): camada única sobre Resend.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.email_resend import enviar_via_resend
from app.services.system_email_config import get_singleton_email_settings, transactional_config_from_row


def enviar_mensagem_texto_sistema(
    db: Session,
    *,
    to_addr: str,
    subject: str,
    body: str,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> str:
    """
    Envia e-mail transaccional. Levanta ``ValueError`` com mensagem legível se não houver configuração.
    """
    row = get_singleton_email_settings(db)
    cfg = transactional_config_from_row(row)
    if not cfg:
        raise ValueError(
            "Envio de e-mail não configurado na plataforma. Defina RESEND_API_KEY e "
            "TRANSACTIONAL_FROM_EMAIL no servidor (ver documentação de deploy)."
        )
    return enviar_via_resend(
        cfg,
        to_addr=to_addr,
        subject=subject,
        body=body,
        in_reply_to=in_reply_to,
        references=references,
    )
