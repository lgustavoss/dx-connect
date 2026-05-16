"""Extrai mensagens de cliente (texto e mídia) de webhooks Evolution (formatos comuns)."""

from __future__ import annotations

import re
from typing import Any, Iterator

_MEDIA_KEYS: list[tuple[str, str]] = [
    ("imageMessage", "imagem"),
    ("ImageMessage", "imagem"),
    ("videoMessage", "video"),
    ("VideoMessage", "video"),
    ("audioMessage", "audio"),
    ("AudioMessage", "audio"),
    ("documentMessage", "documento"),
    ("DocumentMessage", "documento"),
    ("stickerMessage", "figurinha"),
    ("StickerMessage", "figurinha"),
]

_ROTULO_TIPO = {
    "imagem": "[Imagem]",
    "audio": "[Áudio]",
    "video": "[Vídeo]",
    "documento": "[Documento]",
    "figurinha": "[Figurinha]",
}


def _only_digits_jid(jid: str | None) -> str | None:
    if not jid:
        return None
    part = jid.split("@", 1)[0]
    digits = re.sub(r"\D", "", part)
    return digits or None


def _text_from_inner(inner: dict[str, Any]) -> str | None:
    if "conversation" in inner:
        v = inner.get("conversation")
        return str(v).strip() if v is not None else None
    ext = inner.get("extendedTextMessage") or inner.get("ExtendedTextMessage")
    if isinstance(ext, dict):
        t = ext.get("text")
        return str(t).strip() if t else None
    return None


def _detect_media(inner: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for key, kind in _MEDIA_KEYS:
        if key in inner and isinstance(inner[key], dict):
            return kind, inner[key]
    return None


_SUBCOM_KEYS = (
    "extendedTextMessage",
    "ExtendedTextMessage",
    "imageMessage",
    "ImageMessage",
    "videoMessage",
    "VideoMessage",
    "audioMessage",
    "AudioMessage",
    "documentMessage",
    "DocumentMessage",
    "stickerMessage",
    "StickerMessage",
)


def quoted_reply_from_inner(inner: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extrai resposta citada: id da mensagem original (stanzaId) e texto de pré-visualização."""
    for sub_key in _SUBCOM_KEYS:
        sub = inner.get(sub_key)
        if not isinstance(sub, dict):
            continue
        ctx = sub.get("contextInfo") or sub.get("ContextInfo")
        if not isinstance(ctx, dict):
            continue
        sid = ctx.get("stanzaId") or ctx.get("StanzaId")
        if not sid:
            continue
        wid = str(sid).strip()
        if not wid:
            continue
        preview: str | None = None
        qm = ctx.get("quotedMessage") or ctx.get("QuotedMessage")
        if isinstance(qm, dict):
            preview = _text_from_inner(qm)
            if not preview:
                md = _detect_media(qm)
                if md:
                    kind, _ = md
                    preview = _ROTULO_TIPO.get(kind, "[Mídia]")
        return wid, preview
    return None, None


def _mimetype_de_obj_midia(obj: dict[str, Any]) -> str | None:
    for k in ("mimetype", "mimeType", "Mimetype"):
        v = obj.get(k)
        if v:
            return str(v).strip()
    return None


def _caption_de_obj_midia(obj: dict[str, Any]) -> str | None:
    for k in ("caption", "Caption"):
        v = obj.get(k)
        if v and str(v).strip():
            return str(v).strip()
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


def iter_inbound_whatsapp_messages(webhook_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Por cada mensagem inbound (não enviada por nós, não grupo), produz um dict:

    - wa_id, wa_message_id, push_name
    - tipo: texto | imagem | audio | video | documento | figurinha
    - corpo: texto ou legenda ou rótulo [Imagem] etc.
    - mimetype: opcional
    - raw_envelope: objeto completo da mensagem (para POST getBase64FromMediaMessage), só se tipo != texto
    - quoted_wa_message_id, quoted_corpo_preview: se o cliente responde citando outra mensagem
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
        mid = key.get("id") or key.get("Id")
        wa_message_id = str(mid) if mid else None
        push = m.get("pushName") or m.get("PushName")
        push_name = str(push).strip() if push else None

        inner = m.get("message") or m.get("Message")
        if not isinstance(inner, dict):
            continue

        q_wid, q_prev = quoted_reply_from_inner(inner)
        if q_prev and len(q_prev) > 500:
            q_prev = q_prev[:500]

        media = _detect_media(inner)
        if media:
            kind, obj = media
            mime = _mimetype_de_obj_midia(obj)
            cap = _caption_de_obj_midia(obj)
            corpo = cap if cap else _ROTULO_TIPO.get(kind, "[Mídia]")
            yield {
                "wa_id": wa_id,
                "wa_message_id": wa_message_id,
                "push_name": push_name,
                "tipo": kind,
                "corpo": corpo,
                "mimetype": mime,
                "raw_envelope": m,
                "quoted_wa_message_id": q_wid,
                "quoted_corpo_preview": q_prev,
            }
            continue

        text = _text_from_inner(inner)
        if not text:
            continue
        yield {
            "wa_id": wa_id,
            "wa_message_id": wa_message_id,
            "push_name": push_name,
            "tipo": "texto",
            "corpo": text,
            "mimetype": None,
            "raw_envelope": None,
            "quoted_wa_message_id": q_wid,
            "quoted_corpo_preview": q_prev,
        }


def iter_inbound_text_messages(webhook_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Compatibilidade: apenas mensagens de texto (mesmo formato que antes)."""
    for item in iter_inbound_whatsapp_messages(webhook_body):
        if item.get("tipo") != "texto":
            continue
        yield {
            "wa_id": item["wa_id"],
            "text": item["corpo"],
            "wa_message_id": item.get("wa_message_id"),
            "push_name": item.get("push_name"),
        }
