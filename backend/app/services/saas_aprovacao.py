"""Aprovação go-live de licenças SaaS no control-plane."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.cliente_saas import APROVACAO_STATUS, ClienteSaaS
from app.services.saas_clientes import SaasErro, obter


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aprovar(db: Session, cliente_id: int, *, notas: str | None = None, ativar: bool = True) -> ClienteSaaS:
    row = obter(db, cliente_id)
    if row.aprovacao_status == "aprovado" and (not ativar or row.status == "ativo"):
        raise SaasErro("Licença já está aprovada")
    if row.aprovacao_status == "rejeitado":
        raise SaasErro("Licença rejeitada — edite o registo ou crie nova licença")

    row.aprovacao_status = "aprovado"
    row.aprovacao_em = _utcnow()
    if notas is not None:
        row.aprovacao_notas = (notas.strip() or None)
    if ativar and row.status in ("trial", "suspenso"):
        # Go-live: trial/suspenso → ativo após aprovação comercial
        row.status = "ativo"
    db.flush()
    return row


def rejeitar(db: Session, cliente_id: int, *, notas: str | None = None) -> ClienteSaaS:
    row = obter(db, cliente_id)
    if row.aprovacao_status == "rejeitado":
        raise SaasErro("Licença já está rejeitada")
    if row.status == "ativo" and row.aprovacao_status == "aprovado":
        raise SaasErro("Não rejeite uma licença ativa aprovada — use Suspender ou Churn")

    row.aprovacao_status = "rejeitado"
    row.aprovacao_em = _utcnow()
    row.aprovacao_notas = (notas or "").strip() or "Rejeitado pela equipa ops"
    row.status = "churn"
    # Cancela fila se ainda não provisionou com sucesso
    if row.provisionamento_status in ("pendente", "em_progresso", "aguardando_ops", "falha"):
        row.provisionamento_status = "falha"
        row.provisionamento_mensagem = "Cancelado: licença rejeitada"
        row.provisionamento_atualizado_em = _utcnow()
    db.flush()
    return row


def label_aprovacao(status: str | None) -> str:
    if status not in APROVACAO_STATUS:
        return status or "—"
    return {"pendente": "Pendente", "aprovado": "Aprovado", "rejeitado": "Rejeitado"}[status]
