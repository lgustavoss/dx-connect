"""Avaliação 1–5 do atendimento WhatsApp ao encerrar o chat."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem, WhatsappSettings
from app.services import evolution_api
from app.services.whatsapp_auto_messages import (
    DEFAULT_AUTO_MSG_AVALIACAO,
    DEFAULT_AUTO_MSG_AVALIACAO_OBRIGADO,
    DEFAULT_AUTO_MSG_AVALIACAO_PULAR,
    DEFAULT_AUTO_MSG_AVALIACAO_SEM_NOTA,
    DEFAULT_AUTO_MSG_AVALIACAO_TIMEOUT,
    DEFAULT_AUTO_MSG_ENCERRADO,
    EVENTOS_MENSAGEM_OCULTA_CONVERSA,
)

logger = logging.getLogger(__name__)

_NOTA_RE = re.compile(r"^[1-5]$")

MotivoEncerrarAvaliacao = Literal["pular", "timeout", "invalida"]


def parse_nota_avaliacao(texto: str) -> int | None:
    s = (texto or "").strip()
    if _NOTA_RE.match(s):
        return int(s)
    return None


def avaliacao_habilitada(st: WhatsappSettings | None) -> bool:
    return bool(st and getattr(st, "avaliacao_ativa", False))


def mensagem_oculta_na_conversa(evento_sistema: str | None) -> bool:
    return (evento_sistema or "") in EVENTOS_MENSAGEM_OCULTA_CONVERSA


def janela_avaliacao_minutos(st: WhatsappSettings | None) -> int:
    raw = getattr(st, "avaliacao_janela_minutos", None) if st else None
    try:
        n = int(raw) if raw is not None else 30
    except (TypeError, ValueError):
        n = 30
    return max(1, n)


def _evolution_configurada(st: WhatsappSettings | None) -> bool:
    return bool(
        st
        and st.evolution_base_url
        and st.evolution_instance_name
        and st.evolution_api_key
    )


def _render_template(template: str, *, db: Session, chat: WhatsappChat, st: WhatsappSettings | None) -> str:
    from app.api.whatsapp_webhook import _render_template as render_webhook

    return render_webhook(template, db=db, chat=chat, st=st, atendente_nome="BOT")


def _prefixo_bot(texto: str) -> str:
    t = (texto or "").strip()
    if not t:
        return ""
    if not t.startswith("["):
        return f"[ BOT ]: {t}"
    return t


def _enviar_texto_sistema(
    db: Session,
    *,
    chat: WhatsappChat,
    st: WhatsappSettings,
    texto: str,
    evento_sistema: str | None,
) -> bool:
    txt = _prefixo_bot(texto)
    if not txt:
        return False
    ok, err, sent_wa_id = evolution_api.evolution_send_text(
        st.evolution_base_url,
        st.evolution_instance_name,
        st.evolution_api_key,
        chat.wa_id,
        txt,
    )
    if not ok:
        logger.warning("Auto-msg avaliação falhou (chat=%s): %s", chat.protocolo, err)
        return False
    db.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo=txt,
            tipo_midia="texto",
            mimetype=None,
            midia_nome_arquivo=None,
            wa_message_id=sent_wa_id,
            atendente_id=None,
            evento_sistema=evento_sistema,
        )
    )
    return True


def _enviar_encerrado(
    db: Session,
    chat: WhatsappChat,
    st: WhatsappSettings,
    *,
    evento_sistema: str,
) -> None:
    if not bool(getattr(st, "auto_msg_encerrado_ativa", True)):
        return
    raw = (getattr(st, "auto_msg_encerrado_texto", "") or "").strip() or DEFAULT_AUTO_MSG_ENCERRADO
    txt = _render_template(raw, db=db, chat=chat, st=st)
    if txt:
        _enviar_texto_sistema(db, chat=chat, st=st, texto=txt, evento_sistema=evento_sistema)


def encerrar_avaliacao_sem_nota(
    db: Session,
    chat: WhatsappChat,
    st: WhatsappSettings,
    *,
    motivo: MotivoEncerrarAvaliacao = "pular",
    msg_inbound: WhatsappMensagem | None = None,
    enviar_mensagem: bool = True,
) -> None:
    """Finaliza `aguardando_avaliacao` sem nota (pular / timeout / resposta inválida legada)."""
    if msg_inbound is not None:
        msg_inbound.evento_sistema = "avaliacao_cliente_invalida"
    chat.estado = "encerrado"
    chat.avaliacao_nota = None
    chat.avaliacao_respondida_at = None
    db.flush()
    if not enviar_mensagem or not _evolution_configurada(st):
        return
    if not bool(getattr(st, "auto_msg_avaliacao_ativa", True)):
        return
    if motivo == "timeout":
        raw = (getattr(st, "auto_msg_avaliacao_timeout_texto", "") or "").strip() or DEFAULT_AUTO_MSG_AVALIACAO_TIMEOUT
        evento = "auto_avaliacao_timeout"
    elif motivo == "pular":
        raw = (getattr(st, "auto_msg_avaliacao_pular_texto", "") or "").strip() or DEFAULT_AUTO_MSG_AVALIACAO_PULAR
        evento = "auto_avaliacao_pular"
    else:
        raw = DEFAULT_AUTO_MSG_AVALIACAO_SEM_NOTA
        evento = "auto_avaliacao_sem_nota"
    txt = _render_template(raw, db=db, chat=chat, st=st)
    if txt:
        _enviar_texto_sistema(db, chat=chat, st=st, texto=txt, evento_sistema=evento)


def _encerrar_sem_avaliacao(
    db: Session,
    chat: WhatsappChat,
    st: WhatsappSettings,
    *,
    msg_inbound: WhatsappMensagem | None = None,
) -> None:
    """Compat: resposta inválida no mesmo chat (sem abrir atendimento novo)."""
    encerrar_avaliacao_sem_nota(db, chat, st, motivo="invalida", msg_inbound=msg_inbound)


def finalizar_atendimento_whatsapp(
    db: Session,
    chat: WhatsappChat,
    st: WhatsappSettings | None,
    *,
    evento_encerrado: str = "auto_encerrado",
) -> None:
    """
    Encerra o atendimento para o atendente.
    Com avaliação ativa: passa a aguardar nota 1–5 do cliente antes do encerramento final.
    """
    chat.encerramento_at = datetime.now(timezone.utc)
    db.flush()

    if not st or not _evolution_configurada(st):
        chat.estado = "encerrado"
        return

    if avaliacao_habilitada(st):
        chat.estado = "aguardando_avaliacao"
        chat.avaliacao_solicitada = True
        chat.avaliacao_nota = None
        chat.avaliacao_respondida_at = None
        db.flush()
        if bool(getattr(st, "auto_msg_avaliacao_ativa", True)):
            raw = (getattr(st, "auto_msg_avaliacao_texto", "") or "").strip() or DEFAULT_AUTO_MSG_AVALIACAO
            txt = _render_template(raw, db=db, chat=chat, st=st)
            if txt:
                _enviar_texto_sistema(
                    db,
                    chat=chat,
                    st=st,
                    texto=txt,
                    evento_sistema="auto_avaliacao_solicitacao",
                )
        return

    chat.estado = "encerrado"
    _enviar_encerrado(db, chat, st, evento_sistema=evento_encerrado)


def processar_resposta_avaliacao(
    db: Session,
    chat: WhatsappChat,
    st: WhatsappSettings | None,
    texto: str,
    *,
    tipo_midia: str = "texto",
    msg_inbound: WhatsappMensagem | None = None,
) -> Literal["nota", "nao_nota"]:
    """
    Processa inbound em `aguardando_avaliacao`.

    Retorna ``nota`` se registrou 1–5 e encerrou; ``nao_nota`` se a mensagem não é nota
    (o caller deve encerrar a avaliação e abrir atendimento novo com essa mensagem).
    """
    if chat.estado != "aguardando_avaliacao" or not st or not _evolution_configurada(st):
        return "nao_nota"

    if (tipo_midia or "texto").strip().lower() != "texto":
        return "nao_nota"

    nota = parse_nota_avaliacao(texto)
    if nota is None:
        return "nao_nota"

    if msg_inbound is not None:
        msg_inbound.evento_sistema = "avaliacao_cliente_nota"

    chat.avaliacao_nota = nota
    chat.avaliacao_respondida_at = datetime.now(timezone.utc)
    chat.estado = "encerrado"
    db.flush()

    if bool(getattr(st, "auto_msg_avaliacao_ativa", True)):
        raw = (
            (getattr(st, "auto_msg_avaliacao_obrigado_texto", "") or "").strip()
            or DEFAULT_AUTO_MSG_AVALIACAO_OBRIGADO
        )
        txt = _render_template(raw, db=db, chat=chat, st=st)
        if txt:
            _enviar_texto_sistema(
                db,
                chat=chat,
                st=st,
                texto=txt,
                evento_sistema="auto_avaliacao_obrigado",
            )
    return "nota"


def process_whatsapp_avaliacao_timeouts(db: Session, *, limit: int = 200) -> int:
    """
    Encerra chats ainda em `aguardando_avaliacao` após a janela configurada
    (a partir de `encerramento_at`). Retorna quantidade alterada.
    """
    st = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if not st or not avaliacao_habilitada(st):
        return 0
    if not _evolution_configurada(st):
        return 0

    minutos = janela_avaliacao_minutos(st)
    limite = datetime.now(timezone.utc) - timedelta(minutes=minutos)
    chat_ids = [
        row[0]
        for row in (
            db.query(WhatsappChat.id)
            .filter(
                WhatsappChat.estado == "aguardando_avaliacao",
                WhatsappChat.encerramento_at.isnot(None),
                WhatsappChat.encerramento_at <= limite,
            )
            .order_by(WhatsappChat.id.asc())
            .limit(limit)
            .all()
        )
    ]
    alterados = 0
    for chat_id in chat_ids:
        try:
            chat = (
                db.query(WhatsappChat)
                .filter(WhatsappChat.id == chat_id, WhatsappChat.estado == "aguardando_avaliacao")
                .with_for_update()
                .first()
            )
            if not chat:
                db.rollback()
                continue
            enc_at = chat.encerramento_at
            if enc_at is None:
                db.rollback()
                continue
            if enc_at.tzinfo is None:
                enc_at = enc_at.replace(tzinfo=timezone.utc)
            if enc_at > limite:
                db.rollback()
                continue
            encerrar_avaliacao_sem_nota(db, chat, st, motivo="timeout")
            db.commit()
            alterados += 1
            try:
                from app.services.realtime_emit import emit_chat_fila_from_model

                emit_chat_fila_from_model(db, chat, estado_anterior="aguardando_avaliacao")
            except Exception as emit_exc:
                logger.warning("SSE pós-timeout avaliação (chat=%s): %s", chat_id, emit_exc)
        except Exception as exc:
            db.rollback()
            logger.warning("Timeout avaliação WhatsApp (chat=%s): %s", chat_id, exc)
    return alterados
