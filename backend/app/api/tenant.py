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
from app.services.tenant_inbound import format_inbound_address
from app.services.tenant_inbound_sync import sync_inbound_addresses_for_tenant

router = APIRouter(prefix="/tenant", tags=["tenant"])


def _app_host_for_tenant(tenant_id: int) -> str | None:
    client = (settings.CLIENT_APP_HOST or "").strip()
    if client:
        return client
    if settings.single_tenant_mode:
        return None
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
        setor_slug=row.setor.slug if row.setor else None,
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
    sync_inbound_addresses_for_tenant(db, tenant_id)
    rows = (
        db.query(TenantInboundAddress)
        .options(joinedload(TenantInboundAddress.setor))
        .filter(
            TenantInboundAddress.tenant_id == tenant_id,
            TenantInboundAddress.ativo.is_(True),
        )
        .join(Setor, TenantInboundAddress.setor_id == Setor.id)
        .order_by(Setor.nome.asc())
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
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Endereços são criados automaticamente para cada setor ativo. Consulte GET /tenant/inbound-addresses.",
    )


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
