"""API CRM — origens do lead configuráveis (#1319)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_permissao, obter_atendente_atual
from app.database import get_db
from app.models.atendente import Atendente
from app.models.crm import CrmOrigemLead
from app.schemas.crm import CrmOrigemLeadCreate, CrmOrigemLeadRead, CrmOrigemLeadUpdate
from app.services import crm_origens as svc

router = APIRouter(prefix="/crm/origens-lead", tags=["crm"])


def _obter(db: Session, origem_id: int) -> CrmOrigemLead:
    row = db.query(CrmOrigemLead).filter(CrmOrigemLead.id == origem_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Origem do lead não encontrada.")
    return row


@router.get("", response_model=list[CrmOrigemLeadRead])
def listar_origens(
    incluir_inativos: bool = Query(False, description="Incluir origens inativas"),
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    """Lista para o formulário de lead (qualquer pessoa autenticada) e para Configurações."""
    return svc.listar_origens(db, incluir_inativos=incluir_inativos)


@router.post("", response_model=CrmOrigemLeadRead, status_code=201)
def criar_origem(
    data: CrmOrigemLeadCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("funil.editar")),
):
    row = svc.criar_origem(db, data)
    registrar_audit(db, "crm_origem_lead", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{origem_id}", response_model=CrmOrigemLeadRead)
def atualizar_origem(
    origem_id: int,
    data: CrmOrigemLeadUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("funil.editar")),
):
    row = svc.atualizar_origem(db, _obter(db, origem_id), data)
    registrar_audit(db, "crm_origem_lead", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{origem_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_origem(
    origem_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("funil.editar")),
):
    row = _obter(db, origem_id)
    svc.excluir_origem(db, row)
    registrar_audit(db, "crm_origem_lead", origem_id, "delete", atendente.id)
    db.commit()
    return None
