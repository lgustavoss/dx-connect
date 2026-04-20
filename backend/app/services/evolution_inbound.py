"""Extrai mensagens de cliente (texto) de webhooks Evolution (formatos comuns)."""

from __future__ import annotations

import re
from typing import Any, Iterator


def _only_digits_jid(jid: str | None) -> str | None:
    if not jid:
        return None
    part = jid.split("@", 1)[0]
    digits = re.sub(r"\D", "", part)
    return digits or None


def _text_from_message_obj(msg: dict[str, Any]) -> str | None:
    inner = msg.get("message") or msg.get("Message")
    if not isinstance(inner, dict):
        return None
    if "conversation" in inner:
        v = inner.get("conversation")
        return str(v).strip() if v is not None else None
    ext = inner.get("extendedTextMessage") or inner.get("ExtendedTextMessage")
    if isinstance(ext, dict):
        t = ext.get("text")
        return str(t).strip() if t else None
    return None


def _iter_message_dicts(data: Any) -> Iterator[dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(data, dict):
        return
    if "messages" in data and isinstance(data["messages"], list):
        for m in data["messages"]:
            if isinstance(m, dict):
                yield m
        return
    if "key" in data or "message" in data or "Message" in data:
        yield data


def iter_inbound_text_messages(webhook_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Yields dicts: wa_id (digits), text, wa_message_id (optional), push_name (optional).
    Ignora fromMe / grupos (@g.us) na v1.
    """
    event = webhook_body.get("event") or webhook_body.get("Event") or ""
    ev = str(event).lower()
    if "messages" not in ev:
        return
    data = webhook_body.get("data") or webhook_body.get("Data")
    for m in _iter_message_dicts(data):
        key = m.get("key") or m.get("Key") or {}
        if not isinstance(key, dict):
            continue
        if key.get("fromMe") or key.get("FromMe"):
            continue
        rjid = key.get("remoteJid") or key.get("RemoteJid")
        rjid_s = str(rjid) if rjid else ""
        if "@g.us" in rjid_s:
            continue
        wa_id = _only_digits_jid(rjid_s)
        if not wa_id:
            continue
        text = _text_from_message_obj(m)
        if not text:
            continue
        mid = key.get("id") or key.get("Id")
        push = m.get("pushName") or m.get("PushName")
        yield {
            "wa_id": wa_id,
            "text": text,
            "wa_message_id": str(mid) if mid else None,
            "push_name": str(push).strip() if push else None,
        }
