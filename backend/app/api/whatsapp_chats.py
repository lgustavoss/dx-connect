import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.database import get_db
from app.models.atendente import Atendente
from app.models.ticket import Ticket, TicketMensagem
from app.models.status_ticket import StatusTicket
from app.models.empresa import Empresa
from app.models.setor import Setor
from app.models.whatsapp_chat import WhatsappChat, WhatsappChatTicket, WhatsappMensagem, WhatsappSettings
from app.models.whatsapp_chat_read import WhatsappChatRead
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.whatsapp_chat import (
    WhatsappAbrirTicketBody,
    WhatsappChatComentarioInternoCreate,
    WhatsappChatMensagemCreate,
    WhatsappChatRead,
    WhatsappMensagemRead,
    WhatsappTransferirChatBody,
    WhatsappVincularTicketBody,
)
from app.core.auth import obter_atendente_atual
from app.api.tickets import _gerar_protocolo, _pode_ver_ticket
from app.core.setor_scope import ids_setores_visiveis_atendente
from app.config import settings
from app.services import evolution_api
from app.services.whatsapp_media_storage import caminho_absoluto_arquivo, gravar_bytes_em_disco

router = APIRouter(prefix="/whatsapp/chats", tags=["whatsapp-chats"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


@router.get("/transfer/setores", response_model=list[dict])
def listar_setores_para_transferencia(
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    """Lista TODOS os setores ativos para transferência (não implica permissão de visualização de chats)."""
    rows = db.query(Setor).filter(Setor.ativo.is_(True)).order_by(Setor.nome.asc(), Setor.id.asc()).all()
    return [{"id": s.id, "nome": s.nome} for s in rows]


def _settings_envio(db: Session) -> WhatsappSettings:
    row = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if not row or not row.evolution_base_url or not row.evolution_instance_name or not row.evolution_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integração WhatsApp incompleta. Administrador deve preencher URL, instância e API key.",
        )
    return row


def _quoted_evolution_payload(db: Session, chat_id: int, quoted_wa_message_id: str) -> dict:
    q = (quoted_wa_message_id or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Citação inválida.")
    ref = (
        db.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat_id, WhatsappMensagem.wa_message_id == q)
        .first()
    )
    if not ref:
        raise HTTPException(
            status_code=400,
            detail="Mensagem citada não encontrada neste chat (use o id da mensagem no WhatsApp, "
            "campo wa_message_id na listagem de mensagens).",
        )
    pv = ((ref.corpo or "").strip()[:2000] or " ")
    return {"key": {"id": q}, "message": {"conversation": pv}}


def _preview_citacao(ref: WhatsappMensagem) -> str | None:
    s = (ref.corpo or "").strip()[:500]
    return s or None


def _mediatype_evolution(slug: str) -> str:
    s = (slug or "").strip().lower()
    return {
        "imagem": "image",
        "image": "image",
        "video": "video",
        "audio": "audio",
        "documento": "document",
        "document": "document",
    }.get(s, "document")


def _tipo_midia_db(slug: str) -> str:
    s = (slug or "").strip().lower()
    if s in ("imagem", "image"):
        return "imagem"
    if s == "video":
        return "video"
    if s == "audio":
        return "audio"
    return "documento"


def _rotulo_midia_outbound(tipo_db: str) -> str:
    return {
        "imagem": "[Imagem enviada]",
        "video": "[Vídeo enviado]",
        "audio": "[Áudio enviado]",
        "documento": "[Documento enviado]",
    }.get(tipo_db, "[Ficheiro enviado]")


def _sanitizar_nome_ficheiro(name: str | None, fallback: str) -> str:
    raw = (name or fallback or "file").strip() or "file"
    safe = "".join(ch for ch in raw if ch.isalnum() or ch in "._- ")
    return (safe.strip() or fallback)[:200]


def _render_template(
    template: str,
    *,
    chat: WhatsappChat,
    atendente: Atendente | None = None,
    st: WhatsappSettings | None = None,
    atendente_nome: str | None = None,
) -> str:
    t = (template or "").strip()
    if not t:
        return ""
    nome = (chat.cliente_nome or "").strip() or "Cliente"
    nome_atendente = (atendente_nome or "").strip() or (atendente.nome if atendente else "").strip() or "BOT"
    nome_empresa = ((getattr(st, "nome_empresa_exibicao", None) or "").strip() if st else "") or "nossa empresa"
    return (
        t.replace("{nome}", nome)
        .replace("{atendente}", nome_atendente)
        .replace("{protocolo}", chat.protocolo)
        .replace("{telefone}", chat.wa_id)
        .replace("{{nome_cliente}}", nome)
        .replace("{{atendente}}", nome_atendente)
        .replace("{{protocolo}}", chat.protocolo)
        .replace("{{telefone}}", chat.wa_id)
        .replace("{{nome_empresa}}", nome_empresa)
    )


def _enviar_texto_whatsapp(
    db: Session,
    *,
    chat: WhatsappChat,
    texto: str,
    atendente: Atendente | None,
    evento_sistema: str | None,
    quoted_wa_message_id: str | None = None,
) -> WhatsappMensagem:
    texto_eff = (texto or "").strip()
    if not texto_eff:
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    # Quando o atendente envia manualmente pelo DX Connect, prefixa o nome no texto
    # para ficar visível no WhatsApp do cliente (padrão: "[ Nome ]: mensagem").
    # Mensagens automáticas (evento_sistema != None) não recebem este prefixo.
    if atendente is not None and evento_sistema is None:
        nome = (atendente.nome or "").strip()
        if nome:
            texto_eff = f"[ {nome} ]: {texto_eff}"
    # Mensagens automáticas devem deixar claro que são do BOT.
    if evento_sistema is not None:
        if not texto_eff.startswith("["):
            texto_eff = f"[ BOT ]: {texto_eff}"
    if evento_sistema:
        exist = (
            db.query(WhatsappMensagem)
            .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.evento_sistema == evento_sistema)
            .first()
        )
        if exist:
            return exist
    st = _settings_envio(db)
    quoted_payload = None
    q_wa: str | None = None
    q_prev: str | None = None
    if quoted_wa_message_id and str(quoted_wa_message_id).strip() and evento_sistema is None:
        q_wa = str(quoted_wa_message_id).strip()
        quoted_payload = _quoted_evolution_payload(db, chat.id, q_wa)
        ref = (
            db.query(WhatsappMensagem)
            .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.wa_message_id == q_wa)
            .first()
        )
        q_prev = _preview_citacao(ref) if ref else None
    ok, err = evolution_api.evolution_send_text(
        st.evolution_base_url,
        st.evolution_instance_name,
        st.evolution_api_key,
        chat.wa_id,
        texto_eff,
        quoted=quoted_payload,
    )
    if not ok:
        raise HTTPException(status_code=502, detail=err or "Falha ao enviar pela Evolution API")
    m = WhatsappMensagem(
        chat_id=chat.id,
        direcao="outbound",
        corpo=texto_eff,
        tipo_midia="texto",
        mimetype=None,
        midia_nome_arquivo=None,
        wa_message_id=None,
        quoted_wa_message_id=q_wa,
        quoted_corpo_preview=q_prev,
        atendente_id=atendente.id if atendente else None,
        evento_sistema=evento_sistema,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _ticket_ids(db: Session, chat_id: int) -> list[int]:
    return [x[0] for x in db.query(WhatsappChatTicket.ticket_id).filter(WhatsappChatTicket.chat_id == chat_id).all()]


def _chat_read(db: Session, c: WhatsappChat) -> WhatsappChatRead:
    return WhatsappChatRead(
        id=c.id,
        protocolo=c.protocolo,
        wa_id=c.wa_id,
        cliente_nome=c.cliente_nome,
        estado=c.estado,
        setor_id=getattr(c, "setor_id", None),
        setor_nome=c.setor.nome if getattr(c, "setor", None) else None,
        atendente_id=c.atendente_id,
        atendente_nome=c.atendente.nome if c.atendente else None,
        created_at=c.created_at,
        atendimento_inicio_at=c.atendimento_inicio_at,
        encerramento_at=c.encerramento_at,
        ticket_ids=_ticket_ids(db, c.id),
    )


def _mensagem_read(m: WhatsappMensagem) -> WhatsappMensagemRead:
    midia_ok = bool(m.midia_nome_arquivo and str(m.midia_nome_arquivo).strip())
    return WhatsappMensagemRead(
        id=m.id,
        chat_id=m.chat_id,
        direcao=m.direcao,
        corpo=m.corpo,
        tipo_midia=m.tipo_midia,
        mimetype=m.mimetype,
        midia_disponivel=midia_ok,
        evento_sistema=getattr(m, "evento_sistema", None),
        wa_message_id=m.wa_message_id,
        quoted_wa_message_id=getattr(m, "quoted_wa_message_id", None),
        quoted_corpo_preview=getattr(m, "quoted_corpo_preview", None),
        atendente_id=m.atendente_id,
        atendente_nome=m.atendente.nome if m.atendente else None,
        created_at=m.created_at,
    )


@router.get("/fila", response_model=list[WhatsappChatRead])
def listar_fila(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente), joinedload(WhatsappChat.setor)).filter(
        WhatsappChat.estado == "aguardando_atendente"
    )
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter((WhatsappChat.setor_id.is_(None)) | (WhatsappChat.setor_id.in_(vis)))
    rows = q.order_by(WhatsappChat.created_at.asc()).all()
    return [_chat_read(db, c) for c in rows]


