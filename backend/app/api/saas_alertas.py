"""API — alertas operacionais por instância (SaaS Ops) (#1036 / #1038)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.saas import exigir_saas_control_plane
from app.core.auth import exigir_saas_ops
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.saas_alerta_ops import (
    SaasAlertaOpsLista,
    SaasAlertaOpsMitigar,
    SaasAlertaOpsRead,
    SaasAlertaOpsResumo,
)
from app.services import saas_alertas_ops as svc

router = APIRouter(prefix="/saas/alertas", tags=["saas-alertas"])


def _to_read(row) -> SaasAlertaOpsRead:
    cliente = getattr(row, "cliente", None)
    eventos = list(getattr(row, "eventos", None) or [])
    return SaasAlertaOpsRead(
        id=row.id,
        cliente_saas_id=row.cliente_saas_id,
        cliente_nome=cliente.nome if cliente else None,
        cliente_slug=cliente.slug if cliente else None,
        codigo_sinal=row.codigo_sinal,
        modulo=row.modulo,
        severidade=row.severidade,
        estado=row.estado,
        ciclo_id=row.ciclo_id,
        titulo=row.titulo,
        started_at=row.started_at,
        mitigated_at=row.mitigated_at,
        resolved_at=row.resolved_at,
        last_seen_at=row.last_seen_at,
        evidencia=row.evidencia,
        eventos=eventos,
    )


@router.get("/resumo", response_model=SaasAlertaOpsResumo)
def obter_resumo(
    cliente_saas_id: int | None = Query(
        None,
        description="Se informado, resume só o cliente (recomendado na UI Ops).",
    ),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    return svc.resumo_global(db, cliente_saas_id=cliente_saas_id)


@router.get("", response_model=SaasAlertaOpsLista)
def listar(
    cliente_saas_id: int = Query(
        ...,
        description="Obrigatório — evita listar alertas de todos os clientes de uma vez.",
    ),
    estado: str | None = Query(None),
    severidade: str | None = Query(None),
    modulo: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    items, total = svc.listar_alertas(
        db,
        estado=estado,
        severidade=severidade,
        modulo=modulo,
        cliente_saas_id=cliente_saas_id,
        offset=offset,
        limit=limit,
    )
    return SaasAlertaOpsLista(items=[_to_read(i) for i in items], total=total)


@router.get("/cliente/{cliente_id}", response_model=SaasAlertaOpsLista)
def listar_cliente(
    cliente_id: int,
    limit: int = Query(50, ge=1, le=200),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    items = svc.listar_por_cliente(db, cliente_id, limit=limit)
    return SaasAlertaOpsLista(items=[_to_read(i) for i in items], total=len(items))


@router.get("/{alerta_id}", response_model=SaasAlertaOpsRead)
def obter(
    alerta_id: int,
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    return _to_read(svc.obter_alerta(db, alerta_id))


@router.post("/{alerta_id}/mitigar", response_model=SaasAlertaOpsRead)
def mitigar(
    alerta_id: int,
    body: SaasAlertaOpsMitigar,
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
    db: Session = Depends(get_db),
):
    row = svc.mitigar_alerta(db, alerta_id, body.mensagem, atendente_id=ops.id)
    db.commit()
    return _to_read(svc.obter_alerta(db, row.id))
