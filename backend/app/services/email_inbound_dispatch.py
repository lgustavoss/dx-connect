"""Processamento partilhado: ParsedInboundEmail → ticket (webhooks de ingestão)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.tenant import Tenant
from app.schemas.email_inbound import EmailInboundWebhookResponse
from app.services.email_inbound_parse import ParsedInboundEmail
from app.services.tenant_inbound import resolve_routing_from_recipients
from app.services.funcionario_rede_resolver import resolver_remetente_por_email
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


def _empresa_e_funcionario_do_remetente(
    db: Session,
    parsed: ParsedInboundEmail,
    empresa_id_roteamento: int | None,
) -> tuple[int | None, int | None]:
    """
    Resolve empresa e funcionário pelo e-mail do remetente.
    Prioridade: cadastro de funcionário > empresa default do endereço inbound > env.
    """
    rem = resolver_remetente_por_email(db, parsed.from_email)
    if rem.requer_cadastro:
        return None, None
    aberto_por_id = rem.funcionario_id
    if rem.empresa_id is not None:
        return rem.empresa_id, aberto_por_id
    if rem.empresa_ids_opcao:
        return None, aberto_por_id
    return empresa_id_roteamento, aberto_por_id


def dispatch_parsed_inbound(db: Session, parsed: ParsedInboundEmail) -> EmailInboundWebhookResponse:
    if not parsed.message_id:
        raise ValueError("Message-ID ausente ou inválido.")

    tenant_id, empresa_id_rota, setor_id = resolve_inbound_routing(db, parsed)
    empresa_id, aberto_por_id = _empresa_e_funcionario_do_remetente(db, parsed, empresa_id_rota)
    res = processar_email_inbound(
        db,
        empresa_id=empresa_id,
        setor_id=setor_id,
        parsed=parsed,
        tenant_id=tenant_id,
        aberto_por_id=aberto_por_id,
    )
    return EmailInboundWebhookResponse(
        ticket_id=res.ticket.id,
        protocolo=res.ticket.protocolo,
        duplicate=res.duplicate,
        threaded=res.threaded,
        after_close_new_ticket=res.after_close_new_ticket,
        auto_reply_sent=res.auto_reply_sent,
    )