@router.get("/meus", response_model=list[WhatsappChatRead])
def listar_meus_ativos(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = (
        db.query(WhatsappChat)
        .options(joinedload(WhatsappChat.atendente), joinedload(WhatsappChat.setor))
        .filter(WhatsappChat.estado == "em_atendimento")
    )
    if atendente.role != "admin":
        q = q.filter(WhatsappChat.atendente_id == atendente.id)
    rows = q.order_by(WhatsappChat.atendimento_inicio_at.desc().nullslast()).all()
    return [_chat_read(db, c) for c in rows]


@router.get("/encerrados", response_model=ListaPaginada[WhatsappChatRead])
def listar_encerrados(
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.estado == "encerrado")
    total = q.count()
    rows = q.order_by(desc(WhatsappChat.encerramento_at), desc(WhatsappChat.id)).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_chat_read(db, c) for c in rows], total=total)


@router.get("/por-ticket/{ticket_id}", response_model=list[WhatsappChatRead])
def listar_por_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=403, detail="Sem permissão para este ticket")
    chat_ids = [r[0] for r in db.query(WhatsappChatTicket.chat_id).filter(WhatsappChatTicket.ticket_id == ticket_id).all()]
    if not chat_ids:
        return []
    rows = (
        db.query(WhatsappChat)
        .options(joinedload(WhatsappChat.atendente))
        .filter(WhatsappChat.id.in_(chat_ids))
        .order_by(desc(WhatsappChat.id))
        .all()
    )
    return [_chat_read(db, c) for c in rows]


