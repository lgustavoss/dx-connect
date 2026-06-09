from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.auth import exigir_admin, obter_atendente_atual
from app.core.audit import registrar_audit
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.database import get_db
from app.models.atendente import Atendente
from app.models.ticket import Ticket
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.ticket_classificacao import (
    TicketMotivoCreate,
    TicketMotivoRead,
    TicketMotivoUpdate,
    TicketNaturezaCreate,
    TicketNaturezaRead,
    TicketNaturezaUpdate,
)

router = APIRouter(tags=["ticket-catalogos"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 50


class OrdenarCatalogo(str, Enum):
    nome = "nome"
    slug = "slug"
    ordem = "ordem"
    ativo = "ativo"


def _motivo_para_read(row: TicketMotivo) -> TicketMotivoRead:
    return TicketMotivoRead(
        id=row.id,
        natureza_id=row.natureza_id,
        nome=row.nome,
        slug=row.slug,
        ordem=row.ordem,
        ativo=row.ativo,
        natureza_nome=row.natureza.nome if row.natureza else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/ticket-naturezas", response_model=ListaPaginada[TicketNaturezaRead])
def listar_naturezas(
    incluir_inativos: bool = Query(False),
    busca: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarCatalogo | None = Query(OrdenarCatalogo.ordem),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(TicketNatureza)
    if not incluir_inativos:
        q = q.filter(TicketNatureza.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(TicketNatureza.nome.ilike(term), TicketNatureza.slug.ilike(term)))
    total = q.count()
    if ordenar_por == OrdenarCatalogo.nome:
        order_cols = [expr_ordem(TicketNatureza.nome, ordem), expr_ordem(TicketNatureza.id, ordem)]
    elif ordenar_por == OrdenarCatalogo.slug:
        order_cols = [expr_ordem(TicketNatureza.slug, ordem), expr_ordem(TicketNatureza.id, ordem)]
    elif ordenar_por == OrdenarCatalogo.ativo:
        order_cols = [expr_ordem(TicketNatureza.ativo, ordem), expr_ordem(TicketNatureza.ordem, ordem)]
    else:
        order_cols = [expr_ordem(TicketNatureza.ordem, ordem), expr_ordem(TicketNatureza.nome, ordem)]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=items, total=total)


@router.post("/ticket-naturezas", response_model=TicketNaturezaRead, status_code=201)
def criar_natureza(
    data: TicketNaturezaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    if db.query(TicketNatureza).filter(TicketNatureza.slug == data.slug).first():
        raise HTTPException(status_code=400, detail="Slug de natureza já existe.")
    row = TicketNatureza(**data.model_dump())
    db.add(row)
    db.flush()
    registrar_audit(db, "ticket_natureza", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/ticket-naturezas/{natureza_id}", response_model=TicketNaturezaRead)
def atualizar_natureza(
    natureza_id: int,
    data: TicketNaturezaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = db.query(TicketNatureza).filter(TicketNatureza.id == natureza_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Natureza não encontrada.")
    payload = data.model_dump(exclude_unset=True)
    if "slug" in payload:
        dup = (
            db.query(TicketNatureza)
            .filter(TicketNatureza.slug == payload["slug"], TicketNatureza.id != natureza_id)
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="Slug de natureza já existe.")
    for k, v in payload.items():
        setattr(row, k, v)
    registrar_audit(db, "ticket_natureza", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.get("/ticket-motivos", response_model=ListaPaginada[TicketMotivoRead])
def listar_motivos(
    natureza_id: int | None = Query(None),
    incluir_inativos: bool = Query(False),
    busca: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarCatalogo | None = Query(OrdenarCatalogo.ordem),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(TicketMotivo).options(joinedload(TicketMotivo.natureza))
    if natureza_id is not None:
        q = q.filter(TicketMotivo.natureza_id == natureza_id)
    if not incluir_inativos:
        q = q.filter(TicketMotivo.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(TicketMotivo.nome.ilike(term), TicketMotivo.slug.ilike(term)))
    total = q.count()
    if ordenar_por == OrdenarCatalogo.nome:
        order_cols = [expr_ordem(TicketMotivo.nome, ordem), expr_ordem(TicketMotivo.id, ordem)]
    elif ordenar_por == OrdenarCatalogo.slug:
        order_cols = [expr_ordem(TicketMotivo.slug, ordem), expr_ordem(TicketMotivo.id, ordem)]
    elif ordenar_por == OrdenarCatalogo.ativo:
        order_cols = [expr_ordem(TicketMotivo.ativo, ordem), expr_ordem(TicketMotivo.ordem, ordem)]
    else:
        order_cols = [expr_ordem(TicketMotivo.ordem, ordem), expr_ordem(TicketMotivo.nome, ordem)]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_motivo_para_read(i) for i in items], total=total)


@router.post("/ticket-motivos", response_model=TicketMotivoRead, status_code=201)
def criar_motivo(
    data: TicketMotivoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    natureza = db.query(TicketNatureza).filter(TicketNatureza.id == data.natureza_id).first()
    if not natureza:
        raise HTTPException(status_code=404, detail="Natureza não encontrada.")
    dup = (
        db.query(TicketMotivo)
        .filter(TicketMotivo.natureza_id == data.natureza_id, TicketMotivo.slug == data.slug)
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="Slug de motivo já existe nesta natureza.")
    row = TicketMotivo(**data.model_dump())
    db.add(row)
    db.flush()
    registrar_audit(db, "ticket_motivo", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    row = (
        db.query(TicketMotivo)
        .options(joinedload(TicketMotivo.natureza))
        .filter(TicketMotivo.id == row.id)
        .first()
    )
    return _motivo_para_read(row)


@router.patch("/ticket-motivos/{motivo_id}", response_model=TicketMotivoRead)
def atualizar_motivo(
    motivo_id: int,
    data: TicketMotivoUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = (
        db.query(TicketMotivo)
        .options(joinedload(TicketMotivo.natureza))
        .filter(TicketMotivo.id == motivo_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Motivo não encontrado.")
    payload = data.model_dump(exclude_unset=True)
    natureza_id = payload.get("natureza_id", row.natureza_id)
    if "natureza_id" in payload:
        if not db.query(TicketNatureza).filter(TicketNatureza.id == natureza_id).first():
            raise HTTPException(status_code=404, detail="Natureza não encontrada.")
    if "slug" in payload or "natureza_id" in payload:
        slug = payload.get("slug", row.slug)
        dup = (
            db.query(TicketMotivo)
            .filter(
                TicketMotivo.natureza_id == natureza_id,
                TicketMotivo.slug == slug,
                TicketMotivo.id != motivo_id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="Slug de motivo já existe nesta natureza.")
    if payload.get("ativo") is False:
        em_uso = db.query(Ticket.id).filter(Ticket.motivo_id == motivo_id).first()
        if em_uso:
            pass  # permitir desativar mesmo em uso — leitura histórica mantida
    for k, v in payload.items():
        setattr(row, k, v)
    registrar_audit(db, "ticket_motivo", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return _motivo_para_read(row)
