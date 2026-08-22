"""Extrai mensagens de cliente (texto e mídia) de webhooks Evolution (formatos comuns)."""

from __future__ import annotations

import re
from typing import Any, Callable, Iterator

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


def _wa_id_from_message_key(key: dict[str, Any], envelope: dict[str, Any]) -> str | None:
    """
    Extrai wa_id (só dígitos) do key da mensagem.

    Quando remoteJid é @lid (WhatsApp Linked ID), prefere remoteJidAlt / senderPn
    com o número real — senão o inbound não casa com chats abertos por telefone.
    """
    rjid = key.get("remoteJid") or key.get("RemoteJid")
    rjid_s = str(rjid) if rjid else ""
    if not rjid_s:
        return None
    if "@g.us" in rjid_s:
        return None

    if "@lid" in rjid_s.lower():
        for src in (key, envelope):
            for alt_key in (
                "remoteJidAlt",
                "RemoteJidAlt",
                "senderPn",
                "SenderPn",
                "participantPn",
                "ParticipantPn",
            ):
                alt = src.get(alt_key)
                if alt:
                    digits = _only_digits_jid(str(alt))
                    if digits:
                        return digits
        # Sem telefone alternativo: LID opaco (último recurso)
        return _only_digits_jid(rjid_s)

    return _only_digits_jid(rjid_s)


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


def _quoted_from_context_info(ctx: dict[str, Any]) -> tuple[str | None, str | None]:
    sid = ctx.get("stanzaId") or ctx.get("StanzaId")
    if not sid:
        return None, None
    wid = str(sid).strip()
    if not wid:
        return None, None
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


def _forward_from_context_info(ctx: dict[str, Any]) -> tuple[bool, int | None]:
    """Extrai isForwarded / forwardingScore do contextInfo (Baileys / Evolution)."""
    score_raw = ctx.get("forwardingScore")
    if score_raw is None:
        score_raw = ctx.get("ForwardingScore")
    score: int | None = None
    if score_raw is not None:
        try:
            score = int(score_raw)
        except (TypeError, ValueError):
            score = None

    forwarded = bool(ctx.get("isForwarded") or ctx.get("IsForwarded"))
    if score is not None and score > 0:
        forwarded = True
    return forwarded, score


def _iter_context_infos(envelope: dict[str, Any], inner: dict[str, Any]) -> Iterator[dict[str, Any]]:
    ctx = envelope.get("contextInfo") or envelope.get("ContextInfo")
    if isinstance(ctx, dict):
        yield ctx
    for sub_key in _SUBCOM_KEYS:
        sub = inner.get(sub_key)
        if not isinstance(sub, dict):
            continue
        nested = sub.get("contextInfo") or sub.get("ContextInfo")
        if isinstance(nested, dict):
            yield nested


def quoted_reply_from_envelope(envelope: dict[str, Any], inner: dict[str, Any]) -> tuple[str | None, str | None]:
    """
    Extrai citação do payload do webhook.

    A Evolution API (prepareMessage) coloca contextInfo no envelope da mensagem,
    não dentro de extendedTextMessage — formato diferente do Baileys bruto usado em testes.
    """
    for ctx in _iter_context_infos(envelope, inner):
        wid, prev = _quoted_from_context_info(ctx)
        if wid:
            return wid, prev
    return None, None


