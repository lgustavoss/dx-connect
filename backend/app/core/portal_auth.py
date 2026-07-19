"""Autenticação JWT do portal do cliente (funcionário da rede)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.funcionario_rede import FuncionarioRede
from app.core.security import decodificar_token
from app.core.tenant_context import (
    assert_token_tenant_matches_request,
    effective_tenant_id,
    get_request_tenant_id,
    is_multi_tenant_mode,
)

PORTAL_AUD = "portal"

security = HTTPBearer(auto_error=False)


def claims_portal(funcionario: FuncionarioRede, *, tenant_id: int) -> dict:
    email = (funcionario.email or "").strip().lower()
    ver = int(getattr(funcionario, "token_version", 0) or 0)
    return {
        "sub": email,
        "aud": PORTAL_AUD,
        "fid": int(funcionario.id),
        "tid": int(tenant_id),
        "ver": ver,
    }


def token_eh_portal(payload: dict | None) -> bool:
    if not payload:
        return False
    return payload.get("aud") == PORTAL_AUD


def _carregar_funcionario_por_token(
    request: Request,
    token: str,
    db: Session,
) -> FuncionarioRede:
    payload = decodificar_token(token)
    if not payload or "sub" not in payload or not token_eh_portal(payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )
    email = str(payload["sub"]).strip().lower()
    token_tid = payload.get("tid")
    assert_token_tenant_matches_request(request, token_tid)
    if is_multi_tenant_mode():
        host_tid = get_request_tenant_id(request)
        tenant_id = int(host_tid if host_tid is not None else token_tid or 0)
    else:
        tenant_id = effective_tenant_id()

    fid = payload.get("fid")
    q = db.query(FuncionarioRede).filter(
        func.lower(FuncionarioRede.email) == email,
        FuncionarioRede.ativo.is_(True),
    )
    if fid is not None:
        q = q.filter(FuncionarioRede.id == int(fid))
    funcionario = q.first()
    if not funcionario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
        )
    if not (funcionario.senha_hash or "").strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso ao portal não habilitado. Solicite a senha ao suporte.",
        )

    # Valida tenant via rede/empresa do funcionário
    from app.core.portal_scope import tenant_id_do_funcionario

    try:
        tid_func = tenant_id_do_funcionario(db, funcionario)
    except Exception:
        tid_func = tenant_id
    if is_multi_tenant_mode() and int(tid_func) != int(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
        )

    token_ver = int(payload.get("ver") or 0)
    atual_ver = int(getattr(funcionario, "token_version", 0) or 0)
    if token_ver != atual_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada. Faça login novamente.",
        )

    path = request.url.path.rstrip("/") or "/"
    method = request.method.upper()
    if getattr(funcionario, "must_change_password", False):
        pode = (path.endswith("/portal/me") and method == "GET") or (
            path.endswith("/portal/me/trocar-senha") and method == "POST"
        )
        if not pode:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Altere sua senha antes de usar o portal.",
            )
    return funcionario


def obter_funcionario_portal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> FuncionarioRede:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não informado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _carregar_funcionario_por_token(request, credentials.credentials, db)
