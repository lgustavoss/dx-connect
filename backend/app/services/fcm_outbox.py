"""Outbox FCM — enfileirar após o evento de negócio e enviar no worker (#1315)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.structured_log import log_event
from app.database import SessionLocal
from app.models.dispositivo import Dispositivo, FcmOutbox
from app.services.email_outbox_policy import MAX_EMAIL_SEND_ATTEMPTS, retry_delay_seconds
from app.services.fcm import enviar_para_token, fcm_configurado

logger = logging.getLogger(__name__)

STATUS_PENDENTE = "pendente"
STATUS_ENVIADA = "enviada"
STATUS_FALHA = "falha"

TIPOS_FILA = frozenset({"chat.fila", "ticket.fila", "portal.chat.fila", "chat.fila.remind"})
EVENTO_FILA_REMIND = "chat.fila.remind"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _dedup_ja_processado(db: Session, dedup_key: str) -> bool:
    row = db.query(FcmOutbox.id).filter(FcmOutbox.dedup_key == dedup_key).first()
    return row is not None


def _montar_payload(
    *,
    event_type: str,
    entity_id: int,
    titulo: str,
    url_path: str,
    corpo: str | None,
    chat_id: int | None,
    ticket_id: int | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tipo": event_type,
        "id": int(entity_id),
        "titulo": titulo,
        "url_path": url_path,
        "corpo": (corpo or "").strip() or None,
    }
    if chat_id is not None:
        payload["chat_id"] = int(chat_id)
        payload["deep_link"] = f"/conversa/{int(chat_id)}"
    if ticket_id is not None:
        payload["ticket_id"] = int(ticket_id)
        payload["deep_link"] = f"/ticket/{int(ticket_id)}"
    return payload


def enfileirar_para_atendentes(
    *,
    atendente_ids: Iterable[int],
    event_type: str,
    entity_id: int,
    titulo: str,
    url_path: str,
    corpo: str | None = None,
    exclude_atendente_id: int | None = None,
    chat_id: int | None = None,
    ticket_id: int | None = None,
) -> None:
    """Abre sessão própria. Independente de VAPID — só precisa de token FCM cadastrado."""
    if (event_type or "").startswith("portal."):
        return
    ids = {int(i) for i in atendente_ids if i is not None}
    if exclude_atendente_id is not None:
        ids.discard(int(exclude_atendente_id))
    if not ids:
        return

    payload_base = _montar_payload(
        event_type=event_type,
        entity_id=entity_id,
        titulo=titulo,
        url_path=url_path,
        corpo=corpo,
        chat_id=chat_id,
        ticket_id=ticket_id,
    )
    now = _utcnow()
    db = SessionLocal()
    try:
        for aid in ids:
            tem_disp = db.query(Dispositivo.id).filter(Dispositivo.atendente_id == aid).limit(1).first()
            if tem_disp is None:
                continue
            if event_type == EVENTO_FILA_REMIND:
                minutos = max(1, int(settings.WEB_PUSH_FILA_REMIND_MINUTES or 2))
                bucket = int(now.timestamp() // (minutos * 60))
                dedup_key = f"fcm:{event_type}:{aid}:{bucket}"
            elif event_type in TIPOS_FILA:
                dedup_key = f"fcm:{event_type}:{entity_id}:{aid}:{int(now.timestamp() // 60)}"
            else:
                dedup_key = f"fcm:{event_type}:{entity_id}:{aid}"
            if _dedup_ja_processado(db, dedup_key):
                continue
            db.add(
                FcmOutbox(
                    atendente_id=aid,
                    event_type=event_type,
                    dedup_key=dedup_key,
                    payload_json=json.dumps(payload_base, ensure_ascii=False),
                    status=STATUS_PENDENTE,
                    scheduled_at=now,
                )
            )
        db.commit()
    except IntegrityError:
        db.rollback()
    except Exception:
        db.rollback()
        logger.exception("Falha ao enfileirar FCM (%s:%s)", event_type, entity_id)
    finally:
        db.close()


def process_pending_fcm(db: Session, *, limit: int = 40) -> int:
    if not fcm_configurado():
        return 0
    now = _utcnow()
    rows = (
        db.query(FcmOutbox)
        .filter(FcmOutbox.status == STATUS_PENDENTE, FcmOutbox.scheduled_at <= now)
        .order_by(FcmOutbox.scheduled_at.asc())
        .limit(limit)
        .all()
    )
    sent = 0
    for row in rows:
        dispositivos = db.query(Dispositivo).filter(Dispositivo.atendente_id == row.atendente_id).all()
        if not dispositivos:
            row.status = STATUS_ENVIADA
            row.sent_at = now
            row.last_error = "sem dispositivo"
            continue
        payload = json.loads(row.payload_json)
        row.tentativas = int(row.tentativas or 0) + 1
        algum_ok = False
        ultimo_erro = None
        for disp in dispositivos:
            code, err = enviar_para_token(disp.token, payload)
            if 200 <= code < 300:
                algum_ok = True
                continue
            if code in (404, 410):
                db.delete(disp)
                log_event(logger, "fcm_dispositivo_expirado", dispositivo_id=disp.id, http_status=code)
                continue
            ultimo_erro = err or f"HTTP {code}"
        if algum_ok:
            row.status = STATUS_ENVIADA
            row.sent_at = now
            row.last_error = None
            sent += 1
            log_event(logger, "fcm_outbox_send_ok", outbox_id=row.id, event_type=row.event_type)
            continue
        ainda = db.query(Dispositivo.id).filter(Dispositivo.atendente_id == row.atendente_id).first()
        if ainda is None:
            row.status = STATUS_ENVIADA
            row.sent_at = now
            row.last_error = "token expirado"
            continue
        row.last_error = ultimo_erro or "falha no envio"
        if row.tentativas >= MAX_EMAIL_SEND_ATTEMPTS:
            row.status = STATUS_FALHA
            log_event(
                logger,
                "fcm_outbox_send_failed_permanent",
                level=logging.ERROR,
                outbox_id=row.id,
                tentativas=row.tentativas,
                error=(row.last_error or "")[:500],
            )
        else:
            delay = retry_delay_seconds(row.tentativas)
            row.scheduled_at = now + timedelta(seconds=delay)
            log_event(
                logger,
                "fcm_outbox_send_retry",
                level=logging.WARNING,
                outbox_id=row.id,
                tentativas=row.tentativas,
                retry_in_seconds=delay,
            )
    return sent
