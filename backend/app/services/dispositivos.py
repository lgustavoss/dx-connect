"""CRUD de tokens FCM do app companion (#1315)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.dispositivo import Dispositivo

PLATAFORMAS = frozenset({"android"})


def listar_minhas(db: Session, atendente_id: int) -> list[Dispositivo]:
    return (
        db.query(Dispositivo)
        .filter(Dispositivo.atendente_id == atendente_id)
        .order_by(Dispositivo.id.desc())
        .all()
    )


def registrar(db: Session, atendente_id: int, *, token: str, plataforma: str) -> Dispositivo:
    token = token.strip()
    plat = (plataforma or "android").strip().lower()
    if plat not in PLATAFORMAS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plataforma inválida.")
    existente = db.query(Dispositivo).filter(Dispositivo.token == token).first()
    if existente:
        if existente.atendente_id != atendente_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este token pertence a outro usuário.",
            )
        existente.plataforma = plat
        db.add(existente)
        db.commit()
        db.refresh(existente)
        return existente
    row = Dispositivo(atendente_id=atendente_id, token=token, plataforma=plat)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def remover_por_token(db: Session, atendente_id: int, token: str) -> None:
    row = (
        db.query(Dispositivo)
        .filter(Dispositivo.atendente_id == atendente_id, Dispositivo.token == token.strip())
        .first()
    )
    if row is None:
        return
    db.delete(row)
    db.commit()


def remover(db: Session, atendente_id: int, dispositivo_id: int) -> None:
    row = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo não encontrado")
    if row.atendente_id != atendente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não é possível remover o dispositivo de outro usuário.",
        )
    db.delete(row)
    db.commit()
