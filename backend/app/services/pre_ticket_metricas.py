"""Métricas, custo e alertas do pré-ticket IA (#815)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.structured_log import log_event
from app.models.pre_ticket_analise_metrica import PreTicketAnaliseMetrica
from app.models.pre_ticket_historico import PreTicketHistorico
from app.models.pre_ticket_sessao import PreTicketSessao
import logging

logger = logging.getLogger(__name__)


@dataclass
class OpenAiCallMeta:
    latencia_ms: int
    model: str
    prompt_version: str | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    erro_tipo: str = "ok"


def erro_tipo_de_status(status_code: int) -> str:
    if status_code == 504:
        return "timeout"
    if status_code == 429:
        return "rate_limit"
    if status_code == 503:
        return "desligado"
    if status_code == 502:
        return "http_error"
    return "erro"


def estimar_custo_usd(
    tokens_input: int | None,
    tokens_output: int | None,
) -> float | None:
    if tokens_input is None and tokens_output is None:
        return None
    tin = int(tokens_input or 0)
    tout = int(tokens_output or 0)
    return round(
        (tin / 1_000_000) * settings.PRE_TICKET_AI_COST_INPUT_PER_1M
        + (tout / 1_000_000) * settings.PRE_TICKET_AI_COST_OUTPUT_PER_1M,
        6,
    )


def registrar_chamada_ia(
    db: Session,
    *,
    tenant_id: int,
    sessao_id: int,
    atendente_id: int | None,
    meta: OpenAiCallMeta,
    sucesso: bool,
) -> PreTicketAnaliseMetrica:
    custo = estimar_custo_usd(meta.tokens_input, meta.tokens_output) if sucesso else None
    row = PreTicketAnaliseMetrica(
        tenant_id=tenant_id,
        sessao_id=sessao_id,
        atendente_id=atendente_id,
        sucesso=sucesso,
        erro_tipo=meta.erro_tipo if not sucesso else "ok",
        latencia_ms=meta.latencia_ms,
        model=meta.model,
        prompt_version=meta.prompt_version,
        tokens_input=meta.tokens_input,
        tokens_output=meta.tokens_output,
        custo_estimado_usd=custo,
    )
    db.add(row)
    log_event(
        logger,
        "pre_ticket_ia_analise",
        sucesso=sucesso,
        erro_tipo=row.erro_tipo,
        latencia_ms=row.latencia_ms,
        sessao_id=sessao_id,
        tokens_input=row.tokens_input,
        tokens_output=row.tokens_output,
        custo_estimado_usd=custo,
        model=row.model,
    )
    return row


def _percentil(valores: list[int], pct: float) -> int | None:
    if not valores:
        return None
    ordenado = sorted(valores)
    idx = max(0, min(len(ordenado) - 1, int(round((pct / 100) * (len(ordenado) - 1)))))
    return ordenado[idx]


def _periodo_default() -> tuple[datetime, datetime]:
    ate = datetime.now(timezone.utc)
    desde = ate - timedelta(days=30)
    return desde, ate


def montar_relatorio(
    db: Session,
    tenant_id: int,
    *,
    desde: datetime | None = None,
    ate: datetime | None = None,
) -> dict[str, Any]:
    if ate is None and desde is None:
        desde, ate = _periodo_default()
    elif ate is None:
        ate = datetime.now(timezone.utc)
    elif desde is None:
        desde = ate - timedelta(days=30)

    metricas_q = db.query(PreTicketAnaliseMetrica).filter(
        PreTicketAnaliseMetrica.tenant_id == tenant_id,
        PreTicketAnaliseMetrica.created_at >= desde,
        PreTicketAnaliseMetrica.created_at <= ate,
    )
    metricas = metricas_q.all()
    total_chamadas = len(metricas)
    sucesso = sum(1 for m in metricas if m.sucesso)
    falhas = total_chamadas - sucesso
    latencias = [m.latencia_ms for m in metricas if m.latencia_ms is not None]
    custo_total = sum(m.custo_estimado_usd or 0 for m in metricas)

    erros_por_tipo: dict[str, int] = {}
    for m in metricas:
        if not m.sucesso:
            erros_por_tipo[m.erro_tipo] = erros_por_tipo.get(m.erro_tipo, 0) + 1

    sessoes_analisadas = (
        db.query(func.count(func.distinct(PreTicketAnaliseMetrica.sessao_id)))
        .filter(
            PreTicketAnaliseMetrica.tenant_id == tenant_id,
            PreTicketAnaliseMetrica.created_at >= desde,
            PreTicketAnaliseMetrica.created_at <= ate,
            PreTicketAnaliseMetrica.sucesso.is_(True),
        )
        .scalar()
        or 0
    )

    sessoes_aprovadas = (
        db.query(func.count(PreTicketSessao.id))
        .filter(
            PreTicketSessao.tenant_id == tenant_id,
            PreTicketSessao.created_at >= desde,
            PreTicketSessao.created_at <= ate,
            PreTicketSessao.estado.in_(("aprovado", "publicado")),
        )
        .scalar()
        or 0
    )

    retrabalho_rows = (
        db.query(PreTicketHistorico.sessao_id, func.count(PreTicketHistorico.id))
        .join(PreTicketSessao, PreTicketSessao.id == PreTicketHistorico.sessao_id)
        .filter(
            PreTicketSessao.tenant_id == tenant_id,
            PreTicketHistorico.acao == "analisar",
            PreTicketHistorico.created_at >= desde,
            PreTicketHistorico.created_at <= ate,
        )
        .group_by(PreTicketHistorico.sessao_id)
        .all()
    )
    retrabalho = sum(1 for _sid, cnt in retrabalho_rows if cnt > 1)

    taxa_aprovacao = round(sessoes_aprovadas / sessoes_analisadas, 4) if sessoes_analisadas else None
    taxa_retrabalho = round(retrabalho / sessoes_analisadas, 4) if sessoes_analisadas else None
    taxa_erro = round(falhas / total_chamadas, 4) if total_chamadas else None
    latencia_media = round(sum(latencias) / len(latencias), 1) if latencias else None
    latencia_p95 = _percentil(latencias, 95)
    custo_medio = round(custo_total / sucesso, 6) if sucesso else None

    hoje_inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    custo_hoje = (
        db.query(func.coalesce(func.sum(PreTicketAnaliseMetrica.custo_estimado_usd), 0))
        .filter(
            PreTicketAnaliseMetrica.tenant_id == tenant_id,
            PreTicketAnaliseMetrica.created_at >= hoje_inicio,
        )
        .scalar()
        or 0
    )

    alertas: list[dict[str, Any]] = []
    if taxa_erro is not None and taxa_erro * 100 >= settings.PRE_TICKET_ALERT_ERROR_RATE_PCT:
        alertas.append(
            {
                "tipo": "taxa_erro",
                "nivel": "warning",
                "mensagem": f"Taxa de erro IA em {taxa_erro * 100:.1f}% (limite {settings.PRE_TICKET_ALERT_ERROR_RATE_PCT}%).",
            }
        )
    if latencia_p95 is not None and latencia_p95 >= settings.PRE_TICKET_ALERT_LATENCY_P95_MS:
        alertas.append(
            {
                "tipo": "latencia",
                "nivel": "warning",
                "mensagem": f"Latência p95 em {latencia_p95} ms (limite {settings.PRE_TICKET_ALERT_LATENCY_P95_MS} ms).",
            }
        )
    if float(custo_hoje) >= settings.PRE_TICKET_ALERT_CUSTO_DIARIO_USD:
        alertas.append(
            {
                "tipo": "custo_diario",
                "nivel": "warning",
                "mensagem": f"Custo estimado hoje US$ {float(custo_hoje):.4f} (limite US$ {settings.PRE_TICKET_ALERT_CUSTO_DIARIO_USD:.2f}).",
            }
        )

    return {
        "periodo": {"desde": desde, "ate": ate},
        "uso": {
            "total_analises": total_chamadas,
            "analises_sucesso": sucesso,
            "analises_falha": falhas,
            "sessoes_analisadas": sessoes_analisadas,
            "sessoes_aprovadas": sessoes_aprovadas,
            "taxa_aprovacao": taxa_aprovacao,
            "taxa_retrabalho": taxa_retrabalho,
        },
        "tecnicas": {
            "taxa_erro": taxa_erro,
            "erros_por_tipo": erros_por_tipo,
            "latencia_media_ms": latencia_media,
            "latencia_p95_ms": latencia_p95,
        },
        "custo": {
            "total_usd": round(float(custo_total), 6),
            "medio_por_analise_usd": custo_medio,
            "hoje_usd": round(float(custo_hoje), 6),
        },
        "alertas": alertas,
        "limites": {
            "taxa_erro_pct": settings.PRE_TICKET_ALERT_ERROR_RATE_PCT,
            "latencia_p95_ms": settings.PRE_TICKET_ALERT_LATENCY_P95_MS,
            "custo_diario_usd": settings.PRE_TICKET_ALERT_CUSTO_DIARIO_USD,
        },
    }
