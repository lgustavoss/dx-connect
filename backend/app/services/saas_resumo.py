"""Resumo operacional do control-plane SaaS."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.cliente_saas import ClienteSaaS
from app.models.lead_comercial import LeadComercial
from app.schemas.saas import SaasResumoRead


def obter_resumo(db: Session) -> SaasResumoRead:
    janela = max(1, int(settings.SAAS_RENEWAL_ALERT_DAYS_BEFORE or 14))
    hoje = date.today()
    limite = hoje + timedelta(days=janela)

    total = db.query(func.count(ClienteSaaS.id)).scalar() or 0
    por_status_rows = (
        db.query(ClienteSaaS.status, func.count(ClienteSaaS.id)).group_by(ClienteSaaS.status).all()
    )
    por_status = {str(status): int(n) for status, n in por_status_rows}

    vencendo = (
        db.query(func.count(ClienteSaaS.id))
        .filter(
            ClienteSaaS.status.in_(("trial", "ativo")),
            ClienteSaaS.data_renovacao.isnot(None),
            ClienteSaaS.data_renovacao >= hoje,
            ClienteSaaS.data_renovacao <= limite,
        )
        .scalar()
        or 0
    )
    vencidas = (
        db.query(func.count(ClienteSaaS.id))
        .filter(
            ClienteSaaS.status.in_(("trial", "ativo")),
            ClienteSaaS.data_renovacao.isnot(None),
            ClienteSaaS.data_renovacao < hoje,
        )
        .scalar()
        or 0
    )
    prov_pendente = (
        db.query(func.count(ClienteSaaS.id))
        .filter(ClienteSaaS.provisionamento_status.in_(("pendente", "aguardando_ops", "em_progresso")))
        .scalar()
        or 0
    )
    prov_falha = (
        db.query(func.count(ClienteSaaS.id))
        .filter(ClienteSaaS.provisionamento_status == "falha")
        .scalar()
        or 0
    )
    leads_novos = (
        db.query(func.count(LeadComercial.id)).filter(LeadComercial.status == "novo").scalar() or 0
    )
    leads_atend = (
        db.query(func.count(LeadComercial.id))
        .filter(LeadComercial.status == "em_atendimento")
        .scalar()
        or 0
    )

    return SaasResumoRead(
        clientes_total=int(total),
        por_status=por_status,
        vencendo_em_breve=int(vencendo),
        vencidas_ativas=int(vencidas),
        provisionamento_pendente=int(prov_pendente),
        provisionamento_falha=int(prov_falha),
        leads_novos=int(leads_novos),
        leads_em_atendimento=int(leads_atend),
        janela_renovacao_dias=janela,
    )
