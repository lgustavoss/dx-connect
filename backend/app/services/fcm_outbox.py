"""Outbox FCM — enfileirar após o evento de negócio e enviar no worker (#1315)."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.structured_log import log_event
from app.database import SessionLocal
from app.models.atendente_notificacao import AtendenteNotificacaoPreferencias
from app.models.dispositivo import Dispositivo, FcmOutbox
from app.services.email_outbox_policy import MAX_EMAIL_SEND_ATTEMPTS, retry_delay_seconds
from app.services.fcm import enviar_para_token, fcm_configurado
from app.services.notificacao_atendente_email import obter_ou_criar_preferencias

logger = logging.getLogger(__name__)

STATUS_PENDENTE = "pendente"
STATUS_ENVIADA = "enviada"
STATUS_FALHA = "falha"

TIPOS_FILA = frozenset({"chat.fila", "ticket.fila", "portal.chat.fila", "chat.fila.remind"})
EVENTO_FILA_REMIND = "chat.fila.remind"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _prefs_permitem(prefs: AtendenteNotificacaoPreferencias, event_type: str) -> bool:
    """Mesma regra do Web Push: desligar push no perfil vale para o celular também."""
    if not bool(getattr(prefs, "push_habilitado", False)):
        return False
    if event_type in TIPOS_FILA and not bool(getattr(prefs, "push_fila", True)):
        return False
    return True


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
    """Abre sessão própria. Independente de VAPID — precisa de FCM configurado e token cadastrado."""
    if not fcm_configurado():
        return
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
            prefs = obter_ou_criar_preferencias(db, aid)
            if not _prefs_permitem(prefs, event_type):
                continue
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


def _contar_fila_por_atendente(db: Session) -> dict[int, int]:
    """Agrega chats WhatsApp + Portal em aguardando_atendente por destinatário do push."""
    from app.models.portal_chat import PortalChat
    from app.models.whatsapp_chat import WhatsappChat
    from app.services.realtime_emit import ids_atendentes_chat_fila, ids_atendentes_portal_chat_fila

    counts: dict[int, int] = defaultdict(int)
    for chat in db.query(WhatsappChat).filter(WhatsappChat.estado == "aguardando_atendente").all():
        for aid in ids_atendentes_chat_fila(db, chat):
            counts[int(aid)] += 1
    for chat in db.query(PortalChat).filter(PortalChat.estado == "aguardando_atendente").all():
        for aid in ids_atendentes_portal_chat_fila(db, chat):
            counts[int(aid)] += 1
    return dict(counts)


def process_fila_fcm_reminders() -> int:
    """
    Reaviso periódico de fila para o celular (#1315), análogo ao Web Push.
    Um push por atendente elegível por janela WEB_PUSH_FILA_REMIND_MINUTES.
    """
    if not fcm_configurado():
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
            tem_disp = db.query(Dispositivo.id).filter(Dispositivo.atendente_id == aid).limit(1).first()
            if tem_disp is None:
                continue
            dedup_key = f"fcm:{EVENTO_FILA_REMIND}:{aid}:{bucket}"
            if _dedup_ja_processado(db, dedup_key):
                continue
            corpo = "Há 1 chat aguardando atendimento" if n == 1 else f"Há {n} chats aguardando atendimento"
            payload = {
                "tipo": EVENTO_FILA_REMIND,
                "id": int(aid),
                "titulo": "Clientes na fila",
                "url_path": "/chat/espera",
                "corpo": corpo,
                # O painel usa /chat/espera; no celular a aba de chats é a rota válida.
                "deep_link": "/chat",
            }
            db.add(
                FcmOutbox(
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
            log_event(logger, "fcm_fila_remind_enqueued", atendentes=enfileirados)
        else:
            db.rollback()
        return enfileirados
    except IntegrityError:
        db.rollback()
        return 0
    except Exception:
        db.rollback()
        logger.exception("Falha ao enfileirar lembretes FCM da fila")
        return 0
    finally:
        db.close()


def _token_invalido(codigo: int, erro: str | None) -> bool:
    """Token que nunca mais vai funcionar: 404/410, 400 INVALID_ARGUMENT e 403 SENDER_ID_MISMATCH."""
    texto = (erro or "").lower()
    # O FCM alterna entre SENDER_ID_MISMATCH / SenderIdMismatch / INVALID_ARGUMENT.
    normalizado = texto.replace("_", "").replace(" ", "")
    if codigo in (404, 410):
        return True
    if codigo == 400:
        return "invalidargument" in normalizado or "registrationtoken" in normalizado
    if codigo == 403:
        return "senderidmismatch" in normalizado
    return False


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
        try:
            sent += _processar_uma(db, row)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Falha ao processar FCM outbox %s", row.id)
    return sent


def _processar_uma(db: Session, row: FcmOutbox) -> int:
    now = _utcnow()
    alvos = [
        (d.id, d.token)
        for d in db.query(Dispositivo).filter(Dispositivo.atendente_id == row.atendente_id).all()
    ]
    if not alvos:
        row.status = STATUS_ENVIADA
        row.sent_at = now
        row.last_error = "sem dispositivo"
        return 0
    payload_json = row.payload_json
    row.tentativas = int(row.tentativas or 0) + 1
    # Libera a transação antes do I/O de rede: o worker não segura lock/lendo linha
    # enquanto fala com o FCM (o push é at-least-once, o contador já está gravado).
    if db.in_transaction():
        db.commit()
    payload = json.loads(payload_json)
    algum_ok = False
    removidos = 0
    ultimo_erro = None
    for disp_id, token in alvos:
        codigo, erro = enviar_para_token(token, payload)
        if 200 <= codigo < 300:
            algum_ok = True
            continue
        if _token_invalido(codigo, erro):
            disp = db.get(Dispositivo, disp_id)
            if disp is not None:
                db.delete(disp)
            removidos += 1
            log_event(logger, "fcm_dispositivo_expirado", dispositivo_id=disp_id, http_status=codigo)
            continue
        ultimo_erro = erro or f"HTTP {codigo}"
    if algum_ok:
        row.status = STATUS_ENVIADA
        row.sent_at = now
        row.last_error = None
        log_event(logger, "fcm_outbox_send_ok", outbox_id=row.id, event_type=row.event_type)
        return 1
    if removidos >= len(alvos):
        # Todos os tokens do atendente eram inválidos: nada a reenviar.
        row.status = STATUS_ENVIADA
        row.sent_at = now
        row.last_error = "token expirado"
        return 0
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
        return 0
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
    return 0
