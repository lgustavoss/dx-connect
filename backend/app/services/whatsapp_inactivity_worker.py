"""Encerramento automático de chats WhatsApp por inatividade do cliente."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem, WhatsappSettings
from app.services import evolution_api
from app.services.whatsapp_auto_messages import (
    DEFAULT_AUTO_MSG_INATIV_AVISO,
)

logger = logging.getLogger(__name__)


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


def _mensagens_relevantes_q(db: Session, chat_id: int):
    return db.query(WhatsappMensagem).filter(
        WhatsappMensagem.chat_id == chat_id,
        or_(
            WhatsappMensagem.evento_sistema.is_(None),
            WhatsappMensagem.evento_sistema != "comentario_interno",
        ),
    )


def _ultima_mensagem_relevante(db: Session, chat_id: int) -> WhatsappMensagem | None:
    return (
        _mensagens_relevantes_q(db, chat_id)
        .order_by(desc(WhatsappMensagem.created_at), desc(WhatsappMensagem.id))
        .first()
    )


def _ultima_outbound_humana(db: Session, chat_id: int) -> WhatsappMensagem | None:
    """Mensagem enviada pelo atendente (não BOT / auto_assumido / avisos de sistema)."""
    return (
        db.query(WhatsappMensagem)
        .filter(
            WhatsappMensagem.chat_id == chat_id,
            WhatsappMensagem.direcao == "outbound",
            WhatsappMensagem.evento_sistema.is_(None),
        )
        .order_by(desc(WhatsappMensagem.created_at), desc(WhatsappMensagem.id))
        .first()
    )


def _referencia_inatividade_cliente(db: Session, chat: WhatsappChat) -> datetime | None:
    """
    Momento a partir do qual o silêncio conta para inatividade.

    Conta desde a **última mensagem relevante** (inbound do cliente **ou** outbound
    humana do atendente), desde que já exista pelo menos uma outbound humana
    (não dispara na fila / só com auto_assumido/BOT).

    Comentários internos e eventos de sistema não contam como atividade.
    """
    last_out = _ultima_outbound_humana(db, chat.id)
    if not last_out or last_out.created_at is None:
        return None

    last_in = (
        _mensagens_relevantes_q(db, chat.id)
        .filter(WhatsappMensagem.direcao == "inbound")
        .order_by(desc(WhatsappMensagem.created_at), desc(WhatsappMensagem.id))
        .first()
    )

    candidatos: list[datetime] = [last_out.created_at]
    if last_in is not None and last_in.created_at is not None:
        candidatos.append(last_in.created_at)

    retomada = getattr(chat, "inatividade_retomada_em", None)
    if retomada is not None:
        candidatos.append(retomada)

    return max(candidatos)


def _minutos_desde(ref: datetime | None, now: datetime) -> float:
    if ref is None:
        return 0.0
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return max(0.0, (now - ref).total_seconds() / 60.0)


def _normalizar_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _aviso_ja_enviado_no_ciclo(db: Session, chat_id: int, referencia: datetime) -> bool:
    """Evita reenvio do aviso quando vários workers processam o mesmo chat em paralelo."""
    ref = _normalizar_utc(referencia)
    return (
        db.query(WhatsappMensagem.id)
        .filter(
            WhatsappMensagem.chat_id == chat_id,
            WhatsappMensagem.evento_sistema == "auto_inativ_aviso",
            WhatsappMensagem.created_at >= ref,
        )
        .limit(1)
        .first()
        is not None
    )


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
    evento_sistema: str,
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
        logger.warning("Auto-msg %s falhou (chat=%s): %s", evento_sistema, chat.protocolo, err)
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
    db.flush()
    return True


def _encerrar_por_inatividade(db: Session, chat: WhatsappChat, st: WhatsappSettings) -> None:
    from app.services.whatsapp_avaliacao import finalizar_atendimento_whatsapp

    finalizar_atendimento_whatsapp(db, chat, st, evento_encerrado="auto_encerrado_inatividade")


def _processar_chat_inatividade(
    db: Session,
    chat: WhatsappChat,
    st: WhatsappSettings,
    now: datetime,
) -> bool:
    """Retorna True se alterou algo no chat (mensagem ou encerramento)."""
    if chat.estado != "em_atendimento":
        return False

    if getattr(chat, "inatividade_pausada", False):
        return False

    aviso_min = int(getattr(st, "inativ_aviso_minutos", 0) or 0)
    pos_aviso_min = int(getattr(st, "inativ_encerramento_apos_aviso_minutos", 0) or 0)
    if aviso_min < 1 or pos_aviso_min < 1:
        return False

    last = _ultima_mensagem_relevante(db, chat.id)
    if last and last.evento_sistema == "auto_inativ_aviso":
        if _minutos_desde(last.created_at, now) >= pos_aviso_min:
            _encerrar_por_inatividade(db, chat, st)
            return True
        return False

    referencia = _referencia_inatividade_cliente(db, chat)
    if referencia is None:
        return False

    if _minutos_desde(referencia, now) < aviso_min:
        return False

    if _aviso_ja_enviado_no_ciclo(db, chat.id, referencia):
        return False

    if not bool(getattr(st, "auto_msg_inativ_aviso_ativa", True)):
        _encerrar_por_inatividade(db, chat, st)
        return True

    if not _evolution_configurada(st):
        return False

    raw = (getattr(st, "auto_msg_inativ_aviso_texto", "") or "").strip() or DEFAULT_AUTO_MSG_INATIV_AVISO
    txt = _render_template(raw, db=db, chat=chat, st=st)
    if not txt:
        return False
    return _enviar_texto_sistema(db, chat=chat, st=st, texto=txt, evento_sistema="auto_inativ_aviso")


def process_whatsapp_inactivity_closures(db: Session, *, limit: int = 200) -> int:
    """
    Verifica chats em atendimento e envia aviso ou encerra por inatividade do cliente.
    Retorna quantidade de chats alterados.

    Usa lock de linha (FOR UPDATE) e commit por chat para evitar mensagens duplicadas
    quando Gunicorn roda N workers, cada um com thread de inatividade.
    """
    st = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if not st or not bool(getattr(st, "inativ_encerramento_ativa", False)):
        return 0
    if not _evolution_configurada(st):
        return 0

    now = datetime.now(timezone.utc)
    chat_ids = [
        row[0]
        for row in (
            db.query(WhatsappChat.id)
            .filter(WhatsappChat.estado == "em_atendimento")
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
                .filter(WhatsappChat.id == chat_id, WhatsappChat.estado == "em_atendimento")
                .with_for_update()
                .first()
            )
            if not chat:
                db.rollback()
                continue
            if _processar_chat_inatividade(db, chat, st, now):
                db.commit()
                alterados += 1
            else:
                db.rollback()
        except Exception as exc:
            db.rollback()
            logger.warning("Inatividade WhatsApp (chat=%s): %s", chat_id, exc)
    return alterados
