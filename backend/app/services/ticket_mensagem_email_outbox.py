"""
Fila de envio de e-mail para mensagens públicas (#140): janela de graça, lock de edição e worker.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.ticket import Ticket, TicketMensagem
from app.services.ticket_email_grace_config import resolver_grace_seconds
from app.services.ticket_client_email import enviar_resposta_equipa_por_email, ultima_mensagem_inbound
from app.services.ticket_email_index import registar_message_id_para_ticket

logger = logging.getLogger(__name__)

EMAIL_STATUS_PENDENTE = "pendente_envio"
EMAIL_STATUS_EM_EDICAO = "em_edicao"
EMAIL_STATUS_ENVIANDO = "enviando"
EMAIL_STATUS_ENVIADA = "enviada"
EMAIL_STATUS_CANCELADA = "cancelada"

_STATUSES_EDITAVEIS = frozenset({EMAIL_STATUS_PENDENTE, EMAIL_STATUS_EM_EDICAO})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dt_for_db(dt: datetime | None = None) -> datetime:
    """Persistência em UTC naive (compatível SQLite/Postgres)."""
    return _as_utc(dt or _utcnow()).replace(tzinfo=None)  # type: ignore[return-value]


def grace_period_seconds(db: Session) -> int:
    return resolver_grace_seconds(db)


def edit_lock_ttl_seconds() -> int:
    return max(30, int(settings.TICKET_MENSAGEM_EDIT_LOCK_TTL_SECONDS))


def validar_pode_agendar_email_cliente(db: Session, ticket_id: int) -> None:
    """Mesmas pré-condições de ``enviar_resposta_equipa_por_email``, sem enviar."""
    row = ultima_mensagem_inbound(db, ticket_id)
    if not row:
        raise ValueError(
            "Este ticket não tem histórico de e-mail recebido pelo webhook; não é possível notificar o cliente por e-mail."
        )
    from app.services.ticket_client_email import extrair_email_de_from_address

    if not extrair_email_de_from_address(row.from_address):
        raise ValueError(
            "Não foi possível determinar o e-mail do cliente a partir do último remetente recebido. "
            "Peça ao cliente um contacto válido ou use outro canal."
        )
    if not (row.message_id_normalized or "").strip():
        raise ValueError("Message-ID da última mensagem recebida está em falta; não é possível encadear o e-mail.")

    from app.services.system_email_config import get_singleton_email_settings, transactional_config_from_row

    settings_row = get_singleton_email_settings(db)
    if not transactional_config_from_row(settings_row):
        raise ValueError(
            "Envio de e-mail não configurado na plataforma. Contacte o administrador da instalação."
        )


def agendar_envio_email(m: TicketMensagem, db: Session, *, ref: datetime | None = None) -> None:
    now = _dt_for_db(ref)
    secs = grace_period_seconds(db)
    m.email_status = EMAIL_STATUS_PENDENTE
    m.scheduled_at = now if secs == 0 else now + timedelta(seconds=secs)
    m.sent_at = None
    m.edit_lock_token = None
    m.edit_lock_expires_at = None
    m.updated_at = now


def _reagendar_apos_edicao(m: TicketMensagem, db: Session, *, now: datetime) -> None:
    secs = grace_period_seconds(db)
    m.scheduled_at = now if secs == 0 else now + timedelta(seconds=secs)


def liberar_locks_expirados(db: Session, *, ref: datetime | None = None) -> int:
    now = _dt_for_db(ref)
    rows = (
        db.query(TicketMensagem)
        .filter(
            TicketMensagem.email_status == EMAIL_STATUS_EM_EDICAO,
            TicketMensagem.edit_lock_expires_at.isnot(None),
        )
        .all()
    )
    liberados = 0
    for m in rows:
        exp = _as_utc(m.edit_lock_expires_at)
        if exp is None or exp.replace(tzinfo=None) >= now:
            continue
        m.email_status = EMAIL_STATUS_PENDENTE
        m.edit_lock_token = None
        m.edit_lock_expires_at = None
        _reagendar_apos_edicao(m, db, now=now)
        m.updated_at = now
        liberados += 1
    return liberados


def _enviar_uma(db: Session, m: TicketMensagem, ticket: Ticket) -> bool:
    if m.email_status == EMAIL_STATUS_ENVIADA:
        return False
    if m.email_status not in (EMAIL_STATUS_PENDENTE, EMAIL_STATUS_ENVIANDO):
        return False
    if m.email_status == EMAIL_STATUS_EM_EDICAO:
        return False

    now = _dt_for_db()
    m.email_status = EMAIL_STATUS_ENVIANDO
    m.updated_at = now
    db.flush()

    try:
        out_mid = enviar_resposta_equipa_por_email(db, ticket=ticket, corpo=m.corpo)
    except Exception:
        m.email_status = EMAIL_STATUS_PENDENTE
        m.scheduled_at = now + timedelta(seconds=60)
        m.updated_at = now
        raise

    registar_message_id_para_ticket(db, ticket_id=ticket.id, message_id=out_mid, source="outbound")
    m.email_status = EMAIL_STATUS_ENVIADA
    m.sent_at = now
    m.scheduled_at = None
    m.edit_lock_token = None
    m.edit_lock_expires_at = None
    m.updated_at = now
    return True


def process_pending_ticket_mensagem_emails(db: Session, *, limit: int = 20) -> int:
    """
    Processa mensagens prontas para envio. Devolve quantas foram enviadas com sucesso.
    """
    liberar_locks_expirados(db)
    now = _dt_for_db()

    q = (
        db.query(TicketMensagem)
        .filter(
            TicketMensagem.email_status == EMAIL_STATUS_PENDENTE,
            TicketMensagem.scheduled_at.isnot(None),
        )
        .order_by(TicketMensagem.scheduled_at.asc())
        .limit(limit)
    )
    try:
        q = q.with_for_update(skip_locked=True)
    except Exception:
        q = q.with_for_update()

    rows = q.all()
    enviadas = 0
    for m in rows:
        if m.scheduled_at is None or m.scheduled_at > now:
            continue
        ticket = db.query(Ticket).filter(Ticket.id == m.ticket_id).first()
        if not ticket:
            continue
        try:
            if _enviar_uma(db, m, ticket):
                enviadas += 1
        except Exception as e:
            logger.warning(
                "Falha ao enviar e-mail da mensagem %s (ticket %s): %s",
                m.id,
                m.ticket_id,
                e,
            )
    return enviadas


def mensagem_em_fila_email(m: TicketMensagem) -> bool:
    return m.email_status in _STATUSES_EDITAVEIS or m.email_status == EMAIL_STATUS_ENVIANDO


def pode_editar_mensagem_email(m: TicketMensagem) -> bool:
    return m.email_status in _STATUSES_EDITAVEIS


def iniciar_edicao(m: TicketMensagem) -> str:
    if not pode_editar_mensagem_email(m):
        raise ValueError("Esta mensagem não pode ser editada (já enviada ou cancelada).")
    now = _dt_for_db()
    token = str(uuid.uuid4())
    m.email_status = EMAIL_STATUS_EM_EDICAO
    m.edit_lock_token = token
    m.edit_lock_expires_at = now + timedelta(seconds=edit_lock_ttl_seconds())
    m.updated_at = now
    return token


def validar_lock(m: TicketMensagem, token: str) -> None:
    if m.email_status != EMAIL_STATUS_EM_EDICAO:
        raise ValueError("A mensagem não está em edição.")
    if not m.edit_lock_token or m.edit_lock_token != token:
        raise ValueError("Token de edição inválido.")
    exp = _as_utc(m.edit_lock_expires_at)
    if exp and exp.replace(tzinfo=None) < _dt_for_db():
        raise ValueError("O lock de edição expirou. Inicie a edição novamente.")


def salvar_edicao(m: TicketMensagem, db: Session, *, corpo: str) -> None:
    now = _dt_for_db()
    m.corpo = corpo.strip()
    m.email_status = EMAIL_STATUS_PENDENTE
    m.edit_lock_token = None
    m.edit_lock_expires_at = None
    _reagendar_apos_edicao(m, db, now=now)
    m.updated_at = now


def cancelar_envio(m: TicketMensagem) -> None:
    if m.email_status == EMAIL_STATUS_ENVIADA:
        raise ValueError("Mensagem já enviada por e-mail; não é possível cancelar.")
    if m.email_status == EMAIL_STATUS_CANCELADA:
        return
    now = _dt_for_db()
    m.email_status = EMAIL_STATUS_CANCELADA
    m.scheduled_at = None
    m.edit_lock_token = None
    m.edit_lock_expires_at = None
    m.updated_at = now


def forcar_envio_agora(m: TicketMensagem) -> None:
    if m.email_status == EMAIL_STATUS_ENVIADA:
        raise ValueError("Mensagem já enviada.")
    if m.email_status == EMAIL_STATUS_CANCELADA:
        raise ValueError("Mensagem cancelada.")
    if m.email_status == EMAIL_STATUS_EM_EDICAO:
        raise ValueError("Termine a edição antes de enviar agora.")
    now = _dt_for_db()
    m.email_status = EMAIL_STATUS_PENDENTE
    m.scheduled_at = now
    m.updated_at = now
