from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, subqueryload

from app.database import get_db
from app.models.atendente import Atendente
from app.core.setor_scope import atendente_e_financeiro
from app.core.security import decodificar_token
from app.core.tenant_context import (
    assert_token_tenant_matches_request,
    effective_tenant_id,
    get_request_tenant_id,
    is_multi_tenant_mode,
)

security = HTTPBearer(auto_error=False)


def _carregar_atendente_por_token(
    request: Request,
    token: str,
    db: Session,
) -> Atendente:
    payload = decodificar_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )
    # Token do portal do cliente não acessa rotas internas (#300)
    if payload.get("aud") == "portal":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido para o painel interno",
        )
    email = payload["sub"]
    token_tid = payload.get("tid")
    assert_token_tenant_matches_request(request, token_tid)
    if is_multi_tenant_mode():
        host_tid = get_request_tenant_id(request)
        tenant_id = int(host_tid if host_tid is not None else token_tid or 0)
    else:
        tenant_id = effective_tenant_id()
    atendente = (
        db.query(Atendente)
        .options(subqueryload(Atendente.setores))
        .filter(
            Atendente.tenant_id == tenant_id,
            Atendente.email == email,
            Atendente.ativo.is_(True),
        )
        .first()
    )
    if not atendente:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
        )
    token_ver = int(payload.get("ver") or 0)
    atual_ver = int(getattr(atendente, "token_version", 0) or 0)
    if token_ver != atual_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada. Faça login novamente.",
        )
    path = request.url.path.rstrip("/") or "/"
    method = request.method.upper()
    if getattr(atendente, "must_change_password", False):
        # Rotas são montadas com prefixo (ex.: /v1/atendentes/me).
        pode = (path.endswith("/atendentes/me") and method == "GET") or (
            path.endswith("/atendentes/me/trocar-senha") and method == "POST"
        )
        if not pode:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Altere sua senha antes de usar o sistema.",
            )
    return atendente


def obter_atendente_atual(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Atendente:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não informado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _carregar_atendente_por_token(request, credentials.credentials, db)


def obter_atendente_sse(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token: str | None = Query(None, description="JWT access token (alternativa ao header Bearer)"),
    db: Session = Depends(get_db),
) -> Atendente:
    raw = credentials.credentials if credentials else token
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não informado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _carregar_atendente_por_token(request, raw, db)


def exigir_admin(atendente: Atendente = Depends(obter_atendente_atual)) -> Atendente:
    if atendente.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return atendente


def exigir_comercial_ou_admin(atendente: Atendente = Depends(obter_atendente_atual)) -> Atendente:
    """CRM e simulação de custos (#336 / #322): admin ou perfil comercial."""
    if atendente.role not in ("admin", "comercial"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a perfil comercial ou administrador",
        )
    return atendente


def exigir_financeiro_ou_admin(
    atendente: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
) -> Atendente:
    """Faturamento interno (#326): admin ou atendente do setor Financeiro."""
    if atendente_e_financeiro(db, atendente):
        return atendente
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso restrito ao setor Financeiro ou administrador",
    )


def exigir_saas_ops(atendente: Atendente = Depends(obter_atendente_atual)) -> Atendente:
    """Equipa comercial DeskRudder (control-plane) — distinto do admin da instância do cliente."""
    if atendente.role != "saas_ops":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito à equipa SaaS DeskRudder",
        )
    return atendente


ROLES_ATENDENTE = frozenset({"admin", "atendente", "comercial"})


def validar_role(role: str) -> str:
    r = (role or "").strip().lower()
    if r not in ROLES_ATENDENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role inválido: use admin, atendente ou comercial",
        )
    return r
