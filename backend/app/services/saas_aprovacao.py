"""Aprovação go-live de licenças SaaS no control-plane."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.cliente_saas import APROVACAO_STATUS, ClienteSaaS
from app.services.saas_clientes import SaasErro, obter


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aprovar(
    db: Session,
    cliente_id: int,
    *,
    notas: str | None = None,
    ativar: bool = True,
    provisionar: bool = True,
    plano_id: int | None = None,
) -> ClienteSaaS:
    """Aprova a licença e, por omissão, enfileira a criação da base/instância."""
    row = obter(db, cliente_id)
    if row.aprovacao_status == "rejeitado":
        raise SaasErro("Licença rejeitada — edite o registo ou crie nova licença")

    ja_aprovada = row.aprovacao_status == "aprovado"
    ja_provisionada = row.provisionamento_status in (
        "pendente",
        "em_progresso",
        "aguardando_ops",
        "sucesso",
        "falha",
    )
    if ja_aprovada and (not ativar or row.status == "ativo") and (not provisionar or ja_provisionada):
        raise SaasErro("Licença já está aprovada")

    if plano_id is not None:
        from app.services.saas_catalogo import aplicar_plano_em_cliente, sincronizar_snapshot_licenca

        pid, nome, _codigos, _mp, _mu = aplicar_plano_em_cliente(
            db,
            plano_id=plano_id,
            plano_actual_id=getattr(row, "plano_id", None),
        )
        row.plano_id = pid
        row.plano = nome
        sincronizar_snapshot_licenca(db, row)

    row.aprovacao_status = "aprovado"
    row.aprovacao_em = _utcnow()
    if notas is not None:
        row.aprovacao_notas = (notas.strip() or None)
    if ativar and row.status in ("trial", "suspenso"):
        # Go-live comercial: trial/suspenso → ativo após aprovação
        row.status = "ativo"
    db.flush()

    if provisionar and row.provisionamento_status not in ("sucesso", "em_progresso"):
        from app.services.saas_provisionamento import enfileirar_provisionamento

        enfileirar_provisionamento(db, row.id)
        # Tenta processar já neste pedido (cria base se EXEC=true; senão → aguardando_ops).
        from app.services.saas_provisionamento import processar_provisionamentos_pendentes

        processar_provisionamentos_pendentes(db, limit=5)
        db.refresh(row)

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