def quoted_reply_from_inner(inner: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extrai resposta citada: id da mensagem original (stanzaId) e texto de pré-visualização."""
    return quoted_reply_from_envelope({}, inner)


def forward_info_from_envelope(envelope: dict[str, Any], inner: dict[str, Any]) -> tuple[bool, int | None]:
    """Extrai flag de encaminhamento (isForwarded / forwardingScore) do webhook (#827)."""
    for ctx in _iter_context_infos(envelope, inner):
        forwarded, score = _forward_from_context_info(ctx)
        if forwarded or score is not None:
            return forwarded, score
    return False, None


def _mimetype_de_obj_midia(obj: dict[str, Any]) -> str | None:
    for k in ("mimetype", "mimeType", "Mimetype"):
        v = obj.get(k)
        if v:
            return str(v).strip()
    return None


def _file_name_de_obj_midia(obj: dict[str, Any]) -> str | None:
    """Nome original do documento/mídia (Baileys/Evolution) (#679)."""
    for k in ("fileName", "filename", "FileName", "title", "Title", "name", "Name"):
        v = obj.get(k)
        if v and str(v).strip():
            # Evita path traversal e caracteres de controlo
            raw = str(v).strip().replace("\\", "/").split("/")[-1]
            safe = "".join(ch for ch in raw if ch.isprintable() and ch not in '<>:"|?*')
            safe = safe.strip().strip(".")
            if safe:
                return safe[:200]
    return None


def _caption_de_obj_midia(obj: dict[str, Any]) -> str | None:
    for k in ("caption", "Caption"):
        v = obj.get(k)
        if v and str(v).strip():
            return str(v).strip()
    return None


def _telefone_de_vcard(vcard: str | None) -> str | None:
    if not vcard:
        return None
    for line in str(vcard).splitlines():
        s = line.strip()
        if s.upper().startswith("TEL"):
            part = s.split(":", 1)
            if len(part) == 2 and part[1].strip():
                return re.sub(r"\D", "", part[1]) or part[1].strip()
    return None


def _corpo_contacto(obj: dict[str, Any]) -> str:
    nome = str(obj.get("displayName") or obj.get("DisplayName") or "Contacto").strip()
    tel = _telefone_de_vcard(obj.get("vcard") or obj.get("Vcard"))
    if tel:
        return f"[Contacto] {nome} — {tel}"
    return f"[Contacto] {nome}"


def _corpo_localizacao(obj: dict[str, Any]) -> str:
    nome = str(obj.get("name") or obj.get("Name") or obj.get("address") or obj.get("Address") or "Localização").strip()
    lat = obj.get("degreesLatitude") if obj.get("degreesLatitude") is not None else obj.get("DegreesLatitude")
    lng = obj.get("degreesLongitude") if obj.get("degreesLongitude") is not None else obj.get("DegreesLongitude")
    if lat is not None and lng is not None:
        return f"[Localização] {nome}\nhttps://maps.google.com/?q={lat},{lng}"
    return f"[Localização] {nome}"


_ESPECIAL_TEXTO: list[tuple[str, Callable[[dict[str, Any]], str]]] = [
    ("contactMessage", _corpo_contacto),
    ("ContactMessage", _corpo_contacto),
    ("locationMessage", _corpo_localizacao),
    ("LocationMessage", _corpo_localizacao),
    ("liveLocationMessage", _corpo_localizacao),
    ("LiveLocationMessage", _corpo_localizacao),
]


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
    # Evolution MESSAGES_UPDATE (formato flat): { keyId, fromMe, status, remoteJid }
    if "keyId" in data or "KeyId" in data:
        yield data
        return
    if "key" in data or "Key" in data or "message" in data or "Message" in data:
        yield data


def _wa_id_e_from_me_de_update(m: dict[str, Any]) -> tuple[str | None, bool | None]:
    """Extrai wa_message_id e fromMe de update aninhado (key.id) ou flat (keyId)."""
    key = m.get("key") or m.get("Key")
    if isinstance(key, dict):
        mid = key.get("id") or key.get("Id")
        wa_message_id = str(mid).strip() if mid else None
        from_me_raw = key.get("fromMe") if "fromMe" in key else key.get("FromMe")
        from_me = bool(from_me_raw) if from_me_raw is not None else None
        return wa_message_id or None, from_me

    mid = m.get("keyId") or m.get("KeyId") or m.get("id") or m.get("Id")
    wa_message_id = str(mid).strip() if mid else None
    if "fromMe" in m:
        from_me = bool(m.get("fromMe"))
    elif "FromMe" in m:
        from_me = bool(m.get("FromMe"))
    else:
        from_me = None
    return (wa_message_id or None), from_me


def iter_inbound_whatsapp_messages(webhook_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Por cada mensagem inbound (não enviada por nós, não grupo), produz um dict:

    - wa_id, wa_message_id, push_name
    - tipo: texto | imagem | audio | video | documento | figurinha
    - corpo: texto ou legenda ou rótulo [Imagem] etc.
    - mimetype: opcional
    - raw_envelope: objeto completo da mensagem (para POST getBase64FromMediaMessage), só se tipo != texto
    - quoted_wa_message_id, quoted_corpo_preview: se o cliente responde citando outra mensagem
    - is_forwarded, forwarding_score: se a mensagem foi encaminhada (#827)
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
        wa_id = _wa_id_from_message_key(key, m)
        if not wa_id:
            continue
        mid = key.get("id") or key.get("Id")
        wa_message_id = str(mid) if mid else None
        push = m.get("pushName") or m.get("PushName")
        push_name = str(push).strip() if push else None

        inner = m.get("message") or m.get("Message")
        if not isinstance(inner, dict):
            continue

        q_wid, q_prev = quoted_reply_from_envelope(m, inner)
        if q_prev and len(q_prev) > 500:
            q_prev = q_prev[:500]
        is_forwarded, forwarding_score = forward_info_from_envelope(m, inner)

        media = _detect_media(inner)
        if media:
            kind, obj = media
            mime = _mimetype_de_obj_midia(obj)
            cap = _caption_de_obj_midia(obj)
            file_name = _file_name_de_obj_midia(obj)
            corpo = cap if cap else _ROTULO_TIPO.get(kind, "[Mídia]")
            yield {
                "wa_id": wa_id,
                "wa_message_id": wa_message_id,
                "push_name": push_name,
                "tipo": kind,
                "corpo": corpo,
                "mimetype": mime,
                "file_name": file_name,
                "raw_envelope": m,
                "quoted_wa_message_id": q_wid,
                "quoted_corpo_preview": q_prev,
                "is_forwarded": is_forwarded,
                "forwarding_score": forwarding_score,
            }
            continue

        corpo_especial: str | None = None
        for key, formatter in _ESPECIAL_TEXTO:
            obj = inner.get(key)
            if isinstance(obj, dict):
                corpo_fmt = formatter(obj).strip()
                if corpo_fmt:
                    corpo_especial = corpo_fmt
                    break
        if corpo_especial:
            yield {
                "wa_id": wa_id,
                "wa_message_id": wa_message_id,
                "push_name": push_name,
                "tipo": "texto",
                "corpo": corpo_especial,
                "mimetype": None,
                "raw_envelope": None,
                "quoted_wa_message_id": q_wid,
                "quoted_corpo_preview": q_prev,
                "is_forwarded": is_forwarded,
                "forwarding_score": forwarding_score,
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
            "is_forwarded": is_forwarded,
            "forwarding_score": forwarding_score,
        }

def _ack_de_update_dict(update: dict[str, Any]) -> int | str | None:
    if not isinstance(update, dict):
        return None
    for key in ("status", "Status", "ack", "Ack"):
        if key in update:
            return update[key]
    return None


def iter_message_status_updates(webhook_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Por cada atualização de ACK em mensagem outbound, produz:
    wa_message_id, status_entrega (pendente|enviada|entregue|lida|erro)

    Aceita:
    - formato aninhado: data.key.id + data.update.status
    - formato Evolution flat: data.keyId + data.fromMe + data.status (ex.: DELIVERY_ACK)
    - data como lista de qualquer um dos formatos
    """
    from app.services.mensagem_status import ack_evolution_para_status

    event = webhook_body.get("event") or webhook_body.get("Event") or ""
    ev = str(event).lower().replace("_", ".")
    if "update" not in ev or "message" not in ev:
        return

    data = webhook_body.get("data") or webhook_body.get("Data")
    for m in _iter_message_dicts(data):
        wa_message_id, from_me = _wa_id_e_from_me_de_update(m)
        if not wa_message_id:
            continue
        # Só atualiza ticks de mensagens enviadas por nós. Se fromMe vier omitido
        # (alguns payloads), ainda tenta — o lookup no DB exige direcao=outbound.
        if from_me is False:
            continue

        ack_raw = _ack_de_update_dict(m.get("update") or m.get("Update") or {})
        if ack_raw is None:
            ack_raw = m.get("status") or m.get("Status") or m.get("ack") or m.get("Ack")

        status = ack_evolution_para_status(ack_raw)
        if not status:
            continue
        yield {"wa_message_id": wa_message_id, "status_entrega": status}


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


def _reaction_payload_from_inner(inner: dict[str, Any]) -> tuple[str | None, str | None]:
    """Retorna (target_wa_message_id, emoji_ou_vazio)."""
    react = inner.get("reactionMessage") or inner.get("ReactionMessage")
    if not isinstance(react, dict):
        return None, None
    key = react.get("key") or react.get("Key") or {}
    if not isinstance(key, dict):
        return None, None
    mid = key.get("id") or key.get("Id")
    target_id = str(mid).strip() if mid else None
    text = react.get("text") if "text" in react else react.get("Text")
    emoji = "" if text is None else str(text)
    return target_id or None, emoji


def iter_inbound_revokes(webhook_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Apagar para todos (protocolMessage type REVOKE) em messages.upsert.

    Yields: wa_id, target_wa_message_id
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
        wa_id = _wa_id_from_message_key(key, m)
        if not wa_id:
            continue
        inner = m.get("message") or m.get("Message")
        if not isinstance(inner, dict):
            continue
        proto = inner.get("protocolMessage") or inner.get("ProtocolMessage")
        if not isinstance(proto, dict):
            continue
        ptype = str(proto.get("type") or proto.get("Type") or "").upper()
        if ptype not in ("REVOKE", "14"):
            continue
        pkey = proto.get("key") or proto.get("Key") or {}
        if not isinstance(pkey, dict):
            continue
        mid = pkey.get("id") or pkey.get("Id")
        target = str(mid).strip() if mid else None
        if not target:
            continue
        yield {"wa_id": wa_id, "target_wa_message_id": target}


def iter_inbound_edits(webhook_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Edição de mensagem (editedMessage) em messages.upsert.

    Yields: wa_id, target_wa_message_id, texto
    """
    event = webhook_body.get("event") or webhook_body.get("Event") or ""
    ev = str(event).lower()
    if "messages" not in ev and "edit" not in ev:
        return
    data = webhook_body.get("data") or webhook_body.get("Data")
    for m in _iter_message_dicts(data):
        key = m.get("key") or m.get("Key") or {}
        if not isinstance(key, dict):
            continue
        wa_id = _wa_id_from_message_key(key, m)
        if not wa_id:
            continue
        inner = m.get("message") or m.get("Message")
        if not isinstance(inner, dict):
            continue
        edited = inner.get("editedMessage") or inner.get("EditedMessage")
        if not isinstance(edited, dict):
            continue
        # editedMessage.message.{conversation|extendedTextMessage}
        nested = edited.get("message") or edited.get("Message") or edited
        if not isinstance(nested, dict):
            continue
        texto = _text_from_inner(nested)
        if not texto:
            continue
        # alvo: key do envelope ou editedMessage.key
        ekey = edited.get("key") or edited.get("Key") or key
        if not isinstance(ekey, dict):
            ekey = key
        mid = ekey.get("id") or ekey.get("Id")
        target = str(mid).strip() if mid else None
        if not target:
            continue
        yield {"wa_id": wa_id, "target_wa_message_id": target, "texto": texto}


def iter_inbound_reactions(webhook_body: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Reações (cliente ou eco fromMe) em messages.upsert com reactionMessage.

    Yields:
      wa_id, target_wa_message_id, emoji ('' = remover), from_me
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
        wa_id = _wa_id_from_message_key(key, m)
        if not wa_id:
            continue
        inner = m.get("message") or m.get("Message")
        if not isinstance(inner, dict):
            continue
        target_id, emoji = _reaction_payload_from_inner(inner)
        if not target_id:
            continue
        from_me = bool(key.get("fromMe") or key.get("FromMe"))
        yield {
            "wa_id": wa_id,
            "target_wa_message_id": target_id,
            "emoji": emoji if emoji is not None else "",
            "from_me": from_me,
        }
