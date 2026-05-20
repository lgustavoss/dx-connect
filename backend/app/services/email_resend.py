"""Envio de e-mail texto via API HTTP da Resend (sem SMTP)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from email.utils import formataddr

from app.services.email_inbound_parse import normalize_message_id
from app.services.system_email_config import TransactionalEmailConfig

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
DX_CONNECT_USER_AGENT = "DX-Connect/1.0 (transactional-email)"


def _header_message_id_value(mid: str | None) -> str:
    s = (mid or "").strip()
    if not s:
        return ""
    if s.startswith("<") and s.endswith(">"):
        return s
    return f"<{s}>"


def enviar_via_resend(
    cfg: TransactionalEmailConfig,
    *,
    to_addr: str,
    subject: str,
    body: str,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> str:
    """
    Envia mensagem texto e devolve um identificador estável para ``Message-ID`` interno (normalizado).
    """
    to_addr = (to_addr or "").strip()
    if not to_addr:
        raise ValueError("Destinatário vazio.")

    hdrs: dict[str, str] = {}
    if in_reply_to:
        hdrs["In-Reply-To"] = _header_message_id_value(in_reply_to)
    if references:
        hdrs["References"] = references.strip()[:9980]
    elif in_reply_to:
        hdrs["References"] = _header_message_id_value(in_reply_to)

    from_raw = (cfg.from_email or "").strip()
    if not from_raw:
        raise ValueError("Remetente (from) não configurado.")
    fn = (cfg.from_name or "").strip()
    from_line = formataddr((fn or None, from_raw)) if fn else from_raw

    payload: dict = {
        "from": from_line.replace("\n", " ").replace("\r", ""),
        "to": [to_addr],
        "subject": (subject or "(sem assunto)")[:998],
        "text": body,
    }
    if hdrs:
        payload["headers"] = hdrs

    reply_to = (cfg.reply_to or "").strip()
    if reply_to:
        payload["reply_to"] = [reply_to]

    raw_body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        RESEND_API_URL,
        data=raw_body,
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
            "User-Agent": DX_CONNECT_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        logger.warning("Resend HTTP %s: %s", e.code, detail[:500])
        hint = " Verifique domínio/API key."
        if "1010" in detail:
            hint = " (código 1010: falta User-Agent na requisição — atualize o backend)."
        raise ValueError(f"Resend rejeitou o envio (HTTP {e.code}).{hint}") from e

    try:
        out = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        raise ValueError("Resposta inválida da API Resend.") from e

    rid = (out.get("id") or "").strip()
    if not rid:
        raise ValueError("Resend não devolveu id na resposta.")
    synthetic = f"{rid}@resend.dx-connect.local"
    return normalize_message_id(synthetic) or synthetic
