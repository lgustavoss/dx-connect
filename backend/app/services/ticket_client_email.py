"""
Envio de resposta da equipa ao cliente (Resend API), com threading (In-Reply-To) (#165).
"""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.models.email_inbound_received import EmailInboundReceived
from app.models.ticket import Ticket
from app.services.email_send_sistema import enviar_mensagem_texto_sistema
from app.services.system_email_config import get_singleton_email_settings, transactional_config_from_row

logger = logging.getLogger(__name__)

_ANGLE_EMAIL = re.compile(r"<([^<>\s]+@[^<>]+\.[^<>]+)>", re.IGNORECASE)
_BARE_EMAIL = re.compile(r"^[^\s<>]+@[^\s<>]+\.[^\s<>]+$", re.IGNORECASE)


def extrair_email_de_from_address(raw: str | None) -> str | None:
    """Extrai o primeiro endereço ``email@dominio`` de um cabeçalho From ou string semelhante."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    m = _ANGLE_EMAIL.search(s)
    if m:
        return m.group(1).strip().lower()
    partes = s.replace(",", " ").split()
    for p in partes:
        p = p.strip().strip('"').strip("'")
        if _BARE_EMAIL.match(p):
            return p.lower()
    if _BARE_EMAIL.match(s):
        return s.lower()
    return None


def extrair_nome_de_from_address(raw: str | None) -> str | None:
    """Extrai nome legível antes do endereço em formato ``Nome <email@dominio>``."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    m = _ANGLE_EMAIL.search(s)
    if not m:
        return None
    nome = s[: m.start()].strip().strip('"').strip("'")
    return nome or None


def ultima_mensagem_inbound(db: Session, ticket_id: int) -> EmailInboundReceived | None:
    return (
        db.query(EmailInboundReceived)
        .filter(EmailInboundReceived.ticket_id == ticket_id)
        .order_by(EmailInboundReceived.id.desc())
        .first()
    )


def resolver_email_cliente_ticket(db: Session, ticket_id: int) -> str | None:
    """Endereço do cliente a partir do último e-mail recebido na thread do ticket."""
    row = ultima_mensagem_inbound(db, ticket_id)
    if not row:
        return None
    return extrair_email_de_from_address(row.from_address)


def enviar_resposta_equipa_por_email(db: Session, *, ticket: Ticket, corpo: str) -> str:
    """
    Envia e-mail ao último remetente conhecido (ingestão) e devolve o **Message-ID** normalizado do envio.

    Não grava índice nem mensagem — o chamador deve fazê-lo na mesma transacção após sucesso do envio.

    :raises ValueError: destinatário ou envio transaccional indisponível, ou sem histórico inbound.
    """
    row = ultima_mensagem_inbound(db, ticket.id)
    if not row:
        raise ValueError(
            "Este ticket não tem histórico de e-mail recebido pelo webhook; não é possível notificar o cliente por e-mail."
        )
    to_addr = extrair_email_de_from_address(row.from_address)
    if not to_addr:
        raise ValueError(
            "Não foi possível determinar o e-mail do cliente a partir do último remetente recebido. "
            "Peça ao cliente um contacto válido ou use outro canal."
        )
    in_reply_to = (row.message_id_normalized or "").strip()
    if not in_reply_to:
        raise ValueError("Message-ID da última mensagem recebida está em falta; não é possível encadear o e-mail.")

    settings_row = get_singleton_email_settings(db)
    if not transactional_config_from_row(settings_row):
        raise ValueError(
            "Envio de e-mail não configurado na plataforma. Contacte o administrador da instalação."
        )

    base = (ticket.assunto or "Chamado").strip()[:200]
    low = base.lower()
    subj = base if low.startswith("re:") else f"Re: {base}"
    try:
        return enviar_mensagem_texto_sistema(
            db,
            to_addr=to_addr,
            subject=subj[:998],
            body=corpo.strip(),
            in_reply_to=in_reply_to,
        )
    except Exception as e:
        logger.warning("Falha ao enviar resposta da equipa por e-mail (ticket %s): %s", ticket.id, e)
        raise ValueError("Falha ao enviar e-mail. Verifique a configuração de envio da plataforma.") from e
