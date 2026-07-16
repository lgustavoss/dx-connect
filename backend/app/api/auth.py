from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.atendente import AtendenteLogin, RefreshTokenRequest, Token
from app.schemas.password_reset import MensagemAuth, RedefinirSenhaComToken, SolicitarRedefinicaoSenha
from app.services.password_reset import MSG_SOLICITACAO_OK, redefinir_senha_com_token, solicitar_redefinicao
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
    ver = int(getattr(atendente, "token_version", 0) or 0)
    claims = {"sub": atendente.email, "tid": tid_token, "ver": ver}
    access = criar_access_token(data=claims)
    refresh = criar_refresh_token(data=claims)
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
    token_ver = int(payload.get("ver") or 0)
    atual_ver = int(getattr(atendente, "token_version", 0) or 0)
    if token_ver != atual_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada. Faça login novamente.",
        )
    tid_token = int(atendente.tenant_id)
    claims = {"sub": atendente.email, "tid": tid_token, "ver": atual_ver}
    access = criar_access_token(data=claims)
    refresh = criar_refresh_token(data=claims)
    return Token(
        access_token=access,
        refresh_token=refresh,
        must_change_password=bool(getattr(atendente, "must_change_password", False)),
    )


@router.post("/solicitar-redefinicao-senha", response_model=MensagemAuth)
async def solicitar_redefinicao_senha(
    request: Request,
    data: SolicitarRedefinicaoSenha,
    db: Session = Depends(get_db),
):
    check_login_rate_limit(request)
    msg = solicitar_redefinicao(db, data.email)
    return MensagemAuth(detail=msg)


@router.post("/redefinir-senha", response_model=MensagemAuth)
async def redefinir_senha(
    request: Request,
    data: RedefinirSenhaComToken,
    db: Session = Depends(get_db),
):
    check_login_rate_limit(request)
    try:
        redefinir_senha_com_token(db, data.token, data.senha_nova)
    except ValueError as e:
        await delay_on_auth_failure()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return MensagemAuth(detail="Senha atualizada com sucesso. Faça login com a nova senha.")
