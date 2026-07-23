"""Regras de negócio do painel SaaS / licenças — #521–#522."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.cliente_saas import STATUS_CLIENTE_SAAS, ClienteSaaS
from app.schemas.saas import ClienteSaaSCreate, ClienteSaaSRegistrarInstancia, ClienteSaaSUpdate


class SaasErro(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def obter(db: Session, cliente_id: int) -> ClienteSaaS:
    row = db.query(ClienteSaaS).filter(ClienteSaaS.id == cliente_id).first()
    if not row:
        raise SaasErro("Cliente SaaS não encontrado", 404)
    return row


def _garantir_slug_unico(db: Session, slug: str, excluir_id: int | None = None) -> None:
    q = db.query(ClienteSaaS).filter(ClienteSaaS.slug == slug)
    if excluir_id is not None:
        q = q.filter(ClienteSaaS.id != excluir_id)
    if q.first():
        raise SaasErro("Já existe um cliente com este slug", 409)


def criar(db: Session, data: ClienteSaaSCreate) -> ClienteSaaS:
    if data.status not in STATUS_CLIENTE_SAAS:
        raise SaasErro("Status inválido")
    _garantir_slug_unico(db, data.slug)
    row = ClienteSaaS(**data.model_dump())
    db.add(row)
    db.flush()
    return row


def atualizar(db: Session, cliente_id: int, data: ClienteSaaSUpdate) -> ClienteSaaS:
    row = obter(db, cliente_id)
    payload = data.model_dump(exclude_unset=True)
    if "status" in payload and payload["status"] not in STATUS_CLIENTE_SAAS:
        raise SaasErro("Status inválido")
    if "slug" in payload:
        _garantir_slug_unico(db, payload["slug"], excluir_id=cliente_id)
    for k, v in payload.items():
        setattr(row, k, v)
    db.flush()
    return row


def suspender(db: Session, cliente_id: int) -> ClienteSaaS:
    row = obter(db, cliente_id)
    row.status = "suspenso"
    db.flush()
    return row


def reativar(db: Session, cliente_id: int) -> ClienteSaaS:
    row = obter(db, cliente_id)
    if row.status == "churn":
        raise SaasErro("Cliente em churn não pode ser reativado por este atalho; edite o status")
    row.status = "ativo"
    db.flush()
    return row


def registrar_instancia(db: Session, cliente_id: int, data: ClienteSaaSRegistrarInstancia) -> ClienteSaaS:
    row = obter(db, cliente_id)
    row.instancia_url = data.instancia_url
    db.flush()
    return row


def solicitar_provisionamento(db: Session, cliente_id: int) -> ClienteSaaS:
    """Stub DR-04: marca pedido sem orquestrar Docker."""
    row = obter(db, cliente_id)
    row.provisionamento_solicitado = True
    db.flush()
    return row
