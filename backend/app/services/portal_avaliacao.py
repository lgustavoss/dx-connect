"""Avaliação 1–5 do atendimento portal ao encerrar o chat (mesma lógica do WhatsApp, sem Evolution)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.portal_chat import PortalChat, PortalMensagem
from app.models.whatsapp_chat import WhatsappSettings
from app.services.portal_auto_messages import adicionar_mensagem_sistema, render_portal_template
from app.services.whatsapp_auto_messages import (
    DEFAULT_AUTO_MSG_AVALIACAO,
    DEFAULT_AUTO_MSG_AVALIACAO_OBRIGADO,
    DEFAULT_AUTO_MSG_AVALIACAO_SEM_NOTA,
    DEFAULT_AUTO_MSG_ENCERRADO,
)
from app.services.whatsapp_avaliacao import avaliacao_habilitada, parse_nota_avaliacao


def _whatsapp_settings(db: Session) -> WhatsappSettings | None:
    return db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()


def _enviar_encerrado(db: Session, chat: PortalChat, st: WhatsappSettings, *, evento_sistema: str) -> None:
    if not bool(getattr(st, "auto_msg_encerrado_ativa", True)):
        return
    raw = (getattr(st, "auto_msg_encerrado_texto", "") or "").strip() or DEFAULT_AUTO_MSG_ENCERRADO
    txt = render_portal_template(raw, db=db, chat=chat, st=st)
    if txt:
        adicionar_mensagem_sistema(db, chat=chat, texto=txt, evento_sistema=evento_sistema, prefixo_bot=True)


def _encerrar_sem_avaliacao(
    db: Session,
    chat: PortalChat,
    st: WhatsappSettings,
    *,
    msg_inbound: PortalMensagem | None = None,
) -> None:
    if msg_inbound is not None:
        msg_inbound.evento_sistema = "avaliacao_cliente_invalida"
    chat.estado = "encerrado"
    chat.avaliacao_nota = None
    chat.avaliacao_respondida_at = None
    db.flush()
    raw = DEFAULT_AUTO_MSG_AVALIACAO_SEM_NOTA
    txt = render_portal_template(raw, db=db, chat=chat, st=st)
    if txt:
        adicionar_mensagem_sistema(
            db,
            chat=chat,
            texto=txt,
            evento_sistema="auto_avaliacao_sem_nota",
            prefixo_bot=True,
        )


def finalizar_atendimento_portal(
    db: Session,
    chat: PortalChat,
    st: WhatsappSettings | None,
    *,
    evento_encerrado: str = "auto_encerrado",
) -> None:
    """Encerra o atendimento para o atendente; com avaliação ativa aguarda nota do visitante."""
    chat.encerramento_at = datetime.now(timezone.utc)
    db.flush()

    if not st:
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
            txt = render_portal_template(raw, db=db, chat=chat, st=st)
            if txt:
                adicionar_mensagem_sistema(
                    db,
                    chat=chat,
                    texto=txt,
                    evento_sistema="auto_avaliacao_solicitacao",
                    prefixo_bot=True,
                )
        return

    chat.estado = "encerrado"
    _enviar_encerrado(db, chat, st, evento_sistema=evento_encerrado)


def processar_resposta_avaliacao_portal(
    db: Session,
    chat: PortalChat,
    st: WhatsappSettings | None,
    texto: str,
    *,
    tipo_midia: str = "texto",
    msg_inbound: PortalMensagem | None = None,
) -> None:
    """Processa mensagem inbound em chat aguardando_avaliacao."""
    if chat.estado != "aguardando_avaliacao" or not st:
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
        txt = render_portal_template(raw, db=db, chat=chat, st=st)
        if txt:
            adicionar_mensagem_sistema(
                db,
                chat=chat,
                texto=txt,
                evento_sistema="auto_avaliacao_obrigado",
                prefixo_bot=True,
            )
