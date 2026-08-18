from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import obter_atendente_atual
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.web_push import PushSubscriptionCreate, PushSubscriptionRead, PushVapidPublic
from app.services import web_push as svc

router = APIRouter(prefix="/web-push", tags=["web-push"])


@router.get("/vapid", response_model=PushVapidPublic)
def obter_vapid_publico(atendente: Atendente = Depends(obter_atendente_atual)):
    del atendente
    key = svc.vapid_public_key()
    return PushVapidPublic(configurado=bool(key), public_key=key)


@router.get("/subscriptions", response_model=list[PushSubscriptionRead])
def listar_subscriptions(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return svc.listar_minhas(db, atendente.id)


@router.post("/subscriptions", response_model=PushSubscriptionRead, status_code=status.HTTP_201_CREATED)
def registrar_subscription(
    body: PushSubscriptionCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    return svc.registrar(
        db,
        atendente.id,
        endpoint=body.endpoint,
        p256dh=body.p256dh,
        auth=body.auth,
        user_agent=body.user_agent,
    )


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    svc.remover(db, atendente.id, subscription_id)
    return None


@router.delete("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
def apagar_por_endpoint(
    endpoint: str = Query(..., min_length=8),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    """Revoga o dispositivo actual no logout."""
    svc.remover_por_endpoint(db, atendente.id, endpoint)
    return None
