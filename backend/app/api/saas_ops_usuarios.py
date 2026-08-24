"""Equipa do control-plane — contas saas_ops (#883)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.saas import exigir_saas_control_plane
from app.core.auth import exigir_saas_ops
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.saas_ops_usuario import (
    SaasOpsUsuarioCreate,
    SaasOpsUsuarioCriado,
    SaasOpsUsuarioRead,
    SaasOpsUsuarioSenha,
    SaasOpsUsuarioUpdate,
)
from app.services import saas_ops_usuarios as svc

router = APIRouter(prefix="/saas/usuarios", tags=["saas-ops-usuarios"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


@router.get("", response_model=ListaPaginada[SaasOpsUsuarioRead])
def listar_usuarios(
    incluir_inativos: bool = Query(False),
    busca: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    rows, total = svc.listar(
        db, ops, incluir_inativos=incluir_inativos, busca=busca, offset=offset, limit=limit
    )
    return ListaPaginada(items=[SaasOpsUsuarioRead.model_validate(svc.para_dict(r)) for r in rows], total=total)


@router.post("", response_model=SaasOpsUsuarioCriado, status_code=201)
def criar_usuario(
    data: SaasOpsUsuarioCreate,
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    row, senha = svc.criar(db, ops, data)
    db.commit()
    db.refresh(row)
    return SaasOpsUsuarioCriado(senha_temporaria=senha, **svc.para_dict(row))


@router.get("/{usuario_id}", response_model=SaasOpsUsuarioRead)
def obter_usuario(
    usuario_id: int,
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    row = svc.obter(db, ops, usuario_id)
    return SaasOpsUsuarioRead.model_validate(svc.para_dict(row))


@router.patch("/{usuario_id}", response_model=SaasOpsUsuarioRead)
def actualizar_usuario(
    usuario_id: int,
    data: SaasOpsUsuarioUpdate,
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    row = svc.actualizar(db, ops, usuario_id, data)
    db.commit()
    db.refresh(row)
    return SaasOpsUsuarioRead.model_validate(svc.para_dict(row))


@router.post("/{usuario_id}/senha-temporaria", response_model=SaasOpsUsuarioSenha)
def redefinir_senha(
    usuario_id: int,
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    row, senha = svc.redefinir_senha(db, ops, usuario_id)
    db.commit()
    db.refresh(row)
    return SaasOpsUsuarioSenha(senha_temporaria=senha)
