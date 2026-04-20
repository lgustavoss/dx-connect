from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.database import get_db
from app.models.atendente import Atendente
from app.models.ticket import Ticket, TicketMensagem
from app.models.status_ticket import StatusTicket
from app.models.empresa import Empresa
from app.models.setor import Setor
from app.models.whatsapp_chat import WhatsappChat, WhatsappChatTicket, WhatsappMensagem, WhatsappSettings
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.whatsapp_chat import (
    WhatsappAbrirTicketBody,
    WhatsappChatMensagemCreate,
    WhatsappChatRead,
    WhatsappMensagemRead,
    WhatsappVincularTicketBody,
)
from app.core.auth import obter_atendente_atual
from app.api.tickets import _gerar_protocolo, _pode_ver_ticket
from app.core.setor_scope import ids_setores_visiveis_atendente
from app.services import evolution_api

router = APIRouter(prefix="/whatsapp/chats", tags=["whatsapp-chats"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


def _settings_envio(db: Session) -> WhatsappSettings:
    row = db.query(WhatsappSettings).order_by(WhatsappSettings.id.asc()).first()
    if not row or not row.evolution_base_url or not row.evolution_instance_name or not row.evolution_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integração WhatsApp incompleta. Administrador deve preencher URL, instância e API key.",
        )
    return row


def _ticket_ids(db: Session, chat_id: int) -> list[int]:
    return [x[0] for x in db.query(WhatsappChatTicket.ticket_id).filter(WhatsappChatTicket.chat_id == chat_id).all()]


def _chat_read(db: Session, c: WhatsappChat) -> WhatsappChatRead:
    return WhatsappChatRead(
        id=c.id,
        protocolo=c.protocolo,
        wa_id=c.wa_id,
        cliente_nome=c.cliente_nome,
        estado=c.estado,
        atendente_id=c.atendente_id,
        atendente_nome=c.atendente.nome if c.atendente else None,
        created_at=c.created_at,
        atendimento_inicio_at=c.atendimento_inicio_at,
        encerramento_at=c.encerramento_at,
        ticket_ids=_ticket_ids(db, c.id),
    )


def _mensagem_read(m: WhatsappMensagem) -> WhatsappMensagemRead:
    return WhatsappMensagemRead(
        id=m.id,
        chat_id=m.chat_id,
        direcao=m.direcao,
        corpo=m.corpo,
        wa_message_id=m.wa_message_id,
        atendente_id=m.atendente_id,
        atendente_nome=m.atendente.nome if m.atendente else None,
        created_at=m.created_at,
    )


@router.get("/fila", response_model=list[WhatsappChatRead])
def listar_fila(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    rows = (
        db.query(WhatsappChat)
        .options(joinedload(WhatsappChat.atendente))
        .filter(WhatsappChat.estado == "aguardando_atendente")
        .order_by(WhatsappChat.created_at.asc())
        .all()
    )
    return [_chat_read(db, c) for c in rows]


@router.get("/meus", response_model=list[WhatsappChatRead])
def listar_meus_ativos(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.estado == "em_atendimento")
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
    c = db.query(WhatsappChat).options(joinedload(WhatsappChat.atendente)).filter(WhatsappChat.id == chat_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    return _chat_read(db, c)


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
    if c.estado != "aguardando_atendente":
        raise HTTPException(status_code=400, detail="Só é possível assumir chats na fila de espera")
    c.estado = "em_atendimento"
    c.atendente_id = atendente.id
    c.atendimento_inicio_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
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
    if c.estado != "em_atendimento":
        raise HTTPException(status_code=400, detail="Só é possível enviar mensagens em chats ativos")
    if atendente.role != "admin" and c.atendente_id != atendente.id:
        raise HTTPException(status_code=403, detail="Apenas o atendente responsável pode enviar mensagens")
    st = _settings_envio(db)
    texto = data.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    ok, err = evolution_api.evolution_send_text(
        st.evolution_base_url,
        st.evolution_instance_name,
        st.evolution_api_key,
        c.wa_id,
        texto,
    )
    if not ok:
        raise HTTPException(status_code=502, detail=err or "Falha ao enviar pela Evolution API")
    m = WhatsappMensagem(
        chat_id=chat_id,
        direcao="outbound",
        corpo=texto,
        wa_message_id=None,
        atendente_id=atendente.id,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    m = db.query(WhatsappMensagem).options(joinedload(WhatsappMensagem.atendente)).filter(WhatsappMensagem.id == m.id).first()
    assert m is not None
    return _mensagem_read(m)


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
