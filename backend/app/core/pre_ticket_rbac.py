"""RBAC e registo de acesso negado no pré-ticket (#814)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import obter_atendente_atual
from app.database import get_db
from app.models.atendente import Atendente


def pode_acessar_pre_ticket(atendente: Atendente) -> bool:
    """v1: só admin (dev analista na instância)."""
    return atendente.role == "admin"


def pode_analisar_pre_ticket(atendente: Atendente) -> bool:
    return atendente.role == "admin"


def pode_aprovar_pre_ticket(atendente: Atendente) -> bool:
    return atendente.role == "admin"


def pode_publicar_pre_ticket(atendente: Atendente) -> bool:
    return atendente.role == "admin"


def registrar_acesso_negado(
    db: Session,
    atendente: Atendente,
    acao: str,
    *,
    sessao_id: int | None = None,
) -> None:
    registrar_audit(
        db,
        "pre_ticket_sessao",
        sessao_id or 0,
        "acesso_negado",
        atendente.id,
        payload={"acao": acao, "role": atendente.role},
    )
    db.commit()


def _exigir(
    db: Session,
    atendente: Atendente,
    acao: str,
    permitido: bool,
    *,
    sessao_id: int | None = None,
) -> Atendente:
    if permitido:
        return atendente
    registrar_acesso_negado(db, atendente, acao, sessao_id=sessao_id)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso restrito a administradores (pré-ticket IA).",
    )


def exigir_pre_ticket_acesso(
    atendente: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
) -> Atendente:
    return _exigir(db, atendente, "acessar", pode_acessar_pre_ticket(atendente))


def exigir_pre_ticket_analisar(
    sessao_id: int,
    atendente: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
) -> Atendente:
    return _exigir(db, atendente, "analisar", pode_analisar_pre_ticket(atendente), sessao_id=sessao_id)


def exigir_pre_ticket_aprovar(
    sessao_id: int,
    atendente: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
) -> Atendente:
    return _exigir(db, atendente, "aprovar", pode_aprovar_pre_ticket(atendente), sessao_id=sessao_id)


def exigir_pre_ticket_publicar(
    sessao_id: int,
    atendente: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
) -> Atendente:
    return _exigir(db, atendente, "publicar", pode_publicar_pre_ticket(atendente), sessao_id=sessao_id)
