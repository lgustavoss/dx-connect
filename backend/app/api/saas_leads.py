"""API admin — inbox de leads comerciais B2B (DR-06 / #516)."""

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.audit import registrar_audit
from app.core.auth import exigir_saas_ops
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.database import get_db
from app.models.atendente import Atendente
from app.models.lead_comercial import LeadComercial
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.saas import ClienteSaaSRead
from app.services import saas_clientes as svc_clientes
from app.services.saas_contato import LeadComercialRead, LeadComercialUpdate, atualizar_lead, obter_lead
from app.services.saas_lead_convert import LeadConverterCreate, converter_lead

router = APIRouter(prefix="/saas/leads", tags=["saas-leads"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarLeadsPor(str, Enum):
    created_at = "created_at"
    nome = "nome"
    status = "status"


def exigir_saas_control_plane() -> None:
    if not settings.SAAS_CONTROL_PLANE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Painel SaaS não disponível nesta instância",
        )


@router.get("", response_model=ListaPaginada[LeadComercialRead])
def listar(
    busca: str | None = Query(None),
    status_filtro: str | None = Query(None, alias="status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarLeadsPor | None = Query(OrdenarLeadsPor.created_at),
    ordem: OrdemLista = Query(OrdemLista.desc),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    q = db.query(LeadComercial)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(
            (LeadComercial.nome.ilike(term))
            | (LeadComercial.email.ilike(term))
            | (LeadComercial.empresa.ilike(term))
        )
    if status_filtro and status_filtro.strip():
        q = q.filter(LeadComercial.status == status_filtro.strip().lower())
    total = q.count()
    if ordenar_por == OrdenarLeadsPor.nome:
        order_cols = [expr_ordem(LeadComercial.nome, ordem), expr_ordem(LeadComercial.id, ordem)]
    elif ordenar_por == OrdenarLeadsPor.status:
        order_cols = [expr_ordem(LeadComercial.status, ordem), expr_ordem(LeadComercial.id, ordem)]
    else:
        order_cols = [expr_ordem(LeadComercial.created_at, ordem), expr_ordem(LeadComercial.id, ordem)]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=items, total=total)


@router.get("/{lead_id}", response_model=LeadComercialRead)
def obter(
    lead_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    row = obter_lead(db, lead_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado")
    return row


@router.patch("/{lead_id}", response_model=LeadComercialRead)
def atualizar(
    lead_id: int,
    data: LeadComercialUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    row = obter_lead(db, lead_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado")
    try:
        row = atualizar_lead(db, row, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    registrar_audit(db, "lead_comercial", lead_id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{lead_id}/converter", response_model=ClienteSaaSRead, status_code=201)
def converter(
    lead_id: int,
    data: LeadConverterCreate | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    atendente: Atendente = Depends(exigir_saas_ops),
):
    body = data or LeadConverterCreate()
    try:
        row = converter_lead(db, lead_id, body)
    except svc_clientes.SaasErro as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    registrar_audit(db, "lead_comercial", lead_id, "converter", atendente.id)
    registrar_audit(db, "cliente_saas", row.id, "create_from_lead", atendente.id)
    db.commit()
    db.refresh(row)
    return ClienteSaaSRead.model_validate(svc_clientes.serializar_cliente(row))
