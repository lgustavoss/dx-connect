"""Registro de auditoria: quem fez, quando e contexto da requisição."""

from __future__ import annotations

import contextvars
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog

_REDACT_KEY = re.compile(
    r"(password|senha|token|secret|api[_-]?key|credential|cifrada)",
    re.IGNORECASE,
)

_audit_request_ctx: contextvars.ContextVar[dict[str, str | None] | None] = contextvars.ContextVar(
    "audit_request_ctx",
    default=None,
)


def set_audit_request_context(
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    _audit_request_ctx.set(
        {
            "ip_address": ip_address,
            "user_agent": (user_agent[:512] if user_agent else None),
            "request_id": (request_id[:64] if request_id else None),
        }
    )


def clear_audit_request_context() -> None:
    _audit_request_ctx.set(None)


def _sanitize_value(key: str, value: Any) -> Any:
    if _REDACT_KEY.search(key):
        return "[redacted]"
    if isinstance(value, dict):
        return {k: _sanitize_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    return value


def sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    return {str(k): _sanitize_value(str(k), v) for k, v in payload.items()}


def registrar_audit(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    atendente_id: int | None,
    *,
    payload: dict[str, Any] | None = None,
) -> None:
    """Registra auditoria com payload opcional e metadados da requisição HTTP (quando disponíveis)."""
    ctx = _audit_request_ctx.get() or {}
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            atendente_id=atendente_id,
            payload_json=sanitize_payload(payload),
            ip_address=ctx.get("ip_address"),
            user_agent=ctx.get("user_agent"),
            request_id=ctx.get("request_id"),
        )
    )


def registrar_audit_v2(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    atendente_id: int | None,
    *,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    """Alias explícito com override de contexto HTTP (testes ou jobs)."""
    ctx = _audit_request_ctx.get() or {}
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            atendente_id=atendente_id,
            payload_json=sanitize_payload(payload),
            ip_address=ip_address if ip_address is not None else ctx.get("ip_address"),
            user_agent=(user_agent[:512] if user_agent else ctx.get("user_agent")),
            request_id=(request_id[:64] if request_id else ctx.get("request_id")),
        )
    )
