"""Cadastro da equipa saas_ops no control-plane (#883)."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.security import hash_senha
from app.models.atendente import Atendente
from app.schemas.saas_ops_usuario import SaasOpsUsuarioCreate, SaasOpsUsuarioUpdate


def _agora_senha() -> str:
    return secrets.token_urlsafe(12)


def _normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def _validar_email(email: str) -> str:
    valor = _normalizar_email(email)
    if "@" not in valor or valor.startswith("@") or valor.endswith("@"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe um e-mail válido.")
    return valor


def para_dict(row: Atendente) -> dict:
    return {
        "id": row.id,
        "nome": row.nome,
        "email": row.email,
        "ativo": bool(row.ativo),
        "must_change_password": bool(row.must_change_password),
        "mcp_token_configurado": bool((row.mcp_token_hash or "").strip()),
        "mcp_token_gerado_em": row.mcp_token_gerado_em,
        "created_at": row.created_at,
    }


def _query_ops(db: Session, tenant_id: int):
    return db.query(Atendente).filter(Atendente.tenant_id == tenant_id, Atendente.role == "saas_ops")


def _obter_ops(db: Session, tenant_id: int, usuario_id: int) -> Atendente:
    row = _query_ops(db, tenant_id).filter(Atendente.id == usuario_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado")
    return row


def _contar_ops_activos(db: Session, tenant_id: int, excluir_id: int | None = None) -> int:
    q = _query_ops(db, tenant_id).filter(Atendente.ativo.is_(True))
    if excluir_id is not None:
        q = q.filter(Atendente.id != excluir_id)
    return q.count()


def listar(
    db: Session,
    actor: Atendente,
    *,
    incluir_inativos: bool,
    busca: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Atendente], int]:
    q = _query_ops(db, actor.tenant_id)
    if not incluir_inativos:
        q = q.filter(Atendente.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter((Atendente.nome.ilike(term)) | (Atendente.email.ilike(term)))
    total = q.count()
    rows = q.order_by(Atendente.nome.asc(), Atendente.id.asc()).offset(offset).limit(limit).all()
    return rows, total


def obter(db: Session, actor: Atendente, usuario_id: int) -> Atendente:
    return _obter_ops(db, actor.tenant_id, usuario_id)


def criar(db: Session, actor: Atendente, data: SaasOpsUsuarioCreate) -> tuple[Atendente, str]:
    email = _validar_email(data.email)
    nome = (data.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome.")
    existe = (
        db.query(Atendente)
        .filter(Atendente.tenant_id == actor.tenant_id, func.lower(Atendente.email) == email)
        .first()
    )
    if existe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já cadastrado")
    senha = _agora_senha()
    row = Atendente(
        tenant_id=actor.tenant_id,
        email=email,
        nome=nome,
        senha_hash=hash_senha(senha),
        role="saas_ops",
        ativo=True,
        must_change_password=True,
    )
    db.add(row)
    db.flush()
    registrar_audit(db, "atendente", row.id, "create_saas_ops", actor.id)
    return row, senha


def actualizar(db: Session, actor: Atendente, usuario_id: int, data: SaasOpsUsuarioUpdate) -> Atendente:
    row = _obter_ops(db, actor.tenant_id, usuario_id)
    update = data.model_dump(exclude_unset=True)
    if "nome" in update and update["nome"] is not None:
        nome = update["nome"].strip()
        if not nome:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome.")
        row.nome = nome
    if "ativo" in update and update["ativo"] is not None:
        activo = bool(update["ativo"])
        if not activo:
            if row.id == actor.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não podes desactivar a tua própria conta.",
                )
            if row.ativo and _contar_ops_activos(db, actor.tenant_id, excluir_id=row.id) < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Não é possível desactivar o último utilizador activo da equipa.",
                )
        row.ativo = activo
    registrar_audit(db, "atendente", row.id, "update_saas_ops", actor.id)
    db.flush()
    return row


def redefinir_senha(db: Session, actor: Atendente, usuario_id: int) -> tuple[Atendente, str]:
    row = _obter_ops(db, actor.tenant_id, usuario_id)
    if not row.ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active a conta antes de gerar uma senha nova.",
        )
    senha = _agora_senha()
    row.senha_hash = hash_senha(senha)
    row.must_change_password = True
    row.token_version = int(row.token_version or 0) + 1
    registrar_audit(db, "atendente", row.id, "reset_senha_saas_ops", actor.id)
    db.flush()
    return row, senha