@router.get("/{chat_id}", response_model=WhatsappChatRead)
def obter(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = (
        db.query(WhatsappChat)
        .options(joinedload(WhatsappChat.atendente), joinedload(WhatsappChat.setor))
        .filter(WhatsappChat.id == chat_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    return _chat_read(db, c)


@router.get("/{chat_id}/mensagens/{mensagem_id}/midia")
def obter_midia_da_mensagem(
    chat_id: int,
    mensagem_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    """Devolve o ficheiro binário guardado para mensagens inbound com mídia."""
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    m = (
        db.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat_id, WhatsappMensagem.id == mensagem_id)
        .first()
    )
    if not m or not m.midia_nome_arquivo:
        raise HTTPException(status_code=404, detail="Mídia não encontrada")
    path = caminho_absoluto_arquivo(m.midia_nome_arquivo)
    if not path:
        raise HTTPException(status_code=404, detail="Ficheiro não encontrado em disco")
    media_type = m.mimetype or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/{chat_id}/mensagens", response_model=list[WhatsappMensagemRead])
def listar_mensagens(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    rows = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.chat_id == chat_id)
        .order_by(WhatsappMensagem.created_at.asc())
        .all()
    )
    return [_mensagem_read(m) for m in rows]


@router.post("/{chat_id}/assumir", response_model=WhatsappChatRead)
def assumir(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado != "aguardando_atendente":
        raise HTTPException(status_code=400, detail="Só é possível assumir chats na fila de espera")
    c.estado = "em_atendimento"
    c.atendente_id = atendente.id
    c.atendimento_inicio_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    st_auto = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if st_auto and bool(getattr(st_auto, "auto_msg_assumido_ativa", True)):
        txt = _render_template(
            getattr(st_auto, "auto_msg_assumido_texto", "") or "",
            chat=c,
            atendente=atendente,
            st=st_auto,
            # Mensagem é automática (prefixo [ BOT ]), mas o conteúdo pode citar o atendente real.
            atendente_nome=(atendente.nome or "").strip() or "BOT",
        )
        if txt:
            _enviar_texto_whatsapp(db, chat=c, texto=txt, atendente=atendente, evento_sistema="auto_assumido")
    c = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.id == chat_id).first()
    assert c is not None
    return _chat_read(db, c)


@router.post("/{chat_id}/encerrar", response_model=WhatsappChatRead)
def encerrar(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado == "encerrado":
        return _chat_read(db, c)
    if c.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Encerre apenas chats em atendimento")
    if atendente.role != "admin" and c.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode encerrar este chat")
    c.estado = "encerrado"
    c.encerramento_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    st_auto = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if st_auto and bool(getattr(st_auto, "auto_msg_encerrado_ativa", True)):
        txt = _render_template(
            getattr(st_auto, "auto_msg_encerrado_texto", "") or "",
            chat=c,
            atendente=atendente,
            st=st_auto,
            atendente_nome="BOT",
        )
        if txt:
            _enviar_texto_whatsapp(db, chat=c, texto=txt, atendente=atendente, evento_sistema="auto_encerrado")
    c = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.id == chat_id).first()
    assert c is not None
    return _chat_read(db, c)


@router.post("/{chat_id}/mensagens", response_model=WhatsappMensagemRead, status_code=201)
def enviar_mensagem(
    chat_id: int,
    data: WhatsappChatMensagemCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Só é possível enviar mensagens em chats ativos")
    if atendente.role != "admin" and c.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode enviar mensagens")
    texto = data.texto.strip()
    m = _enviar_texto_whatsapp(
        db,
        chat=c,
        texto=texto,
        atendente=atendente,
        evento_sistema=None,
        quoted_wa_message_id=data.quoted_wa_message_id,
    )
    m = db.query(WhatsappMensagem).options(joinedload(WhatsappMensagem.atendente)).filter(WhatsappMensagem.id == m.id).first()
    assert m is not None
    return _mensagem_read(m)


@router.post("/{chat_id}/mensagens/midia", response_model=WhatsappMensagemRead, status_code=201)
async def enviar_mensagem_midia(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
    file: UploadFile = File(...),
    mediatipo: str = Form(..., description="imagem | video | audio | documento"),
    caption: str = Form(""),
    quoted_wa_message_id: str | None = Form(None),
):
    """Envia mídia para o cliente via Evolution API (base64). Opcionalmente cita uma mensagem anterior."""
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Só é possível enviar mensagens em chats ativos")
    if atendente.role != "admin" and c.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode enviar mensagens")

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

    cap = (caption or "").strip()
    base_legenda = cap if cap else _rotulo_midia_outbound(tipo_db)
    nome_atend = (atendente.nome or "").strip()
    legenda_whatsapp = f"[ {nome_atend} ]: {base_legenda}" if nome_atend else base_legenda
    corpo_eff = legenda_whatsapp

    b64 = base64.b64encode(data).decode("ascii")
    st = _settings_envio(db)
    ev_mt = _mediatype_evolution(mediatipo)
    fname = _sanitizar_nome_ficheiro(file.filename, f"envio.{tipo_db}")

    quoted_payload = None
    q_wa: str | None = None
    q_prev: str | None = None
    if quoted_wa_message_id and str(quoted_wa_message_id).strip():
        q_wa = str(quoted_wa_message_id).strip()
        quoted_payload = _quoted_evolution_payload(db, chat_id, q_wa)
        ref = (
            db.query(WhatsappMensagem)
            .filter(WhatsappMensagem.chat_id == chat_id, WhatsappMensagem.wa_message_id == q_wa)
            .first()
        )
        q_prev = _preview_citacao(ref) if ref else None

    ok, err = evolution_api.evolution_send_media(
        st.evolution_base_url,
        st.evolution_instance_name,
        st.evolution_api_key,
        c.wa_id,
        mediatype=ev_mt,
        mimetype=mime,
        caption=legenda_whatsapp,
        media_base64=b64,
        file_name=fname,
        quoted=quoted_payload,
    )
    if not ok:
        raise HTTPException(status_code=502, detail=err or "Falha ao enviar mídia pela Evolution API")

    m = WhatsappMensagem(
        chat_id=c.id,
        direcao="outbound",
        corpo=corpo_eff,
        tipo_midia=tipo_db,
        mimetype=mime,
        midia_nome_arquivo=nome_guardado,
        wa_message_id=None,
        quoted_wa_message_id=q_wa,
        quoted_corpo_preview=q_prev,
        atendente_id=atendente.id,
        evento_sistema=None,
    )
    db.add(m)
    db.commit()
    m2 = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.id == m.id)
        .first()
    )
    assert m2 is not None
    return _mensagem_read(m2)


@router.post("/{chat_id}/comentarios-internos", response_model=WhatsappMensagemRead, status_code=201)
def comentar_interno(
    chat_id: int,
    data: WhatsappChatComentarioInternoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if c.estado == "encerrado":
        raise HTTPException(status_code=400, detail="Chat encerrado (somente leitura)")
    texto = data.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Comentário vazio")
    nome = (atendente.nome or "").strip() or "Equipe"
    corpo = f"[ INTERNO / {nome} ]: {texto}"
    m = WhatsappMensagem(
        chat_id=c.id,
        direcao="outbound",
        corpo=corpo,
        tipo_midia="texto",
        mimetype=None,
        midia_nome_arquivo=None,
        wa_message_id=None,
        atendente_id=atendente.id,
        evento_sistema="comentario_interno",
    )
    db.add(m)
    db.commit()
    m2 = (
        db.query(WhatsappMensagem)
        .options(joinedload(WhatsappMensagem.atendente))
        .filter(WhatsappMensagem.id == m.id)
        .first()
    )
    assert m2 is not None
    return _mensagem_read(m2)


@router.post("/{chat_id}/visto", status_code=204)
def marcar_chat_visto(
    chat_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin" and c.setor_id is not None:
        vis = ids_setores_visiveis_atendente(db, atendente)
        if c.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")

    now = datetime.now(timezone.utc)
    row = (
        db.query(WhatsappChatRead)
        .filter(WhatsappChatRead.chat_id == chat_id, WhatsappChatRead.atendente_id == atendente.id)
        .first()
    )
    if row:
        row.last_seen_at = now
    else:
        db.add(WhatsappChatRead(chat_id=chat_id, atendente_id=atendente.id, last_seen_at=now))
    db.commit()
    return None


@router.post("/{chat_id}/vincular-ticket", response_model=WhatsappChatRead)
def vincular_ticket(
    chat_id: int,
    data: WhatsappVincularTicketBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    ticket = db.query(Ticket).filter(Ticket.id == data.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=403, detail="Sem permissão para este ticket")
    exist = (
        db.query(WhatsappChatTicket)
        .filter(WhatsappChatTicket.chat_id == chat_id, WhatsappChatTicket.ticket_id == data.ticket_id)
        .first()
    )
    if not exist:
        db.add(WhatsappChatTicket(chat_id=chat_id, ticket_id=data.ticket_id, atendente_id=atendente.id))
        db.commit()
    c2 = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


@router.post("/{chat_id}/abrir-ticket", response_model=WhatsappChatRead)
def abrir_ticket(
    chat_id: int,
    data: WhatsappAbrirTicketBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        if data.setor_id not in vis:
            raise HTTPException(status_code=403, detail="Sem permissão para este setor")
    if not db.query(Empresa).filter(Empresa.id == data.empresa_id).first():
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if not db.query(Setor).filter(Setor.id == data.setor_id).first():
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    status_inicial = db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).order_by(StatusTicket.ordem).first()
    if not status_inicial:
        raise HTTPException(status_code=400, detail="Cadastre ao menos um status de ticket")
    protocolo = _gerar_protocolo(db)
    desc = (data.descricao or "").strip()
    linha_chat = f"Vinculado ao chat WhatsApp {c.protocolo} (contato {c.wa_id})."
    descricao_final = f"{linha_chat}\n\n{desc}" if desc else linha_chat
    ticket = Ticket(
        protocolo=protocolo,
        empresa_id=data.empresa_id,
        setor_id=data.setor_id,
        status_id=status_inicial.id,
        assunto=data.assunto.strip(),
        descricao=descricao_final,
        aberto_por_id=None,
    )
    db.add(ticket)
    db.flush()
    corpo_abertura = desc or linha_chat
    db.add(
        TicketMensagem(
            ticket_id=ticket.id,
            atendente_id=atendente.id,
            tipo="abertura",
            corpo=corpo_abertura,
        )
    )
    db.add(WhatsappChatTicket(chat_id=chat_id, ticket_id=ticket.id, atendente_id=atendente.id))
    db.commit()
    c2 = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.id == chat_id).first()
    assert c2 is not None
    return _chat_read(db, c2)


@router.post("/{chat_id}/transferir", response_model=WhatsappChatRead)
def transferir(
    chat_id: int,
    data: WhatsappTransferirChatBody,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    c = (
        db.query(WhatsappChat)
        .options(joinedload(WhatsappChat.atendente), joinedload(WhatsappChat.setor))
        .filter(WhatsappChat.id == chat_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    if c.estado == "encerrado":
        raise HTTPException(status_code=400, detail="Chat encerrado não pode ser transferido")
    # Permissão: admin ou atendente responsável atual
    if atendente.role != "admin" and c.atendente_id not in (None, atendente.id):
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode transferir este chat")

    setor = db.query(Setor).filter(Setor.id == data.setor_id, Setor.ativo.is_(True)).first()
    if not setor:
        raise HTTPException(status_code=404, detail="Setor não encontrado ou inativo")

    # Atendente pode transferir para qualquer setor.
    # Porém, só pode escolher um responsável (atendente_id) se tiver acesso ao setor destino (ou for admin).
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
        # destino deve pertencer ao setor escolhido (a menos que seja admin)
        if destino.role != "admin":
            setor_ids = {s.id for s in destino.setores}
            if data.setor_id not in setor_ids:
                raise HTTPException(status_code=400, detail="Atendente selecionado não pertence ao setor escolhido")

    c.setor_id = data.setor_id
    c.atendente_id = destino.id if destino else None
    if destino:
        c.estado = "em_atendimento"
        c.atendimento_inicio_at = c.atendimento_inicio_at or datetime.now(timezone.utc)
    else:
        c.estado = "aguardando_atendente"
        c.atendimento_inicio_at = None
    db.commit()
    db.refresh(c)
    c2 = (
        db.query(WhatsappChat)
        .options(joinedload(WhatsappChat.atendente), joinedload(WhatsappChat.setor))
        .filter(WhatsappChat.id == chat_id)
        .first()
    )
    assert c2 is not None
    return _chat_read(db, c2)
