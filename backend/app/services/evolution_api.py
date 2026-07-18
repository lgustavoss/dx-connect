"""Cliente HTTP mínimo para Evolution API (sem dependência extra: urllib)."""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

from app.config import settings
from app.core.structured_log import log_event
from app.services.email_outbox_policy import TRANSIENT_HTTP_CODES, http_retry_delay_seconds

logger = logging.getLogger(__name__)


def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int, Any | None, str | None]:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = resp.getcode()
            try:
                return code, json.loads(raw) if raw.strip() else None, None
            except json.JSONDecodeError:
                return code, raw, None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, None, err_body or str(e.reason)
    except Exception as e:
        return 0, None, str(e)


def _request_json_with_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
    timeout: int = 20,
    max_attempts: int | None = None,
) -> tuple[int, Any | None, str | None]:
    attempts = max(1, int(max_attempts or settings.EVOLUTION_HTTP_MAX_ATTEMPTS))
    last: tuple[int, Any | None, str | None] = (0, None, "sem resposta")
    for attempt in range(1, attempts + 1):
        code, data, err = _request_json(method, url, headers=headers, body=body, timeout=timeout)
        last = (code, data, err)
        if code in (200, 201) or code not in TRANSIENT_HTTP_CODES:
            if attempt > 1 and code in (200, 201):
                log_event(
                    logger,
                    "evolution_http_send_ok_after_retry",
                    url=url.split("?")[0][-120:],
                    attempts=attempt,
                    http_status=code,
                )
            return code, data, err
        if attempt < attempts:
            delay = http_retry_delay_seconds(attempt)
            log_event(
                logger,
                "evolution_http_retry",
                level=logging.WARNING,
                url=url.split("?")[0][-120:],
                attempt=attempt,
                http_status=code,
                retry_in_seconds=delay,
                error=(err or f"HTTP {code}")[:500],
            )
            time.sleep(delay)
    log_event(
        logger,
        "evolution_http_failed_permanent",
        level=logging.ERROR,
        url=url.split("?")[0][-120:],
        attempts=attempts,
        http_status=last[0],
        error=(last[2] or f"HTTP {last[0]}")[:500],
    )
    return last


def evolution_connection_state(base_url: str, instance: str, api_key: str) -> tuple[bool, str | None]:
    code, _data, err = evolution_connection_state_json(base_url, instance, api_key)
    if code == 200:
        return True, None
    if err:
        return False, err[:500]
    return False, f"HTTP {code}"


