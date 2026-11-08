"""Origens do lead — lista configurável (#1319).

A origem deixa de ser texto livre: o lead guarda o nome canônico de um item
desta lista. A lista nasce com o seed `ORIGENS_SEED` e é mantida em
Configurações → Funil CRM.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.crm import ORIGENS_SEED, CrmLead, CrmOrigemLead
from app.schemas.crm import CrmOrigemLeadCreate, CrmOrigemLeadUpdate


def _limpar(nome: str | None) -> str:
    return " ".join((nome or "").split())


def ensure_origens_padrao(db: Session) -> None:
    """Cria o seed uma única vez (tabela vazia)."""
    if db.query(CrmOrigemLead.id).first() is not None:
        return
    for i, nome in enumerate(ORIGENS_SEED):
        db.add(CrmOrigemLead(nome=nome, ordem=(i + 1) * 10, ativo=True))
    db.flush()


def listar_origens(db: Session, *, incluir_inativos: bool = False) -> list[CrmOrigemLead]:
    ensure_origens_padrao(db)
    q = db.query(CrmOrigemLead)
    if not incluir_inativos:
        q = q.filter(CrmOrigemLead.ativo.is_(True))
    return q.order_by(CrmOrigemLead.ordem.asc(), CrmOrigemLead.nome.asc()).all()


def normalizar_origem(db: Session, valor: str | None) -> str | None:
    """Valida o valor contra a lista ativa e devolve o nome canônico."""
    ensure_origens_padrao(db)
    nome = _limpar(valor)
    if not nome:
        return None
    row = (
        db.query(CrmOrigemLead)
        .filter(func.lower(CrmOrigemLead.nome) == nome.lower())
        .first()
    )
    if row is None or not row.ativo:
        raise HTTPException(
            status_code=400,
            detail="Origem do lead inválida. Escolha uma origem da lista em Configurações → Funil CRM.",
        )
    return row.nome


def _origem_com_mesmo_nome(db: Session, nome: str, *, exceto_id: int | None = None) -> CrmOrigemLead | None:
    q = db.query(CrmOrigemLead).filter(func.lower(CrmOrigemLead.nome) == nome.lower())
    if exceto_id is not None:
        q = q.filter(CrmOrigemLead.id != exceto_id)
    return q.first()


def criar_origem(db: Session, data: CrmOrigemLeadCreate) -> CrmOrigemLead:
    ensure_origens_padrao(db)
    nome = _limpar(data.nome)
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome da origem.")
    if _origem_com_mesmo_nome(db, nome):
        raise HTTPException(status_code=400, detail="Já existe uma origem com este nome.")
    row = CrmOrigemLead(nome=nome, ordem=data.ordem, ativo=data.ativo)
    db.add(row)
    db.flush()
    return row


def atualizar_origem(db: Session, row: CrmOrigemLead, data: CrmOrigemLeadUpdate) -> CrmOrigemLead:
    payload = data.model_dump(exclude_unset=True)
    if "nome" in payload:
        nome = _limpar(payload["nome"])
        if not nome:
            raise HTTPException(status_code=400, detail="Informe o nome da origem.")
        if _origem_com_mesmo_nome(db, nome, exceto_id=row.id):
            raise HTTPException(status_code=400, detail="Já existe uma origem com este nome.")
        anterior = row.nome
        if nome != anterior:
            # Os leads guardam o nome; renomear mantém os registros consistentes.
            db.query(CrmLead).filter(CrmLead.origem == anterior).update(
                {CrmLead.origem: nome}, synchronize_session=False
            )
        payload["nome"] = nome
    for k, v in payload.items():
        setattr(row, k, v)
    db.flush()
    return row


def excluir_origem(db: Session, row: CrmOrigemLead) -> None:
    em_uso = db.query(CrmLead.id).filter(CrmLead.origem == row.nome).first()
    if em_uso is not None:
        raise HTTPException(
            status_code=409,
            detail="Há leads com esta origem. Desative a origem em vez de excluir.",
        )
    db.delete(row)
    db.flush()
