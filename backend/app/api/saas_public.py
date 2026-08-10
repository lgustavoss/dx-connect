"""Endpoints públicos do control-plane SaaS — trial (#527) e contato B2B (#516 / DR-06)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.kb_public_rate_limit import check_saas_contato_rate_limit, check_saas_trial_rate_limit
from app.database import get_db
from app.services import saas_clientes as svc
from app.services.saas_contato import LeadComercialCreate, LeadComercialPublicRead, criar_lead_publico
from app.services.saas_trial import TrialSolicitacaoCreate, TrialSolicitacaoRead, criar_trial_publico

router = APIRouter(prefix="/saas/public", tags=["saas-public"])


def exigir_saas_control_plane() -> None:
    if not settings.SAAS_CONTROL_PLANE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Painel SaaS não disponível nesta instância",
        )


@router.post("/trial", response_model=TrialSolicitacaoRead, status_code=201)
def solicitar_trial(
    data: TrialSolicitacaoCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
):
    check_saas_trial_rate_limit(request)
    try:
        row = criar_trial_publico(db, data)
    except svc.SaasErro as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    db.commit()
    db.refresh(row)
    return TrialSolicitacaoRead(
        id=row.id,
        nome=row.nome,
        slug=row.slug,
        status=row.status,
        data_renovacao=row.data_renovacao,
        mensagem=(
            "Pedido de trial recebido. A instância entra na fila de provisionamento; "
            "a equipa DeskRudder analisa e contactá-lo "
            f"em {row.contato_email}."
        ),
    )


@router.post("/contato", response_model=LeadComercialPublicRead, status_code=201)
def enviar_contato_comercial(
    data: LeadComercialCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
):
    """Captura lead B2B na landing — NÃO usa /kb/public/chat."""
    check_saas_contato_rate_limit(request)
    row = criar_lead_publico(db, data)
    db.commit()
    db.refresh(row)
    return LeadComercialPublicRead(
        id=row.id,
        mensagem=(
            "Mensagem recebida. A equipa comercial DeskRudder vai responder "
            f"em {row.email}."
        ),
    )
