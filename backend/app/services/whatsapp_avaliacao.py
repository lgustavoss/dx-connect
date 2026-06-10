"""Avaliação 1–5 do atendimento WhatsApp ao encerrar o chat."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem, WhatsappSettings
from app.services import evolution_api
from app.services.whatsapp_auto_messages import (
    DEFAULT_AUTO_MSG_AVALIACAO,
    DEFAULT_AUTO_MSG_AVALIACAO_OBRIGADO,
    DEFAULT_AUTO_MSG_AVALIACAO_SEM_NOTA,
    DEFAULT_AUTO_MSG_ENCERRADO,
    EVENTOS_MENSAGEM_OCULTA_CONVERSA,
)

logger = logging.getLogger(__name__)

_NOTA_RE = re.compile(r"^[1-5]$")


def parse_nota_avaliacao(texto: str) -> int | None:
    s = (texto or "").strip()
    if _NOTA_RE.match(s):
        return int(s)
    return None


def avaliacao_habilitada(st: WhatsappSettings | None) -> bool:
    return bool(st and getattr(st, "avaliacao_ativa", False))


def mensagem_oculta_na_conversa(evento_sistema: str | None) -> bool:
    return (evento_sistema or "") in EVENTOS_MENSAGEM_OCULTA_CONVERSA


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


def _encerrar_sem_avaliacao(
    db: Session,
    chat: WhatsappChat,
    st: WhatsappSettings,
    *,
    msg_inbound: WhatsappMensagem | None = None,
) -> None:
    if msg_inbound is not None:
        msg_inbound.evento_sistema = "avaliacao_cliente_invalida"
    chat.estado = "encerrado"
    chat.avaliacao_nota = None
    chat.avaliacao_respondida_at = None
    db.flush()
    raw = DEFAULT_AUTO_MSG_AVALIACAO_SEM_NOTA
    txt = _render_template(raw, db=db, chat=chat, st=st)
    if txt:
        _enviar_texto_sistema(
            db,
            chat=chat,
            st=st,
            texto=txt,
            evento_sistema="auto_avaliacao_sem_nota",
        )


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
) -> None:
    """Processa mensagem inbound em chat aguardando_avaliacao."""
    if chat.estado != "aguardando_avaliacao" or not st or not _evolution_configurada(st):
        return

    if (tipo_midia or "texto").strip().lower() != "texto":
        _encerrar_sem_avaliacao(db, chat, st, msg_inbound=msg_inbound)
        return

    nota = parse_nota_avaliacao(texto)
    if nota is None:
        _encerrar_sem_avaliacao(db, chat, st, msg_inbound=msg_inbound)
        return

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
