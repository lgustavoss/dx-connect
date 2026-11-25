"""API — contas bancárias de cobrança na instância (#1392)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_permissao
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.cobranca_conta import CobrancaContaLista, CobrancaContaRead, CobrancaContaUpsert
from app.services import cobranca_conta as svc

router = APIRouter(prefix="/cobranca/contas-bancarias", tags=["cobranca-contas"])


@router.get("", response_model=CobrancaContaLista)
def listar(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_permissao("faturamento.politica")),
):
    return svc.listar(db)


@router.post("", response_model=CobrancaContaRead, status_code=201)
def criar(
    body: CobrancaContaUpsert,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("faturamento.politica")),
):
    row = svc.criar(db, body)
    registrar_audit(
        db,
        "cobranca_conta_bancaria",
        row.id,
        "create",
        atendente.id,
        payload={"apelido": row.apelido, "tem_token": row.tem_token},
    )
    db.commit()
    return row


@router.put("/{conta_id}", response_model=CobrancaContaRead)
def atualizar(
    conta_id: int,
    body: CobrancaContaUpsert,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("faturamento.politica")),
):
    row = svc.atualizar(db, conta_id, body)
    registrar_audit(
        db,
        "cobranca_conta_bancaria",
        row.id,
        "update",
        atendente.id,
        payload={"apelido": row.apelido, "tem_token": row.tem_token, "ativo": row.ativo},
    )
    db.commit()
    return row


@router.post("/{conta_id}/desativar", response_model=CobrancaContaRead)
def desativar(
    conta_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("faturamento.politica")),
):
    row = svc.desativar(db, conta_id)
    registrar_audit(
        db,
        "cobranca_conta_bancaria",
        row.id,
        "update",
        atendente.id,
        payload={"ativo": False},
    )
    db.commit()
    return row
