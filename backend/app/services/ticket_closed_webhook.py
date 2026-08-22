"""Webhook de saída: ticket fechado (#119)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import ssl
import urllib.error
import urllib.request
import uuid
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


def _post_webhook(
    *,
    url: str,
    body: bytes,
    event_type: str,
    secret: str | None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, str | None]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "DX-Connect-Webhook/1.0",
        "X-DX-Webhook-Event": event_type,
    }
    if secret:
        headers["X-DX-Webhook-Signature"] = _sign_payload(body, secret)
    if extra_headers:
        headers.update(extra_headers)
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


def _encode_multipart(
    fields: dict[str, str],
    *,
    file_field: str,
    filename: str,
    content_type: str,
    data: bytes,
) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )
    safe_name = "".join(ch for ch in filename if ch not in '"\r\n') or "arquivo"
    chunks.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{file_field}"; filename="{safe_name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append(data)
    chunks.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _post_multipart(
    *,
    url: str,
    body: bytes,
    content_type: str,
    extra_headers: dict[str, str] | None = None,
    timeout: int = 120,
) -> tuple[int, str | None]:
    headers = {
        "Content-Type": content_type,
        "Accept": "application/json",
        "User-Agent": "DX-Connect-Webhook/1.0",
        "X-DX-Webhook-Event": "saas.solicitacao.media",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.getcode(), None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, (err_body or str(e.reason))[:2000]
    except Exception as e:
        return 0, str(e)[:2000]


def _enviar_saas_solicitacao_media(row: WebhookOutbox) -> tuple[int, str | None]:
    from app.services.solicitacao_melhoria_media import caminho_absoluto, sanitizar_nome

    try:
        payload = json.loads(row.payload_json or "{}")
    except json.JSONDecodeError:
        return 0, "payload inválido"
    storage_key = (payload.get("storage_key") or "").strip()
    path = caminho_absoluto(storage_key)
    if not path:
        return 0, "ficheiro em falta no disco"
    nome = sanitizar_nome(payload.get("nome_original") or storage_key)
    ctype = (payload.get("content_type") or "application/octet-stream").split(";", 1)[0].strip()
    body, content_type = _encode_multipart(
        {
            "papel": str(payload.get("papel") or "anexo"),
            "storage_key": storage_key,
        },
        file_field="file",
        filename=nome,
        content_type=ctype or "application/octet-stream",
        data=path.read_bytes(),
    )
    token = (settings.SAAS_INSTANCE_INGEST_TOKEN or "").strip()
    extra = {"Authorization": f"Bearer {token}"} if token else None
    return _post_multipart(
        url=row.target_url,
        body=body,
        content_type=content_type,
        extra_headers=extra,
    )


def process_pending_webhooks(db: Session, *, limit: int = 20) -> int:
    now = _utcnow()
    secret = (settings.TICKET_CLOSED_WEBHOOK_SECRET or "").strip() or None
    rows = (
        db.query(WebhookOutbox)
        .filter(WebhookOutbox.status == STATUS_PENDENTE, WebhookOutbox.scheduled_at <= now)
        .order_by(WebhookOutbox.scheduled_at.asc(), WebhookOutbox.id.asc())
        .limit(limit)
        .all()
    )
    sent = 0
    for row in rows:
        row.tentativas = int(row.tentativas or 0) + 1
        if row.event_type == "saas.solicitacao.media":
            code, err = _enviar_saas_solicitacao_media(row)
        else:
            body = row.payload_json.encode("utf-8")
            extra: dict[str, str] | None = None
            row_secret = secret
            if row.event_type == "saas.solicitacao":
                row_secret = None
                token = (settings.SAAS_INSTANCE_INGEST_TOKEN or "").strip()
                extra = {"Authorization": f"Bearer {token}"} if token else None
            code, err = _post_webhook(
                url=row.target_url,
                body=body,
                event_type=row.event_type,
                secret=row_secret,
                extra_headers=extra,
            )
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
