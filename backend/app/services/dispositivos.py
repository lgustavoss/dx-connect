"""CRUD de tokens FCM do app companion (#1315)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.atendente_notificacao import AtendenteNotificacaoPreferencias
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
        if existente.atendente_id == atendente_id:
            existente.plataforma = plat
            db.add(existente)
            db.commit()
            db.refresh(existente)
            return existente
        # O token passa a valer para o aparelho que acabou de logar: reaproveitar
        # cobre logout sem rede + login de outro atendente no mesmo celular.
        db.delete(existente)
        db.flush()
    row = Dispositivo(atendente_id=atendente_id, token=token, plataforma=plat)
    db.add(row)
    _ativar_push_no_novo_dispositivo(db, atendente_id)
    db.commit()
    db.refresh(row)
    return row


def _ativar_push_no_novo_dispositivo(db: Session, atendente_id: int) -> None:
    """
    Registrar o primeiro aparelho conta como opt-in do push (#1315): sem isso a
    preferência nasce desligada e o FCM nunca entrega. Desligar depois é pelo
    PATCH /notificacoes/preferencias (switch no Perfil do app).
    """
    prefs = (
        db.query(AtendenteNotificacaoPreferencias)
        .filter(AtendenteNotificacaoPreferencias.atendente_id == atendente_id)
        .first()
    )
    if prefs is None:
        db.add(AtendenteNotificacaoPreferencias(atendente_id=atendente_id, push_habilitado=True))
    elif not bool(prefs.push_habilitado):
        prefs.push_habilitado = True


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
