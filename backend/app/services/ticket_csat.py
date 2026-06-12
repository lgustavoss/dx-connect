"""CSAT de tickets: convite por e-mail (24h) e métricas por atendente."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.ticket_avaliacao import TicketAvaliacao, TicketCsatInvite
from app.services.email_send_sistema import enviar_mensagem_texto_sistema
from app.services.ticket_client_email import resolver_email_cliente_ticket, ultima_mensagem_inbound
from app.services.password_reset import _public_app_origin  # reuse origin builder

logger = logging.getLogger(__name__)

CSAT_EXPIRE_HOURS = 24
MSG_TOKEN_INVALIDO = "Link inválido ou expirado."


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_csat_link(raw_token: str) -> str:
    origin = _public_app_origin().rstrip("/")
    return f"{origin}/avaliar-ticket?token={raw_token}"


def _invalidate_pending_invites(db: Session, ticket_id: int) -> None:
    now = datetime.now(timezone.utc)
    rows = (
        db.query(TicketCsatInvite)
        .filter(
            TicketCsatInvite.ticket_id == ticket_id,
            TicketCsatInvite.used_at.is_(None),
        )
        .all()
    )
    for row in rows:
        if _as_utc_aware(row.expires_at) > now:
            row.used_at = now


def _convite_ativo(db: Session, ticket_id: int) -> TicketCsatInvite | None:
    now = datetime.now(timezone.utc)
    return (
        db.query(TicketCsatInvite)
        .filter(
            TicketCsatInvite.ticket_id == ticket_id,
            TicketCsatInvite.used_at.is_(None),
            TicketCsatInvite.expires_at > now,
        )
        .order_by(TicketCsatInvite.id.desc())
        .first()
    )


def csat_brief_para_ticket(db: Session, ticket_id: int) -> dict:
    aval = db.query(TicketAvaliacao).filter(TicketAvaliacao.ticket_id == ticket_id).first()
    if aval:
        return {
            "avaliacao_nota": aval.nota,
            "avaliacao_comentario": aval.comentario,
            "avaliacao_respondida_em": aval.respondida_em,
            "csat_pendente": False,
        }
    pendente = _convite_ativo(db, ticket_id) is not None
    return {
        "avaliacao_nota": None,
        "avaliacao_comentario": None,
        "avaliacao_respondida_em": None,
        "csat_pendente": pendente,
    }


def criar_convite_csat(
    db: Session,
    ticket_id: int,
    *,
    enviar_email: bool = True,
    exigir_email_cliente: bool = True,
) -> dict | None:
    """
    Cria convite CSAT para ticket fechado. Retorna ``{link, expires_at}`` ou None se não aplicável.

    ``exigir_email_cliente=False`` permite convite em dev sem histórico inbound (sem enviar e-mail).
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket or ticket.fechado_em is None:
        return None
    if db.query(TicketAvaliacao).filter(TicketAvaliacao.ticket_id == ticket_id).first():
        return None

    to_addr = resolver_email_cliente_ticket(db, ticket_id)
    if exigir_email_cliente and not to_addr:
        return None

    raw = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=CSAT_EXPIRE_HOURS)
    _invalidate_pending_invites(db, ticket_id)
    invite = TicketCsatInvite(
        ticket_id=ticket_id,
        atendente_id=ticket.atendente_id,
        token_hash=_hash_token(raw),
        expires_at=expires,
    )
    db.add(invite)
    db.commit()

    link = build_csat_link(raw)
    if enviar_email and to_addr:
        proto = ticket.protocolo or str(ticket.id)
        subject = f"Avalie o atendimento — chamado {proto}"
        body = (
            "Olá,\n\n"
            f"Seu chamado {proto} foi encerrado.\n"
            "Gostaríamos de saber como foi sua experiência (nota de 1 a 5 estrelas).\n\n"
            f"Acesse o link abaixo (válido por {CSAT_EXPIRE_HOURS} horas):\n"
            f"{link}\n\n"
            "Obrigado,\n"
            "Equipe de atendimento"
        )
        try:
            inbound = ultima_mensagem_inbound(db, ticket_id)
            in_reply_to = (inbound.message_id_normalized or "").strip() if inbound else None
            enviar_mensagem_texto_sistema(
                db,
                to_addr=to_addr,
                subject=subject[:998],
                body=body,
                in_reply_to=in_reply_to or None,
            )
        except ValueError as e:
            logger.info("CSAT ticket %s: e-mail não enviado (%s)", ticket_id, e)
        except Exception:
            logger.exception("CSAT ticket %s: falha ao enviar e-mail", ticket_id)

    return {"link": link, "expires_at": expires}


def processar_convite_csat_ao_fechar(db: Session, ticket_id: int) -> None:
    """Após fecho do ticket: cria convite e envia e-mail se o cliente tiver endereço."""
    criar_convite_csat(db, ticket_id, enviar_email=True, exigir_email_cliente=True)


def _invite_por_token(db: Session, raw_token: str) -> TicketCsatInvite | None:
    token = (raw_token or "").strip()
    if not token:
        return None
    return db.query(TicketCsatInvite).filter(TicketCsatInvite.token_hash == _hash_token(token)).first()


def consultar_csat_publico(db: Session, raw_token: str) -> dict:
    invite = _invite_por_token(db, raw_token)
    if not invite:
        return {"status": "invalido"}
    ticket = db.query(Ticket).filter(Ticket.id == invite.ticket_id).first()
    aval = db.query(TicketAvaliacao).filter(TicketAvaliacao.ticket_id == invite.ticket_id).first()
    if aval:
        return {
            "status": "respondido",
            "protocolo": ticket.protocolo if ticket else None,
            "assunto": ticket.assunto if ticket else None,
            "nota": aval.nota,
            "comentario": aval.comentario,
            "respondida_em": aval.respondida_em,
        }
    now = datetime.now(timezone.utc)
    if invite.used_at is not None or _as_utc_aware(invite.expires_at) <= now:
        return {
            "status": "expirado",
            "protocolo": ticket.protocolo if ticket else None,
            "assunto": ticket.assunto if ticket else None,
        }
    return {
        "status": "pendente",
        "protocolo": ticket.protocolo if ticket else None,
        "assunto": ticket.assunto if ticket else None,
    }


def registrar_csat_publico(db: Session, raw_token: str, *, nota: int, comentario: str | None) -> None:
    invite = _invite_por_token(db, raw_token)
    if not invite:
        raise ValueError(MSG_TOKEN_INVALIDO)
    now = datetime.now(timezone.utc)
    if invite.used_at is not None or _as_utc_aware(invite.expires_at) <= now:
        raise ValueError(MSG_TOKEN_INVALIDO)
    if db.query(TicketAvaliacao).filter(TicketAvaliacao.ticket_id == invite.ticket_id).first():
        raise ValueError("Este chamado já foi avaliado.")

    comentario_eff = (comentario or "").strip() or None
    aval = TicketAvaliacao(
        ticket_id=invite.ticket_id,
        atendente_id=invite.atendente_id,
        nota=int(nota),
        comentario=comentario_eff,
        invite_id=invite.id,
    )
    invite.used_at = now
    db.add(aval)
    db.commit()
