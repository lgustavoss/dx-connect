"""Envio simples de e-mail texto (SMTP a partir de `SmtpRuntimeConfig`)."""

from __future__ import annotations

import logging
import smtplib
import uuid
from email.message import EmailMessage
from email.utils import formataddr

from app.services.email_inbound_parse import normalize_message_id
from app.services.system_email_config import SmtpRuntimeConfig

logger = logging.getLogger(__name__)


def _message_id_header_value(normalized_id: str) -> str:
    s = (normalized_id or "").strip()
    if not s:
        return ""
    if s.startswith("<") and s.endswith(">"):
        return s
    return f"<{s}>"


def enviar_texto_smtp(
    cfg: SmtpRuntimeConfig,
    *,
    to_addr: str,
    subject: str,
    body: str,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> str:
    """
    Envia uma mensagem texto e devolve o **Message-ID** gerado (normalizado, sem <>).
    Levanta excepção se SMTP falhar ou remetente inválido.
    """
    to_addr = (to_addr or "").strip()
    if not to_addr:
        raise ValueError("Destinatário (to) vazio.")

    from_addr = (cfg.from_email or (cfg.user or "")).strip()
    if not from_addr:
        raise ValueError("Remetente SMTP não configurado (smtp_from_email / smtp_user).")
    if not cfg.password or not (cfg.user or "").strip():
        raise ValueError("Credenciais SMTP incompletas.")

    our_mid = f"<{uuid.uuid4()}@{cfg.host or 'dx-connect.local'}>"
    msg = EmailMessage()
    msg["Subject"] = (subject or "(sem assunto)")[:998]
    msg["From"] = formataddr(((cfg.from_name or "").strip() or None, from_addr))
    msg["To"] = to_addr
    msg["Message-ID"] = our_mid
    if in_reply_to:
        msg["In-Reply-To"] = _message_id_header_value(in_reply_to)
    if references:
        msg["References"] = references.strip()[:9980]
    elif in_reply_to:
        msg["References"] = _message_id_header_value(in_reply_to)
    msg.set_content(body, subtype="plain", charset="utf-8")

    with smtplib.SMTP(host=cfg.host, port=cfg.port, timeout=20) as smtp:
        smtp.ehlo()
        if cfg.use_starttls:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(cfg.user or "", cfg.password)
        smtp.send_message(msg)

    inner = our_mid.strip().strip("<>")
    return normalize_message_id(inner) or inner
