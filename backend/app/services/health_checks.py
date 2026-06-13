"""Health e readiness para operação (#119)."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


def _git_sha() -> str | None:
    return (os.environ.get("DX_CONNECT_GIT_SHA") or "").strip() or None


def check_database(db: Session) -> dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:500]}


def integrations_status() -> dict[str, Any]:
    """Sinais de configuração (não testa conectividade externa)."""
    resend_key = bool((settings.RESEND_API_KEY or "").strip())
    transactional_from = bool((settings.TRANSACTIONAL_FROM_EMAIL or "").strip())
    inbound_webhook = bool((settings.EMAIL_INBOUND_WEBHOOK_SECRET or "").strip())
    resend_inbound = bool((settings.RESEND_WEBHOOK_SECRET or "").strip())
    evolution = settings.evolution_embutida_disponivel

    email_outbound = "configured" if resend_key and transactional_from else "missing" if not resend_key else "partial"
    email_inbound = "configured" if resend_inbound or inbound_webhook else "missing"

    return {
        "email_outbound": email_outbound,
        "email_inbound": email_inbound,
        "evolution_whatsapp": "configured" if evolution else "missing",
    }


def build_health_payload(*, capabilities: dict[str, bool]) -> dict[str, Any]:
    """Liveness: processo de pé; não exige BD."""
    return {
        "status": "ok",
        "git_sha": _git_sha(),
        "environment": settings.ENVIRONMENT,
        "capabilities": capabilities,
        "integrations": integrations_status(),
    }


def build_readiness_payload(*, db: Session, capabilities: dict[str, bool]) -> tuple[dict[str, Any], int]:
    """Readiness: inclui checagem de BD; HTTP 503 se não estiver pronto."""
    base = build_health_payload(capabilities=capabilities)
    db_check = check_database(db)
    checks = {"database": db_check}
    base["checks"] = checks

    if db_check["status"] != "ok":
        base["status"] = "unavailable"
        return base, 503

    integrations = base.get("integrations") or {}
    if any(v in ("missing", "partial") for v in integrations.values()):
        base["status"] = "degraded"
    else:
        base["status"] = "ok"
    return base, 200
