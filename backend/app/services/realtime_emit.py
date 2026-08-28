"""Emissão SSE após commit — tickets e chats (#265)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.core.setor_scope import ids_setores_mesmo_nome, ids_setores_visiveis_atendente
from app.core.tenant_context import effective_tenant_id
from app.models.atendente import Atendente
from app.models.setor import Setor
from app.models.ticket import Ticket
from app.models.whatsapp_chat import WhatsappChat
from app.models.portal_chat import PortalChat
from app.services.realtime_hub import publish_to_atendente

logger = logging.getLogger(__name__)

_main_loop: asyncio.AbstractEventLoop | None = None


def register_realtime_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def _schedule(coro) -> None:
    loop = _main_loop
    if loop is None or not loop.is_running():
        try:
            asyncio.run(coro)
        except RuntimeError:
            logger.debug("SSE: loop principal indisponível; evento descartado")
        return
    asyncio.run_coroutine_threadsafe(coro, loop)


async def _publish_many(atendente_ids: Iterable[int], event_type: str, payload: dict[str, Any]) -> None:
    seen: set[int] = set()
    for aid in atendente_ids:
        if aid in seen:
            continue
        seen.add(aid)
        await publish_to_atendente(aid, event_type, payload)


def _publish_to_atendentes(atendente_ids: Iterable[int], event_type: str, payload: dict[str, Any]) -> None:
    ids = list(atendente_ids)
    if not ids:
        return
    _schedule(_publish_many(ids, event_type, payload))


def _pode_ver_chat(db: Session, atendente: Atendente, chat: WhatsappChat) -> bool:
    if atendente.role == "admin":
        return True
    if chat.atendente_id == atendente.id:
        return True
    vis = ids_setores_visiveis_atendente(db, atendente)
    if chat.setor_id is None:
        return chat.estado == "aguardando_atendente"
    if chat.estado in ("aguardando_atendente", "encerrado", "aguardando_avaliacao"):
        return chat.setor_id in vis
    return False


def _pode_ver_ticket(db: Session, atendente: Atendente, ticket: Ticket) -> bool:
    if atendente.role == "admin":
        return True
    vis = ids_setores_visiveis_atendente(db, atendente)
    return ticket.setor_id in vis


def _ids_atendentes_ativos(db: Session) -> list[Atendente]:
    tenant_id = effective_tenant_id()
    return (
        db.query(Atendente)
        .filter(Atendente.ativo.is_(True), Atendente.tenant_id == tenant_id)
        .all()
    )


def _ids_atendentes_por_setor(db: Session, setor_id: int) -> set[int]:
    alvo_ids = list(ids_setores_mesmo_nome(db, setor_id))
    q = (
        db.query(Atendente)
        .join(Atendente.setores)
        .filter(Setor.id.in_(alvo_ids), Atendente.ativo.is_(True))
        .distinct()
    )
    ids = {a.id for a in q.all()}
    admins = (
        db.query(Atendente)
        .filter(Atendente.role == "admin", Atendente.ativo.is_(True))
        .all()
    )
    ids.update(a.id for a in admins)
    return ids


def ids_atendentes_acesso_chat(db: Session, chat: WhatsappChat) -> set[int]:
    return {a.id for a in _ids_atendentes_ativos(db) if _pode_ver_chat(db, a, chat)}


def ids_atendentes_chat_fila(db: Session, chat: WhatsappChat) -> set[int]:
    if chat.setor_id is None:
        return {a.id for a in _ids_atendentes_ativos(db)}
    return _ids_atendentes_por_setor(db, chat.setor_id)


def _pode_ver_portal_chat(db: Session, atendente: Atendente, chat: PortalChat) -> bool:
    from app.services.portal_chat import pode_ver_portal_chat

    return pode_ver_portal_chat(db, atendente, chat)


def ids_atendentes_acesso_portal_chat(db: Session, chat: PortalChat) -> set[int]:
    return {a.id for a in _ids_atendentes_ativos(db) if _pode_ver_portal_chat(db, a, chat)}


def ids_atendentes_portal_chat_fila(db: Session, chat: PortalChat) -> set[int]:
    if chat.setor_id is None:
        return {a.id for a in _ids_atendentes_ativos(db)}
    return _ids_atendentes_por_setor(db, chat.setor_id)


def ids_atendentes_ticket_mensagem(
    db: Session,
    ticket: Ticket,
    *,
    exclude_atendente_id: int | None = None,
) -> set[int]:
    ids = {a.id for a in _ids_atendentes_ativos(db) if _pode_ver_ticket(db, a, ticket)}
    if exclude_atendente_id is not None:
        ids.discard(exclude_atendente_id)
    return ids


def ids_atendentes_ticket_fila(db: Session, ticket: Ticket) -> set[int]:
    if ticket.atendente_id is not None or ticket.fechado_em is not None:
        return set()
    return _ids_atendentes_por_setor(db, ticket.setor_id)


def ids_atendentes_sla_ticket(db: Session, ticket: Ticket) -> set[int]:
    """Responsável + atendentes/admins do setor para alertas SLA."""
    ids = _ids_atendentes_por_setor(db, ticket.setor_id)
    if ticket.atendente_id is not None:
        ids.add(ticket.atendente_id)
    return ids


def emit_ticket_sla_alerta(
    db: Session,
    ticket: Ticket,
    *,
    meta: str,
    evento: str,
    meta_label: str,
    evento_label: str,
    atendente_ids: set[int],
) -> None:
    payload = {
        "ticket_id": ticket.id,
        "protocolo": ticket.protocolo,
        "assunto": ticket.assunto,
        "meta": meta,
        "evento": evento,
        "meta_label": meta_label,
        "evento_label": evento_label,
    }
    _publish_to_atendentes(atendente_ids, "ticket.sla_alerta", payload)
    _emit_notificacao_after_counter_change(db)


def emit_notificacao_contagem(db: Session, atendente_ids: Iterable[int]) -> None:
    """Publica contadores personalizados por atendente (#266)."""
    from app.api.notificacoes import build_notificacao_resumo

    seen: set[int] = set()
    for aid in atendente_ids:
        if aid in seen:
            continue
        seen.add(aid)
        atendente = (
            db.query(Atendente)
            .filter(Atendente.id == aid, Atendente.ativo.is_(True))
            .first()
        )
        if not atendente:
            continue
        payload = build_notificacao_resumo(db, atendente).model_dump(mode="json")
        _publish_to_atendentes([atendente.id], "notificacao.contagem", payload)


def emit_notificacao_contagem_all(db: Session) -> None:
    """Recalcula e envia contadores a todos os atendentes ativos."""
    emit_notificacao_contagem(db, [a.id for a in _ids_atendentes_ativos(db)])


def _emit_notificacao_after_counter_change(db: Session) -> None:
    emit_notificacao_contagem_all(db)


def emit_notificacao_after_counter_change(db: Session) -> None:
    """API pública para recalcular contadores SSE após mudanças operacionais."""
    _emit_notificacao_after_counter_change(db)


def _enfileirar_web_push(**kwargs) -> None:
    try:
        from app.services.web_push_outbox import enfileirar_para_atendentes

        enfileirar_para_atendentes(**kwargs)
    except Exception:
        logger.exception("Web Push: falha ao enfileirar")


def emit_chat_mensagem(
    db: Session,
    chat: WhatsappChat,
    mensagem_payload: dict[str, Any],
    *,
    exclude_atendente_id: int | None = None,
) -> None:
    recipients = ids_atendentes_acesso_chat(db, chat)
    if exclude_atendente_id is not None:
        recipients.discard(exclude_atendente_id)
    payload = {"chat_id": chat.id, "mensagem": mensagem_payload}
    _publish_to_atendentes(recipients, "chat.mensagem", payload)
    _emit_notificacao_after_counter_change(db)
    if chat.atendente_id and chat.estado == "em_atendimento":
        direcao = (mensagem_payload or {}).get("direcao")
        if direcao == "inbound":
            nome = chat.cliente_nome or "WhatsApp"
            _enfileirar_web_push(
                atendente_ids={chat.atendente_id},
                event_type="chat.mensagem",
                entity_id=int((mensagem_payload or {}).get("id") or chat.id),
                titulo=f"WhatsApp · {nome}",
                url_path="/chat/atendendo",
                corpo=str((mensagem_payload or {}).get("corpo") or "Nova mensagem")[:180],
                exclude_atendente_id=exclude_atendente_id,
            )


def emit_chat_fila(
    db: Session,
    chat: WhatsappChat,
    *,
    chat_payload: dict[str, Any] | None = None,
    estado_anterior: str | None = None,
) -> None:
    recipients = ids_atendentes_chat_fila(db, chat)
    if chat.atendente_id is not None:
        recipients.add(chat.atendente_id)
    payload: dict[str, Any] = {
        "chat_id": chat.id,
        "estado": chat.estado,
        "estado_anterior": estado_anterior,
    }
    if chat_payload is not None:
        payload["chat"] = chat_payload
    _publish_to_atendentes(recipients, "chat.fila", payload)
    _emit_notificacao_after_counter_change(db)
    if chat.estado == "aguardando_atendente":
        nome = (chat_payload or {}).get("cliente_nome") or chat.cliente_nome or "cliente"
        _enfileirar_web_push(
            atendente_ids=recipients,
            event_type="chat.fila",
            entity_id=chat.id,
            titulo="Cliente na fila WhatsApp",
            url_path="/chat/espera",
            corpo=str(nome)[:180],
        )


def emit_ticket_mensagem(
    db: Session,
    ticket: Ticket,
    mensagem_payload: dict[str, Any],
    *,
    exclude_atendente_id: int | None = None,
    emit_notificacao: bool = True,
) -> None:
    recipients = ids_atendentes_ticket_mensagem(
        db, ticket, exclude_atendente_id=exclude_atendente_id
    )
    payload = {"ticket_id": ticket.id, "mensagem": mensagem_payload}
    _publish_to_atendentes(recipients, "ticket.mensagem", payload)
    if emit_notificacao:
        _emit_notificacao_after_counter_change(db)
    if ticket.atendente_id:
        _enfileirar_web_push(
            atendente_ids={ticket.atendente_id},
            event_type="ticket.mensagem",
            entity_id=int((mensagem_payload or {}).get("id") or ticket.id),
            titulo=f"Ticket {ticket.protocolo}",
            url_path="/tickets",
            corpo=str((mensagem_payload or {}).get("corpo") or ticket.assunto or "Nova mensagem")[:180],
            exclude_atendente_id=exclude_atendente_id,
        )


def emit_ticket_fila(db: Session, ticket: Ticket) -> None:
    recipients = ids_atendentes_ticket_fila(db, ticket)
    if not recipients:
        return
    payload = {
        "ticket_id": ticket.id,
        "setor_id": ticket.setor_id,
        "protocolo": ticket.protocolo,
    }
    _publish_to_atendentes(recipients, "ticket.fila", payload)
    _emit_notificacao_after_counter_change(db)
    _enfileirar_web_push(
        atendente_ids=recipients,
        event_type="ticket.fila",
        entity_id=ticket.id,
        titulo="Chamado na fila",
        url_path="/tickets",
        corpo=str(ticket.protocolo or ticket.assunto or "")[:180],
    )


def emit_chat_mensagem_from_models(
    db: Session,
    chat: WhatsappChat,
    mensagem: Any,
    *,
    exclude_atendente_id: int | None = None,
) -> None:
    from app.api.whatsapp_chats import _mensagem_read

    # Flags de permissão são por visualizador — omitir no broadcast SSE
    # para não sobrescrever pode_editar / pode_apagar no cliente do responsável.
    payload = _mensagem_read(mensagem).model_dump(mode="json")
    payload.pop("pode_editar", None)
    payload.pop("pode_apagar_para_todos", None)
    emit_chat_mensagem(
        db,
        chat,
        payload,
        exclude_atendente_id=exclude_atendente_id,
    )


def emit_chat_fila_from_model(
    db: Session,
    chat: WhatsappChat,
    *,
    estado_anterior: str | None = None,
) -> None:
    from app.api.whatsapp_chats import _chat_read

    emit_chat_fila(
        db,
        chat,
        chat_payload=_chat_read(db, chat).model_dump(mode="json"),
        estado_anterior=estado_anterior,
    )


def emit_portal_chat_mensagem(
    db: Session,
    chat: PortalChat,
    mensagem_payload: dict[str, Any],
    *,
    exclude_atendente_id: int | None = None,
) -> None:
    recipients = ids_atendentes_acesso_portal_chat(db, chat)
    if exclude_atendente_id is not None:
        recipients.discard(exclude_atendente_id)
    payload = {"chat_id": chat.id, "mensagem": mensagem_payload}
    _publish_to_atendentes(recipients, "portal.chat.mensagem", payload)
    _emit_notificacao_after_counter_change(db)
    if chat.atendente_id and chat.estado == "em_atendimento":
        direcao = (mensagem_payload or {}).get("direcao")
        if direcao == "inbound":
            _enfileirar_web_push(
                atendente_ids={chat.atendente_id},
                event_type="portal.chat.mensagem",
                entity_id=int((mensagem_payload or {}).get("id") or chat.id),
                titulo="Portal · nova mensagem",
                url_path="/chat/atendendo",
                corpo=str((mensagem_payload or {}).get("corpo") or "Nova mensagem")[:180],
                exclude_atendente_id=exclude_atendente_id,
            )


def emit_portal_chat_fila(
    db: Session,
    chat: PortalChat,
    *,
    chat_payload: dict[str, Any] | None = None,
    estado_anterior: str | None = None,
) -> None:
    recipients = ids_atendentes_portal_chat_fila(db, chat)
    if chat.atendente_id is not None:
        recipients.add(chat.atendente_id)
    payload: dict[str, Any] = {
        "chat_id": chat.id,
        "estado": chat.estado,
        "estado_anterior": estado_anterior,
    }
    if chat_payload is not None:
        payload["chat"] = chat_payload
    _publish_to_atendentes(recipients, "portal.chat.fila", payload)
    _emit_notificacao_after_counter_change(db)
    if chat.estado == "aguardando_atendente":
        _enfileirar_web_push(
            atendente_ids=recipients,
            event_type="portal.chat.fila",
            entity_id=chat.id,
            titulo="Cliente na fila do portal",
            url_path="/chat/espera",
            corpo="Novo atendimento no portal",
        )


def emit_portal_chat_mensagem_from_models(
    db: Session,
    chat: PortalChat,
    mensagem: Any,
    *,
    exclude_atendente_id: int | None = None,
) -> None:
    from app.services.portal_chat import serializar_mensagem

    emit_portal_chat_mensagem(
        db,
        chat,
        serializar_mensagem(mensagem),
        exclude_atendente_id=exclude_atendente_id,
    )


def emit_portal_chat_fila_from_model(
    db: Session,
    chat: PortalChat,
    *,
    estado_anterior: str | None = None,
) -> None:
    from app.services.portal_chat import serializar_chat

    emit_portal_chat_fila(
        db,
        chat,
        chat_payload=serializar_chat(db, chat),
        estado_anterior=estado_anterior,
    )


def emit_ticket_mensagem_from_model(
    db: Session,
    ticket: Ticket,
    mensagem: Any,
    *,
    exclude_atendente_id: int | None = None,
    emit_notificacao: bool = True,
) -> None:
    from app.api.tickets import _mensagem_para_read

    emit_ticket_mensagem(
        db,
        ticket,
        _mensagem_para_read(mensagem).model_dump(mode="json"),
        exclude_atendente_id=exclude_atendente_id,
        emit_notificacao=emit_notificacao,
    )


def ids_destinatarios_chat_interno_mensagem(
    db: Session,
    conversa: Any,
    *,
    exclude_atendente_id: int | None = None,
) -> set[int]:
    from app.models.chat_interno import (
        TIPO_CONVERSA_DIRETA,
        TIPO_CONVERSA_GRUPO,
        TIPO_CONVERSA_SETOR,
        ConversaInternaParticipante,
    )

    if conversa.tipo in (TIPO_CONVERSA_DIRETA, TIPO_CONVERSA_GRUPO):
        rows = (
            db.query(ConversaInternaParticipante.atendente_id)
            .filter(ConversaInternaParticipante.conversa_id == conversa.id)
            .all()
        )
        ids = {aid for (aid,) in rows}
    elif conversa.tipo == TIPO_CONVERSA_SETOR and conversa.setor_id is not None:
        ids = _ids_atendentes_por_setor(db, conversa.setor_id)
    else:
        ids = set()

    if exclude_atendente_id is not None:
        ids.discard(exclude_atendente_id)
    return ids


def emit_chat_interno_mensagem(
    db: Session,
    conversa: Any,
    mensagem: Any,
    *,
    exclude_atendente_id: int | None = None,
) -> None:
    """Nova mensagem no chat interno — direta ou canal de setor (IC-03)."""
    from app.services.chat_interno import preview_mensagem

    preview = preview_mensagem(mensagem)
    if len(preview) > 80:
        preview = preview[:80] + "…"

    recipients = ids_destinatarios_chat_interno_mensagem(
        db,
        conversa,
        exclude_atendente_id=exclude_atendente_id,
    )
    tipo_midia = getattr(mensagem, "tipo_midia", None) or "texto"
    payload = {
        "conversa_id": conversa.id,
        "tipo": conversa.tipo,
        "setor_id": conversa.setor_id,
        "remetente_id": getattr(mensagem, "atendente_id", None),
        "corpo_preview": preview,
        "mensagem_id": getattr(mensagem, "id", None),
        "tipo_midia": tipo_midia,
        "midia_disponivel": bool(getattr(mensagem, "storage_key", None)),
    }
    _publish_to_atendentes(recipients, "chat.interno.mensagem", payload)
    _emit_notificacao_after_counter_change(db)


def emit_chat_interno_lido(
    db: Session,
    conversa: Any,
    leitor_atendente_id: int,
) -> None:
    """Participante leu a conversa — atualiza ticks de leitura para remetentes."""
    recipients = ids_destinatarios_chat_interno_mensagem(
        db,
        conversa,
        exclude_atendente_id=leitor_atendente_id,
    )
    if not recipients:
        return
    payload = {
        "conversa_id": conversa.id,
        "leitor_atendente_id": leitor_atendente_id,
    }
    _publish_to_atendentes(recipients, "chat.interno.lido", payload)


def emit_chat_interno_mensagem_atualizada(
    db: Session,
    conversa: Any,
    mensagem: Any,
    *,
    acao: str,
) -> None:
    """Mensagem editada, apagada ou com reação alterada."""
    recipients = ids_destinatarios_chat_interno_mensagem(db, conversa)
    payload = {
        "conversa_id": conversa.id,
        "mensagem_id": getattr(mensagem, "id", None),
        "acao": acao,
    }
    _publish_to_atendentes(recipients, "chat.interno.mensagem.atualizada", payload)
    if acao in {"editada", "apagada"}:
        _emit_notificacao_after_counter_change(db)


def emit_ponto_he_atualizada(
    db: Session,
    *,
    tenant_id: int,
    he_id: int,
    atendente_id: int,
    estado: str,
    origem: str | None = None,
) -> None:
    """Pedido/decisão/concessão de hora extra (#982) — admins + colaborador."""
    ids = {
        a.id
        for a in db.query(Atendente)
        .filter(
            Atendente.tenant_id == tenant_id,
            Atendente.role == "admin",
            Atendente.ativo.is_(True),
        )
        .all()
    }
    ids.add(atendente_id)
    payload = {
        "he_id": he_id,
        "atendente_id": atendente_id,
        "estado": estado,
        "origem": origem,
    }
    _publish_to_atendentes(ids, "ponto.he_atualizada", payload)
    # Contagem do sino (HE pendentes) para admins
    emit_notificacao_contagem(db, ids)
