"""Retenção local de mídias WhatsApp e fallback Evolution (#899 / #900 / #901)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.structured_log import log_event
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem, WhatsappSettings
from app.services import evolution_api
from app.services.whatsapp_media_storage import (
    caminho_absoluto_arquivo,
    gravar_base64_em_disco,
    remover_arquivo_local,
)

logger = logging.getLogger(__name__)

MIDIA_ATIVA = "ativa"
MIDIA_EXPIRADA_LOCAL = "expirada_local"
MIDIA_INDISPONIVEL = "indisponivel"

MSG_MIDIA_INDISPONIVEL = (
    "Esta mídia não está mais disponível. Peça para o cliente enviar novamente."
)
MSG_MIDIA_TEMPORARIA = "Não foi possível recuperar a mídia agora. Tente de novo."

RETENCAO_PADRAO = {
    "imagem": 90,
    "audio": 90,
    "video": 30,
    "documento": 90,
}

TIPOS_COM_ARQUIVO = ("imagem", "audio", "video", "documento", "figurinha")

_DIAS_MIN = 1
_DIAS_MAX = 3650


class MidiaIndisponivelErro(Exception):
    """Mídia confirmada como inexistente no provedor (não tenta de novo)."""


class MidiaTemporariamenteIndisponivelErro(Exception):
    """Timeout/rede ou falha transitória — não marca indisponivel."""


@dataclass(frozen=True)
class ResultadoRehidratacao:
    path: Path | None = None
    permanente: bool = False


def estado_midia(m: WhatsappMensagem) -> str:
    raw = (getattr(m, "midia_estado", None) or "").strip().lower()
    if raw in (MIDIA_EXPIRADA_LOCAL, MIDIA_INDISPONIVEL, MIDIA_ATIVA):
        return raw
    return MIDIA_ATIVA


def midia_ainda_recuperavel(m: WhatsappMensagem) -> bool:
    """True se vale tentar servir ou reidratar (histórico da conversa permanece)."""
    if estado_midia(m) == MIDIA_INDISPONIVEL:
        return False
    tipo = (m.tipo_midia or "").strip().lower()
    if tipo in ("", "texto"):
        return False
    return bool((m.midia_nome_arquivo or "").strip() or (m.wa_message_id or "").strip())


def _clamp_dias(valor: int | None, padrao: int) -> int:
    try:
        n = int(valor) if valor is not None else padrao
    except (TypeError, ValueError):
        n = padrao
    return max(_DIAS_MIN, min(_DIAS_MAX, n))


def dias_retencao_tipo(row: WhatsappSettings | None, tipo: str | None) -> int:
    t = (tipo or "").strip().lower()
    if t == "figurinha":
        t = "imagem"
    padrao = RETENCAO_PADRAO.get(t, RETENCAO_PADRAO["imagem"])
    if row is None:
        return padrao
    if t == "audio":
        return _clamp_dias(getattr(row, "midia_retencao_dias_audio", None), padrao)
    if t == "video":
        return _clamp_dias(getattr(row, "midia_retencao_dias_video", None), padrao)
    if t == "documento":
        return _clamp_dias(getattr(row, "midia_retencao_dias_documento", None), padrao)
    return _clamp_dias(getattr(row, "midia_retencao_dias_imagem", None), padrao)


def _settings_row(db: Session) -> WhatsappSettings | None:
    return db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()


def envelope_fallback(m: WhatsappMensagem, chat: WhatsappChat) -> dict:
    wa_mid = (m.wa_message_id or "").strip()
    key: dict = {"id": wa_mid, "fromMe": (m.direcao or "") == "outbound"}
    wa = (chat.wa_id or "").strip()
    if wa:
        key["remoteJid"] = wa if "@" in wa else f"{wa}@s.whatsapp.net"
    return {"key": key}


def processar_expiracao_midias(db: Session, *, limit: int = 200) -> dict[str, int]:
    """Remove arquivos vencidos; não apaga metadados da mensagem (#900)."""
    row = _settings_row(db)
    agora = datetime.now(timezone.utc)
    removidas = 0
    falhas = 0
    restantes = max(1, limit)
    for tipo in TIPOS_COM_ARQUIVO:
        if restantes <= 0:
            break
        dias = dias_retencao_tipo(row, tipo)
        corte = agora - timedelta(days=dias)
        q = (
            db.query(WhatsappMensagem)
            .filter(WhatsappMensagem.tipo_midia == tipo)
            .filter(WhatsappMensagem.midia_nome_arquivo.isnot(None))
            .filter(WhatsappMensagem.created_at < corte)
            .filter(
                (WhatsappMensagem.midia_estado.is_(None))
                | (WhatsappMensagem.midia_estado == MIDIA_ATIVA)
            )
            .order_by(WhatsappMensagem.id.asc())
            .limit(restantes)
        )
        lote = q.all()
        for m in lote:
            nome = m.midia_nome_arquivo
            try:
                if caminho_absoluto_arquivo(nome):
                    if not remover_arquivo_local(nome):
                        falhas += 1
                        continue
                m.midia_estado = MIDIA_EXPIRADA_LOCAL
                removidas += 1
                restantes -= 1
            except Exception:
                falhas += 1
                logger.exception("Falha ao expirar mídia mensagem_id=%s", m.id)
    if removidas or falhas:
        db.flush()
        log_event(
            logger,
            "whatsapp.midia.retencao",
            removidas=removidas,
            falhas=falhas,
        )
    return {"removidas": removidas, "falhas": falhas}


def _erro_fallback_permanente(err: str | None) -> bool:
    if not err:
        return False
    low = err.lower()
    return "message not found" in low or "mensagem não encontrada" in low or "mensagem nao encontrada" in low


def rehidratar_via_evolution(db: Session, m: WhatsappMensagem, chat: WhatsappChat) -> ResultadoRehidratacao:
    """Tenta getBase64FromMediaMessage e grava de novo em disco (#901)."""
    wa_mid = (m.wa_message_id or "").strip()
    if not wa_mid:
        return ResultadoRehidratacao(permanente=True)
    st = _settings_row(db)
    if not st or not st.evolution_base_url or not st.evolution_instance_name or not st.evolution_api_key:
        return ResultadoRehidratacao(permanente=False)
    tipo = (m.tipo_midia or "").strip().lower()
    try:
        ok, b64, err = evolution_api.evolution_get_base64_from_media_message(
            st.evolution_base_url,
            st.evolution_instance_name,
            st.evolution_api_key,
            envelope_fallback(m, chat),
            convert_to_mp4=(tipo in ("video", "audio")),
            timeout=20,
        )
    except Exception:
        logger.warning("Fallback Evolution falhou (mensagem_id=%s)", m.id, exc_info=True)
        return ResultadoRehidratacao(permanente=False)
    if not ok or not b64:
        permanente = _erro_fallback_permanente(err)
        log_event(
            logger,
            "whatsapp.midia.fallback_falhou",
            mensagem_id=m.id,
            erro=(err or "")[:300],
            permanente=permanente,
            level=logging.WARNING,
        )
        return ResultadoRehidratacao(permanente=permanente)
    nome = gravar_base64_em_disco(b64, m.mimetype)
    if not nome:
        return ResultadoRehidratacao(permanente=False)
    m.midia_nome_arquivo = nome
    m.midia_estado = MIDIA_ATIVA
    db.flush()
    path = caminho_absoluto_arquivo(nome)
    return ResultadoRehidratacao(path=path, permanente=False)


def obter_arquivo_midia(db: Session, m: WhatsappMensagem, chat: WhatsappChat) -> Path:
    """Serve o arquivo local ou reidrata. 410 permanente ou 503 transitório."""
    if getattr(m, "apagada_em", None):
        raise MidiaIndisponivelErro()
    if estado_midia(m) == MIDIA_INDISPONIVEL:
        raise MidiaIndisponivelErro()
    path = caminho_absoluto_arquivo(m.midia_nome_arquivo)
    if path:
        return path
    resultado = rehidratar_via_evolution(db, m, chat)
    if resultado.path:
        db.commit()
        return resultado.path
    if resultado.permanente:
        m.midia_estado = MIDIA_INDISPONIVEL
        db.commit()
        raise MidiaIndisponivelErro()
    raise MidiaTemporariamenteIndisponivelErro()
