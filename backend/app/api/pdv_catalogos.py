from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, obter_atendente_atual
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.database import get_db
from app.models.atendente import Atendente
from app.models.empresa_pdv import PdvRotulo, PdvTipoAcessoRemoto
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.pdv import (
    PdvRotuloCreate,
    PdvRotuloRead,
    PdvRotuloUpdate,
    PdvTipoAcessoRemotoCreate,
    PdvTipoAcessoRemotoRead,
    PdvTipoAcessoRemotoUpdate,
)

router = APIRouter(tags=["pdv-catalogos"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 50


class OrdenarCatalogo(str, Enum):
    nome = "nome"
    ordem_exibicao = "ordem_exibicao"
    ativo = "ativo"


def _listar_catalogo(db, model, incluir_inativos, busca, offset, limit, ordenar_por, ordem):
    q = db.query(model)
    if not incluir_inativos:
        q = q.filter(model.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(model.nome.ilike(term))
    total = q.count()
    if ordenar_por == OrdenarCatalogo.nome:
        order_cols = [expr_ordem(model.nome, ordem), expr_ordem(model.id, ordem)]
    elif ordenar_por == OrdenarCatalogo.ativo:
        order_cols = [expr_ordem(model.ativo, ordem), expr_ordem(model.ordem_exibicao, ordem)]
    else:
        order_cols = [expr_ordem(model.ordem_exibicao, ordem), expr_ordem(model.nome, ordem)]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=items, total=total)


@router.get("/pdv-rotulos", response_model=ListaPaginada[PdvRotuloRead])
def listar_rotulos(
    incluir_inativos: bool = Query(False),
    busca: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarCatalogo | None = Query(OrdenarCatalogo.ordem_exibicao),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    return _listar_catalogo(db, PdvRotulo, incluir_inativos, busca, offset, limit, ordenar_por, ordem)


@router.post("/pdv-rotulos", response_model=PdvRotuloRead, status_code=201)
def criar_rotulo(
    data: PdvRotuloCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = PdvRotulo(**data.model_dump())
    db.add(row)
    db.flush()
    registrar_audit(db, "pdv_rotulo", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/pdv-rotulos/{rotulo_id}", response_model=PdvRotuloRead)
def atualizar_rotulo(
    rotulo_id: int,
    data: PdvRotuloUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = db.query(PdvRotulo).filter(PdvRotulo.id == rotulo_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Rótulo não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    registrar_audit(db, "pdv_rotulo", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.get("/pdv-tipos-acesso-remoto", response_model=ListaPaginada[PdvTipoAcessoRemotoRead])
def listar_tipos_acesso(
    incluir_inativos: bool = Query(False),
    busca: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarCatalogo | None = Query(OrdenarCatalogo.ordem_exibicao),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(obter_atendente_atual),
):
    return _listar_catalogo(db, PdvTipoAcessoRemoto, incluir_inativos, busca, offset, limit, ordenar_por, ordem)


@router.post("/pdv-tipos-acesso-remoto", response_model=PdvTipoAcessoRemotoRead, status_code=201)
def criar_tipo_acesso(
    data: PdvTipoAcessoRemotoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = PdvTipoAcessoRemoto(**data.model_dump())
    db.add(row)
    db.flush()
    registrar_audit(db, "pdv_tipo_acesso_remoto", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/pdv-tipos-acesso-remoto/{tipo_id}", response_model=PdvTipoAcessoRemotoRead)
def atualizar_tipo_acesso(
    tipo_id: int,
    data: PdvTipoAcessoRemotoUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = db.query(PdvTipoAcessoRemoto).filter(PdvTipoAcessoRemoto.id == tipo_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Tipo de acesso remoto não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    registrar_audit(db, "pdv_tipo_acesso_remoto", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row
