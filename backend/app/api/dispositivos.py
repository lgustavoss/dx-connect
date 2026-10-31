from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import obter_atendente_atual
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.dispositivo import DispositivoCreate, DispositivoRead
from app.services import dispositivos as svc

router = APIRouter(prefix="/dispositivos", tags=["dispositivos"])


@router.get("", response_model=list[DispositivoRead])
def listar(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return svc.listar_minhas(db, atendente.id)


@router.post("", response_model=DispositivoRead, status_code=status.HTTP_201_CREATED)
def registrar(
    body: DispositivoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return svc.registrar(db, atendente.id, token=body.token, plataforma=body.plataforma)


@router.delete("/{dispositivo_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar(
    dispositivo_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    svc.remover(db, atendente.id, dispositivo_id)
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def apagar_por_token(
    token: str = Query(..., min_length=8),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    svc.remover_por_token(db, atendente.id, token)
    return None
