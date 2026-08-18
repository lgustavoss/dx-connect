"""CRUD de subscriptions Web Push e chave VAPID pública (#693)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.web_push import PushSubscription


def vapid_configurado() -> bool:
    pub = (settings.WEB_PUSH_VAPID_PUBLIC_KEY or "").strip()
    priv = (settings.WEB_PUSH_VAPID_PRIVATE_KEY or "").strip()
    return bool(pub and priv)


def vapid_public_key() -> str | None:
    if not vapid_configurado():
        return None
    return (settings.WEB_PUSH_VAPID_PUBLIC_KEY or "").strip()


def listar_minhas(db: Session, atendente_id: int) -> list[PushSubscription]:
    return (
        db.query(PushSubscription)
        .filter(PushSubscription.atendente_id == atendente_id)
        .order_by(PushSubscription.id.desc())
        .all()
    )


def registrar(db: Session, atendente_id: int, *, endpoint: str, p256dh: str, auth: str, user_agent: str | None) -> PushSubscription:
    endpoint = endpoint.strip()
    existente = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if existente:
        if existente.atendente_id != atendente_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta subscription pertence a outro utilizador.",
            )
        existente.p256dh = p256dh.strip()
        existente.auth = auth.strip()
        existente.user_agent = (user_agent or "").strip() or None
        db.add(existente)
        db.commit()
        db.refresh(existente)
        return existente
    row = PushSubscription(
        atendente_id=atendente_id,
        endpoint=endpoint,
        p256dh=p256dh.strip(),
        auth=auth.strip(),
        user_agent=(user_agent or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def remover(db: Session, atendente_id: int, subscription_id: int) -> None:
    row = db.query(PushSubscription).filter(PushSubscription.id == subscription_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription não encontrada")
    if row.atendente_id != atendente_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não pode remover a subscription de outro utilizador.")
    db.delete(row)
    db.commit()


def remover_por_endpoint(db: Session, atendente_id: int, endpoint: str) -> None:
    row = (
        db.query(PushSubscription)
        .filter(PushSubscription.atendente_id == atendente_id, PushSubscription.endpoint == endpoint.strip())
        .first()
    )
    if row is None:
        return
    db.delete(row)
    db.commit()


def revogar_todas(db: Session, atendente_id: int) -> int:
    n = db.query(PushSubscription).filter(PushSubscription.atendente_id == atendente_id).delete()
    db.flush()
    return int(n or 0)
