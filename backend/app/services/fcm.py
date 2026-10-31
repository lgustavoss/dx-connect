"""Envio FCM HTTP v1 com conta de serviço Google (#1315)."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import jwt

from app.config import settings

logger = logging.getLogger(__name__)

_TOKEN_CACHE: tuple[str, float] | None = None


def fcm_configurado() -> bool:
    raw = (settings.FCM_SERVICE_ACCOUNT_JSON or "").strip()
    if not raw:
        return False
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return bool(info.get("client_email") and info.get("private_key") and info.get("project_id"))


def _conta() -> dict[str, Any] | None:
    raw = (settings.FCM_SERVICE_ACCOUNT_JSON or "").strip()
    if not raw:
        return None
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not (info.get("client_email") and info.get("private_key") and info.get("project_id")):
        return None
    return info


def _access_token() -> str | None:
    global _TOKEN_CACHE
    now = time.time()
    if _TOKEN_CACHE and _TOKEN_CACHE[1] > now + 60:
        return _TOKEN_CACHE[0]
    info = _conta()
    if not info:
        return None
    token_uri = str(info.get("token_uri") or "https://oauth2.googleapis.com/token")
    assertion = jwt.encode(
        {
            "iss": info["client_email"],
            "scope": "https://www.googleapis.com/auth/firebase.messaging",
            "aud": token_uri,
            "iat": int(now),
            "exp": int(now) + 3600,
        },
        info["private_key"],
        algorithm="RS256",
    )
    body = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode()
    req = urllib.request.Request(
        token_uri,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        logger.warning("FCM OAuth HTTP %s", exc.code)
        return None
    except OSError as exc:
        logger.warning("FCM OAuth falhou: %s", exc)
        return None
    token = str(data.get("access_token") or "")
    if not token:
        return None
    _TOKEN_CACHE = (token, now + 50 * 60)
    return token


def enviar_para_token(token: str, payload: dict[str, Any]) -> tuple[int, str | None]:
    """Devolve (http_status, erro). 404/410 = token inválido."""
    info = _conta()
    if not info:
        return 503, "FCM não configurado"
    access = _access_token()
    if not access:
        return 503, "FCM sem token OAuth"
    project_id = info["project_id"]
    data_fields = {k: str(v) for k, v in payload.items() if v is not None}
    body = {
        "message": {
            "token": token,
            "notification": {
                "title": str(payload.get("titulo") or "DeskRudder"),
                "body": str(payload.get("corpo") or ""),
            },
            "data": data_fields,
            "android": {"priority": "high"},
        }
    }
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, None
    except urllib.error.HTTPError as exc:
        err = exc.read().decode()[:500]
        return exc.code, err
    except OSError as exc:
        return 599, str(exc)[:500]
