"""Outbox Web Push — enfileirar após o evento de negócio e enviar no worker (#693)."""

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
from app.models.atendente_notificacao import AtendenteNotificacaoPreferencias
from app.models.web_push import PushOutbox, PushSubscription
from app.services.email_outbox_policy import MAX_EMAIL_SEND_ATTEMPTS, retry_delay_seconds
from app.services.notificacao_atendente_email import obter_ou_criar_preferencias
from app.services.web_push import vapid_configurado

logger = logging.getLogger(__name__)

STATUS_PENDENTE = "pendente"
STATUS_ENVIADA = "enviada"
STATUS_FALHA = "falha"

TIPOS_FILA = frozenset({"chat.fila", "ticket.fila", "portal.chat.fila", "chat.fila.remind"})
EVENTO_FILA_REMIND = "chat.fila.remind"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _prefs_permitem(prefs: AtendenteNotificacaoPreferencias, event_type: str) -> bool:
    if not bool(getattr(prefs, "push_habilitado", False)):
        return False
    if event_type in TIPOS_FILA and not bool(getattr(prefs, "push_fila", True)):
        return False
    return True


def _dedup_ja_processado(db: Session, dedup_key: str) -> bool:
    row = db.query(PushOutbox.id).filter(PushOutbox.dedup_key == dedup_key).first()
    return row is not None


