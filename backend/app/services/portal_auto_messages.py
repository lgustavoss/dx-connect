"""Mensagens automáticas do chat portal — mesmos templates do WhatsApp, entrega in-app."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.atendente import Atendente
from app.models.portal_chat import PortalChat, PortalMensagem
from app.models.whatsapp_chat import WhatsappSettings
from app.services.whatsapp_auto_messages import (
    DEFAULT_AUTO_MSG_ASSUMIDO,
    DEFAULT_AUTO_MSG_ESPERA,
    resolver_nome_empresa_para_template,
)


def _fmt_data_abertura(dt: datetime | None, tz: ZoneInfo) -> str:
    if not dt:
        dt = datetime.now(tz)
    try:
        local = dt.astimezone(tz)
    except Exception:
        local = dt
    return local.strftime("%d/%m/%Y %H:%M")


def render_portal_template(
    template: str,
    *,
    db: Session,
    chat: PortalChat,
    st: WhatsappSettings | None,
    atendente_nome: str | None = None,
) -> str:
    t = (template or "").strip()
    if not t:
        return ""
    nome = (chat.visitante_nome or "").strip() or "Cliente"
    nome_atendente = (atendente_nome or "").strip() or "BOT"
    nome_empresa = resolver_nome_empresa_para_template(db)
    telefone = (chat.visitante_email or "").strip() or "—"
    tzname = (getattr(st, "horario_timezone", None) or "America/Sao_Paulo").strip() or "America/Sao_Paulo"
    try:
        tz = ZoneInfo(tzname)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("America/Sao_Paulo")
    data_abertura = _fmt_data_abertura(getattr(chat, "created_at", None), tz)
    return (
        t.replace("{nome}", nome)
        .replace("{atendente}", nome_atendente)
        .replace("{protocolo}", chat.protocolo)
        .replace("{telefone}", telefone)
        .replace("{{nome_cliente}}", nome)
        .replace("{{atendente}}", nome_atendente)
        .replace("{{protocolo}}", chat.protocolo)
        .replace("{{telefone}}", telefone)
        .replace("{{nome_empresa}}", nome_empresa)
        .replace("{{data_abertura}}", data_abertura)
    )


def _whatsapp_settings(db: Session) -> WhatsappSettings | None:
    return db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()


def adicionar_mensagem_sistema(
    db: Session,
    *,
    chat: PortalChat,
    texto: str,
    evento_sistema: str | None,
    atendente: Atendente | None = None,
    prefixo_bot: bool = False,
) -> PortalMensagem | None:
    texto_eff = (texto or "").strip()
    if not texto_eff:
        return None
    if evento_sistema:
        exist = (
            db.query(PortalMensagem)
            .filter(PortalMensagem.chat_id == chat.id, PortalMensagem.evento_sistema == evento_sistema)
            .first()
        )
        if exist:
            return exist
    if atendente is not None and evento_sistema in (None, "auto_assumido"):
        nome = (atendente.nome or "").strip()
        if nome and not texto_eff.startswith("["):
            texto_eff = f"[ {nome} ]: {texto_eff}"
    elif prefixo_bot or evento_sistema is not None:
        if not texto_eff.startswith("["):
            texto_eff = f"[ BOT ]: {texto_eff}"
    msg = PortalMensagem(
        chat_id=chat.id,
        direcao="outbound",
        corpo=texto_eff,
        tipo_midia="texto",
        atendente_id=atendente.id if atendente and evento_sistema == "auto_assumido" else None,
        evento_sistema=evento_sistema,
    )
    db.add(msg)
    db.flush()
    return msg


def try_auto_msg_espera(db: Session, chat: PortalChat) -> PortalMensagem | None:
    st = _whatsapp_settings(db)
    if not st or not bool(getattr(st, "auto_msg_espera_ativa", True)):
        return None
    raw = (getattr(st, "auto_msg_espera_texto", "") or "").strip() or DEFAULT_AUTO_MSG_ESPERA
    txt = render_portal_template(raw, db=db, chat=chat, st=st)
    if not txt:
        return None
    return adicionar_mensagem_sistema(db, chat=chat, texto=txt, evento_sistema="auto_espera", prefixo_bot=True)


def try_auto_msg_assumido(db: Session, chat: PortalChat, atendente: Atendente) -> PortalMensagem | None:
    st = _whatsapp_settings(db)
    if not st or not bool(getattr(st, "auto_msg_assumido_ativa", True)):
        return None
    raw = (getattr(st, "auto_msg_assumido_texto", "") or "").strip() or DEFAULT_AUTO_MSG_ASSUMIDO
    txt = render_portal_template(
        raw,
        db=db,
        chat=chat,
        st=st,
        atendente_nome=(atendente.nome or "").strip() or "Atendente",
    )
    if not txt:
        return None
    return adicionar_mensagem_sistema(
        db,
        chat=chat,
        texto=txt,
        evento_sistema="auto_assumido",
        atendente=atendente,
    )
