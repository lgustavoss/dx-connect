"""CRUD de setores (cargos) da equipe DeskRudder no control-plane."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.saas_setor import SaasSetor
from app.schemas.saas_setor import SaasSetorCreate, SaasSetorUpdate


def _normalizar_nome(nome: str) -> str:
    return " ".join((nome or "").split()).strip()


def listar(
    db: Session,
    actor: Atendente,
    *,
    incluir_inativos: bool,
) -> list[SaasSetor]:
    q = db.query(SaasSetor).filter(SaasSetor.tenant_id == actor.tenant_id)
    if not incluir_inativos:
        q = q.filter(SaasSetor.ativo.is_(True))
    return q.order_by(SaasSetor.nome.asc(), SaasSetor.id.asc()).all()


def obter(db: Session, actor: Atendente, setor_id: int) -> SaasSetor:
    row = (
        db.query(SaasSetor)
        .filter(SaasSetor.tenant_id == actor.tenant_id, SaasSetor.id == setor_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")
    return row


def criar(db: Session, actor: Atendente, data: SaasSetorCreate) -> SaasSetor:
    nome = _normalizar_nome(data.nome)
    if not nome:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome do setor.")
    existe = (
        db.query(SaasSetor)
        .filter(
            SaasSetor.tenant_id == actor.tenant_id,
            func.lower(SaasSetor.nome) == nome.lower(),
        )
        .first()
    )
    if existe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um setor com este nome.")
    row = SaasSetor(tenant_id=actor.tenant_id, nome=nome, ativo=True)
    db.add(row)
    db.flush()
    registrar_audit(db, "saas_setor", row.id, "create", actor.id)
    return row


def atualizar(db: Session, actor: Atendente, setor_id: int, data: SaasSetorUpdate) -> SaasSetor:
    row = obter(db, actor, setor_id)
    update = data.model_dump(exclude_unset=True)
    if "nome" in update and update["nome"] is not None:
        nome = _normalizar_nome(update["nome"])
        if not nome:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome do setor.")
        conflito = (
            db.query(SaasSetor)
            .filter(
                SaasSetor.tenant_id == actor.tenant_id,
                func.lower(SaasSetor.nome) == nome.lower(),
                SaasSetor.id != row.id,
            )
            .first()
        )
        if conflito:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um setor com este nome.",
            )
        row.nome = nome
    if "ativo" in update and update["ativo"] is not None:
        row.ativo = bool(update["ativo"])
    registrar_audit(db, "saas_setor", row.id, "update", actor.id)
    db.flush()
    return row


def resolver_setores_ativos(db: Session, tenant_id: int, setor_ids: list[int]) -> list[SaasSetor]:
    if not setor_ids:
        return []
    ids = sorted({int(i) for i in setor_ids})
    rows = (
        db.query(SaasSetor)
        .filter(
            SaasSetor.tenant_id == tenant_id,
            SaasSetor.id.in_(ids),
            SaasSetor.ativo.is_(True),
        )
        .all()
    )
    if len(rows) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um ou mais setores são inválidos ou estão inativos.",
        )
    return rows
