"""API — setores (cargos) da equipe SaaS."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.saas import exigir_saas_control_plane
from app.core.auth import exigir_saas_ops
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.saas_setor import SaasSetorCreate, SaasSetorRead, SaasSetorUpdate
from app.services import saas_setores as svc

router = APIRouter(prefix="/saas/setores", tags=["saas-setores"])


@router.get("", response_model=list[SaasSetorRead])
def listar_setores(
    incluir_inativos: bool = Query(False),
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    return svc.listar(db, ops, incluir_inativos=incluir_inativos)


@router.post("", response_model=SaasSetorRead, status_code=201)
def criar_setor(
    data: SaasSetorCreate,
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    row = svc.criar(db, ops, data)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{setor_id}", response_model=SaasSetorRead)
def obter_setor(
    setor_id: int,
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    return svc.obter(db, ops, setor_id)


@router.patch("/{setor_id}", response_model=SaasSetorRead)
def atualizar_setor(
    setor_id: int,
    data: SaasSetorUpdate,
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    row = svc.atualizar(db, ops, setor_id, data)
    db.commit()
    db.refresh(row)
    return row
