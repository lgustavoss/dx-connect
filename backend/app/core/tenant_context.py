"""
Resolução do tenant: single-tenant por instância (produção) ou multi-tenant lógico (dev legado).
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import settings

_TENANT_HEADER = "x-dx-tenant-id"
_STATE_KEY = "tenant_id"


def is_multi_tenant_mode() -> bool:
    return bool(settings.DX_CONNECT_MULTI_TENANT)


def effective_tenant_id() -> int:
    return int(settings.DEFAULT_TENANT_ID)


def parse_tenant_id_from_host(host: str | None) -> int | None:
    """Extrai tenant numérico de ``{id}.{CONNECT_APP_BASE_DOMAIN}`` (só modo multi-tenant)."""
    if not host:
        return None
    h = host.split(":")[0].strip().lower()
    base = (settings.CONNECT_APP_BASE_DOMAIN or "").strip().lower()
    if not base:
        return None
    if h == base:
        return None
    suffix = f".{base}"
    if not h.endswith(suffix):
        return None
    prefix = h[: -len(suffix)]
    if not prefix or "." in prefix:
        return None
    if not re.fullmatch(r"\d+", prefix):
        return None
    return int(prefix)


def resolve_tenant_id(request: Request) -> int:
    """
    Single-tenant: sempre ``DEFAULT_TENANT_ID`` (uma BD por deploy).
    Multi-tenant: subdomínio → cabeçalho X-Dx-Tenant-Id → default.
    """
    if settings.single_tenant_mode:
        return effective_tenant_id()

    tid = parse_tenant_id_from_host(request.headers.get("host"))
    if tid is not None:
        return tid
    hdr = (request.headers.get(_TENANT_HEADER) or "").strip()
    if hdr.isdigit():
        return int(hdr)
    if settings.DEFAULT_TENANT_ID is not None:
        return int(settings.DEFAULT_TENANT_ID)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tenant não identificado (use subdomínio {id}.domínio ou cabeçalho X-Dx-Tenant-Id).",
    )


def set_request_tenant_id(request: Request, tenant_id: int) -> None:
    request.state.__setattr__(_STATE_KEY, tenant_id)


def get_request_tenant_id(request: Request) -> int | None:
    return getattr(request.state, _STATE_KEY, None)


def obter_tenant_id_request(request: Request) -> int:
    tid = get_request_tenant_id(request)
    if tid is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Contexto de tenant ausente.",
        )
    return tid


def assert_token_tenant_matches_request(request: Request, token_tid: object) -> None:
    """Em multi-tenant, valida JWT ``tid`` vs host/header. Em single-tenant, ignora divergência de subdomínio."""
    if settings.single_tenant_mode:
        return
    host_tid = get_request_tenant_id(request)
    if token_tid is not None and host_tid is not None and int(token_tid) != int(host_tid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sessão não corresponde a este tenant.",
        )


TenantIdDep = Annotated[int, Depends(obter_tenant_id_request)]
