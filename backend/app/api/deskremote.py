from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth import exigir_permissao
from app.core.kb_public_rate_limit import check_deskremote_enroll_rate_limit, check_deskremote_sync_rate_limit
from app.database import get_db
from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.schemas.deskremote import (
    DeskremoteConfirmarIdIn,
    DeskremoteConfirmarIdOut,
    DeskremoteEnrollIn,
    DeskremoteEnrollOut,
    DeskremoteSyncOut,
    DeskremoteTokenCreate,
    DeskremoteTokenCriado,
    DeskremoteTokenStatus,
)
from app.services import deskremote_enroll as svc

router = APIRouter(tags=["deskremote"])
_bearer = HTTPBearer(auto_error=False)


def _empresa_or_404(db: Session, empresa_id: int) -> Empresa:
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return emp


def _token_dispositivo(creds: HTTPAuthorizationCredentials | None) -> str:
    if not creds or not (creds.credentials or "").strip():
        raise HTTPException(status_code=401, detail=svc.MSG_DISPOSITIVO)
    return creds.credentials.strip()


@router.post(
    "/empresas/{empresa_id}/pdvs/{pdv_id}/deskremote/token",
    response_model=DeskremoteTokenCriado,
)
def gerar_token_instalacao(
    empresa_id: int,
    pdv_id: int,
    body: DeskremoteTokenCreate | None = None,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("empresas.editar")),
):
    _empresa_or_404(db, empresa_id)
    return svc.gerar_token(
        db,
        empresa_id=empresa_id,
        pdv_id=pdv_id,
        acesso_id=(body.acesso_id if body else None),
        atendente=atendente,
    )


@router.get(
    "/empresas/{empresa_id}/pdvs/{pdv_id}/deskremote/token/{token_id}",
    response_model=DeskremoteTokenStatus,
)
def status_token_instalacao(
    empresa_id: int,
    pdv_id: int,
    token_id: int,
    db: Session = Depends(get_db),
    _atendente: Atendente = Depends(exigir_permissao("empresas.editar")),
):
    _empresa_or_404(db, empresa_id)
    return svc.status_token(db, empresa_id=empresa_id, pdv_id=pdv_id, token_id=token_id)


@router.post("/deskremote/enroll", response_model=DeskremoteEnrollOut)
def resgatar_instalacao(
    body: DeskremoteEnrollIn,
    request: Request,
    db: Session = Depends(get_db),
):
    check_deskremote_enroll_rate_limit(request)
    return svc.resgatar(db, body.token, body.rustdesk_id)


@router.post("/deskremote/dispositivo/id", response_model=DeskremoteConfirmarIdOut)
def confirmar_id(
    body: DeskremoteConfirmarIdIn,
    request: Request,
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    check_deskremote_sync_rate_limit(request)
    return svc.confirmar_id(db, _token_dispositivo(creds), body.rustdesk_id)


@router.get("/deskremote/dispositivo/config", response_model=DeskremoteSyncOut)
def sync_config(
    request: Request,
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    check_deskremote_sync_rate_limit(request)
    return svc.sync_config(db, _token_dispositivo(creds))
