"""Recepção de e-mails via API Resend (Receiving) após webhook ``email.received``."""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import replace
from email.utils import getaddresses, parseaddr

from sqlalchemy.orm import Session

from app.config import settings
from app.services.email_inbound_parse import (
    ParsedInboundEmail,
    normalize_message_id,
    parse_from_rfc822_bytes,
)
from app.services.email_resend import DX_CONNECT_USER_AGENT
from app.services.system_email_config import get_singleton_email_settings, transactional_config_from_row

logger = logging.getLogger(__name__)

RESEND_RECEIVING_API = "https://api.resend.com/emails/receiving"


def resend_api_key() -> str:
    key = (settings.RESEND_API_KEY or "").strip()
    if not key:
        raise ValueError("RESEND_API_KEY não configurada no servidor.")
    return key


def resend_api_key_for_db(db: Session) -> str:
    """Mesma origem da key que o envio transaccional (BD cifrada ou ``RESEND_API_KEY`` no env)."""
    row = get_singleton_email_settings(db)
    cfg = transactional_config_from_row(row)
    if cfg and (cfg.api_key or "").strip():
        return cfg.api_key.strip()
    return resend_api_key()


def _resend_json_request(api_key: str, email_id: str) -> dict:
    req = urllib.request.Request(
        f"{RESEND_RECEIVING_API}/{email_id}",
        method="GET",
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": DX_CONNECT_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        logger.warning("Resend receiving HTTP %s: %s", e.code, detail[:500])
        msg = detail[:300]
        try:
            err = json.loads(detail)
            if isinstance(err, dict):
                msg = str(err.get("message") or err.get("detail") or msg)
        except json.JSONDecodeError:
            pass
        raise ValueError(f"Resend receiving falhou (HTTP {e.code}): {msg}") from e
    try:
        out = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        raise ValueError("Resposta inválida da API Resend receiving.") from e
    if not isinstance(out, dict):
        raise ValueError("Resposta inválida da API Resend receiving.")
    return out


def fetch_received_email(email_id: str, *, api_key: str | None = None) -> dict:
    key = (api_key or "").strip() or resend_api_key()
    eid = (email_id or "").strip()
    if not eid:
        raise ValueError("email_id vazio.")
    return _resend_json_request(key, eid)


def fetch_received_email_with_retry(
    email_id: str,
    *,
    api_key: str | None = None,
    attempts: int = 4,
) -> dict:
    """GET /emails/receiving/{id} com espera breve (o webhook pode chegar antes do índice)."""
    last: ValueError | None = None
    for i in range(max(1, attempts)):
        try:
            return fetch_received_email(email_id, api_key=api_key)
        except ValueError as e:
            last = e
            err = str(e)
            if i < attempts - 1 and ("HTTP 400" in err or "HTTP 404" in err):
                time.sleep(0.5 * (2**i))
                continue
            raise
    if last:
        raise last
    raise ValueError("Resend receiving falhou.")


def parsed_from_resend_webhook_data(data: dict, *, fallback_email_id: str) -> ParsedInboundEmail:
    """
    Monta ingestão a partir do payload do webhook (sem corpo completo).
    Usado quando a API GET receiving falha ou ainda não indexou o e-mail.
    """
    mid = normalize_message_id(data.get("message_id"))
    if not mid:
        mid = normalize_message_id(f"{fallback_email_id}@resend-inbound.dx-connect.local")

    from_raw = (data.get("from") or "").strip()
    name, addr = parseaddr(from_raw)
    display = (f"{name} <{addr}>" if name else from_raw).strip() or addr or "(sem remetente)"
    subj = (data.get("subject") or "").strip() or "(sem assunto)"
    to_list = _addresses_lower(data.get("to"))

    return ParsedInboundEmail(
        message_id=mid,
        in_reply_to=None,
        references=None,
        from_display=display[:512],
        from_email=(addr.strip() or None),
        subject=subj[:500],
        body_text="(Mensagem recebida por e-mail; corpo não obtido da API Resend no momento do webhook.)",
        to_recipients=to_list,
    )


def _download_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url.strip(),
        method="GET",
        headers={"User-Agent": DX_CONNECT_USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _header_map_value(headers: dict | None, name: str) -> str | None:
    if not headers or not isinstance(headers, dict):
        return None
    for key, val in headers.items():
        if str(key).lower() == name.lower():
            s = str(val).strip()
            return s or None
    return None


def _addresses_lower(addrs: list[str] | tuple[str, ...] | str | None) -> tuple[str, ...]:
    out: list[str] = []
    if addrs is None:
        return ()
    items = [addrs] if isinstance(addrs, str) else list(addrs)
    for item in items:
        for _n, a in getaddresses([str(item)]):
            x = (a or "").strip().lower()
            if x and x not in out:
                out.append(x)
    return tuple(out)


def parsed_from_resend_received(data: dict, *, fallback_email_id: str | None = None) -> ParsedInboundEmail:
    """Converte resposta GET /emails/receiving/{id} em ``ParsedInboundEmail``."""
    raw_block = data.get("raw") if isinstance(data.get("raw"), dict) else {}
    download_url = (raw_block.get("download_url") or "").strip()
    if download_url:
        try:
            return parse_from_rfc822_bytes(_download_bytes(download_url))
        except Exception as e:
            logger.warning("Falha ao obter MIME bruto da Resend (%s); usa campos da API.", e)

    headers = data.get("headers") if isinstance(data.get("headers"), dict) else {}
    mid = normalize_message_id(data.get("message_id")) or normalize_message_id(
        _header_map_value(headers, "Message-ID")
    )
    if not mid and fallback_email_id:
        mid = normalize_message_id(f"{fallback_email_id}@resend-inbound.dx-connect.local")

    from_raw = (data.get("from") or _header_map_value(headers, "From") or "").strip()
    name, addr = parseaddr(from_raw)
    display = (f"{name} <{addr}>" if name else from_raw).strip() or addr or "(sem remetente)"

    subj = (data.get("subject") or _header_map_value(headers, "Subject") or "").strip() or "(sem assunto)"
    text = (data.get("text") or "").strip()
    if not text:
        html = (data.get("html") or "").strip()
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = "(corpo vazio ou não texto)"

    irt = normalize_message_id(_header_map_value(headers, "In-Reply-To"))
    refs = (_header_map_value(headers, "References") or "").strip() or None

    to_list = _addresses_lower(data.get("to"))
    if not to_list:
        to_list = _addresses_lower(_header_map_value(headers, "To"))

    parsed = ParsedInboundEmail(
        message_id=mid,
        in_reply_to=irt,
        references=refs,
        from_display=display[:512],
        from_email=(addr.strip() or None),
        subject=subj[:500],
        body_text=text,
        to_recipients=to_list,
    )
    if not parsed.message_id and fallback_email_id:
        return replace(
            parsed,
            message_id=normalize_message_id(f"{fallback_email_id}@resend-inbound.dx-connect.local"),
        )
    return parsed
