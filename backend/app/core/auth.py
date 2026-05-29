from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.atendente import Atendente
from app.core.security import decodificar_token
from app.core.tenant_context import (
    assert_token_tenant_matches_request,
    effective_tenant_id,
    get_request_tenant_id,
    is_multi_tenant_mode,
)

security = HTTPBearer(auto_error=False)

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
    payload = decodificar_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
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


def exigir_admin(atendente: Atendente = Depends(obter_atendente_atual)) -> Atendente:
    if atendente.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return atendente
