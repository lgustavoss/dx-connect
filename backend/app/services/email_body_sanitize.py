"""
Normaliza o corpo de e-mails inbound para exibição no ticket (sem metadados nem citações).
"""

from __future__ import annotations

import re

_QUOTE_HEADER_PT = re.compile(
    r"^\s*Em\s+.+?\bescreveu:\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_QUOTE_HEADER_EN = re.compile(
    r"^\s*On\s+.+?\bwrote:\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_QUOTE_ORIGINAL = re.compile(
    r"\n-{2,}\s*Original Message\s*-{2,}\s*",
    re.IGNORECASE,
)


def _is_meta_line(line: str) -> bool:
    t = line.strip()
    if not t:
        return False
    tl = t.lower()
    if tl.startswith("mensagem recebida por e-mail"):
        return True
    if tl.startswith("(mensagem recebida por e-mail"):
        return True
    if tl.startswith("remetente:"):
        return True
    if re.match(r"message[\s-]?id\s*:", tl, re.IGNORECASE):
        return True
    return False


def _strip_leading_meta(text: str) -> str:
    lines = text.splitlines()
    while lines:
        if not lines[0].strip():
            lines.pop(0)
            continue
        if _is_meta_line(lines[0]):
            lines.pop(0)
            continue
        break
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines).strip()


def _strip_quoted_reply(text: str) -> str:
    s = text
    for pat in (_QUOTE_ORIGINAL, _QUOTE_HEADER_PT, _QUOTE_HEADER_EN):
        m = pat.search(s)
        if m:
            s = s[: m.start()].rstrip()
    lines = s.splitlines()
    cut = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        t = lines[i].strip()
        if t.startswith(">"):
            cut = i
            continue
        if cut < len(lines):
            break
        break
    if cut < len(lines):
        s = "\n".join(lines[:cut]).rstrip()
    return s


def sanitize_inbound_email_body(text: str | None) -> str:
    """
    Remove prefixos técnicos (remetente, Message-ID, aviso Resend) e trecho citado da mensagem anterior.
    """
    raw = (text or "").strip()
    if not raw:
        return "(sem conteúdo)"

    if raw.lower().startswith("(mensagem recebida por e-mail") and "corpo não obtido" in raw.lower():
        return "(sem conteúdo)"

    s = _strip_leading_meta(raw)
    s = _strip_quoted_reply(s)
    s = s.strip()
    return s or "(sem conteúdo)"
