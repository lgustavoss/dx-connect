"""Tenant actual e endereços de encaminhamento inbound."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.auth import exigir_admin, obter_atendente_atual
from app.core.tenant_context import TenantIdDep
from app.database import get_db
from app.models import Empresa, Setor, Tenant
from app.models.tenant_inbound_address import TenantInboundAddress
from app.models.atendente import Atendente
from app.schemas.tenant import (
    TenantInboundAddressCreate,
    TenantInboundAddressRead,
    TenantInboundAddressUpdate,
    TenantRead,
)
from app.services.tenant_inbound import format_inbound_address, normalize_local_part

router = APIRouter(prefix="/tenant", tags=["tenant"])


def _app_host_for_tenant(tenant_id: int) -> str | None:
    base = (settings.CONNECT_APP_BASE_DOMAIN or "").strip()
    if not base:
        return None
    return f"{tenant_id}.{base}"


def _inbound_to_read(row: TenantInboundAddress) -> TenantInboundAddressRead:
    return TenantInboundAddressRead(
        id=row.id,
        tenant_id=row.tenant_id,
        local_part=row.local_part,
        full_address=format_inbound_address(row.local_part),
        label=row.label,
        setor_id=row.setor_id,
        setor_nome=row.setor.nome if row.setor else None,
        default_empresa_id=row.default_empresa_id,
        ativo=row.ativo,
    )


@router.get("/atual", response_model=TenantRead)
def get_tenant_atual(
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    row = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.ativo.is_(True)).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado ou inativo.")
    return TenantRead(
        id=row.id,
        nome=row.nome,
        ativo=row.ativo,
        app_host=_app_host_for_tenant(row.id),
    )


@router.get("/inbound-addresses", response_model=list[TenantInboundAddressRead])
def list_inbound_addresses(
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    rows = (
        db.query(TenantInboundAddress)
        .options(joinedload(TenantInboundAddress.setor))
        .filter(TenantInboundAddress.tenant_id == tenant_id)
        .order_by(TenantInboundAddress.local_part.asc())
        .all()
    )
    return [_inbound_to_read(r) for r in rows]


@router.post("/inbound-addresses", response_model=TenantInboundAddressRead, status_code=status.HTTP_201_CREATED)
def create_inbound_address(
    data: TenantInboundAddressCreate,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    lp = normalize_local_part(data.local_part)
    prefix = f"{tenant_id}_"
    if not lp.startswith(prefix) and lp != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O identificador deve começar por «{prefix}» (ex.: {tenant_id}_comercial).",
        )
    setor = (
        db.query(Setor)
        .filter(Setor.id == data.setor_id, Setor.tenant_id == tenant_id, Setor.ativo.is_(True))
        .first()
    )
    if not setor:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setor inválido para este tenant.")
    if data.default_empresa_id is not None:
        emp = (
            db.query(Empresa)
            .filter(Empresa.id == data.default_empresa_id, Empresa.tenant_id == tenant_id)
            .first()
        )
        if not emp:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa inválida para este tenant.")
    if db.query(TenantInboundAddress).filter(TenantInboundAddress.local_part == lp).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este endereço de encaminhamento já existe.")
    row = TenantInboundAddress(
        tenant_id=tenant_id,
        local_part=lp,
        label=(data.label or "").strip() or None,
        setor_id=data.setor_id,
        default_empresa_id=data.default_empresa_id,
        ativo=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _inbound_to_read(row)


@router.put("/inbound-addresses/{address_id}", response_model=TenantInboundAddressRead)
def update_inbound_address(
    address_id: int,
    data: TenantInboundAddressUpdate,
    tenant_id: TenantIdDep,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    row = (
        db.query(TenantInboundAddress)
        .filter(TenantInboundAddress.id == address_id, TenantInboundAddress.tenant_id == tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endereço não encontrado.")
    payload = data.model_dump(exclude_unset=True)
    if "setor_id" in payload and payload["setor_id"] is not None:
        setor = (
            db.query(Setor)
            .filter(Setor.id == payload["setor_id"], Setor.tenant_id == tenant_id, Setor.ativo.is_(True))
            .first()
        )
        if not setor:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setor inválido.")
        row.setor_id = payload["setor_id"]
    if "default_empresa_id" in payload:
        eid = payload["default_empresa_id"]
        if eid is not None:
            emp = db.query(Empresa).filter(Empresa.id == eid, Empresa.tenant_id == tenant_id).first()
            if not emp:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa inválida.")
        row.default_empresa_id = eid
    if "label" in payload:
        v = payload["label"]
        row.label = (v.strip() if isinstance(v, str) else v) or None
    if "ativo" in payload and payload["ativo"] is not None:
        row.ativo = bool(payload["ativo"])
    db.commit()
    db.refresh(row)
    return _inbound_to_read(row)
