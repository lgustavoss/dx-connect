"""Processamento partilhado: ParsedInboundEmail → ticket (webhooks de ingestão)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.tenant import Tenant
from app.schemas.email_inbound import EmailInboundWebhookResponse
from app.services.email_inbound_parse import ParsedInboundEmail
from app.services.tenant_inbound import resolve_routing_from_recipients
from app.services.ticket_from_inbound_email import processar_email_inbound


def _defaults_empresa_setor() -> tuple[int, int]:
    eid = settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID
    sid = settings.EMAIL_INBOUND_DEFAULT_SETOR_ID
    if eid is None or sid is None:
        raise ValueError(
            "Configure EMAIL_INBOUND_DEFAULT_EMPRESA_ID e EMAIL_INBOUND_DEFAULT_SETOR_ID "
            "ou um endereço de encaminhamento em Configurações → E-mail."
        )
    return int(eid), int(sid)


def resolve_inbound_routing(db: Session, parsed: ParsedInboundEmail) -> tuple[int, int, int | None]:
    """(tenant_id, empresa_id, setor_id)."""
    cfg, _lp = resolve_routing_from_recipients(db, list(parsed.to_recipients))
    if cfg:
        tenant = db.query(Tenant).filter(Tenant.id == cfg.tenant_id, Tenant.ativo.is_(True)).first()
        if not tenant:
            raise ValueError("Tenant inativo.")
        eid = cfg.default_empresa_id
        if eid is None:
            eid, _ = _defaults_empresa_setor()
        return cfg.tenant_id, int(eid), cfg.setor_id
    empresa_id, setor_id = _defaults_empresa_setor()
    return int(settings.DEFAULT_TENANT_ID), empresa_id, setor_id


def dispatch_parsed_inbound(db: Session, parsed: ParsedInboundEmail) -> EmailInboundWebhookResponse:
    if not parsed.message_id:
        raise ValueError("Message-ID ausente ou inválido.")

    tenant_id, empresa_id, setor_id = resolve_inbound_routing(db, parsed)
    res = processar_email_inbound(
        db,
        empresa_id=empresa_id,
        setor_id=setor_id,
        parsed=parsed,
        tenant_id=tenant_id,
    )
    return EmailInboundWebhookResponse(
        ticket_id=res.ticket.id,
        protocolo=res.ticket.protocolo,
        duplicate=res.duplicate,
        threaded=res.threaded,
        after_close_new_ticket=res.after_close_new_ticket,
        auto_reply_sent=res.auto_reply_sent,
    )
