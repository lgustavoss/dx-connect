"""Motor de avaliação de regras de roteamento (#258)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.routing import RoutingCampo, RoutingCanal, RoutingOperador
from app.core.ticket_prioridade import PrioridadeTicket
from app.models.routing_rule import RoutingRule

logger = logging.getLogger(__name__)


@dataclass
class RoutingContext:
    email_from: str | None = None
    email_to: str | None = None
    assunto: str | None = None
    canal: RoutingCanal = RoutingCanal.email
    rede_id: int | None = None


@dataclass
class RoutingResult:
    matched: bool = False
    rule_id: int | None = None
    rule_nome: str | None = None
    setor_id: int | None = None
    prioridade: PrioridadeTicket | None = None
    natureza_id: int | None = None
    motivo_id: int | None = None
    atendente_id: int | None = None
    acoes_parciais: dict = field(default_factory=dict)


def _valor_campo(ctx: RoutingContext, campo: RoutingCampo) -> str:
    if campo == RoutingCampo.email_from:
        return (ctx.email_from or "").strip().lower()
    if campo == RoutingCampo.email_to:
        return (ctx.email_to or "").strip().lower()
    if campo == RoutingCampo.assunto:
        return (ctx.assunto or "").strip()
    if campo == RoutingCampo.canal:
        return ctx.canal.value
    return ""


def _condicao_atende(ctx: RoutingContext, cond: dict) -> bool:
    try:
        campo = RoutingCampo(cond["campo"])
        operador = RoutingOperador(cond["operador"])
        valor_regra = str(cond.get("valor") or "").strip()
    except (KeyError, ValueError):
        return False

    atual = _valor_campo(ctx, campo)
    if operador == RoutingOperador.equals:
        if campo == RoutingCampo.assunto:
            return atual.lower() == valor_regra.lower()
        return atual == valor_regra.lower()
    if operador == RoutingOperador.contains:
        if campo == RoutingCampo.assunto:
            return valor_regra.lower() in atual.lower()
        return valor_regra.lower() in atual
    if operador == RoutingOperador.regex:
        try:
            return bool(re.search(valor_regra, atual, re.IGNORECASE))
        except re.error:
            return False
    return False


def _regra_no_escopo(rule: RoutingRule, rede_id: int | None) -> bool:
    if rule.rede_id is None:
        return True
    return rede_id is not None and rule.rede_id == rede_id


def _regra_atende(ctx: RoutingContext, rule: RoutingRule) -> bool:
    if not _regra_no_escopo(rule, ctx.rede_id):
        return False
    condicoes = rule.condicoes or []
    if not condicoes:
        return False
    return all(_condicao_atende(ctx, c) for c in condicoes)


def _merge_acoes(resultado: RoutingResult, acoes: dict) -> None:
    if not acoes:
        return
    if acoes.get("setor_id") is not None:
        resultado.setor_id = int(acoes["setor_id"])
    if acoes.get("prioridade") is not None:
        resultado.prioridade = PrioridadeTicket(str(acoes["prioridade"]))
    if acoes.get("natureza_id") is not None:
        resultado.natureza_id = int(acoes["natureza_id"])
    if acoes.get("motivo_id") is not None:
        resultado.motivo_id = int(acoes["motivo_id"])
    if acoes.get("atendente_id") is not None:
        resultado.atendente_id = int(acoes["atendente_id"])


def evaluate_routing(db: Session, *, tenant_id: int, context: RoutingContext) -> RoutingResult:
    """Primeira regra ativa que casa (ordem ascendente) define o resultado."""
    rules = (
        db.query(RoutingRule)
        .filter(RoutingRule.tenant_id == tenant_id, RoutingRule.ativo.is_(True))
        .order_by(RoutingRule.ordem.asc(), RoutingRule.id.asc())
        .all()
    )
    for rule in rules:
        if not _regra_atende(context, rule):
            continue
        resultado = RoutingResult(matched=True, rule_id=rule.id, rule_nome=rule.nome)
        _merge_acoes(resultado, rule.acoes or {})
        logger.debug("Roteamento: regra #%s (%s) aplicada", rule.id, rule.nome)
        return resultado
    return RoutingResult()


def aplicar_roteamento_setor(
    *,
    setor_atual: int | None,
    resultado: RoutingResult,
    aplicar_setor: bool,
) -> int | None:
    """Respeita setor explícito quando aplicar_setor=False."""
    if aplicar_setor and resultado.setor_id is not None:
        return resultado.setor_id
    return setor_atual


def resultado_para_read_dict(resultado: RoutingResult) -> dict:
    return {
        "matched": resultado.matched,
        "rule_id": resultado.rule_id,
        "rule_nome": resultado.rule_nome,
        "setor_id": resultado.setor_id,
        "prioridade": resultado.prioridade.value if resultado.prioridade else None,
        "natureza_id": resultado.natureza_id,
        "motivo_id": resultado.motivo_id,
        "atendente_id": resultado.atendente_id,
    }
