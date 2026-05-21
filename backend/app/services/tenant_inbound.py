"""Resolução de endereços de encaminhamento inbound por tenant."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.config import settings
from app.models.setor import Setor
from app.models.tenant_inbound_address import TenantInboundAddress

_LOCAL_PART_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,126}$", re.IGNORECASE)
_LEGACY_LP_RE = re.compile(r"^(\d+)_([a-z0-9_-]+)$", re.IGNORECASE)


def inbound_email_domain() -> str:
    return (settings.INBOUND_EMAIL_DOMAIN or "").strip().lower()


def format_inbound_address(local_part: str) -> str:
    domain = inbound_email_domain()
    if not domain:
        raise ValueError("INBOUND_EMAIL_DOMAIN não configurado.")
    lp = normalize_local_part(local_part)
    return f"{lp}@{domain}"


def normalize_local_part(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s or not _LOCAL_PART_RE.fullmatch(s):
        raise ValueError(
            "Identificador inválido. Use letras, números, ponto, hífen ou sublinhado (ex.: suporte.t1, financeiro.t2)."
        )
    return s


def extract_local_part_from_email(addr: str) -> str | None:
    a = (addr or "").strip().lower()
    if "@" not in a:
        return None
    local, domain = a.rsplit("@", 1)
    if domain != inbound_email_domain():
        return None
    lp = local.strip()
    if not lp or not _LOCAL_PART_RE.fullmatch(lp):
        return None
    return lp


def lookup_inbound_address(db: Session, *, local_part: str) -> TenantInboundAddress | None:
    lp = normalize_local_part(local_part)
    row = (
        db.query(TenantInboundAddress)
        .filter(
            TenantInboundAddress.local_part == lp,
            TenantInboundAddress.ativo.is_(True),
        )
        .first()
    )
    if row:
        return row
    legacy = _LEGACY_LP_RE.fullmatch(lp)
    if not legacy:
        return None
    tenant_id = int(legacy.group(1))
    slug = legacy.group(2).lower()
    return (
        db.query(TenantInboundAddress)
        .join(Setor, TenantInboundAddress.setor_id == Setor.id)
        .filter(
            TenantInboundAddress.tenant_id == tenant_id,
            Setor.slug == slug,
            TenantInboundAddress.ativo.is_(True),
        )
        .first()
    )


def resolve_routing_from_recipients(
    db: Session, recipients: list[str]
) -> tuple[TenantInboundAddress | None, str | None]:
    """
    Devolve (config, local_part) para o primeiro destinatário que corresponda ao domínio inbound.
    """
    domain = inbound_email_domain()
    if not domain:
        return None, None
    for raw in recipients:
        for part in re.split(r"[,;\s]+", raw):
            part = part.strip()
            if not part:
                continue
            lp = extract_local_part_from_email(part)
            if not lp:
                continue
            row = lookup_inbound_address(db, local_part=lp)
            if row:
                return row, lp
    return None, None
