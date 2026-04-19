import json
from urllib import error, request

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.core.auth import obter_atendente_atual
from app.models import Atendente
from app.schemas.chat_assistant import (
    ChatAssistantSuggestRequest,
    ChatAssistantSuggestResponse,
)

router = APIRouter(prefix="/chat-assistant", tags=["chat-assistant"])


def _build_prompt(payload: ChatAssistantSuggestRequest) -> str:
    lines = [
        "Contexto do atendimento:",
        f"- Ticket: {payload.ticket.protocolo}",
        f"- Assunto: {payload.ticket.assunto}",
        f"- Empresa/posto: {payload.ticket.empresa_nome or 'Nao informado'}",
        f"- Setor: {payload.ticket.setor_nome or 'Nao informado'}",
        f"- Status atual: {payload.ticket.status_nome or 'Nao informado'}",
        "",
        "Historico recente da conversa:",
    ]
    if payload.conversation:
        for item in payload.conversation[-10:]:
            role = {
                "customer": "Cliente",
                "agent": "Equipe",
                "internal": "Nota interna",
            }[item.role]
            lines.append(f"{role}: {item.content.strip()}")
    else:
        lines.append("Sem historico anterior.")
    if payload.objective:
        lines.extend(["", f"Objetivo adicional: {payload.objective.strip()}"])
    lines.extend(
        [
            "",
            "Gere apenas a resposta que a equipe pode enviar ao cliente agora.",
            "A resposta deve ser em portugues do Brasil, clara, objetiva e adequada para suporte de posto de combustivel.",
            "Nao invente dados operacionais, prazos ou acoes ja executadas.",
            "Se faltar informacao, peca de forma pratica os dados necessarios.",
        ]
    )
    return "\n".join(lines)


def _system_instructions(tone: str) -> str:
    tone_map = {
        "acolhedor": "tom acolhedor, humano e tranquilizador",
        "consultivo": "tom consultivo, profissional e seguro",
        "agil": "tom agil, direto e operacional",
    }
    return (
        "Voce e um assistente de atendimento do DX Connect para operacoes de postos de combustivel. "
        f"Escreva com {tone_map.get(tone, tone_map['consultivo'])}. "
        "Priorize respostas curtas, orientadas a proximo passo e sem jargao excessivo. "
        "Nunca exponha notas internas nem mencione que voce e uma IA."
    )


def _extract_output_text(data: dict) -> str:
    text = (data.get("output_text") or "").strip()
    if text:
        return text
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                candidate = (content.get("text") or "").strip()
                if candidate:
                    return candidate
    return ""


def generate_chat_reply(payload: ChatAssistantSuggestRequest) -> ChatAssistantSuggestResponse:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integracao com OpenAI nao configurada no servidor.",
        )

    body = {
        "model": settings.OPENAI_CHAT_MODEL,
        "input": [
            {"role": "system", "content": _system_instructions(payload.tone)},
            {"role": "user", "content": _build_prompt(payload)},
        ],
    }
    raw = json.dumps(body).encode("utf-8")
    req = request.Request(
        url=f"{settings.OPENAI_BASE_URL.rstrip('/')}/responses",
        data=raw,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        },
    )

    try:
        with request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = "Nao foi possivel obter sugestao da OpenAI."
        try:
            payload_err = json.loads(exc.read().decode("utf-8"))
            detail = payload_err.get("error", {}).get("message") or detail
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao comunicar com a OpenAI.",
        ) from exc

    reply = _extract_output_text(data)
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="A OpenAI nao retornou texto utilizavel para a sugestao.",
        )

    return ChatAssistantSuggestResponse(
        reply=reply,
        model=settings.OPENAI_CHAT_MODEL,
        provider="openai",
    )


@router.post("/respond", response_model=ChatAssistantSuggestResponse)
def suggest_reply(
    payload: ChatAssistantSuggestRequest,
    _: Atendente = Depends(obter_atendente_atual),
):
    return generate_chat_reply(payload)
