"""API admin — pools Boleto Cloud e vínculos cliente→pool (#1392)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.saas import exigir_saas_control_plane
from app.core.auth import exigir_saas_ops
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.saas_boleto_cloud import (
    BoletoCloudRead,
    BoletoCloudTestarResultado,
    BoletoCloudUpsert,
    BoletoPoolLista,
    BoletoPoolRead,
    BoletoPoolUpsert,
    BoletoVinculoCreate,
    BoletoVinculoLista,
    BoletoVinculoRead,
)
from app.services import saas_boleto_cloud as svc

router = APIRouter(prefix="/saas/boleto-cloud", tags=["saas-boleto-cloud"])


@router.get("/pools", response_model=BoletoPoolLista)
def listar_pools(
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.listar_pools(db)


@router.post("/pools", response_model=BoletoPoolRead, status_code=201)
def criar_pool(
    body: BoletoPoolUpsert,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.criar_pool(db, body)


@router.get("/pools/{pool_id}", response_model=BoletoPoolRead)
def obter_pool(
    pool_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.pool_para_read(db, svc.obter_pool(db, pool_id))


@router.put("/pools/{pool_id}", response_model=BoletoPoolRead)
def atualizar_pool(
    pool_id: int,
    body: BoletoPoolUpsert,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.atualizar_pool(db, pool_id, body)


@router.post("/pools/{pool_id}/testar", response_model=BoletoCloudTestarResultado)
def testar_pool(
    pool_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.testar_pool(db, pool_id)


@router.get("/clientes/{cliente_saas_id}/vinculos", response_model=BoletoVinculoLista)
def listar_vinculos(
    cliente_saas_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.listar_vinculos_cliente(db, cliente_saas_id)


@router.post(
    "/clientes/{cliente_saas_id}/vinculos",
    response_model=BoletoVinculoRead,
    status_code=201,
)
def criar_vinculo(
    cliente_saas_id: int,
    body: BoletoVinculoCreate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.vincular_cliente(db, cliente_saas_id, body)


# --- Compatibilidade piloto ---

@router.get("", response_model=BoletoCloudRead)
def obter(
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.obter_mascarado(db)


@router.put("", response_model=BoletoCloudRead)
def salvar(
    body: BoletoCloudUpsert,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.upsert(db, body)


@router.post("/testar", response_model=BoletoCloudTestarResultado)
def testar(
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return svc.testar_conexao(db)
