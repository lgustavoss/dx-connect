"""Editar / apagar para todos em mensagens WhatsApp (#630 lote 3)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from app.models.whatsapp_chat import WhatsappMensagem

CORPO_MENSAGEM_APAGADA = "Mensagem apagada"
# Limites alinhados à experiência típica do WhatsApp / Evolution (documentar em WHATSAPP_EVOLUTION.md).
JANELA_EDICAO_MINUTOS = 15
JANELA_APAGAR_TODOS_HORAS = 48

_PREFIXO_ASSINATURA = re.compile(r"^\[\s*[^\]]+\s*\]:\s*\n?", re.MULTILINE)


class WhatsappEdicaoErro(ValueError):
    """Validação de edição/apagamento WhatsApp."""


def corpo_sem_prefixo(corpo: str | None) -> str:
    t = (corpo or "").strip()
    return _PREFIXO_ASSINATURA.sub("", t, count=1).strip()


def mensagem_apagada(m: WhatsappMensagem) -> bool:
    return getattr(m, "apagada_em", None) is not None


def mensagem_editada(m: WhatsappMensagem) -> bool:
    return getattr(m, "editada_em", None) is not None


def _created_aware(m: WhatsappMensagem) -> datetime | None:
    ts = m.created_at
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def dentro_janela_edicao(m: WhatsappMensagem, *, agora: datetime | None = None) -> bool:
    ts = _created_aware(m)
    if ts is None:
        return False
    now = agora or datetime.now(timezone.utc)
    return now - ts <= timedelta(minutes=JANELA_EDICAO_MINUTOS)


def dentro_janela_apagar_todos(m: WhatsappMensagem, *, agora: datetime | None = None) -> bool:
    ts = _created_aware(m)
    if ts is None:
        return False
    now = agora or datetime.now(timezone.utc)
    return now - ts <= timedelta(hours=JANELA_APAGAR_TODOS_HORAS)


def pode_editar_mensagem(m: WhatsappMensagem, *, is_responsavel: bool) -> bool:
    if not is_responsavel or mensagem_apagada(m):
        return False
    if m.direcao != "outbound" or m.evento_sistema:
        return False
    if not m.wa_message_id:
        return False
    tipo = (m.tipo_midia or "texto").lower()
    if tipo not in ("texto", ""):
        return False  # legenda de mídia fora de escopo v1
    return dentro_janela_edicao(m)


def pode_apagar_para_todos(m: WhatsappMensagem, *, is_responsavel: bool) -> bool:
    if not is_responsavel or mensagem_apagada(m):
        return False
    if m.direcao != "outbound" or m.evento_sistema:
        return False
    if not m.wa_message_id:
        return False
    return dentro_janela_apagar_todos(m)
