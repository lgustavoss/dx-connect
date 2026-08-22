"""Chamada ao provedor OpenAI para análise de pré-ticket (#809 / #815)."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings
from app.services.pre_ticket_metricas import OpenAiCallMeta
from app.services.pre_ticket_prompt import (
    PRE_TICKET_PROMPT_VERSION,
    SYSTEM_PROMPT_V1,
    montar_user_prompt,
)
from app.services.pre_ticket_redaction import redact_fields

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 60.0

CLASSIFICACOES = frozenset({"bug", "melhoria", "spike", "infra", "documentacao", "duvida"})
VIABILIDADES = frozenset({"viavel", "nao_viavel", "precisa_contexto"})


@dataclass
class PreTicketAiCallResult:
    data: dict[str, Any] | None
    meta: OpenAiCallMeta
    http_error: HTTPException | None = None


class PreTicketAiHttpError(HTTPException):
    def __init__(self, status_code: int, detail: str, meta: OpenAiCallMeta):
        super().__init__(status_code=status_code, detail=detail)
        self.meta = meta


def pre_ticket_ia_habilitada() -> bool:
    if not settings.PRE_TICKET_AI_ENABLED:
        return False
    return bool((settings.OPENAI_API_KEY or "").strip())


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY.strip()}",
        "Content-Type": "application/json",
    }


def _validar_analise(data: dict[str, Any]) -> dict[str, Any]:
    classificacao = str(data.get("classificacao", "")).strip().lower()
    if classificacao not in CLASSIFICACOES:
        raise HTTPException(status_code=502, detail="Resposta da IA com classificação inválida.")

    viabilidade = str(data.get("viabilidade", "")).strip().lower()
    if viabilidade not in VIABILIDADES:
        raise HTTPException(status_code=502, detail="Resposta da IA com viabilidade inválida.")

    titulo = str(data.get("titulo_sugerido", "")).strip()
    if not titulo:
        raise HTTPException(status_code=502, detail="Resposta da IA sem título sugerido.")

    corpo = str(data.get("corpo_sugerido", "")).strip()
    if not corpo:
        raise HTTPException(status_code=502, detail="Resposta da IA sem corpo sugerido.")

    def _lista(key: str) -> list[str]:
        raw = data.get(key, [])
        if not isinstance(raw, list):
            return []
        return [str(x).strip() for x in raw if str(x).strip()]

    return {
        "classificacao": classificacao,
        "lacunas_perguntas": _lista("lacunas_perguntas"),
        "riscos": _lista("riscos"),
        "viabilidade": viabilidade,
        "titulo_sugerido": titulo[:255],
        "criterios_aceite": _lista("criterios_aceite"),
        "corpo_sugerido": corpo,
        "dependencias": _lista("dependencias"),
        "prompt_version": PRE_TICKET_PROMPT_VERSION,
    }


def _chamar_openai(system: str, user: str) -> tuple[dict[str, Any], OpenAiCallMeta]:
    model = settings.PRE_TICKET_AI_MODEL.strip()
    inicio = time.perf_counter()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }

    def _meta(erro_tipo: str, **extra: Any) -> OpenAiCallMeta:
        return OpenAiCallMeta(
            latencia_ms=int((time.perf_counter() - inicio) * 1000),
            model=model,
            prompt_version=PRE_TICKET_PROMPT_VERSION,
            erro_tipo=erro_tipo,
            **extra,
        )

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            res = client.post(OPENAI_CHAT_URL, headers=_headers(), json=payload)
    except httpx.TimeoutException as exc:
        logger.warning("OpenAI timeout pré-ticket: %s", exc)
        raise PreTicketAiHttpError(
            504,
            "A análise demorou demais. Tente novamente em instantes.",
            _meta("timeout"),
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("OpenAI HTTP error pré-ticket: %s", exc)
        raise PreTicketAiHttpError(
            502,
            "Não foi possível contactar o serviço de IA. Tente novamente.",
            _meta("http_error"),
        ) from exc

    usage = {}
    try:
        body = res.json()
        usage = body.get("usage") or {}
    except json.JSONDecodeError:
        body = {}

    tokens_in = usage.get("prompt_tokens")
    tokens_out = usage.get("completion_tokens")
    extra_tokens = {
        "tokens_input": int(tokens_in) if tokens_in is not None else None,
        "tokens_output": int(tokens_out) if tokens_out is not None else None,
    }

    if res.status_code == 429:
        raise PreTicketAiHttpError(
            429,
            "Limite de uso da IA atingido. Aguarde e tente novamente.",
            _meta("rate_limit", **extra_tokens),
        )
    if res.status_code >= 500:
        raise PreTicketAiHttpError(
            502,
            "Serviço de IA indisponível no momento. Tente novamente.",
            _meta("http_error", **extra_tokens),
        )
    if res.status_code >= 400:
        logger.warning("OpenAI rejeitou pré-ticket: %s", res.text[:500])
        raise PreTicketAiHttpError(
            502,
            "Serviço de IA rejeitou a solicitação. Verifique a configuração.",
            _meta("rejeitado", **extra_tokens),
        )

    try:
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("OpenAI resposta inválida pré-ticket: %s", exc)
        raise PreTicketAiHttpError(
            502,
            "Resposta da IA em formato inesperado. Tente analisar novamente.",
            _meta("resposta_invalida", **extra_tokens),
        ) from exc

    if not isinstance(parsed, dict):
        raise PreTicketAiHttpError(
            502,
            "Resposta da IA em formato inesperado.",
            _meta("resposta_invalida", **extra_tokens),
        )

    return parsed, _meta("ok", **extra_tokens)


def analisar(
    *,
    contexto: str,
    problema: str,
    impacto: str | None = None,
    evidencias: str | None = None,
    urgencia: str | None = None,
    ticket_id: int | None = None,
) -> PreTicketAiCallResult:
    model = settings.PRE_TICKET_AI_MODEL.strip()
    if not pre_ticket_ia_habilitada():
        meta = OpenAiCallMeta(latencia_ms=0, model=model, erro_tipo="desligado")
        return PreTicketAiCallResult(
            None,
            meta,
            HTTPException(
                status_code=503,
                detail="Análise IA desligada (PRE_TICKET_AI_ENABLED / OPENAI_API_KEY).",
            ),
        )

    redacted = redact_fields(
        contexto=contexto,
        problema=problema,
        impacto=impacto,
        evidencias=evidencias,
        urgencia=urgencia,
    )
    user_prompt = montar_user_prompt(
        contexto=redacted["contexto"] or "",
        problema=redacted["problema"] or "",
        impacto=redacted.get("impacto"),
        evidencias=redacted.get("evidencias"),
        urgencia=redacted.get("urgencia"),
        ticket_id=ticket_id,
    )
    try:
        raw, meta = _chamar_openai(SYSTEM_PROMPT_V1, user_prompt)
        try:
            validated = _validar_analise(raw)
        except HTTPException as exc:
            meta.erro_tipo = "resposta_invalida"
            return PreTicketAiCallResult(None, meta, exc)
        return PreTicketAiCallResult(validated, meta, None)
    except PreTicketAiHttpError as exc:
        return PreTicketAiCallResult(None, exc.meta, exc)
