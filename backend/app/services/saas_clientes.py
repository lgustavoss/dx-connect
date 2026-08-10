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
    if getattr(row, "aprovacao_status", None) == "rejeitado":
        raise SaasErro("Licença rejeitada não pode ser reativada")
    row.status = "ativo"
    db.flush()
    return row


def registrar_instancia(db: Session, cliente_id: int, data: ClienteSaaSRegistrarInstancia) -> ClienteSaaS:
    row = obter(db, cliente_id)
    row.instancia_url = data.instancia_url
    db.flush()
    return row


def solicitar_provisionamento(db: Session, cliente_id: int) -> ClienteSaaS:
    """Enfileira provisionamento (DR-04)."""
    from app.services.saas_provisionamento import enfileirar_provisionamento

    return enfileirar_provisionamento(db, cliente_id)


def confirmar_provisionamento(
    db: Session,
    cliente_id: int,
    *,
    instancia_url: str | None = None,
) -> ClienteSaaS:
    """Confirma provisionamento ops-assisted (DR-04)."""
    from app.services.saas_provisionamento import confirmar_provisionamento as _confirmar

    return _confirmar(db, cliente_id, instancia_url=instancia_url)


def serializar_cliente(row: ClienteSaaS) -> dict:
    from app.services.saas_provisionamento import montar_comandos_ops
    from app.services.saas_renovacoes import dias_para_renovacao

    return {
        "id": row.id,
        "nome": row.nome,
        "slug": row.slug,
        "status": row.status,
        "plano": row.plano,
        "data_inicio": row.data_inicio,
        "data_renovacao": row.data_renovacao,
        "instancia_url": row.instancia_url,
        "contato_email": row.contato_email,
        "contato_nome": row.contato_nome,
        "api_port": row.api_port,
        "notas": row.notas,
        "provisionamento_solicitado": bool(row.provisionamento_solicitado),
        "provisionamento_status": row.provisionamento_status,
        "provisionamento_mensagem": row.provisionamento_mensagem,
        "provisionamento_atualizado_em": row.provisionamento_atualizado_em,
        "aprovacao_status": getattr(row, "aprovacao_status", None) or "aprovado",
        "aprovacao_notas": getattr(row, "aprovacao_notas", None),
        "aprovacao_em": getattr(row, "aprovacao_em", None),
        "comandos_ops": montar_comandos_ops(row),
        "dias_para_renovacao": dias_para_renovacao(row.data_renovacao),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
