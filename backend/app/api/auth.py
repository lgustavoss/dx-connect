from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.atendente import AtendenteLogin, RefreshTokenRequest, Token
from app.core.security import criar_access_token, criar_refresh_token, decodificar_refresh_token, verificar_senha
from app.core.login_protection import check_login_rate_limit, delay_on_auth_failure
from app.core.tenant_context import (
    assert_token_tenant_matches_request,
    effective_tenant_id,
    get_request_tenant_id,
    is_multi_tenant_mode,
    resolve_tenant_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _buscar_atendente_por_email(db: Session, email: str, tenant_id: int) -> Atendente | None:
    q = db.query(Atendente).filter(
        func.lower(Atendente.email) == email,
        Atendente.ativo.is_(True),
    )
    if is_multi_tenant_mode():
        q = q.filter(Atendente.tenant_id == tenant_id)
    return q.first()


@router.post("/login", response_model=Token)
async def login(request: Request, data: AtendenteLogin, db: Session = Depends(get_db)):
    check_login_rate_limit(request)
    email_login = data.email.strip().lower()
    tenant_id = resolve_tenant_id(request)
    atendente = _buscar_atendente_por_email(db, email_login, tenant_id)
    if not atendente:
        await delay_on_auth_failure()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos")
    if not verificar_senha(data.senha, atendente.senha_hash):
        await delay_on_auth_failure()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos")
    tid_token = int(atendente.tenant_id)
    access = criar_access_token(data={"sub": atendente.email, "tid": tid_token})
    refresh = criar_refresh_token(data={"sub": atendente.email, "tid": tid_token})
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
    assert_token_tenant_matches_request(request, token_tid)
    if is_multi_tenant_mode():
        host_tid = get_request_tenant_id(request)
        tenant_id = int(host_tid if host_tid is not None else token_tid or 0)
    else:
        tenant_id = effective_tenant_id()
    atendente = _buscar_atendente_por_email(db, email, tenant_id)
    if not atendente:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado ou inativo")
    tid_token = int(atendente.tenant_id)
    access = criar_access_token(data={"sub": atendente.email, "tid": tid_token})
    return Token(
        access_token=access,
        refresh_token=data.refresh_token,
        must_change_password=bool(getattr(atendente, "must_change_password", False)),
    )
