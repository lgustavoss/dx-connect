"""
Parse de mensagens recebidas por webhook (SendGrid-style form, JSON de teste ou RFC822 cru).
"""

from __future__ import annotations

import email.policy
import json
import re
from dataclasses import dataclass
from email import message_from_bytes
from email.message import Message
from email.utils import parseaddr, getaddresses


@dataclass(frozen=True)
class ParsedInboundEmail:
    message_id: str | None
    in_reply_to: str | None
    references: str | None
    from_display: str
    from_email: str | None
    subject: str
    body_text: str
    to_recipients: tuple[str, ...] = ()


def normalize_message_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.startswith("<") and s.endswith(">"):
        s = s[1:-1].strip()
    return s[:998] if s else None


def thread_lookup_message_ids(parsed: ParsedInboundEmail) -> list[str]:
    """
    Message-IDs a consultar para encontrar o ticket da thread (ordem: In-Reply-To;
    depois ``References`` do mais recente ao mais antigo).
    """
    out: list[str] = []
    seen: set[str] = set()

    def push(n: str | None) -> None:
        if not n or n in seen:
            return
        seen.add(n)
        out.append(n)

    push(parsed.in_reply_to)
    if parsed.references:
        raw = parsed.references.replace("\n", " ").strip()
        tokens: list[str] = []
        for part in raw.split():
            n = normalize_message_id(part)
            if n:
                tokens.append(n)
        for n in reversed(tokens):
            push(n)
    return out


def _header_from_block(block: str, name: str) -> str | None:
    """Extrai um cabeçalho de um bloco tipo 'Header: valor\\n'."""
    if not block or not block.strip():
        return None
    pattern = re.compile(rf"^{re.escape(name)}\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
    m = pattern.search(block)
    if not m:
        return None
    return m.group(1).strip() or None


def _decode_part_payload(part: Message) -> str:
    try:
        raw = part.get_payload(decode=True)
    except Exception:
        raw = None
    if raw is None:
        p = part.get_payload()
        return p if isinstance(p, str) else ""
    if isinstance(raw, bytes):
        return raw.decode(part.get_content_charset() or "utf-8", errors="replace")
    return str(raw)


def _collect_recipient_addresses(msg: Message) -> tuple[str, ...]:
    out: list[str] = []
    for header in ("To", "Delivered-To", "Envelope-To", "X-Original-To", "X-Forwarded-To"):
        raw = msg.get(header)
        if not raw:
            continue
        for _name, addr in getaddresses([str(raw)]):
            a = (addr or "").strip().lower()
            if a and a not in out:
                out.append(a)
    return tuple(out)


def _plain_text_from_message(msg: Message) -> str:
    if msg.is_multipart():
        chunks: list[str] = []
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            if ctype == "text/plain" and not part.get_filename():
                chunks.append(_decode_part_payload(part))
        return "\n\n".join(c for c in chunks if c.strip())
    if (msg.get_content_type() or "").lower() == "text/plain":
        return _decode_part_payload(msg)
    return ""


def parse_from_rfc822_bytes(raw: bytes) -> ParsedInboundEmail:
    msg = message_from_bytes(raw, policy=email.policy.default)
    mid = normalize_message_id(msg.get("Message-ID"))
    irt = normalize_message_id(msg.get("In-Reply-To"))
    refs = (msg.get("References") or "").strip() or None
    from_raw = msg.get("From") or ""
    name, addr = parseaddr(from_raw)
    display = (f"{name} <{addr}>" if name else from_raw).strip() or addr or "(sem remetente)"
    subj = (msg.get("Subject") or "").strip() or "(sem assunto)"
    body = _plain_text_from_message(msg).strip() or "(corpo vazio ou não texto)"
    return ParsedInboundEmail(
        message_id=mid,
        in_reply_to=irt,
        references=refs,
        from_display=display,
        from_email=(addr.strip() or None),
        subject=subj[:500],
        body_text=body,
        to_recipients=_collect_recipient_addresses(msg),
    )


def parse_from_sendgrid_like_form(fields: dict[str, str]) -> ParsedInboundEmail:
    """
    Campos típicos: from, subject, text, html, headers (string ou JSON com pares).
    Campo opcional `email`: mensagem RFC822 completa (prioridade sobre o resto).
    """
    raw = (fields.get("email") or "").strip()
    if raw:
        try:
            return parse_from_rfc822_bytes(raw.encode("utf-8", errors="replace"))
        except Exception:
            pass

    headers_blob = (fields.get("headers") or "").strip()
    mid = None
    irt = None
    refs = None
    if headers_blob:
        if headers_blob.startswith("{"):
            try:
                hj = json.loads(headers_blob)
                if isinstance(hj, dict):
                    mid = normalize_message_id(
                        hj.get("Message-ID") or hj.get("Message-Id") or hj.get("message-id")
                    )
                    irt = normalize_message_id(hj.get("In-Reply-To") or hj.get("In-reply-to"))
                    refs = (hj.get("References") or hj.get("references") or "").strip() or None
            except json.JSONDecodeError:
                pass
        if not mid:
            mid = normalize_message_id(_header_from_block(headers_blob, "Message-ID"))
        if not irt:
            irt = normalize_message_id(_header_from_block(headers_blob, "In-Reply-To"))
        if not refs:
            refs = (_header_from_block(headers_blob, "References") or "").strip() or None

    from_raw = (fields.get("from") or "").strip()
    pairs = getaddresses([from_raw]) if from_raw else []
    from_email = pairs[0][1].strip() if pairs and pairs[0][1] else None
    display = from_raw or from_email or "(sem remetente)"

    subj = (fields.get("subject") or "").strip() or "(sem assunto)"
    text = (fields.get("text") or "").strip()
    if not text:
        text = (fields.get("stripped-text") or fields.get("body-plain") or "").strip()
    if not text:
        html = (fields.get("html") or "").strip()
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = "(corpo vazio)"

    to_addrs: list[str] = []
    for key in ("to", "recipient", "envelope"):
        raw_to = (fields.get(key) or "").strip()
        if not raw_to:
            continue
        for _n, a in getaddresses([raw_to]):
            x = (a or "").strip().lower()
            if x and x not in to_addrs:
                to_addrs.append(x)
    if headers_blob and not to_addrs:
        raw_to = _header_from_block(headers_blob, "To") or _header_from_block(headers_blob, "Delivered-To")
        if raw_to:
            for _n, a in getaddresses([raw_to]):
                x = (a or "").strip().lower()
                if x and x not in to_addrs:
                    to_addrs.append(x)

    return ParsedInboundEmail(
        message_id=mid,
        in_reply_to=irt,
        references=refs,
        from_display=display[:512],
        from_email=from_email,
        subject=subj[:500],
        body_text=text,
        to_recipients=tuple(to_addrs),
    )
