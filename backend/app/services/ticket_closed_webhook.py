"""Webhook de saída: ticket fechado (#119)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.core.structured_log import log_event
from app.models.ticket import Ticket
from app.models.webhook_outbox import WebhookOutbox
from app.services.email_outbox_policy import MAX_EMAIL_SEND_ATTEMPTS, retry_delay_seconds

logger = logging.getLogger(__name__)

EVENT_TICKET_CLOSED = "ticket.closed"
STATUS_PENDENTE = "pendente"
STATUS_ENVIADA = "enviada"
STATUS_FALHA = "falha"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def webhook_ticket_fechado_configurado() -> bool:
    return bool((settings.TICKET_CLOSED_WEBHOOK_URL or "").strip())


def _payload_ticket_fechado(ticket: Ticket) -> dict:
    return {
        "event": EVENT_TICKET_CLOSED,
        "ticket_id": ticket.id,
        "protocolo": ticket.protocolo,
        "empresa_id": ticket.empresa_id,
        "setor_id": ticket.setor_id,
        "atendente_id": ticket.atendente_id,
        "assunto": ticket.assunto,
        "fechado_em": ticket.fechado_em.isoformat() if ticket.fechado_em else None,
    }


def _dedup_ja_processado(db: Session, dedup_key: str) -> bool:
    row = (
        db.query(WebhookOutbox.id)
        .filter(
            WebhookOutbox.dedup_key == dedup_key,
            WebhookOutbox.status.in_([STATUS_PENDENTE, STATUS_ENVIADA]),
        )
        .first()
    )
    if row:
        return True
    falha = (
        db.query(WebhookOutbox.id)
        .filter(
            WebhookOutbox.dedup_key == dedup_key,
            WebhookOutbox.status == STATUS_FALHA,
            WebhookOutbox.tentativas >= MAX_EMAIL_SEND_ATTEMPTS,
        )
        .first()
    )
    return falha is not None


def enfileirar_webhook_ticket_fechado(db: Session, ticket_id: int) -> None:
    url = (settings.TICKET_CLOSED_WEBHOOK_URL or "").strip()
    if not url:
        return

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket or ticket.fechado_em is None:
        return

    dedup_key = f"{EVENT_TICKET_CLOSED}:{ticket_id}"
    if _dedup_ja_processado(db, dedup_key):
        return

    payload = _payload_ticket_fechado(ticket)
    now = _utcnow()
    db.add(
        WebhookOutbox(
            event_type=EVENT_TICKET_CLOSED,
            dedup_key=dedup_key,
            target_url=url,
            payload_json=json.dumps(payload, ensure_ascii=False),
            status=STATUS_PENDENTE,
            scheduled_at=now,
        )
    )
    db.flush()
    log_event(logger, "webhook_outbox_enqueued", event_type=EVENT_TICKET_CLOSED, ticket_id=ticket_id)


def _sign_payload(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _post_webhook(*, url: str, body: bytes, event_type: str, secret: str | None) -> tuple[int, str | None]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "DX-Connect-Webhook/1.0",
        "X-DX-Webhook-Event": event_type,
    }
    if secret:
        headers["X-DX-Webhook-Signature"] = _sign_payload(body, secret)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            return resp.getcode(), None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, (err_body or str(e.reason))[:2000]
    except Exception as e:
        return 0, str(e)[:2000]


def process_pending_webhooks(db: Session, *, limit: int = 20) -> int:
    now = _utcnow()
    secret = (settings.TICKET_CLOSED_WEBHOOK_SECRET or "").strip() or None
    rows = (
        db.query(WebhookOutbox)
        .filter(WebhookOutbox.status == STATUS_PENDENTE, WebhookOutbox.scheduled_at <= now)
        .order_by(WebhookOutbox.scheduled_at.asc())
        .limit(limit)
        .all()
    )
    sent = 0
    for row in rows:
        row.tentativas = int(row.tentativas or 0) + 1
        body = row.payload_json.encode("utf-8")
        code, err = _post_webhook(url=row.target_url, body=body, event_type=row.event_type, secret=secret)
        if 200 <= code < 300:
            row.status = STATUS_ENVIADA
            row.sent_at = now
            row.last_error = None
            row.dedup_key = f"{row.dedup_key}:sent:{row.id}"
            sent += 1
            log_event(
                logger,
                "webhook_outbox_send_ok",
                outbox_id=row.id,
                event_type=row.event_type,
                http_status=code,
            )
            continue

        row.last_error = err or f"HTTP {code}"
        if row.tentativas >= MAX_EMAIL_SEND_ATTEMPTS:
            row.status = STATUS_FALHA
            log_event(
                logger,
                "webhook_outbox_send_failed_permanent",
                level=logging.ERROR,
                outbox_id=row.id,
                event_type=row.event_type,
                tentativas=row.tentativas,
                http_status=code,
                error=row.last_error[:500],
            )
        else:
            delay = retry_delay_seconds(row.tentativas)
            row.scheduled_at = now + timedelta(seconds=delay)
            log_event(
                logger,
                "webhook_outbox_send_retry",
                level=logging.WARNING,
                outbox_id=row.id,
                event_type=row.event_type,
                tentativas=row.tentativas,
                retry_in_seconds=delay,
                http_status=code,
                error=row.last_error[:500],
            )
    return sent
