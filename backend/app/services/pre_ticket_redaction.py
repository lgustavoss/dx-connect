"""Redacção básica de dados sensíveis antes do envio à IA (#812)."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_PHONE_BR = re.compile(
    r"(?<!\d)(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4})-?\d{4}(?!\d)"
)


def redact_text(text: str | None) -> str | None:
    if text is None:
        return None
    out = _EMAIL.sub("[EMAIL_REDACTED]", text)
    out = _CPF.sub("[CPF_REDACTED]", out)
    out = _PHONE_BR.sub("[TELEFONE_REDACTED]", out)
    return out


def redact_fields(**fields: str | None) -> dict[str, str | None]:
    return {k: redact_text(v) for k, v in fields.items()}
