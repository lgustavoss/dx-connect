"""Regras de negócio — chat portal /kb (#468)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.setor_scope import ids_setores_visiveis_atendente
from app.models.atendente import Atendente
from app.models.kb import KbPortalSettings
from app.models.portal_chat import PortalChat, PortalChatRead as PortalChatReadRow, PortalMensagem
from app.models.whatsapp_chat import WhatsappSettings
from app.services.protocolo_mensal import gerar_protocolo_chat

VISITOR_TOKEN_HEADER = "x-portal-visitor-token"

_ESTADOS_ATIVOS = ("aguardando_atendente", "em_atendimento", "aguardando_avaliacao")


def hash_visitor_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_visitor_token() -> str:
    return secrets.token_urlsafe(32)


def _portal_settings(db: Session, tenant_id: int) -> KbPortalSettings | None:
    return db.query(KbPortalSettings).filter(KbPortalSettings.tenant_id == tenant_id).first()


def portal_chat_habilitado(db: Session, tenant_id: int) -> bool:
    row = _portal_settings(db, tenant_id)
    return bool(row and row.chat_habilitado and row.chat_setor_id)


def exigir_portal_chat_habilitado(db: Session, tenant_id: int) -> KbPortalSettings:
    row = _portal_settings(db, tenant_id)
    if not row or not row.chat_habilitado:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chat do portal desabilitado.")
    if not row.chat_setor_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat do portal sem setor configurado.",
        )
    return row


def pode_ver_portal_chat(db: Session, atendente: Atendente, chat: PortalChat) -> bool:
    if atendente.role == "admin":
        return True
    if chat.atendente_id == atendente.id:
        return True
    vis = ids_setores_visiveis_atendente(db, atendente)
    if chat.setor_id is None:
        return chat.estado == "aguardando_atendente"
    if chat.estado == "aguardando_atendente":
        return chat.setor_id in vis
    if chat.estado == "em_atendimento":
        return chat.atendente_id == atendente.id
    return chat.setor_id in vis


def exigir_acesso_portal_chat(db: Session, atendente: Atendente, chat: PortalChat) -> None:
    if not pode_ver_portal_chat(db, atendente, chat):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este chat.")


def chat_por_token(db: Session, tenant_id: int, token: str) -> PortalChat | None:
    if not token.strip():
        return None
    return (
        db.query(PortalChat)
        .filter(
            PortalChat.tenant_id == tenant_id,
            PortalChat.visitor_token_hash == hash_visitor_token(token),
        )
        .first()
    )


def criar_ou_retomar_sessao_visitante(
    db: Session,
    *,
    tenant_id: int,
    visitante_nome: str,
    visitante_email: str | None,
    token_existente: str | None,
) -> tuple[str, PortalChat, bool]:
    settings = exigir_portal_chat_habilitado(db, tenant_id)
    nome = visitante_nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome.")

    if token_existente:
        existente = chat_por_token(db, tenant_id, token_existente)
        if existente and existente.estado in _ESTADOS_ATIVOS:
            return token_existente, existente, True

    token = new_visitor_token()
    chat = PortalChat(
        tenant_id=tenant_id,
        protocolo=gerar_protocolo_chat(db),
        visitor_token_hash=hash_visitor_token(token),
        visitante_nome=nome,
        visitante_email=(visitante_email or "").strip() or None,
        estado="aguardando_atendente",
        setor_id=settings.chat_setor_id,
    )
    db.add(chat)
    db.flush()
    from app.services.portal_auto_messages import try_auto_msg_espera

    auto_espera = try_auto_msg_espera(db, chat)
    if not auto_espera:
        boas_vindas = (settings.chat_texto_boas_vindas or "").strip()
        if boas_vindas:
            db.add(
                PortalMensagem(
                    chat_id=chat.id,
                    direcao="outbound",
                    corpo=boas_vindas,
                    tipo_midia="texto",
                    atendente_id=None,
                )
            )
    return token, chat, False


def registrar_mensagem_visitante(db: Session, chat: PortalChat, corpo: str) -> PortalMensagem:
    if chat.estado == "encerrado":
        raise HTTPException(status_code=400, detail="Este atendimento foi encerrado.")
    if chat.estado == "aguardando_avaliacao":
        from app.services.portal_avaliacao import processar_resposta_avaliacao_portal

        st = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
        texto = corpo.strip()
        if not texto:
            raise HTTPException(status_code=400, detail="Mensagem vazia.")
        msg = PortalMensagem(chat_id=chat.id, direcao="inbound", corpo=texto, tipo_midia="texto")
        db.add(msg)
        db.flush()
        processar_resposta_avaliacao_portal(db, chat, st, texto, msg_inbound=msg)
        return msg
    if chat.estado not in _ESTADOS_ATIVOS:
        raise HTTPException(status_code=400, detail="Chat indisponível.")
    texto = corpo.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")
    msg = PortalMensagem(chat_id=chat.id, direcao="inbound", corpo=texto, tipo_midia="texto")
    db.add(msg)
    db.flush()
    return msg


def registrar_mensagem_atendente(
    db: Session,
    chat: PortalChat,
    atendente: Atendente,
    corpo: str,
) -> PortalMensagem:
    exigir_acesso_portal_chat(db, atendente, chat)
    if chat.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Assuma o chat antes de responder.")
    if atendente.role != "admin" and chat.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode responder.")
    texto = corpo.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")
    msg = PortalMensagem(
        chat_id=chat.id,
        direcao="outbound",
        corpo=texto,
        tipo_midia="texto",
        atendente_id=atendente.id,
    )
    db.add(msg)
    db.flush()
    return msg


def assumir_portal_chat(db: Session, chat: PortalChat, atendente: Atendente) -> str:
    exigir_acesso_portal_chat(db, atendente, chat)
    if chat.estado != "aguardando_atendente":
        raise HTTPException(status_code=400, detail="Só é possível assumir chats na fila.")
    estado_anterior = chat.estado
    chat.estado = "em_atendimento"
    chat.atendente_id = atendente.id
    chat.atendimento_inicio_at = datetime.now(timezone.utc)
    return estado_anterior


def encerrar_portal_chat(db: Session, chat: PortalChat, atendente: Atendente) -> None:
    exigir_acesso_portal_chat(db, atendente, chat)
    if chat.estado == "encerrado":
        return
    if chat.estado == "aguardando_avaliacao":
        return
    if chat.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Encerre apenas chats em atendimento.")
    if atendente.role != "admin" and chat.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode encerrar.")
    from app.services.portal_avaliacao import finalizar_atendimento_portal

    st = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    finalizar_atendimento_portal(db, chat, st)


def transferir_portal_chat(
    db: Session,
    chat: PortalChat,
    atendente: Atendente,
    *,
    setor_id: int,
    destino_atendente_id: int | None,
    setor_nome: str,
    destino: Atendente | None,
) -> str:
    """Transfere chat portal; retorna estado_anterior."""
    exigir_acesso_portal_chat(db, atendente, chat)
    if chat.estado == "encerrado":
        raise HTTPException(status_code=400, detail="Chat encerrado não pode ser transferido")
    if atendente.role != "admin" and chat.atendente_id not in (None, atendente.id):
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode transferir este chat")

    estado_anterior = chat.estado
    chat.setor_id = setor_id
    chat.atendente_id = destino.id if destino else None
    if destino:
        chat.estado = "em_atendimento"
        chat.atendimento_inicio_at = chat.atendimento_inicio_at or datetime.now(timezone.utc)
    else:
        chat.estado = "aguardando_atendente"
        chat.atendimento_inicio_at = None

    nome_origem = (atendente.nome or "").strip() or "Equipe"
    if destino:
        texto_transfer = f"Chat transferido por {nome_origem} para {destino.nome} (setor {setor_nome})."
    else:
        texto_transfer = f"Chat transferido por {nome_origem} para a fila do setor {setor_nome}."
    db.add(
        PortalMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo=f"[ TRANSFERÊNCIA / {nome_origem} ]: {texto_transfer}",
            tipo_midia="texto",
            atendente_id=atendente.id,
            evento_sistema="transferencia",
        )
    )
    return estado_anterior


def marcar_visto_portal_chat(db: Session, chat_id: int, atendente_id: int) -> None:
    now = datetime.now(timezone.utc)
    row = (
        db.query(PortalChatReadRow)
        .filter(PortalChatReadRow.chat_id == chat_id, PortalChatReadRow.atendente_id == atendente_id)
        .first()
    )
    if row:
        row.last_seen_at = now
    else:
        db.add(PortalChatReadRow(chat_id=chat_id, atendente_id=atendente_id, last_seen_at=now))


def listar_mensagens_chat(
    db: Session,
    chat_id: int,
    *,
    since_id: int | None = None,
    limit: int = 100,
) -> list[PortalMensagem]:
    q = (
        db.query(PortalMensagem)
        .options(joinedload(PortalMensagem.atendente))
        .filter(PortalMensagem.chat_id == chat_id)
    )
    if since_id is not None:
        q = q.filter(PortalMensagem.id > since_id)
    return q.order_by(PortalMensagem.id.asc()).limit(limit).all()


def _preview_corpo(corpo: str | None) -> str | None:
    if not corpo:
        return None
    texto = corpo.strip()
    if len(texto) > 80:
        return texto[:80] + "…"
    return texto


def ultima_mensagem_preview(db: Session, chat_id: int) -> str | None:
    corpo = (
        db.query(PortalMensagem.corpo)
        .filter(PortalMensagem.chat_id == chat_id)
        .order_by(PortalMensagem.id.desc())
        .limit(1)
        .scalar()
    )
    return _preview_corpo(corpo)


def serializar_mensagem(m: PortalMensagem) -> dict:
    from app.schemas.portal_chat import PortalChatMensagemRead

    midia_ok = bool(m.midia_nome_arquivo and str(m.midia_nome_arquivo).strip())
    return PortalChatMensagemRead(
        id=m.id,
        chat_id=m.chat_id,
        direcao=m.direcao,
        corpo=m.corpo,
        tipo_midia=m.tipo_midia or "texto",
        mimetype=m.mimetype,
        midia_disponivel=midia_ok,
        atendente_id=m.atendente_id,
        atendente_nome=m.atendente.nome if m.atendente else None,
        evento_sistema=m.evento_sistema,
        created_at=m.created_at,
    ).model_dump(mode="json")


def _rotulo_midia_outbound(tipo_db: str) -> str:
    return {
        "imagem": "[Imagem enviada]",
        "video": "[Vídeo enviado]",
        "audio": "[Áudio enviado]",
        "documento": "[Documento enviado]",
        "figurinha": "[Figurinha enviada]",
    }.get(tipo_db, "[Ficheiro enviado]")


def registrar_mensagem_midia_atendente(
    db: Session,
    chat: PortalChat,
    atendente: Atendente,
    *,
    tipo_midia: str,
    mimetype: str | None,
    midia_nome_arquivo: str,
    caption: str = "",
) -> PortalMensagem:
    exigir_acesso_portal_chat(db, atendente, chat)
    if chat.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Assuma o chat antes de responder.")
    if atendente.role != "admin" and chat.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode responder.")
    tipo_db = (tipo_midia or "documento").strip().lower()
    if tipo_db in ("image", "imagem"):
        tipo_db = "imagem"
    if tipo_db == "figurinha":
        corpo_eff = _rotulo_midia_outbound(tipo_db)
    else:
        cap = (caption or "").strip()
        base_legenda = cap if cap else _rotulo_midia_outbound(tipo_db)
        nome_atend = (atendente.nome or "").strip()
        corpo_eff = f"[ {nome_atend} ]: {base_legenda}" if nome_atend else base_legenda
    msg = PortalMensagem(
        chat_id=chat.id,
        direcao="outbound",
        corpo=corpo_eff,
        tipo_midia=tipo_db,
        mimetype=mimetype,
        midia_nome_arquivo=midia_nome_arquivo,
        atendente_id=atendente.id,
    )
    db.add(msg)
    db.flush()
    return msg


def registrar_mensagem_midia_visitante(
    db: Session,
    chat: PortalChat,
    *,
    tipo_midia: str,
    mimetype: str | None,
    midia_nome_arquivo: str,
    caption: str = "",
) -> PortalMensagem:
    if chat.estado == "encerrado":
        raise HTTPException(status_code=400, detail="Este atendimento foi encerrado.")
    if chat.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Só é possível enviar mídia durante o atendimento.")
    tipo_db = (tipo_midia or "documento").strip().lower()
    if tipo_db in ("image", "imagem"):
        tipo_db = "imagem"
    cap = (caption or "").strip()
    corpo_eff = cap if cap else _rotulo_midia_outbound(tipo_db)
    msg = PortalMensagem(
        chat_id=chat.id,
        direcao="inbound",
        corpo=corpo_eff,
        tipo_midia=tipo_db,
        mimetype=mimetype,
        midia_nome_arquivo=midia_nome_arquivo,
    )
    db.add(msg)
    db.flush()
    return msg


def serializar_chat(db: Session, c: PortalChat) -> dict:
    from app.schemas.portal_chat import PortalChatRead

    return PortalChatRead(
        id=c.id,
        protocolo=c.protocolo,
        visitante_nome=c.visitante_nome,
        visitante_email=c.visitante_email,
        estado=c.estado,
        setor_id=c.setor_id,
        setor_nome=c.setor.nome if c.setor else None,
        atendente_id=c.atendente_id,
        atendente_nome=c.atendente.nome if c.atendente else None,
        created_at=c.created_at,
        atendimento_inicio_at=c.atendimento_inicio_at,
        encerramento_at=c.encerramento_at,
        ultima_mensagem_preview=ultima_mensagem_preview(db, c.id),
    ).model_dump(mode="json")