def evolution_create_instance(
    base_url: str,
    global_api_key: str,
    body: dict[str, Any],
) -> tuple[int, Any | None, str | None]:
    url = base_url.rstrip("/") + "/instance/create"
    headers = {
        "apikey": global_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    return _request_json("POST", url, headers=headers, body=body)


def evolution_connect(base_url: str, api_key: str, instance: str) -> tuple[int, Any | None, str | None]:
    url = base_url.rstrip("/") + "/instance/connect/" + instance
    headers = {"apikey": api_key, "Accept": "application/json"}
    return _request_json("GET", url, headers=headers)


def evolution_delete_instance(base_url: str, api_key: str, instance: str) -> tuple[int, Any | None, str | None]:
    url = base_url.rstrip("/") + "/instance/delete/" + instance
    headers = {"apikey": api_key, "Accept": "application/json"}
    return _request_json("DELETE", url, headers=headers)


def evolution_fetch_instances(base_url: str, global_api_key: str) -> tuple[int, Any | None, str | None]:
    url = base_url.rstrip("/") + "/instance/fetchInstances"
    headers = {"apikey": global_api_key, "Accept": "application/json"}
    return _request_json("GET", url, headers=headers)


def evolution_connection_state_json(
    base_url: str, instance: str, api_key: str
) -> tuple[int, Any | None, str | None]:
    base = base_url.rstrip("/")
    path = f"/instance/connectionState/{instance}"
    url = base + path
    headers = {"apikey": api_key, "Accept": "application/json"}
    return _request_json("GET", url, headers=headers)


def _extract_wa_message_id(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    key = data.get("key") or data.get("Key")
    if isinstance(key, dict):
        mid = key.get("id") or key.get("Id")
        if mid:
            s = str(mid).strip()
            return s or None
    for k in ("keyId", "KeyId", "id", "Id"):
        mid = data.get(k)
        if mid and not isinstance(mid, dict):
            s = str(mid).strip()
            if s:
                return s
    return None


def evolution_set_webhook(
    base_url: str,
    instance: str,
    api_key: str,
    *,
    webhook_url: str,
    secret: str | None = None,
    events: list[str] | None = None,
) -> tuple[int, Any | None, str | None]:
    """POST /webhook/set/{instance} — garante MESSAGES_UPSERT + MESSAGES_UPDATE."""
    base = base_url.rstrip("/")
    url = f"{base}/webhook/set/{instance}"
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    ev = events or ["MESSAGES_UPSERT", "MESSAGES_UPDATE"]
    webhook: dict[str, Any] = {
        "enabled": True,
        "url": webhook_url,
        "byEvents": False,
        "events": ev,
    }
    if secret:
        webhook["headers"] = {"X-Dx-Webhook-Secret": secret}
    body = {"webhook": webhook}
    return _request_json_with_retry("POST", url, headers=headers, body=body)


def evolution_mark_messages_as_read(
    base_url: str,
    instance: str,
    api_key: str,
    *,
    remote_jid: str,
    message_ids: list[str],
) -> tuple[bool, str | None]:
    """POST /chat/markMessageAsRead/{instance} — marca inbound como lida no WhatsApp do cliente."""
    import re

    ids = [str(i).strip() for i in message_ids if str(i).strip()]
    if not ids:
        return True, None
    base = base_url.rstrip("/")
    url = f"{base}/chat/markMessageAsRead/{instance}"
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    digits = re.sub(r"\D", "", remote_jid)
    jid = remote_jid if "@" in remote_jid else f"{digits}@s.whatsapp.net"
    body = {
        "readMessages": [{"remoteJid": jid, "fromMe": False, "id": mid} for mid in ids]
    }
    code, _data, err = _request_json_with_retry("POST", url, headers=headers, body=body)
    if code in (200, 201):
        return True, None
    if err:
        return False, err[:800]
    return False, f"HTTP {code}"


def evolution_send_text(
    base_url: str,
    instance: str,
    api_key: str,
    number_digits: str,
    text: str,
    *,
    quoted: dict[str, Any] | None = None,
) -> tuple[bool, str | None, str | None]:
    base = base_url.rstrip("/")
    path = f"/message/sendText/{instance}"
    url = base + path
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    body: dict[str, Any] = {"number": number_digits, "text": text}
    if quoted:
        body["quoted"] = quoted
    code, data, err = _request_json_with_retry(
        "POST",
        url,
        headers=headers,
        body=body,
    )
    if code in (200, 201):
        return True, None, _extract_wa_message_id(data)
    if err:
        return False, err[:800], None
    return False, f"HTTP {code}", None


def evolution_send_whatsapp_audio(
    base_url: str,
    instance: str,
    api_key: str,
    number_digits: str,
    *,
    audio_base64: str,
    quoted: dict[str, Any] | None = None,
) -> tuple[bool, str | None, str | None]:
    """POST /message/sendWhatsAppAudio/{instance} — nota de voz (PTT) com encoding automático."""
    base = base_url.rstrip("/")
    url = f"{base}/message/sendWhatsAppAudio/{instance}"
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    body: dict[str, Any] = {
        "number": number_digits,
        "audio": audio_base64,
        "encoding": True,
    }
    if quoted:
        body["quoted"] = quoted
    code, data, err = _request_json_with_retry("POST", url, headers=headers, body=body, timeout=120)
    if code in (200, 201):
        return True, None, _extract_wa_message_id(data)
    if err:
        return False, err[:1200], None
    return False, f"HTTP {code}", None


def evolution_send_sticker(
    base_url: str,
    instance: str,
    api_key: str,
    number_digits: str,
    *,
    sticker_base64: str,
    quoted: dict[str, Any] | None = None,
) -> tuple[bool, str | None, str | None]:
    """POST /message/sendSticker/{instance} — figurinha (WebP/PNG em base64)."""
    base = base_url.rstrip("/")
    url = f"{base}/message/sendSticker/{instance}"
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    body: dict[str, Any] = {
        "number": number_digits,
        "sticker": sticker_base64,
    }
    if quoted:
        body["quoted"] = quoted
    code, data, err = _request_json_with_retry("POST", url, headers=headers, body=body, timeout=120)
    if code in (200, 201):
        return True, None, _extract_wa_message_id(data)
    if err:
        return False, err[:1200], None
    return False, f"HTTP {code}", None


def evolution_send_media(
    base_url: str,
    instance: str,
    api_key: str,
    number_digits: str,
    *,
    mediatype: str,
    mimetype: str,
    caption: str,
    media_base64: str,
    file_name: str,
    quoted: dict[str, Any] | None = None,
) -> tuple[bool, str | None, str | None]:
    """POST /message/sendMedia/{instance} — mediatype típico: image | video | audio | document."""
    base = base_url.rstrip("/")
    url = f"{base}/message/sendMedia/{instance}"
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    body: dict[str, Any] = {
        "number": number_digits,
        "mediatype": mediatype,
        "mimetype": mimetype,
        "caption": caption or "",
        "media": media_base64,
        "fileName": file_name or "file",
    }
    if quoted:
        body["quoted"] = quoted
    code, data, err = _request_json_with_retry("POST", url, headers=headers, body=body, timeout=120)
    if code in (200, 201):
        return True, None, _extract_wa_message_id(data)
    if err:
        return False, err[:1200], None
    return False, f"HTTP {code}", None


def _extrair_base64_resposta(data: Any) -> str | None:
    if isinstance(data, str) and len(data) > 80 and not data.strip().startswith("{"):
        return data.strip()
    if not isinstance(data, dict):
        return None
    for k in ("base64", "Base64", "buffer", "Buffer"):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    for wrap in ("data", "response", "Data", "Response"):
        inner = data.get(wrap)
        got = _extrair_base64_resposta(inner)
        if got:
            return got
    return None


def _payloads_get_base64_from_envelope(message_envelope: dict[str, Any]) -> list[dict[str, Any]]:
    """Variantes aceites pela Evolution v2 (envelope completo ou só key.id)."""
    payloads: list[dict[str, Any]] = [message_envelope]
    key = message_envelope.get("key") or message_envelope.get("Key")
    if isinstance(key, dict):
        slim_key: dict[str, Any] = {}
        mid = key.get("id") or key.get("Id")
        if mid:
            slim_key["id"] = str(mid).strip()
        rj = key.get("remoteJid") or key.get("RemoteJid")
        if rj:
            slim_key["remoteJid"] = rj
        if "fromMe" in key:
            slim_key["fromMe"] = key["fromMe"]
        elif "FromMe" in key:
            slim_key["fromMe"] = key["FromMe"]
        if slim_key.get("id"):
            payloads.append({"key": slim_key})
            payloads.append({"key": {"id": slim_key["id"]}})
    # dedupe mantendo ordem
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for p in payloads:
        sig = json.dumps(p, sort_keys=True, default=str)
        if sig not in seen:
            seen.add(sig)
            out.append(p)
    return out


def _erro_indica_mensagem_nao_encontrada(err: str | None) -> bool:
    if not err:
        return False
    low = err.lower()
    return "message not found" in low or "mensagem não encontrada" in low or "mensagem nao encontrada" in low


def evolution_get_base64_from_media_message(
    base_url: str,
    instance: str,
    api_key: str,
    message_envelope: dict[str, Any],
    *,
    convert_to_mp4: bool = False,
    timeout: int = 90,
) -> tuple[bool, str | None, str | None]:
    """
    POST /chat/getBase64FromMediaMessage/{instance}
    `message_envelope` costuma ser o objeto completo da mensagem no webhook (key, message, …).
    Tenta envelope completo e fallback com key mínima; repete uma vez se a Evolution ainda
    não persistiu a mensagem (erro «Message not found»).
    """
    base = base_url.rstrip("/")
    url = f"{base}/chat/getBase64FromMediaMessage/{instance}"
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    last_err: str | None = None
    for attempt in range(2):
        for msg_payload in _payloads_get_base64_from_envelope(message_envelope):
            body: dict[str, Any] = {"message": msg_payload, "convertToMp4": convert_to_mp4}
            code, data, err = _request_json_with_retry("POST", url, headers=headers, body=body, timeout=timeout)
            if code in (200, 201):
                b64 = _extrair_base64_resposta(data)
                if b64:
                    return True, b64, None
                last_err = "Evolution não devolveu base64 no formato esperado"
            else:
                last_err = (err[:1200] if err else f"HTTP {code}") or last_err
        if attempt == 0 and _erro_indica_mensagem_nao_encontrada(last_err):
            time.sleep(1.5)
            continue
        break
    return False, None, last_err or "Falha ao obter mídia da Evolution"
