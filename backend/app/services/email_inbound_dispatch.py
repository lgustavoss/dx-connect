"""Processamento partilhado: ParsedInboundEmail → ticket (webhooks de ingestão)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.tenant import Tenant
from app.schemas.email_inbound import EmailInboundWebhookResponse
from app.services.email_inbound_parse import ParsedInboundEmail
from app.services.tenant_inbound import resolve_routing_from_recipients
from app.services.ticket_from_inbound_email import processar_email_inbound


def _default_setor_id() -> int:
    sid = settings.EMAIL_INBOUND_DEFAULT_SETOR_ID
    if sid is None:
        raise ValueError(
            "Configure EMAIL_INBOUND_DEFAULT_SETOR_ID ou um endereço de encaminhamento em Configurações → E-mail."
        )
    return int(sid)


def _default_empresa_id_optional() -> int | None:
    eid = settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID
    return int(eid) if eid is not None else None


def resolve_inbound_routing(db: Session, parsed: ParsedInboundEmail) -> tuple[int, int | None, int]:
    """(tenant_id, empresa_id ou None na triagem, setor_id)."""
    cfg, _lp = resolve_routing_from_recipients(db, list(parsed.to_recipients))
    if cfg:
        tenant = db.query(Tenant).filter(Tenant.id == cfg.tenant_id, Tenant.ativo.is_(True)).first()
        if not tenant:
            raise ValueError("Tenant inativo.")
        eid = cfg.default_empresa_id
        if eid is None:
            eid = _default_empresa_id_optional()
        return cfg.tenant_id, int(eid) if eid is not None else None, int(cfg.setor_id)
    return int(settings.DEFAULT_TENANT_ID), _default_empresa_id_optional(), _default_setor_id()


def dispatch_parsed_inbound(db: Session, parsed: ParsedInboundEmail) -> EmailInboundWebhookResponse:
    if not parsed.message_id:
        raise ValueError("Message-ID ausente ou inválido.")

    tenant_id, empresa_id, setor_id = resolve_inbound_routing(db, parsed)
    res = processar_email_inbound(
        db,
        empresa_id=empresa_id,  # None = triagem manual no painel
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
