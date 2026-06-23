"""Aplicação de resultado de roteamento em tickets (#258)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.models import TicketHistorico
from app.models.atendente import Atendente
from app.models.ticket_classificacao import TicketMotivo
from app.services.routing_evaluate import RoutingResult

CAMPO_HISTORICO_ROTEAMENTO = "roteamento_regra"


def resolver_motivo_roteamento(
    db: Session,
    *,
    natureza_id: int | None,
    motivo_id: int | None,
) -> int | None:
    """Resolve motivo_id efetivo; natureza sozinha usa o primeiro motivo ativo da natureza."""
    if motivo_id is not None:
        mot = db.query(TicketMotivo).filter(TicketMotivo.id == motivo_id, TicketMotivo.ativo.is_(True)).first()
        if not mot:
            return None
        if natureza_id is not None and mot.natureza_id != natureza_id:
            return None
        return motivo_id
    if natureza_id is not None:
        mot = (
            db.query(TicketMotivo)
            .filter(TicketMotivo.natureza_id == natureza_id, TicketMotivo.ativo.is_(True))
            .order_by(TicketMotivo.ordem.asc(), TicketMotivo.id.asc())
            .first()
        )
        return mot.id if mot else None
    return None


def resolver_atendente_roteamento(
    db: Session,
    *,
    tenant_id: int,
    setor_id: int,
    atendente_id: int | None,
) -> int | None:
    if atendente_id is None:
        return None
    at = (
        db.query(Atendente)
        .filter(Atendente.id == atendente_id, Atendente.tenant_id == tenant_id, Atendente.ativo.is_(True))
        .first()
    )
    if not at:
        return None
    ids_setor = {s.id for s in at.setores}
    if setor_id not in ids_setor:
        return None
    return atendente_id


def registrar_roteamento_aplicado(
    db: Session,
    *,
    resultado: RoutingResult,
    ticket_id: int | None = None,
    atendente_audit_id: int | None = None,
) -> None:
    if not resultado.matched or resultado.rule_id is None:
        return
    registrar_audit(db, "routing_rule", resultado.rule_id, "apply", atendente_audit_id)
    if ticket_id is not None:
        db.add(
            TicketHistorico(
                ticket_id=ticket_id,
                atendente_id=atendente_audit_id,
                campo=CAMPO_HISTORICO_ROTEAMENTO,
                valor_antigo="",
                valor_novo=f"{resultado.rule_id}:{resultado.rule_nome or ''}",
            )
        )


def acoes_efetivas_do_resultado(
    db: Session,
    *,
    tenant_id: int,
    setor_id: int,
    resultado: RoutingResult,
) -> tuple[int | None, int | None]:
    """Retorna (motivo_id, atendente_id) resolvidos e validados."""
    motivo_id = resolver_motivo_roteamento(
        db,
        natureza_id=resultado.natureza_id,
        motivo_id=resultado.motivo_id,
    )
    atendente_id = resolver_atendente_roteamento(
        db,
        tenant_id=tenant_id,
        setor_id=setor_id,
        atendente_id=resultado.atendente_id,
    )
    return motivo_id, atendente_id
