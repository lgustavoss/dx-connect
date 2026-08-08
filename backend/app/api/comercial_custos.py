"""API admin do catálogo comercial de custos (#321 / #333)."""

from __future__ import annotations

from datetime import date
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import exigir_admin
from app.core.audit import registrar_audit
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.database import get_db
from app.models.atendente import Atendente
from app.models.comercial_custo import CustoCatalogoItem, SalarioMinimoReferencia
from app.schemas.comercial_custo import (
    CustoCatalogoItemCreate,
    CustoCatalogoItemRead,
    CustoCatalogoItemUpdate,
    CustoSimularRequest,
    CustoSimularResponse,
    SalarioMinimoAtualizarValor,
    SalarioMinimoCreate,
    SalarioMinimoRead,
    SalarioMinimoUpdate,
)
from app.schemas.lista_paginada import ListaPaginada
from app.services import comercial_custo as svc

router = APIRouter(prefix="/comercial", tags=["comercial-custos"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 50


class OrdenarSm(str, Enum):
    vigencia_inicio = "vigencia_inicio"
    valor = "valor"
    id = "id"


class OrdenarItem(str, Enum):
    nome = "nome"
    slug = "slug"
    ordem = "ordem"
    tipo = "tipo"
    ativo = "ativo"


@router.get("/salario-minimo", response_model=ListaPaginada[SalarioMinimoRead])
def listar_salario_minimo(
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarSm | None = Query(OrdenarSm.vigencia_inicio),
    ordem: OrdemLista = Query(OrdemLista.desc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    q = db.query(SalarioMinimoReferencia)
    total = q.count()
    if ordenar_por == OrdenarSm.valor:
        cols = [expr_ordem(SalarioMinimoReferencia.valor, ordem), expr_ordem(SalarioMinimoReferencia.id, ordem)]
    elif ordenar_por == OrdenarSm.id:
        cols = [expr_ordem(SalarioMinimoReferencia.id, ordem)]
    else:
        cols = [
            expr_ordem(SalarioMinimoReferencia.vigencia_inicio, ordem),
            expr_ordem(SalarioMinimoReferencia.id, ordem),
        ]
    items = q.order_by(*cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=items, total=total)


@router.get("/salario-minimo/na-data", response_model=SalarioMinimoRead | None)
def salario_minimo_na_data(
    data: date = Query(..., description="Data de referência"),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    return svc.obter_sm_na_data(db, data)


@router.post("/salario-minimo", response_model=SalarioMinimoRead, status_code=201)
def criar_salario_minimo(
    data: SalarioMinimoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.criar_sm(db, data)
    registrar_audit(db, "salario_minimo", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.post("/salario-minimo/atualizar-valor", response_model=SalarioMinimoRead, status_code=201)
def atualizar_valor_salario_minimo(
    data: SalarioMinimoAtualizarValor,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    """Novo valor a partir de uma data: fecha o vigente e mantém o histórico intacto."""
    row = svc.atualizar_valor_sm(db, data)
    registrar_audit(db, "salario_minimo", row.id, "atualizar_valor", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/salario-minimo/{sm_id}", response_model=SalarioMinimoRead)
def atualizar_salario_minimo(
    sm_id: int,
    data: SalarioMinimoUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = db.query(SalarioMinimoReferencia).filter(SalarioMinimoReferencia.id == sm_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Salário mínimo não encontrado.")
    row = svc.atualizar_sm(db, row, data)
    registrar_audit(db, "salario_minimo", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/salario-minimo/{sm_id}", status_code=204)
def excluir_salario_minimo(
    sm_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = db.query(SalarioMinimoReferencia).filter(SalarioMinimoReferencia.id == sm_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Salário mínimo não encontrado.")
    registrar_audit(db, "salario_minimo", row.id, "delete", atendente.id)
    db.delete(row)
    db.commit()
    return None


@router.get("/custos/itens", response_model=ListaPaginada[CustoCatalogoItemRead])
def listar_itens_custo(
    incluir_inativos: bool = Query(False),
    busca: str | None = Query(None),
    tipo: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarItem | None = Query(OrdenarItem.ordem),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    q = db.query(CustoCatalogoItem)
    if not incluir_inativos:
        q = q.filter(CustoCatalogoItem.ativo.is_(True))
    if tipo:
        q = q.filter(CustoCatalogoItem.tipo == tipo)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(CustoCatalogoItem.nome.ilike(term), CustoCatalogoItem.slug.ilike(term)))
    total = q.count()
    if ordenar_por == OrdenarItem.nome:
        cols = [expr_ordem(CustoCatalogoItem.nome, ordem), expr_ordem(CustoCatalogoItem.id, ordem)]
    elif ordenar_por == OrdenarItem.slug:
        cols = [expr_ordem(CustoCatalogoItem.slug, ordem), expr_ordem(CustoCatalogoItem.id, ordem)]
    elif ordenar_por == OrdenarItem.tipo:
        cols = [expr_ordem(CustoCatalogoItem.tipo, ordem), expr_ordem(CustoCatalogoItem.ordem, ordem)]
    elif ordenar_por == OrdenarItem.ativo:
        cols = [expr_ordem(CustoCatalogoItem.ativo, ordem), expr_ordem(CustoCatalogoItem.ordem, ordem)]
    else:
        cols = [expr_ordem(CustoCatalogoItem.ordem, ordem), expr_ordem(CustoCatalogoItem.nome, ordem)]
    items = q.order_by(*cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=items, total=total)


@router.post("/custos/itens", response_model=CustoCatalogoItemRead, status_code=201)
def criar_item_custo(
    data: CustoCatalogoItemCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.criar_item(db, data)
    registrar_audit(db, "custo_catalogo_item", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/custos/itens/{item_id}", response_model=CustoCatalogoItemRead)
def atualizar_item_custo(
    item_id: int,
    data: CustoCatalogoItemUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = db.query(CustoCatalogoItem).filter(CustoCatalogoItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item de custo não encontrado.")
    row = svc.atualizar_item(db, row, data)
    registrar_audit(db, "custo_catalogo_item", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/custos/itens/{item_id}", status_code=204)
def excluir_item_custo(
    item_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = db.query(CustoCatalogoItem).filter(CustoCatalogoItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item de custo não encontrado.")
    registrar_audit(db, "custo_catalogo_item", row.id, "delete", atendente.id)
    db.delete(row)
    db.commit()
    return None


@router.post("/custos/simular", response_model=CustoSimularResponse)
def simular_custo(
    body: CustoSimularRequest,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    """Simula pacote de custos; devolve também snapshot imutável (#331/#332/#335)."""
    return svc.simular_custo(
        db,
        item_ids=body.item_ids,
        quantidade_pdvs=body.quantidade_pdvs,
        data_referencia=body.data_referencia,
        desconto_posto_100k=body.desconto_posto_100k,
        tef_override=body.tef_override,
    )
