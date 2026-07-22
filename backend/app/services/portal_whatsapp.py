"""Chats WhatsApp no portal autenticado do cliente (#603)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.portal_scope import chat_no_escopo, filtro_query_chats_portal
from app.models.funcionario_rede import FuncionarioRede
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem
from app.schemas.portal import (
    PortalWhatsappChatDetail,
    PortalWhatsappChatListItem,
    PortalWhatsappMensagemRead,
)
from app.services.whatsapp_auto_messages import EVENTOS_MENSAGEM_OCULTA_CONVERSA
from app.services.whatsapp_avaliacao import mensagem_oculta_na_conversa

EVENTOS_OCULTOS_PORTAL = EVENTOS_MENSAGEM_OCULTA_CONVERSA | frozenset(
    {
        "comentario_interno",
        "transferencia",
        "demanda_registrada",
        "demanda_escalada",
    }
)


def mensagem_visivel_no_portal(m: WhatsappMensagem) -> bool:
    ev = (getattr(m, "evento_sistema", None) or "").strip()
    if ev in EVENTOS_OCULTOS_PORTAL:
        return False
    if mensagem_oculta_na_conversa(ev or None):
        return False
    return True


def _preview(corpo: str | None) -> str | None:
    if not corpo:
        return None
    texto = corpo.strip()
    if len(texto) > 100:
        return texto[:100] + "…"
    return texto


def _ultima_mensagem_visivel(db: Session, chat_id: int) -> tuple[datetime | None, str | None]:
    rows = (
        db.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat_id)
        .order_by(WhatsappMensagem.id.desc())
        .limit(30)
        .all()
    )
    for m in rows:
        if mensagem_visivel_no_portal(m):
            return m.created_at, _preview(m.corpo)
    return None, None


def chat_para_list_item(db: Session, chat: WhatsappChat) -> PortalWhatsappChatListItem:
    ultima_em, preview = _ultima_mensagem_visivel(db, chat.id)
    emp = getattr(chat, "empresa", None)
    setor = getattr(chat, "setor", None)
    return PortalWhatsappChatListItem(
        id=chat.id,
        protocolo=chat.protocolo,
        estado=chat.estado,
        empresa_id=chat.empresa_id,
        empresa_nome=getattr(emp, "nome", None) if emp else None,
        setor_nome=getattr(setor, "nome", None) if setor else None,
        created_at=chat.created_at,
        encerramento_at=chat.encerramento_at,
        ultima_mensagem_em=ultima_em,
        ultima_mensagem_preview=preview,
    )


def chat_para_detail(db: Session, chat: WhatsappChat) -> PortalWhatsappChatDetail:
    base = chat_para_list_item(db, chat)
    return PortalWhatsappChatDetail(**base.model_dump(), encerrado=(chat.estado or "") == "encerrado")


def obter_chat_escopo(db: Session, funcionario: FuncionarioRede, chat_id: int) -> WhatsappChat:
    chat = (
        db.query(WhatsappChat)
        .options(
            joinedload(WhatsappChat.empresa),
            joinedload(WhatsappChat.setor),
        )
        .filter(WhatsappChat.id == chat_id)
        .first()
    )
    if not chat or not chat_no_escopo(db, funcionario, chat):
        raise LookupError("Atendimento não encontrado")
    return chat


def listar_chats(
    db: Session,
    funcionario: FuncionarioRede,
    *,
    situacao: str = "abertos",
    busca: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[WhatsappChat], int]:
    q = db.query(WhatsappChat).options(
        joinedload(WhatsappChat.empresa),
        joinedload(WhatsappChat.setor),
    )
    q = filtro_query_chats_portal(q, db, funcionario)
    if q is None:
        return [], 0

    sit = (situacao or "abertos").strip().lower()
    if sit == "abertos":
        q = q.filter(WhatsappChat.estado != "encerrado")
    elif sit == "encerrados":
        q = q.filter(WhatsappChat.estado == "encerrado")

    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(WhatsappChat.protocolo.ilike(term), WhatsappChat.cliente_nome.ilike(term)))

    total = q.count()
    rows = q.order_by(WhatsappChat.id.desc()).offset(offset).limit(limit).all()
    return rows, total


def mensagem_para_read(m: WhatsappMensagem) -> PortalWhatsappMensagemRead:
    midia_ok = bool(m.midia_nome_arquivo and str(m.midia_nome_arquivo).strip())
    if (m.direcao or "").strip().lower() == "inbound":
        papel: str = "voce"
        nome = "Você"
    elif m.atendente_id:
        atendente = getattr(m, "atendente", None)
        papel = "equipe"
        nome = getattr(atendente, "nome", None) or "Equipe de suporte"
    else:
        papel = "sistema"
        nome = "Sistema"
    return PortalWhatsappMensagemRead(
        id=m.id,
        direcao=m.direcao,
        corpo=m.corpo,
        tipo_midia=m.tipo_midia,
        midia_disponivel=midia_ok,
        autor_nome=nome,
        autor_papel=papel,  # type: ignore[arg-type]
        created_at=m.created_at,
    )


def listar_mensagens_visiveis(db: Session, chat: WhatsappChat) -> list[PortalWhatsappMensagemRead]:
    rows = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.chat_id == chat.id)
        .order_by(WhatsappMensagem.created_at.asc())
        .all()
    )
    return [mensagem_para_read(m) for m in rows if mensagem_visivel_no_portal(m)]


def obter_mensagem_midia(db: Session, chat: WhatsappChat, mensagem_id: int) -> WhatsappMensagem:
    m = (
        db.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.id == mensagem_id)
        .first()
    )
    if not m or not mensagem_visivel_no_portal(m) or not m.midia_nome_arquivo:
        raise LookupError("Mídia não encontrada")
    return m
