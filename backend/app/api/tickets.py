from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, asc, desc, nullslast

from app.database import get_db
from app.models import Ticket, TicketHistorico, TicketMensagem, Empresa, Setor, StatusTicket, Atendente, Rede
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketRead,
    TicketHistoricoRead,
    TicketMensagemCreate,
    TicketMensagemRead,
)
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import obter_atendente_atual
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.core.setor_scope import ids_setores_visiveis_atendente, atendente_atende_algum_id_setor

router = APIRouter(prefix="/tickets", tags=["tickets"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarTicketsPor(str, Enum):
    protocolo = "protocolo"
    rede = "rede"
    empresa = "empresa"
    setor = "setor"
    assunto = "assunto"
    status = "status"
    responsavel = "responsavel"
    fechado_em = "fechado_em"

class SituacaoTicket(str, Enum):
    abertos = "abertos"
    fechados = "fechados"
    todos = "todos"


def _gerar_protocolo(db: Session) -> str:
    """Gera próximo número de protocolo único (sequencial global)."""
    from sqlalchemy import func
    r = db.query(func.max(Ticket.id)).scalar() or 0
    return str(10000 + r + 1)


def _ticket_para_read(t: Ticket) -> TicketRead:
    return TicketRead(
        id=t.id,
        protocolo=t.protocolo,
        empresa_id=t.empresa_id,
        setor_id=t.setor_id,
        status_id=t.status_id,
        atendente_id=t.atendente_id,
        aberto_por_id=t.aberto_por_id,
        assunto=t.assunto,
        descricao=t.descricao,
        fechado_em=t.fechado_em,
        created_at=t.created_at,
        updated_at=t.updated_at,
        empresa_nome=t.empresa.nome if t.empresa else None,
        rede_nome=t.empresa.rede.nome if t.empresa and t.empresa.rede else None,
        setor_nome=t.setor.nome if t.setor else None,
        status_nome=t.status.nome if t.status else None,
        atendente_nome=t.atendente.nome if t.atendente else None,
    )


def _pode_ver_ticket(db: Session, atendente: Atendente, ticket: Ticket) -> bool:
    if atendente.role == "admin":
        return True
    vis = ids_setores_visiveis_atendente(db, atendente)
    return ticket.setor_id in vis


def _pode_enviar_mensagem_publica(atendente: Atendente, ticket: Ticket) -> bool:
    """Andamento visível na conversa (tipo publico): admin, responsável ou fila sem responsável."""
    if atendente.role == "admin":
        return True
    if ticket.atendente_id is None:
        return True
    return ticket.atendente_id == atendente.id


@router.get("", response_model=ListaPaginada[TicketRead])
def listar(
    empresa_id: int | None = Query(None),
    rede_id: int | None = Query(None, description="Tickets de empresas desta rede"),
    setor_id: int | None = Query(None),
    status_id: int | None = Query(None),
    protocolo: str | None = Query(None, description="Legado: use busca"),
    busca: str | None = Query(None, description="Protocolo, assunto ou nome da empresa"),
    sem_responsavel: bool = Query(
        False,
        description="Somente tickets sem atendente atribuído (fila do setor)",
    ),
    meus: bool = Query(False, description="Somente tickets em que você é o responsável"),
    atendente_id: int | None = Query(
        None,
        description="Filtrar por responsável (apenas administradores)",
    ),
    situacao: SituacaoTicket = Query(
        SituacaoTicket.abertos,
        description="abertos = fechado_em vazio; fechados = fechado_em preenchido; todos = sem filtro",
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarTicketsPor | None = Query(
        None,
        description="Coluna para ordenação (default: data de criação, mais recentes primeiro)",
    ),
    ordem: OrdemLista = Query(
        OrdemLista.asc,
        description="asc = A→Z / menor primeiro; desc = Z→A / maior primeiro",
    ),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(Ticket).join(Ticket.empresa).join(Ticket.setor).join(Ticket.status)
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter(Ticket.setor_id.in_(vis))
    if empresa_id is not None:
        q = q.filter(Ticket.empresa_id == empresa_id)
    if rede_id is not None:
        q = q.filter(Empresa.rede_id == rede_id)
    if setor_id is not None:
        q = q.filter(Ticket.setor_id == setor_id)
    if status_id is not None:
        q = q.filter(Ticket.status_id == status_id)
    if atendente_id is not None:
        if atendente.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas administradores podem filtrar por outro responsável",
            )
        q = q.filter(Ticket.atendente_id == atendente_id)
    elif meus:
        q = q.filter(Ticket.atendente_id == atendente.id)
    if sem_responsavel:
        q = q.filter(Ticket.atendente_id.is_(None))

    if situacao == SituacaoTicket.abertos:
        q = q.filter(Ticket.fechado_em.is_(None))
    elif situacao == SituacaoTicket.fechados:
        q = q.filter(Ticket.fechado_em.is_not(None))
    if protocolo and protocolo.strip():
        q = q.filter(Ticket.protocolo.ilike(f"%{protocolo.strip()}%"))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                Ticket.protocolo.ilike(term),
                Ticket.assunto.ilike(term),
                Empresa.nome.ilike(term),
            )
        )
    total = q.count()

    if ordenar_por is None:
        # Em finalizados, o mais útil é ordenar por data de fechamento (mais recentes primeiro).
        if situacao == SituacaoTicket.fechados:
            order_cols = [Ticket.fechado_em.desc().nullslast(), Ticket.id.desc()]
        else:
            order_cols = [Ticket.created_at.desc(), Ticket.id.desc()]
    else:
        if ordenar_por == OrdenarTicketsPor.responsavel:
            q = q.outerjoin(Ticket.atendente)
        elif ordenar_por == OrdenarTicketsPor.rede:
            q = q.join(Empresa.rede)

        if ordenar_por == OrdenarTicketsPor.protocolo:
            primary = expr_ordem(Ticket.protocolo, ordem)
        elif ordenar_por == OrdenarTicketsPor.rede:
            primary = expr_ordem(Rede.nome, ordem)
        elif ordenar_por == OrdenarTicketsPor.empresa:
            primary = expr_ordem(Empresa.nome, ordem)
        elif ordenar_por == OrdenarTicketsPor.setor:
            primary = expr_ordem(Setor.nome, ordem)
        elif ordenar_por == OrdenarTicketsPor.assunto:
            primary = expr_ordem(Ticket.assunto, ordem)
        elif ordenar_por == OrdenarTicketsPor.status:
            primary = expr_ordem(StatusTicket.nome, ordem)
        elif ordenar_por == OrdenarTicketsPor.fechado_em:
            primary = nullslast(expr_ordem(Ticket.fechado_em, ordem))
        else:
            primary = nullslast(expr_ordem(Atendente.nome, ordem))
        tie = expr_ordem(Ticket.id, ordem)
        order_cols = [primary, tie]

    rows = (
        q.options(
            joinedload(Ticket.empresa).joinedload(Empresa.rede),
            joinedload(Ticket.setor),
            joinedload(Ticket.status),
            joinedload(Ticket.atendente),
        )
        .order_by(*order_cols)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ListaPaginada(items=[_ticket_para_read(t) for t in rows], total=total)


@router.post("", response_model=TicketRead, status_code=201)
def criar(
    data: TicketCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    # Atendente só pode abrir ticket em setor que ele atende
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        if data.setor_id not in vis:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este setor")
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    setor = db.query(Setor).filter(Setor.id == data.setor_id).first()
    if not setor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")
    # Status inicial: primeiro status ativo por ordem (ex.: «Aguardando atendimento» na fila do setor)
    status_inicial = db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).order_by(StatusTicket.ordem).first()
    if not status_inicial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cadastre ao menos um status de ticket")
    protocolo = _gerar_protocolo(db)
    ticket = Ticket(
        protocolo=protocolo,
        empresa_id=data.empresa_id,
        setor_id=data.setor_id,
        status_id=status_inicial.id,
        assunto=data.assunto,
        descricao=data.descricao,
        aberto_por_id=data.aberto_por_id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    corpo_abertura = (data.descricao or "").strip() or "—"
    db.add(
        TicketMensagem(
            ticket_id=ticket.id,
            atendente_id=atendente.id,
            tipo="abertura",
            corpo=corpo_abertura,
        )
    )
    db.commit()
    return _ticket_para_read(ticket)


@router.delete("/{ticket_id}")
def excluir_nao_permitido(ticket_id: int):
    """Tickets não podem ser excluídos; use alteração de status (ex.: fechado) conforme regra de negócio."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tickets não podem ser excluídos. Para encerrar, altere o status do ticket (ex.: Fechado).",
    )


@router.get("/{ticket_id}", response_model=TicketRead)
def obter(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.empresa).joinedload(Empresa.rede),
            joinedload(Ticket.setor),
            joinedload(Ticket.status),
            joinedload(Ticket.atendente),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    return _ticket_para_read(ticket)


@router.get("/{ticket_id}/historico", response_model=list[TicketHistoricoRead])
def historico(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    rows = (
        db.query(TicketHistorico)
        .options(joinedload(TicketHistorico.atendente))
        .filter(TicketHistorico.ticket_id == ticket_id)
        .order_by(TicketHistorico.created_at.desc())
        .all()
    )
    return [
        TicketHistoricoRead(
            id=h.id,
            ticket_id=h.ticket_id,
            atendente_id=h.atendente_id,
            atendente_nome=h.atendente.nome if h.atendente else None,
            campo=h.campo,
            valor_antigo=h.valor_antigo,
            valor_novo=h.valor_novo,
            created_at=h.created_at,
        )
        for h in rows
    ]


def _mensagem_para_read(m: TicketMensagem) -> TicketMensagemRead:
    return TicketMensagemRead(
        id=m.id,
        ticket_id=m.ticket_id,
        atendente_id=m.atendente_id,
        atendente_nome=m.atendente.nome if m.atendente else None,
        tipo=m.tipo,
        corpo=m.corpo,
        created_at=m.created_at,
    )


@router.get("/{ticket_id}/mensagens", response_model=list[TicketMensagemRead])
def listar_mensagens(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    rows = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.ticket_id == ticket_id)
        .order_by(TicketMensagem.created_at.asc())
        .all()
    )
    return [_mensagem_para_read(m) for m in rows]


@router.post("/{ticket_id}/mensagens", response_model=TicketMensagemRead, status_code=201)
def criar_mensagem(
    ticket_id: int,
    data: TicketMensagemCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    if ticket.fechado_em is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket fechado. Reabra o ticket para enviar novas mensagens.",
        )
    if data.tipo == "publico" and not _pode_enviar_mensagem_publica(atendente, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o responsável pelo chamado ou um administrador pode enviar mensagem da equipe. "
            "Colaboradores do mesmo setor podem usar comentário interno.",
        )
    corpo = data.corpo.strip()
    if not corpo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem vazia")
    m = TicketMensagem(
        ticket_id=ticket_id,
        atendente_id=atendente.id,
        tipo=data.tipo,
        corpo=corpo,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    m = (
        db.query(TicketMensagem)
        .options(joinedload(TicketMensagem.atendente))
        .filter(TicketMensagem.id == m.id)
        .first()
    )
    assert m is not None
    return _mensagem_para_read(m)


def _registrar_historico(db: Session, ticket_id: int, atendente_id: int | None, campo: str, valor_antigo: str | None, valor_novo: str | None):
    db.add(TicketHistorico(
        ticket_id=ticket_id,
        atendente_id=atendente_id,
        campo=campo,
        valor_antigo=valor_antigo,
        valor_novo=valor_novo,
    ))


@router.post("/{ticket_id}/reabrir", response_model=TicketRead)
def reabrir(
    ticket_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    if atendente.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores podem reabrir tickets")
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if ticket.fechado_em is None:
        return _ticket_para_read(ticket)

    # Status para retorno: primeiro status ativo que não seja "fechado"
    status_reaberto = (
        db.query(StatusTicket)
        .filter(StatusTicket.ativo.is_(True))
        .order_by(StatusTicket.ordem.asc(), StatusTicket.id.asc())
        .all()
    )
    novo_status = None
    for st in status_reaberto:
        if (st.slug or "").lower() != "fechado":
            novo_status = st
            break
    if not novo_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cadastre um status não-final para reabrir")

    _registrar_historico(db, ticket.id, atendente.id, "fechado_em", str(ticket.fechado_em), "")
    if ticket.status_id != novo_status.id:
        _registrar_historico(db, ticket.id, atendente.id, "status_id", str(ticket.status_id), str(novo_status.id))

    ticket.fechado_em = None
    ticket.status_id = novo_status.id
    db.commit()
    db.refresh(ticket)
    return _ticket_para_read(ticket)


@router.patch("/{ticket_id}", response_model=TicketRead)
def atualizar(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado")
    if not _pode_ver_ticket(db, atendente, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para este ticket")
    if ticket.fechado_em is not None and atendente.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ticket fechado. Apenas administradores podem reabrir ou alterar este ticket.",
        )
    update = data.model_dump(exclude_unset=True)

    if "setor_id" in update:
        if atendente.role != "admin":
            permitidos = ids_setores_visiveis_atendente(db, atendente)
            if update["setor_id"] not in permitidos:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sem permissão para mover o ticket para este setor",
                )
        novo_setor = db.query(Setor).filter(Setor.id == update["setor_id"]).first()
        if not novo_setor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")

    setor_final = update["setor_id"] if "setor_id" in update else ticket.setor_id

    if "atendente_id" in update and update["atendente_id"] is not None:
        if not atendente_atende_algum_id_setor(db, update["atendente_id"], setor_final):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O responsável indicado não está vinculado ao setor do ticket.",
            )

    # Transferência: se o responsável atual não atende o setor de destino, volta à fila (sem responsável).
    if "setor_id" in update and update["setor_id"] != ticket.setor_id and "atendente_id" not in update:
        if ticket.atendente_id is not None and not atendente_atende_algum_id_setor(db, ticket.atendente_id, update["setor_id"]):
            update["atendente_id"] = None

    if "status_id" in update:
        antigo = str(ticket.status_id)
        novo = str(update["status_id"])
        _registrar_historico(db, ticket.id, atendente.id, "status_id", antigo, novo)
    if "atendente_id" in update:
        antigo = str(ticket.atendente_id) if ticket.atendente_id else ""
        novo_s = update["atendente_id"]
        novo = str(novo_s) if novo_s is not None else ""
        _registrar_historico(db, ticket.id, atendente.id, "atendente_id", antigo, novo)
    if "setor_id" in update:
        antigo = str(ticket.setor_id)
        novo = str(update["setor_id"])
        _registrar_historico(db, ticket.id, atendente.id, "setor_id", antigo, novo)

    for k, v in update.items():
        setattr(ticket, k, v)

    if "status_id" in update:
        st = db.query(StatusTicket).filter(StatusTicket.id == ticket.status_id).first()
        slug = (st.slug or "").lower() if st else ""
        if slug == "fechado":
            ticket.fechado_em = datetime.now(timezone.utc)
        else:
            ticket.fechado_em = None

    db.commit()
    db.refresh(ticket)
    return _ticket_para_read(ticket)
