"""API atendente — chat ao vivo do portal /kb (#468)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.auth import obter_atendente_atual
from app.core.setor_scope import ids_setores_visiveis_atendente
from app.database import get_db
from app.models.atendente import Atendente
from app.models.portal_chat import PortalChat, PortalChatRead as PortalChatReadModel, PortalMensagem
from app.models.setor import Setor
from app.schemas.portal_chat import (
    PortalChatDemandaCreate,
    PortalChatDemandaRead,
    PortalChatDemandaUpdate,
    PortalChatMensagemCreate,
    PortalChatMensagemRead,
    PortalChatRead,
    PortalTransferirChatBody,
)
from app.services.portal_auto_messages import try_auto_msg_assumido
from app.services.portal_chat import (
    assumir_portal_chat,
    encerrar_portal_chat,
    exigir_acesso_portal_chat,
    listar_mensagens_chat,
    marcar_visto_portal_chat,
    pode_ver_portal_chat,
    registrar_mensagem_atendente,
    registrar_mensagem_midia_atendente,
    transferir_portal_chat,
)
from app.services.realtime_emit import emit_portal_chat_fila_from_model, emit_portal_chat_mensagem_from_models
from app.services.whatsapp_avaliacao import mensagem_oculta_na_conversa
from app.services.whatsapp_media_storage import caminho_absoluto_arquivo, gravar_bytes_em_disco

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal-chats", tags=["portal-chats"])

_CHAT_LOAD_OPTIONS = (
    joinedload(PortalChat.setor),
    joinedload(PortalChat.atendente),
)


def _preview_corpo(corpo: str | None) -> str | None:
    if not corpo:
        return None
    texto = corpo.strip()
    if len(texto) > 80:
        return texto[:80] + "…"
    return texto


def _ultima_mensagem_preview(db: Session, chat_id: int) -> str | None:
    corpo = (
        db.query(PortalMensagem.corpo)
        .filter(PortalMensagem.chat_id == chat_id)
        .order_by(PortalMensagem.id.desc())
        .limit(1)
        .scalar()
    )
    return _preview_corpo(corpo)


def _nao_lidas_portal(
    db: Session, c: PortalChat, atendente_id: int
) -> tuple[int, datetime | None, int | None]:
    row = (
        db.query(PortalChatReadModel.last_seen_at, PortalChatReadModel.last_seen_mensagem_id)
        .filter(
            PortalChatReadModel.chat_id == c.id,
            PortalChatReadModel.atendente_id == atendente_id,
        )
        .first()
    )
    ls = row[0] if row else None
    cursor_id = row[1] if row else None
    q = db.query(func.count(PortalMensagem.id)).filter(
        PortalMensagem.chat_id == c.id,
        PortalMensagem.direcao == "inbound",
    )
    if cursor_id is not None:
        q = q.filter(PortalMensagem.id > cursor_id)
    else:
        eff = ls if ls is not None else (c.atendimento_inicio_at or c.created_at)
        if eff is None:
            return 0, ls, cursor_id
        q = q.filter(PortalMensagem.created_at > eff)
    return int(q.scalar() or 0), ls, cursor_id


def _chat_read(db: Session, c: PortalChat, *, atendente_id: int | None = None) -> PortalChatRead:
    nao_lidas = 0
    last_seen: datetime | None = None
    last_seen_msg: int | None = None
    if atendente_id is not None:
        nao_lidas, last_seen, last_seen_msg = _nao_lidas_portal(db, c, atendente_id)
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
        ultima_mensagem_preview=_ultima_mensagem_preview(db, c.id),
        nao_lidas_count=nao_lidas,
        last_seen_at=last_seen,
        last_seen_mensagem_id=last_seen_msg,
    )


def _mensagem_read(m: PortalMensagem) -> PortalChatMensagemRead:
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
    )


def _tipo_midia_db(slug: str) -> str:
    s = (slug or "").strip().lower()
    if s in ("imagem", "image"):
        return "imagem"
    if s == "video":
        return "video"
    if s == "audio":
        return "audio"
    if s in ("figurinha", "sticker"):
        return "figurinha"
    return "documento"


def _pode_registrar_demanda(db: Session, atendente: Atendente, c: PortalChat) -> bool:
    if c.estado != "em_atendimento":
        return False
    if not pode_ver_portal_chat(db, atendente, c):
        return False
    if atendente.role == "admin":
        return True
    return c.atendente_id == atendente.id


def _get_chat(db: Session, chat_id: int) -> PortalChat:
    c = db.query(PortalChat).options(*_CHAT_LOAD_OPTIONS).filter(PortalChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    return c


@router.get("/transfer/setores", response_model=list[dict])
def listar_setores_para_transferencia(
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    rows = db.query(Setor).filter(Setor.ativo.is_(True)).order_by(Setor.nome.asc(), Setor.id.asc()).all()
    return [{"id": s.id, "nome": s.nome} for s in rows]


@router.get("/fila", response_model=list[PortalChatRead])
def listar_fila(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = (
        db.query(PortalChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(PortalChat.estado == "aguardando_atendente")
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter(or_(PortalChat.setor_id.is_(None), PortalChat.setor_id.in_(vis)))
    rows = q.order_by(PortalChat.created_at.asc()).all()
    return [_chat_read(db, c) for c in rows]


@router.get("/meus", response_model=list[PortalChatRead])
def listar_meus(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = (
        db.query(PortalChat)
        .options(*_CHAT_LOAD_OPTIONS)
        .filter(PortalChat.estado == "em_atendimento")
    )
    if atendente.role != "admin":
        q = q.filter(PortalChat.atendente_id == atendente.id)
    rows = q.order_by(PortalChat.atendimento_inicio_at.desc().nullslast()).all()
    return [_chat_read(db, c, atendente_id=atendente.id) for c in rows]


@router.get("/{chat_id}", response_model=PortalChatRead)
def obter_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = _get_chat(db, chat_id)
    exigir_acesso_portal_chat(db, atendente, c)
    return _chat_read(db, c, atendente_id=atendente.id)


@router.get("/{chat_id}/mensagens", response_model=list[PortalChatMensagemRead])
def listar_mensagens(
    chat_id: int,
    since_id: int | None = Query(None, ge=1),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = _get_chat(db, chat_id)
    exigir_acesso_portal_chat(db, atendente, c)
    rows = listar_mensagens_chat(db, chat_id, since_id=since_id, limit=limit)
    visiveis = [m for m in rows if not mensagem_oculta_na_conversa(getattr(m, "evento_sistema", None))]
    return [_mensagem_read(m) for m in visiveis]


@router.post("/{chat_id}/assumir", response_model=PortalChatRead)
def assumir(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = _get_chat(db, chat_id)
    estado_anterior = assumir_portal_chat(db, c, atendente)
    db.commit()
    db.refresh(c)
    try:
        auto_msg = try_auto_msg_assumido(db, c, atendente)
        if auto_msg:
            db.commit()
            emit_portal_chat_mensagem_from_models(db, c, auto_msg)
    except Exception as exc:
        logger.warning("Auto-msg assumido portal falhou (chat=%s): %s", c.protocolo, exc)
    c = _get_chat(db, chat_id)
    emit_portal_chat_fila_from_model(db, c, estado_anterior=estado_anterior)
    return _chat_read(db, c)


@router.post("/{chat_id}/transferir", response_model=PortalChatRead)
def transferir(
    chat_id: int,
    data: PortalTransferirChatBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = _get_chat(db, chat_id)
    setor = db.query(Setor).filter(Setor.id == data.setor_id, Setor.ativo.is_(True)).first()
    if not setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado ou inativo")

    vis_destino_ok = True
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        vis_destino_ok = data.setor_id in vis

    destino: Atendente | None = None
    if data.atendente_id is not None:
        if not vis_destino_ok:
            raise HTTPException(
                status_code=403,
                detail="Sem permissão para atribuir responsável no setor destino. Transfira sem atendente para cair na fila do setor.",
            )
        destino = db.query(Atendente).filter(Atendente.id == data.atendente_id, Atendente.ativo.is_(True)).first()
        if not destino:
            raise HTTPException(status_code=404, detail="Atendente não encontrado ou inativo")
        if destino.role != "admin":
            setor_ids = {s.id for s in destino.setores}
            if data.setor_id not in setor_ids:
                raise HTTPException(status_code=400, detail="Atendente selecionado não pertence ao setor escolhido")

    estado_anterior = transferir_portal_chat(
        db,
        c,
        atendente,
        setor_id=data.setor_id,
        destino_atendente_id=data.atendente_id,
        setor_nome=setor.nome,
        destino=destino,
    )
    db.commit()
    c = _get_chat(db, chat_id)
    emit_portal_chat_fila_from_model(db, c, estado_anterior=estado_anterior)
    ultima = (
        db.query(PortalMensagem)
        .options(joinedload(PortalMensagem.atendente))
        .filter(PortalMensagem.chat_id == chat_id)
        .order_by(PortalMensagem.id.desc())
        .first()
    )
    if ultima and ultima.evento_sistema == "transferencia":
        emit_portal_chat_mensagem_from_models(db, c, ultima, exclude_atendente_id=atendente.id)
    return _chat_read(db, c)


@router.get("/{chat_id}/demandas", response_model=list[PortalChatDemandaRead])
def listar_demandas(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    from app.services.portal_chat_demandas import listar_demandas_chat

    c = _get_chat(db, chat_id)
    exigir_acesso_portal_chat(db, atendente, c)
    return listar_demandas_chat(db, chat_id)


@router.post("/{chat_id}/demandas", response_model=PortalChatDemandaRead, status_code=201)
def registrar_demanda(
    chat_id: int,
    data: PortalChatDemandaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    from app.services.portal_chat_demandas import (
        criar_demanda_chat,
        criar_marco_demanda_mensagem,
        demanda_para_read,
    )

    c = _get_chat(db, chat_id)
    if not _pode_registrar_demanda(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para registrar demanda neste chat")
    row = criar_demanda_chat(db, c, atendente, data, desfecho="resolvido_sessao")
    marco = criar_marco_demanda_mensagem(db, chat=c, atendente=atendente, demanda=row)
    db.commit()
    db.refresh(marco)
    marco = (
        db.query(PortalMensagem)
        .options(joinedload(PortalMensagem.atendente))
        .filter(PortalMensagem.id == marco.id)
        .first()
    )
    emit_portal_chat_mensagem_from_models(db, c, marco, exclude_atendente_id=atendente.id)
    return demanda_para_read(row)


@router.patch("/{chat_id}/demandas/{demanda_id}", response_model=PortalChatDemandaRead)
def atualizar_demanda(
    chat_id: int,
    demanda_id: int,
    data: PortalChatDemandaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    from app.models.portal_chat_demanda import PortalChatDemanda
    from app.services.portal_chat_demandas import atualizar_demanda_chat, demanda_para_read

    c = _get_chat(db, chat_id)
    if not _pode_registrar_demanda(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para alterar demandas neste chat")
    row = (
        db.query(PortalChatDemanda)
        .filter(PortalChatDemanda.id == demanda_id, PortalChatDemanda.chat_id == chat_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    updated = atualizar_demanda_chat(db, c, row, data, atendente=atendente)
    db.commit()
    return demanda_para_read(updated)


@router.delete("/{chat_id}/demandas/{demanda_id}", status_code=204)
def excluir_demanda(
    chat_id: int,
    demanda_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    from app.models.portal_chat_demanda import PortalChatDemanda
    from app.services.portal_chat_demandas import remover_marco_demanda_mensagem

    c = _get_chat(db, chat_id)
    if not _pode_registrar_demanda(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para alterar demandas neste chat")
    row = (
        db.query(PortalChatDemanda)
        .filter(PortalChatDemanda.id == demanda_id, PortalChatDemanda.chat_id == chat_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    remover_marco_demanda_mensagem(db, chat_id=chat_id, demanda_id=demanda_id)
    db.delete(row)
    db.commit()


@router.post("/{chat_id}/encerrar", response_model=PortalChatRead)
def encerrar(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = _get_chat(db, chat_id)
    estado_anterior = c.estado
    encerrar_portal_chat(db, c, atendente)
    db.commit()
    db.refresh(c)
    c = _get_chat(db, chat_id)
    emit_portal_chat_fila_from_model(db, c, estado_anterior=estado_anterior)
    ultimas = listar_mensagens_chat(db, chat_id, limit=5)
    for m in reversed(ultimas):
        if m.evento_sistema in (
            "auto_encerrado",
            "auto_avaliacao_solicitacao",
            "auto_avaliacao_obrigado",
            "auto_avaliacao_sem_nota",
        ):
            emit_portal_chat_mensagem_from_models(db, c, m)
            break
    return _chat_read(db, c)


@router.post("/{chat_id}/mensagens", response_model=PortalChatMensagemRead)
def enviar_mensagem(
    chat_id: int,
    body: PortalChatMensagemCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = _get_chat(db, chat_id)
    msg = registrar_mensagem_atendente(db, c, atendente, body.corpo)
    db.commit()
    db.refresh(msg)
    msg = (
        db.query(PortalMensagem)
        .options(joinedload(PortalMensagem.atendente))
        .filter(PortalMensagem.id == msg.id)
        .first()
    )
    assert msg is not None
    emit_portal_chat_mensagem_from_models(db, c, msg, exclude_atendente_id=atendente.id)
    return _mensagem_read(msg)


@router.get("/{chat_id}/mensagens/{mensagem_id}/midia")
def obter_midia_da_mensagem(
    chat_id: int,
    mensagem_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = _get_chat(db, chat_id)
    exigir_acesso_portal_chat(db, atendente, c)
    m = (
        db.query(PortalMensagem)
        .filter(PortalMensagem.chat_id == chat_id, PortalMensagem.id == mensagem_id)
        .first()
    )
    if not m or not m.midia_nome_arquivo:
        raise HTTPException(status_code=404, detail="Mídia não encontrada")
    path = caminho_absoluto_arquivo(m.midia_nome_arquivo)
    if not path:
        raise HTTPException(status_code=404, detail="Ficheiro não encontrado em disco")
    media_type = m.mimetype or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.post("/{chat_id}/mensagens/midia", response_model=PortalChatMensagemRead, status_code=201)
async def enviar_mensagem_midia(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
    file: UploadFile = File(...),
    mediatipo: str = Form(..., description="imagem | video | audio | documento | figurinha"),
    caption: str = Form(""),
):
    c = _get_chat(db, chat_id)
    data = await file.read()
    if len(data) > settings.WHATSAPP_MEDIA_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Ficheiro excede o tamanho máximo permitido.")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Ficheiro vazio.")
    mime = (file.content_type or "application/octet-stream").split(";")[0].strip()
    tipo_db = _tipo_midia_db(mediatipo)
    nome_guardado = gravar_bytes_em_disco(data, mime)
    if not nome_guardado:
        raise HTTPException(status_code=500, detail="Não foi possível guardar o ficheiro em disco.")
    msg = registrar_mensagem_midia_atendente(
        db,
        c,
        atendente,
        tipo_midia=tipo_db,
        mimetype=mime,
        midia_nome_arquivo=nome_guardado,
        caption=caption,
    )
    db.commit()
    db.refresh(msg)
    msg = (
        db.query(PortalMensagem)
        .options(joinedload(PortalMensagem.atendente))
        .filter(PortalMensagem.id == msg.id)
        .first()
    )
    assert msg is not None
    emit_portal_chat_mensagem_from_models(db, c, msg, exclude_atendente_id=atendente.id)
    return _mensagem_read(msg)


@router.post("/{chat_id}/visto", status_code=204)
def marcar_visto(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = _get_chat(db, chat_id)
    if not pode_ver_portal_chat(db, atendente, c):
        raise HTTPException(status_code=403, detail="Sem permissão para este chat.")
    marcar_visto_portal_chat(db, chat_id, atendente.id)
    db.commit()
    from app.services.realtime_emit import emit_notificacao_after_counter_change

    emit_notificacao_after_counter_change(db)
