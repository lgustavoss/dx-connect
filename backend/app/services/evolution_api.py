"""Cliente HTTP mínimo para Evolution API (sem dependência extra: urllib)."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any


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


def evolution_send_text(
    base_url: str,
    instance: str,
    api_key: str,
    number_digits: str,
    text: str,
    *,
    quoted: dict[str, Any] | None = None,
) -> tuple[bool, str | None]:
    base = base_url.rstrip("/")
    path = f"/message/sendText/{instance}"
    url = base + path
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    body: dict[str, Any] = {"number": number_digits, "text": text}
    if quoted:
        body["quoted"] = quoted
    code, _data, err = _request_json(
        "POST",
        url,
        headers=headers,
        body=body,
    )
    if code in (200, 201):
        return True, None
    if err:
        return False, err[:800]
    return False, f"HTTP {code}"


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
) -> tuple[bool, str | None]:
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
    code, _data, err = _request_json("POST", url, headers=headers, body=body, timeout=120)
    if code in (200, 201):
        return True, None
    if err:
        return False, err[:1200]
    return False, f"HTTP {code}"


def _extrair_base64_resposta(data: Any) -> str | None:
    if isinstance(data, str) and len(data) > 80 and not data.strip().startswith("{"):
        return data.strip()
    if not isinstance(data, dict):
        return None
    for k in ("base64", "Base64"):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    for wrap in ("data", "response", "Data", "Response"):
        inner = data.get(wrap)
        got = _extrair_base64_resposta(inner)
        if got:
            return got
    return None


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
    """
    base = base_url.rstrip("/")
    url = f"{base}/chat/getBase64FromMediaMessage/{instance}"
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    body: dict[str, Any] = {"message": message_envelope, "convertToMp4": convert_to_mp4}
    code, data, err = _request_json("POST", url, headers=headers, body=body, timeout=timeout)
    if code in (200, 201):
        b64 = _extrair_base64_resposta(data)
        if b64:
            return True, b64, None
        return False, None, "Evolution não devolveu base64 no formato esperado"
    if err:
        return False, None, err[:1200]
    return False, None, f"HTTP {code}"
