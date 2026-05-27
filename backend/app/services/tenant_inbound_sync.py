"""Sincronização automática de endereços inbound (um por setor ativo)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Setor
from app.models.tenant_inbound_address import TenantInboundAddress
from app.services.tenant_inbound import normalize_local_part


def local_part_for_setor(tenant_id: int, setor_slug: str) -> str:
    """Padrão helpdesk: departamento + conta (ex.: ``suporte.t1``)."""
    slug = (setor_slug or "").strip().lower()
    return normalize_local_part(f"{slug}.t{tenant_id}")


def sync_inbound_addresses_for_tenant(db: Session, tenant_id: int) -> list[TenantInboundAddress]:
    """
    Garante um endereço ativo por setor ativo do tenant.
    Convenção: ``{setor.slug}.t{tenant_id}`` (ex.: ``suporte.t1``).
    """
    active_setores = (
        db.query(Setor)
        .filter(Setor.tenant_id == tenant_id, Setor.ativo.is_(True))
        .order_by(Setor.nome.asc())
        .all()
    )
    active_ids = {s.id for s in active_setores}

    existing_rows = (
        db.query(TenantInboundAddress).filter(TenantInboundAddress.tenant_id == tenant_id).all()
    )
    existing_by_setor = {row.setor_id: row for row in existing_rows}

    synced: list[TenantInboundAddress] = []
    for setor in active_setores:
        desired_lp = local_part_for_setor(tenant_id, setor.slug)
        row = existing_by_setor.get(setor.id)
        if row:
            if row.local_part != desired_lp:
                conflict = (
                    db.query(TenantInboundAddress)
                    .filter(
                        TenantInboundAddress.local_part == desired_lp,
                        TenantInboundAddress.id != row.id,
                    )
                    .first()
                )
                if not conflict:
                    row.local_part = desired_lp
            row.label = setor.nome
            row.ativo = True
        else:
            if db.query(TenantInboundAddress).filter(TenantInboundAddress.local_part == desired_lp).first():
                continue
            row = TenantInboundAddress(
                tenant_id=tenant_id,
                local_part=desired_lp,
                label=setor.nome,
                setor_id=setor.id,
                ativo=True,
            )
            db.add(row)
            existing_by_setor[setor.id] = row
        synced.append(row)

    for row in existing_rows:
        if row.setor_id not in active_ids:
            row.ativo = False

    db.commit()
    for row in synced:
        db.refresh(row)
    return synced
