from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.atendente import AtendenteLogin, RefreshTokenRequest, Token
from app.core.security import criar_access_token, criar_refresh_token, decodificar_refresh_token, verificar_senha
from app.core.login_protection import check_login_rate_limit, delay_on_auth_failure
from app.core.tenant_context import get_request_tenant_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(request: Request, data: AtendenteLogin, db: Session = Depends(get_db)):
    check_login_rate_limit(request)
    email_login = data.email.strip().lower()
    tenant_id = get_request_tenant_id(request)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant não identificado.",
        )
    atendente = (
        db.query(Atendente)
        .filter(
            Atendente.tenant_id == tenant_id,
            func.lower(Atendente.email) == email_login,
        )
        .first()
    )
    if not atendente or not atendente.ativo:
        await delay_on_auth_failure()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos")
    if not verificar_senha(data.senha, atendente.senha_hash):
        await delay_on_auth_failure()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos")
    access = criar_access_token(data={"sub": atendente.email, "tid": tenant_id})
    refresh = criar_refresh_token(data={"sub": atendente.email, "tid": tenant_id})
    return Token(
        access_token=access,
        refresh_token=refresh,
        must_change_password=bool(getattr(atendente, "must_change_password", False)),
    )


@router.post("/refresh", response_model=Token)
async def refresh(
    request: Request,
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    payload = decodificar_refresh_token(data.refresh_token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido ou expirado")
    email = str(payload["sub"]).strip().lower()
    token_tid = payload.get("tid")
    host_tid = get_request_tenant_id(request)
    if token_tid is not None and host_tid is not None and int(token_tid) != int(host_tid):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão não corresponde a este tenant.")
    tenant_id = int(host_tid if host_tid is not None else token_tid or 0)
    atendente = (
        db.query(Atendente)
        .filter(Atendente.tenant_id == tenant_id, func.lower(Atendente.email) == email)
        .first()
    )
    if not atendente or not atendente.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado ou inativo")
    access = criar_access_token(data={"sub": atendente.email, "tid": tenant_id})
    # Mantém o mesmo refresh token (stateless); cliente pode reutilizar até expirar.
    return Token(
        access_token=access,
        refresh_token=data.refresh_token,
        must_change_password=bool(getattr(atendente, "must_change_password", False)),
    )
