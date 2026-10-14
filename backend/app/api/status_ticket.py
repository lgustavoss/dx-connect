from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, asc
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.models import StatusTicket
from app.models.atendente import Atendente
from app.schemas.status_ticket import StatusTicketCreate, StatusTicketUpdate, StatusTicketRead
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import obter_atendente_atual, exigir_permissao
from app.core.audit import registrar_audit

router = APIRouter(prefix="/status-ticket", tags=["status-ticket"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarStatusPor(str, Enum):
    nome = "nome"
    slug = "slug"
    ordem = "ordem"
    ativo = "ativo"


@router.get("", response_model=ListaPaginada[StatusTicketRead])
def listar(
    incluir_inativos: bool = Query(False, description="Incluir status inativos"),
    busca: str | None = Query(None, description="Filtra por nome ou slug"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarStatusPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(StatusTicket)
    if not incluir_inativos:
        q = q.filter(StatusTicket.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(StatusTicket.nome.ilike(term), StatusTicket.slug.ilike(term)))
    total = q.count()
    if ordenar_por is None:
        order_cols = [StatusTicket.ordem.asc(), StatusTicket.nome.asc(), StatusTicket.id.asc()]
    elif ordenar_por == OrdenarStatusPor.nome:
        order_cols = [expr_ordem(StatusTicket.nome, ordem), expr_ordem(StatusTicket.id, ordem)]
    elif ordenar_por == OrdenarStatusPor.slug:
        order_cols = [expr_ordem(StatusTicket.slug, ordem), expr_ordem(StatusTicket.id, ordem)]
    elif ordenar_por == OrdenarStatusPor.ordem:
        order_cols = [expr_ordem(StatusTicket.ordem, ordem), expr_ordem(StatusTicket.id, ordem)]
    else:
        order_cols = [expr_ordem(StatusTicket.ativo, ordem), expr_ordem(StatusTicket.id, ordem)]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=items, total=total)


@router.post("", response_model=StatusTicketRead, status_code=201)
def criar(
    data: StatusTicketCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("status_ticket.criar")),
):
    if db.query(StatusTicket).filter(StatusTicket.slug == data.slug).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug já existe")
    st = StatusTicket(**data.model_dump())
    db.add(st)
    db.flush()
    registrar_audit(db, "status_ticket", st.id, "create", atendente.id)
    db.commit()
    db.refresh(st)
    return st


@router.get("/{status_id}", response_model=StatusTicketRead)
def obter(
    status_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_permissao("status_ticket.ver")),
):
    st = db.query(StatusTicket).filter(StatusTicket.id == status_id).first()
    if not st:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status não encontrado")
    return st


@router.patch("/{status_id}", response_model=StatusTicketRead)
def atualizar(
    status_id: int,
    data: StatusTicketUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("status_ticket.editar")),
):
    st = db.query(StatusTicket).filter(StatusTicket.id == status_id).first()
    if not st:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(st, k, v)
    registrar_audit(db, "status_ticket", status_id, "update", atendente.id)
    db.commit()
    db.refresh(st)
    return st


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    status_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_permissao("status_ticket.excluir")),
):
    st = db.query(StatusTicket).filter(StatusTicket.id == status_id).first()
    if not st:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status não encontrado")
    db.delete(st)
    db.commit()
