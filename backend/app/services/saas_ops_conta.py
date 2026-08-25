"""Conta do ops no control-plane — perfil e token Cursor."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.security import criar_access_token, criar_refresh_token
from app.models.atendente import Atendente
from app.schemas.saas_ops_conta import SaasOpsContaPerfilUpdate


def _normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def _validar_email(email: str) -> str:
    valor = _normalizar_email(email)
    if "@" not in valor or valor.startswith("@") or valor.endswith("@"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe um e-mail válido.")
    return valor


def atualizar_perfil(
    db: Session,
    actor: Atendente,
    data: SaasOpsContaPerfilUpdate,
) -> tuple[Atendente, dict | None]:
    """Atualiza nome/e-mail da própria conta. Se o e-mail mudar, devolve claims para novos tokens."""
    update = data.model_dump(exclude_unset=True)
    if not update:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nada para atualizar.")

    email_mudou = False
    if "nome" in update and update["nome"] is not None:
        nome = update["nome"].strip()
        if not nome:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome.")
        actor.nome = nome

    if "email" in update and update["email"] is not None:
        email = _validar_email(update["email"])
        if email != _normalizar_email(actor.email):
            existe = (
                db.query(Atendente)
                .filter(
                    Atendente.tenant_id == actor.tenant_id,
                    func.lower(Atendente.email) == email,
                    Atendente.id != actor.id,
                )
                .first()
            )
            if existe:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já cadastrado")
            actor.email = email
            actor.token_version = int(actor.token_version or 0) + 1
            email_mudou = True

    registrar_audit(db, "atendente", actor.id, "update_saas_ops_perfil", actor.id)
    db.flush()

    tokens = None
    if email_mudou:
        ver = int(getattr(actor, "token_version", 0) or 0)
        claims = {"sub": actor.email, "tid": int(actor.tenant_id), "ver": ver}
        tokens = {
            "access_token": criar_access_token(data=claims),
            "refresh_token": criar_refresh_token(data=claims),
        }
    return actor, tokens
