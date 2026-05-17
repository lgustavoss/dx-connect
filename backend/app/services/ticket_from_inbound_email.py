"""
Processamento de e-mail ingerido → ticket (idempotência, threading, resposta a fechado).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.email_inbound_received import EmailInboundReceived
from app.models.empresa import Empresa
from app.models.setor import Setor
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket, TicketMensagem
from app.models.ticket_email_message_id import TicketEmailMessageId
from app.services.email_send_sistema import enviar_mensagem_texto_sistema
from app.services.email_inbound_parse import ParsedInboundEmail, thread_lookup_message_ids
from app.services.system_email_config import get_singleton_email_settings, transactional_config_from_row
from app.services.protocolo_mensal import gerar_protocolo_ticket
from app.services.email_body_sanitize import sanitize_inbound_email_body
from app.services.ticket_email_index import registar_message_id_para_ticket

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailInboundProcessResult:
    ticket: Ticket
    duplicate: bool
    threaded: bool = False
    after_close_new_ticket: bool = False
    auto_reply_sent: bool = False


def _corpo_mensagem(parsed: ParsedInboundEmail, mid: str) -> str:
    """Corpo visível no ticket (sem metadados técnicos de e-mail)."""
    _ = mid
    return sanitize_inbound_email_body(parsed.body_text)


def _find_ticket_by_thread(db: Session, parsed: ParsedInboundEmail) -> Ticket | None:
    for lid in thread_lookup_message_ids(parsed):
        row = db.query(TicketEmailMessageId).filter(TicketEmailMessageId.message_id_normalized == lid).first()
        if row:
            t = db.query(Ticket).filter(Ticket.id == row.ticket_id).first()
            if t:
                return t
    return None


def _try_auto_reply_ticket_encerrado(db: Session, parsed: ParsedInboundEmail, chamado_fechado: Ticket) -> str | None:
    """
    Envia e-mail automático ao remetente. Devolve o Message-ID normalizado do envio, ou ``None`` se não enviou.
    """
    dest = (parsed.from_email or "").strip()
    if not dest:
        logger.info("Auto-resposta pós-fecho: remetente sem e-mail; skip.")
        return None
    cfg = transactional_config_from_row(get_singleton_email_settings(db))
    assinatura = (cfg.from_name.strip() if cfg and cfg.from_name else None) or "Suporte"
    body = (
        f"Olá,\n\n"
        f"O chamado **{chamado_fechado.protocolo}** já se encontra **encerrado** no nosso sistema.\n\n"
        f"— Se a sua questão é **outro assunto** (ou um problema novo), envie um **novo e-mail** "
        f"(sem responder a esta conversa) para abrir um novo registo.\n\n"
        f"— Se considera que esta mensagem **continua o mesmo assunto** do chamado encerrado, a nossa equipa "
        f"irá analisá-la num **novo ticket de triagem** e poderá associá-la ao histórico anterior, se for adequado.\n\n"
        f"Com os melhores cumprimentos,\n{assinatura}\n"
    )
    subj = f"Re: {(parsed.subject or 'Chamado')[:200]}"
    try:
        out_mid_raw = enviar_mensagem_texto_sistema(
            db,
            to_addr=dest,
            subject=subj,
            body=body,
            in_reply_to=parsed.message_id,
        )
        return out_mid_raw if out_mid_raw else None
    except ValueError as e:
        logger.info("Auto-resposta pós-fecho: %s", e)
        return None
    except Exception as e:
        logger.warning("Auto-resposta ticket encerrado falhou: %s", e)
        return None


def _criar_ticket_triagem_pos_fecho(
    db: Session,
    *,
    tenant_id: int,
    empresa_id: int | None,
    setor_id: int,
    status_inicial: StatusTicket,
    parsed: ParsedInboundEmail,
    mid: str,
    chamado_fechado: Ticket,
) -> Ticket:
    assunto_cli = (parsed.subject or "(sem assunto)")[:450]
    assunto = f"[Triagem] {assunto_cli} (ref. #{chamado_fechado.protocolo})"[:500]
    corpo = (
        "[Triagem — resposta por e-mail a chamado **já encerrado**]\n\n"
        f"Chamado de referência: **{chamado_fechado.protocolo}** (ID interno {chamado_fechado.id}).\n"
        f"Message-ID da mensagem do cliente: `{mid}`\n\n"
        "--- Mensagem do cliente ---\n\n"
        f"{parsed.body_text}"
    ).strip()

    protocolo = gerar_protocolo_ticket(db)
    ticket = Ticket(
        tenant_id=tenant_id,
        protocolo=protocolo,
        empresa_id=empresa_id,
        setor_id=setor_id,
        status_id=status_inicial.id,
        assunto=assunto,
        descricao=corpo,
        aberto_por_id=None,
    )
    db.add(ticket)
    db.flush()

    db.add(
        TicketMensagem(
            ticket_id=ticket.id,
            atendente_id=None,
            tipo="email_cliente",
            corpo=corpo,
            autor_externo=(parsed.from_display or parsed.from_email or "")[:512] or None,
        )
    )
    db.add(
        EmailInboundReceived(
            message_id_normalized=mid,
            ticket_id=ticket.id,
            from_address=(parsed.from_display or parsed.from_email or "")[:512],
            subject=(parsed.subject or "(sem assunto)")[:500],
        )
    )
    registar_message_id_para_ticket(db, ticket_id=ticket.id, message_id=mid, source="inbound")
    return ticket


def processar_email_inbound(
    db: Session,
    *,
    tenant_id: int,
    empresa_id: int | None,
    setor_id: int,
    parsed: ParsedInboundEmail,
) -> EmailInboundProcessResult:
    """
    Idempotente por ``parsed.message_id``.

    Ver ``EmailInboundProcessResult`` para o significado dos campos booleanos.
    """
    mid = parsed.message_id
    if not mid:
        raise ValueError("Message-ID é obrigatório para ingestão idempotente.")

    row = db.query(EmailInboundReceived).filter(EmailInboundReceived.message_id_normalized == mid).first()
    if row:
        t = db.query(Ticket).filter(Ticket.id == row.ticket_id).first()
        if t:
            return EmailInboundProcessResult(ticket=t, duplicate=True)
        db.delete(row)
        db.flush()

    if empresa_id is not None:
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id, Empresa.tenant_id == tenant_id).first()
        if not empresa:
            raise ValueError("Empresa não encontrada.")
    setor = db.query(Setor).filter(Setor.id == setor_id, Setor.tenant_id == tenant_id).first()
    if not setor:
        raise ValueError("Setor não encontrado.")

    status_inicial = db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).order_by(StatusTicket.ordem).first()
    if not status_inicial:
        raise ValueError("Cadastre ao menos um status de ticket.")

    existing_ticket = _find_ticket_by_thread(db, parsed)
    if existing_ticket:
        if existing_ticket.fechado_em is not None:
            ticket = _criar_ticket_triagem_pos_fecho(
                db,
                tenant_id=tenant_id,
                empresa_id=empresa_id,
                setor_id=setor_id,
                status_inicial=status_inicial,
                parsed=parsed,
                mid=mid,
                chamado_fechado=existing_ticket,
            )
            out_mid = _try_auto_reply_ticket_encerrado(db, parsed, existing_ticket)
            if out_mid:
                registar_message_id_para_ticket(db, ticket_id=ticket.id, message_id=out_mid, source="outbound")
            db.commit()
            db.refresh(ticket)
            return EmailInboundProcessResult(
                ticket=ticket,
                duplicate=False,
                after_close_new_ticket=True,
                auto_reply_sent=bool(out_mid),
            )

        corpo = _corpo_mensagem(parsed, mid)
        assunto = (parsed.subject or "(sem assunto)")[:500]
        db.add(
            TicketMensagem(
                ticket_id=existing_ticket.id,
                atendente_id=None,
                tipo="email_cliente",
                corpo=corpo,
                autor_externo=(parsed.from_display or parsed.from_email or "")[:512] or None,
            )
        )
        db.add(
            EmailInboundReceived(
                message_id_normalized=mid,
                ticket_id=existing_ticket.id,
                from_address=(parsed.from_display or parsed.from_email or "")[:512],
                subject=assunto[:500],
            )
        )
        registar_message_id_para_ticket(db, ticket_id=existing_ticket.id, message_id=mid, source="inbound")
        db.commit()
        db.refresh(existing_ticket)
        return EmailInboundProcessResult(ticket=existing_ticket, duplicate=False, threaded=True)

    protocolo = gerar_protocolo_ticket(db)
    assunto = (parsed.subject or "(sem assunto)")[:500]
    corpo = _corpo_mensagem(parsed, mid)

    ticket = Ticket(
        tenant_id=tenant_id,
        protocolo=protocolo,
        empresa_id=empresa_id,
        setor_id=setor_id,
        status_id=status_inicial.id,
        assunto=assunto,
        descricao=corpo,
        aberto_por_id=None,
    )
    db.add(ticket)
    db.flush()

    db.add(
        TicketMensagem(
            ticket_id=ticket.id,
            atendente_id=None,
            tipo="email_cliente",
            corpo=corpo,
            autor_externo=(parsed.from_display or parsed.from_email or "")[:512] or None,
        )
    )
    db.add(
        EmailInboundReceived(
            message_id_normalized=mid,
            ticket_id=ticket.id,
            from_address=(parsed.from_display or parsed.from_email or "")[:512],
            subject=assunto[:500],
        )
    )
    registar_message_id_para_ticket(db, ticket_id=ticket.id, message_id=mid, source="inbound")
    db.commit()
    db.refresh(ticket)
    return EmailInboundProcessResult(ticket=ticket, duplicate=False)


def criar_ou_obter_ticket_por_message_id(
    db: Session,
    *,
    tenant_id: int,
    empresa_id: int | None,
    setor_id: int,
    parsed: ParsedInboundEmail,
) -> tuple[Ticket, bool]:
    r = processar_email_inbound(
        db,
        tenant_id=tenant_id,
        empresa_id=empresa_id,
        setor_id=setor_id,
        parsed=parsed,
    )
    return r.ticket, r.duplicate
