"""Notificações por e-mail para atendentes (#109): preferências, fila e disparos."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.core.structured_log import log_event
from app.models.atendente import Atendente
from app.models.atendente_notificacao import AtendenteNotificacaoPreferencias, NotificacaoEmailOutbox
from app.models.ticket import Ticket, TicketMensagem
from app.services.email_outbox_policy import MAX_EMAIL_SEND_ATTEMPTS
from app.services.email_send_sistema import enviar_mensagem_texto_sistema
from app.services.password_reset import _public_app_origin

logger = logging.getLogger(__name__)

STATUS_PENDENTE = "pendente"
STATUS_ENVIADA = "enviada"
STATUS_FALHA = "falha"

TIPO_TICKET_ATRIBUIDO = "ticket_atribuido"
TIPO_NOVA_MENSAGEM = "nova_mensagem"
TIPO_SLA_EM_RISCO = "sla_em_risco"
TIPO_SLA_VIOLADO = "sla_violado"

MAX_TENTATIVAS = MAX_EMAIL_SEND_ATTEMPTS


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _debounce_minutes() -> int:
    return max(1, int(settings.NOTIFICACAO_EMAIL_DEBOUNCE_MINUTES))


def _ticket_link() -> str:
    origin = _public_app_origin().rstrip("/")
    return f"{origin}/tickets"


def obter_ou_criar_preferencias(db: Session, atendente_id: int) -> AtendenteNotificacaoPreferencias:
    row = (
        db.query(AtendenteNotificacaoPreferencias)
        .filter(AtendenteNotificacaoPreferencias.atendente_id == atendente_id)
        .first()
    )
    if row:
        return row
    row = AtendenteNotificacaoPreferencias(atendente_id=atendente_id)
    db.add(row)
    db.flush()
    return row


def preferencias_para_dict(p: AtendenteNotificacaoPreferencias) -> dict:
    return {
        "email_habilitado": bool(p.email_habilitado),
        "email_ticket_atribuido": bool(p.email_ticket_atribuido),
        "email_nova_mensagem": bool(p.email_nova_mensagem),
        "email_sla_em_risco": bool(getattr(p, "email_sla_em_risco", True)),
        "email_sla_violado": bool(getattr(p, "email_sla_violado", True)),
    }


def atualizar_preferencias(db: Session, atendente_id: int, data: dict) -> AtendenteNotificacaoPreferencias:
    row = obter_ou_criar_preferencias(db, atendente_id)
    for k, v in data.items():
        if v is not None:
            setattr(row, k, v)
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def _deve_notificar(prefs: AtendenteNotificacaoPreferencias, *, tipo: str) -> bool:
    if not prefs.email_habilitado:
        return False
    if tipo == TIPO_TICKET_ATRIBUIDO:
        return bool(prefs.email_ticket_atribuido)
    if tipo == TIPO_NOVA_MENSAGEM:
        return bool(prefs.email_nova_mensagem)
    if tipo == TIPO_SLA_EM_RISCO:
        return bool(getattr(prefs, "email_sla_em_risco", True))
    if tipo == TIPO_SLA_VIOLADO:
        return bool(getattr(prefs, "email_sla_violado", True))
    return False


def _enqueue_email(
    db: Session,
    *,
    atendente: Atendente,
    ticket: Ticket | None,
    tipo: str,
    dedup_key: str,
    subject: str,
    body: str,
    debounce: bool = False,
) -> None:
    if not (atendente.email or "").strip() or not atendente.ativo:
        return
    prefs = obter_ou_criar_preferencias(db, atendente.id)
    if not _deve_notificar(prefs, tipo=tipo):
        return

    now = _utcnow()
    scheduled = now
    if debounce:
        scheduled = now + timedelta(minutes=_debounce_minutes())

    existing = (
        db.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.dedup_key == dedup_key,
            NotificacaoEmailOutbox.status == STATUS_PENDENTE,
        )
        .first()
    )
    if existing:
        if debounce:
            existing.scheduled_at = scheduled
            existing.subject = subject[:998]
            existing.body = body
            existing.to_email = atendente.email.strip().lower()
            return
        existing.subject = subject[:998]
        existing.body = body
        existing.to_email = atendente.email.strip().lower()
        existing.scheduled_at = scheduled
        existing.last_error = None
        return

    failed = (
        db.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.dedup_key == dedup_key,
            NotificacaoEmailOutbox.status == STATUS_FALHA,
            NotificacaoEmailOutbox.tentativas >= MAX_TENTATIVAS,
        )
        .first()
    )
    if failed:
        return

    db.add(
        NotificacaoEmailOutbox(
            atendente_id=atendente.id,
            ticket_id=ticket.id if ticket else None,
            tipo=tipo,
            dedup_key=dedup_key,
            to_email=atendente.email.strip().lower(),
            subject=subject[:998],
            body=body,
            status=STATUS_PENDENTE,
            scheduled_at=scheduled,
        )
    )


def notificar_ticket_atribuido(
    db: Session,
    *,
    ticket: Ticket,
    novo_atendente_id: int,
    actor_id: int | None = None,
) -> None:
    if ticket.fechado_em is not None:
        return
    if novo_atendente_id == actor_id:
        return
    atendente = db.query(Atendente).filter(Atendente.id == novo_atendente_id, Atendente.ativo.is_(True)).first()
    if not atendente:
        return
    proto = ticket.protocolo or str(ticket.id)
    link = _ticket_link()
    subject = f"Chamado atribuído a você — {proto}"
    body = (
        f"Olá {atendente.nome},\n\n"
        f"O chamado {proto} foi atribuído a você.\n"
        f"Assunto: {ticket.assunto or '—'}\n\n"
        f"Acesse: {link}\n"
    )
    dedup = f"atribuido:{novo_atendente_id}:{ticket.id}"
    try:
        _enqueue_email(
            db,
            atendente=atendente,
            ticket=ticket,
            tipo=TIPO_TICKET_ATRIBUIDO,
            dedup_key=dedup,
            subject=subject,
            body=body,
            debounce=False,
        )
    except Exception:
        logger.exception("Falha ao enfileirar notificação de atribuição (ticket %s)", ticket.id)


def notificar_nova_mensagem_ticket(
    db: Session,
    *,
    ticket: Ticket,
    mensagem: TicketMensagem,
    autor_atendente_id: int | None,
) -> None:
    if ticket.fechado_em is not None or ticket.atendente_id is None:
        return
    if mensagem.tipo not in ("publico", "email_cliente"):
        return
    if autor_atendente_id is not None and autor_atendente_id == ticket.atendente_id:
        return

    atendente = (
        db.query(Atendente)
        .filter(Atendente.id == ticket.atendente_id, Atendente.ativo.is_(True))
        .first()
    )
    if not atendente:
        return

    proto = ticket.protocolo or str(ticket.id)
    link = _ticket_link()
    preview = (mensagem.corpo or "").strip().replace("\n", " ")[:200]
    if len((mensagem.corpo or "").strip()) > 200:
        preview += "…"
    origem = (mensagem.autor_externo or "").strip() or "Cliente"
    if mensagem.tipo == "publico" and mensagem.atendente_id:
        autor = db.query(Atendente).filter(Atendente.id == mensagem.atendente_id).first()
        if autor:
            origem = autor.nome

    subject = f"Nova mensagem — {proto}"
    body = (
        f"Olá {atendente.nome},\n\n"
        f"Há uma nova mensagem no chamado {proto}.\n"
        f"De: {origem}\n"
        f"Prévia: {preview or '—'}\n\n"
        f"Acesse: {link}\n"
    )
    dedup = f"nova_msg:{ticket.atendente_id}:{ticket.id}"
    try:
        _enqueue_email(
            db,
            atendente=atendente,
            ticket=ticket,
            tipo=TIPO_NOVA_MENSAGEM,
            dedup_key=dedup,
            subject=subject,
            body=body,
            debounce=True,
        )
    except Exception:
        logger.exception("Falha ao enfileirar notificação de mensagem (ticket %s)", ticket.id)


def notificar_sla_alerta_email(
    db: Session,
    *,
    atendente: Atendente,
    ticket: Ticket,
    meta: str,
    evento: str,
    meta_label: str,
    evento_label: str,
) -> None:
    if ticket.fechado_em is not None:
        return
    proto = ticket.protocolo or str(ticket.id)
    link = _ticket_link()
    tipo = TIPO_SLA_EM_RISCO if evento == "em_risco" else TIPO_SLA_VIOLADO
    subject = f"SLA {evento_label} — {proto} ({meta_label})"
    body = (
        f"Olá {atendente.nome},\n\n"
        f"O chamado {proto} está com SLA de {meta_label.lower()} {evento_label}.\n"
        f"Assunto: {ticket.assunto or '—'}\n\n"
        f"Acesse: {link}\n"
    )
    dedup = f"sla:{evento}:{meta}:{ticket.id}:{atendente.id}"
    _enqueue_email(
        db,
        atendente=atendente,
        ticket=ticket,
        tipo=tipo,
        dedup_key=dedup,
        subject=subject,
        body=body,
        debounce=False,
    )


def process_pending_notificacao_emails(db: Session, *, limit: int = 20) -> int:
    now = _utcnow()
    rows = (
        db.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.status == STATUS_PENDENTE,
            NotificacaoEmailOutbox.scheduled_at <= now,
        )
        .order_by(NotificacaoEmailOutbox.scheduled_at.asc())
        .limit(limit)
        .all()
    )
    sent = 0
    for row in rows:
        row.tentativas = int(row.tentativas or 0) + 1
        try:
            enviar_mensagem_texto_sistema(
                db,
                to_addr=row.to_email,
                subject=row.subject,
                body=row.body,
            )
            row.status = STATUS_ENVIADA
            row.sent_at = now
            row.last_error = None
            row.dedup_key = f"{row.dedup_key}:sent:{row.id}"
            sent += 1
            log_event(
                logger,
                "notificacao_email_send_ok",
                outbox_id=row.id,
                tipo=row.tipo,
                ticket_id=row.ticket_id,
                atendente_id=row.atendente_id,
            )
        except ValueError as e:
            row.last_error = str(e)[:2000]
            if settings.ENVIRONMENT == "development":
                log_event(
                    logger,
                    "notificacao_email_send_simulated_dev",
                    outbox_id=row.id,
                    to_email=row.to_email,
                    subject=row.subject,
                    tipo=row.tipo,
                    ticket_id=row.ticket_id,
                )
                row.status = STATUS_ENVIADA
                row.sent_at = now
                row.dedup_key = f"{row.dedup_key}:sent:{row.id}"
                sent += 1
            elif row.tentativas >= MAX_TENTATIVAS:
                row.status = STATUS_FALHA
                log_event(
                    logger,
                    "notificacao_email_send_failed_permanent",
                    level=logging.ERROR,
                    outbox_id=row.id,
                    tentativas=row.tentativas,
                    error=str(e)[:500],
                )
            else:
                log_event(
                    logger,
                    "notificacao_email_send_retry",
                    level=logging.WARNING,
                    outbox_id=row.id,
                    tentativas=row.tentativas,
                    error=str(e)[:500],
                )
        except Exception as e:
            row.last_error = str(e)[:2000]
            if row.tentativas >= MAX_TENTATIVAS:
                row.status = STATUS_FALHA
                log_event(
                    logger,
                    "notificacao_email_send_failed_permanent",
                    level=logging.ERROR,
                    outbox_id=row.id,
                    tentativas=row.tentativas,
                    error=str(e)[:500],
                )
            else:
                log_event(
                    logger,
                    "notificacao_email_send_retry",
                    level=logging.WARNING,
                    outbox_id=row.id,
                    tentativas=row.tentativas,
                    error=str(e)[:500],
                )
            logger.exception("Falha ao enviar notificação e-mail %s", row.id)
    return sent
