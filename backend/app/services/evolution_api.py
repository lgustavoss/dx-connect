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
    base = base_url.rstrip("/")
    path = f"/instance/connectionState/{instance}"
    url = base + path
    headers = {"apikey": api_key, "Accept": "application/json"}
    code, data, err = _request_json("GET", url, headers=headers)
    if code == 200:
        return True, None
    if err:
        return False, err[:500]
    return False, f"HTTP {code}"


def evolution_send_text(
    base_url: str,
    instance: str,
    api_key: str,
    number_digits: str,
    text: str,
) -> tuple[bool, str | None]:
    base = base_url.rstrip("/")
    path = f"/message/sendText/{instance}"
    url = base + path
    headers = {"apikey": api_key, "Content-Type": "application/json", "Accept": "application/json"}
    code, _data, err = _request_json(
        "POST",
        url,
        headers=headers,
        body={"number": number_digits, "text": text},
    )
    if code in (200, 201):
        return True, None
    if err:
        return False, err[:800]
    return False, f"HTTP {code}"
