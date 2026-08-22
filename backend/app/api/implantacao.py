"""Implantação — templates de checklist (#325 / #358)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, exigir_comercial_ou_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.implantacao import (
    ImplantacaoTemplateCreate,
    ImplantacaoTemplateRead,
    ImplantacaoTemplateUpdate,
)
from app.services import implantacao as svc

router = APIRouter(prefix="/comercial", tags=["comercial-implantacao"])


@router.get("/implantacao-templates", response_model=list[ImplantacaoTemplateRead])
def listar_templates(
    incluir_inativos: bool = Query(False),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    if incluir_inativos and atendente.role != "admin":
        incluir_inativos = False
    rows = svc.listar_templates(db, incluir_inativos=incluir_inativos, tenant_id=atendente.tenant_id)
    db.commit()
    return [svc.template_para_read(r) for r in rows]


@router.post("/implantacao-templates", response_model=ImplantacaoTemplateRead, status_code=201)
def criar_template(
    data: ImplantacaoTemplateCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.criar_template(db, data, atendente.tenant_id)
    registrar_audit(db, "implantacao_checklist_template", row.id, "create", atendente.id)
    db.commit()
    return svc.template_para_read(row)


@router.patch("/implantacao-templates/{template_id}", response_model=ImplantacaoTemplateRead)
def atualizar_template(
    template_id: int,
    data: ImplantacaoTemplateUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.obter_template(db, template_id, apenas_ativos=False)
    row = svc.atualizar_template(db, row, data, atendente.tenant_id)
    registrar_audit(db, "implantacao_checklist_template", row.id, "update", atendente.id)
    db.commit()
    return svc.template_para_read(row)