def enfileirar_para_atendentes(
    *,
    atendente_ids: Iterable[int],
    event_type: str,
    entity_id: int,
    titulo: str,
    url_path: str,
    corpo: str | None = None,
    exclude_atendente_id: int | None = None,
) -> None:
    """Abre sessão própria para não interferir no commit do chamador (emit pós-commit)."""
    if not vapid_configurado():
        return
    ids = {int(i) for i in atendente_ids if i is not None}
    if exclude_atendente_id is not None:
        ids.discard(int(exclude_atendente_id))
    if not ids:
        return

    payload_base = {
        "tipo": event_type,
        "id": int(entity_id),
        "titulo": titulo,
        "url_path": url_path,
        "corpo": (corpo or "").strip() or None,
    }
    now = _utcnow()
    db = SessionLocal()
    try:
        for aid in ids:
            prefs = obter_ou_criar_preferencias(db, aid)
            if not _prefs_permitem(prefs, event_type):
                continue
            tem_sub = (
                db.query(PushSubscription.id).filter(PushSubscription.atendente_id == aid).limit(1).first()
            )
            if tem_sub is None:
                continue
            if event_type == EVENTO_FILA_REMIND:
                minutos = max(1, int(settings.WEB_PUSH_FILA_REMIND_MINUTES or 2))
                bucket = int(now.timestamp() // (minutos * 60))
                dedup_key = f"{event_type}:{aid}:{bucket}"
            elif event_type in TIPOS_FILA:
                dedup_key = f"{event_type}:{entity_id}:{aid}:{int(now.timestamp() // 60)}"
            else:
                dedup_key = f"{event_type}:{entity_id}:{aid}"
            if _dedup_ja_processado(db, dedup_key):
                continue
            db.add(
                PushOutbox(
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
        logger.exception("Falha ao enfileirar Web Push (%s:%s)", event_type, entity_id)
    finally:
        db.close()


def _contar_fila_por_atendente(db: Session) -> dict[int, int]:
    """Agrega chats WhatsApp + Portal em aguardando_atendente por destinatário do push."""
    from collections import defaultdict

    from app.models.portal_chat import PortalChat
    from app.models.whatsapp_chat import WhatsappChat
    from app.services.realtime_emit import ids_atendentes_chat_fila, ids_atendentes_portal_chat_fila

    counts: dict[int, int] = defaultdict(int)
    wpp = (
        db.query(WhatsappChat)
        .filter(WhatsappChat.estado == "aguardando_atendente")
        .all()
    )
    for chat in wpp:
        for aid in ids_atendentes_chat_fila(db, chat):
            counts[int(aid)] += 1
    portal = (
        db.query(PortalChat)
        .filter(PortalChat.estado == "aguardando_atendente")
        .all()
    )
    for chat in portal:
        for aid in ids_atendentes_portal_chat_fila(db, chat):
            counts[int(aid)] += 1
    return dict(counts)


def process_fila_web_push_reminders() -> int:
    """
    Reaviso periódico enquanto houver fila (app fechada / kill).
    Um push por atendente elegível por janela WEB_PUSH_FILA_REMIND_MINUTES.
    Retorna quantos pushes foram enfileirados nesta passagem.
    """
    if not vapid_configurado():
        return 0
    if int(settings.WEB_PUSH_FILA_REMIND_MINUTES or 0) <= 0:
        return 0

    db = SessionLocal()
    try:
        counts = _contar_fila_por_atendente(db)
        if not counts:
            return 0

        now = _utcnow()
        minutos = max(1, int(settings.WEB_PUSH_FILA_REMIND_MINUTES or 2))
        bucket = int(now.timestamp() // (minutos * 60))
        enfileirados = 0

        for aid, n in counts.items():
            if n <= 0:
                continue
            prefs = obter_ou_criar_preferencias(db, aid)
            if not _prefs_permitem(prefs, EVENTO_FILA_REMIND):
                continue
            tem_sub = (
                db.query(PushSubscription.id).filter(PushSubscription.atendente_id == aid).limit(1).first()
            )
            if tem_sub is None:
                continue
            dedup_key = f"{EVENTO_FILA_REMIND}:{aid}:{bucket}"
            if _dedup_ja_processado(db, dedup_key):
                continue
            corpo = (
                "Há 1 chat aguardando atendimento"
                if n == 1
                else f"Há {n} chats aguardando atendimento"
            )
            payload = {
                "tipo": EVENTO_FILA_REMIND,
                "id": int(aid),
                "titulo": "Clientes na fila",
                "url_path": "/chat/espera",
                "corpo": corpo,
            }
            db.add(
                PushOutbox(
                    atendente_id=aid,
                    event_type=EVENTO_FILA_REMIND,
                    dedup_key=dedup_key,
                    payload_json=json.dumps(payload, ensure_ascii=False),
                    status=STATUS_PENDENTE,
                    scheduled_at=now,
                )
            )
            enfileirados += 1

        if enfileirados:
            db.commit()
            log_event(logger, "web_push_fila_remind_enqueued", atendentes=enfileirados)
        else:
            db.rollback()
        return enfileirados
    except IntegrityError:
        db.rollback()
        return 0
    except Exception:
        db.rollback()
        logger.exception("Falha ao enfileirar lembretes Web Push da fila")
        return 0
    finally:
        db.close()


def _enviar_uma(sub: PushSubscription, payload: dict[str, Any]) -> tuple[int, str | None]:
    from pywebpush import WebPushException, webpush

    info = {
        "endpoint": sub.endpoint,
        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
    }
    claims = {"sub": (settings.WEB_PUSH_VAPID_SUBJECT or "mailto:ops@deskrudder.com.br").strip()}
    try:
        webpush(
            subscription_info=info,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=(settings.WEB_PUSH_VAPID_PRIVATE_KEY or "").strip(),
            vapid_claims=claims,
        )
        return 201, None
    except WebPushException as e:
        code = 0
        resp = getattr(e, "response", None)
        if resp is not None:
            code = int(getattr(resp, "status_code", 0) or 0)
        return code, str(e)[:2000]
    except Exception as e:
        return 0, str(e)[:2000]


def process_pending_web_push(db: Session, *, limit: int = 40) -> int:
    if not vapid_configurado():
        return 0
    now = _utcnow()
    rows = (
        db.query(PushOutbox)
        .filter(PushOutbox.status == STATUS_PENDENTE, PushOutbox.scheduled_at <= now)
        .order_by(PushOutbox.scheduled_at.asc())
        .limit(limit)
        .all()
    )
    sent = 0
    for row in rows:
        subs = db.query(PushSubscription).filter(PushSubscription.atendente_id == row.atendente_id).all()
        if not subs:
            row.status = STATUS_ENVIADA
            row.sent_at = now
            row.last_error = "sem subscription"
            continue
        payload = json.loads(row.payload_json)
        row.tentativas = int(row.tentativas or 0) + 1
        algum_ok = False
        ultimo_erro = None
        for sub in subs:
            code, err = _enviar_uma(sub, payload)
            if 200 <= code < 300 or code == 201:
                algum_ok = True
                continue
            if code in (404, 410):
                db.delete(sub)
                log_event(logger, "web_push_subscription_expired", subscription_id=sub.id, http_status=code)
                continue
            ultimo_erro = err or f"HTTP {code}"
        if algum_ok:
            row.status = STATUS_ENVIADA
            row.sent_at = now
            row.last_error = None
            sent += 1
            log_event(logger, "web_push_outbox_send_ok", outbox_id=row.id, event_type=row.event_type)
            continue
        ainda_subs = (
            db.query(PushSubscription.id).filter(PushSubscription.atendente_id == row.atendente_id).first()
        )
        if ainda_subs is None:
            row.status = STATUS_ENVIADA
            row.sent_at = now
            row.last_error = "subscription expirada"
            continue
        row.last_error = ultimo_erro or "falha no envio"
        if row.tentativas >= MAX_EMAIL_SEND_ATTEMPTS:
            row.status = STATUS_FALHA
            log_event(
                logger,
                "web_push_outbox_send_failed_permanent",
                level=logging.ERROR,
                outbox_id=row.id,
                tentativas=row.tentativas,
                error=row.last_error[:500],
            )
        else:
            delay = retry_delay_seconds(row.tentativas)
            row.scheduled_at = now + timedelta(seconds=delay)
            log_event(
                logger,
                "web_push_outbox_send_retry",
                level=logging.WARNING,
                outbox_id=row.id,
                tentativas=row.tentativas,
                retry_in_seconds=delay,
            )
    return sent
