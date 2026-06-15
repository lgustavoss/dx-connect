from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.models import Setor
from app.models.atendente import Atendente
from app.schemas.setor import SetorCreate, SetorUpdate, SetorRead
from app.schemas.setor_distribuicao import SetorDistribuicaoRead, SetorDistribuicaoUpdate
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import obter_atendente_atual, exigir_admin
from app.core.audit import registrar_audit
from app.core.setor_scope import ids_setores_visiveis_atendente
from app.services.ticket_distribuicao import setor_para_distribuicao_read, validar_atendentes_elegiveis

router = APIRouter(prefix="/setores", tags=["setores"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


def _setor_para_read(setor: Setor) -> SetorRead:
    base = SetorRead.model_validate(setor)
    return base.model_copy(update={"distribuicao": setor_para_distribuicao_read(setor)})


class OrdenarSetoresPor(str, Enum):
    nome = "nome"
    slug = "slug"
    ativo = "ativo"


@router.get("", response_model=ListaPaginada[SetorRead])
def listar_setores(
    incluir_inativos: bool = Query(False, description="Incluir setores inativos"),
    busca: str | None = Query(None, description="Filtra por nome"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarSetoresPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    q = db.query(Setor).filter(Setor.tenant_id == atendente.tenant_id)
    if atendente.role != "admin":
        vis = ids_setores_visiveis_atendente(db, atendente)
        q = q.filter(Setor.id.in_(vis))
    if not incluir_inativos:
        q = q.filter(Setor.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(Setor.nome.ilike(term))
    total = q.count()
    if ordenar_por is None:
        order_cols = [Setor.nome.asc(), Setor.id.asc()]
    elif ordenar_por == OrdenarSetoresPor.nome:
        order_cols = [expr_ordem(Setor.nome, ordem), expr_ordem(Setor.id, ordem)]
    elif ordenar_por == OrdenarSetoresPor.slug:
        order_cols = [expr_ordem(Setor.slug, ordem), expr_ordem(Setor.id, ordem)]
    else:
        order_cols = [expr_ordem(Setor.ativo, ordem), expr_ordem(Setor.id, ordem)]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_setor_para_read(s) for s in items], total=total)


@router.post("", response_model=SetorRead, status_code=201)
def criar_setor(
    data: SetorCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    if (
        db.query(Setor)
        .filter(Setor.tenant_id == atendente.tenant_id, Setor.slug == data.slug)
        .first()
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug já existe")
    setor = Setor(**data.model_dump(), tenant_id=atendente.tenant_id)
    db.add(setor)
    db.flush()
    registrar_audit(db, "setor", setor.id, "create", atendente.id)
    db.commit()
    db.refresh(setor)
    return _setor_para_read(setor)


@router.get("/{setor_id}", response_model=SetorRead)
def obter_setor(
    setor_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    setor = db.query(Setor).filter(Setor.id == setor_id).first()
    if not setor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")
    return _setor_para_read(setor)


@router.patch("/{setor_id}", response_model=SetorRead)
def atualizar_setor(
    setor_id: int,
    data: SetorUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    setor = db.query(Setor).filter(Setor.id == setor_id).first()
    if not setor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(setor, k, v)
    registrar_audit(db, "setor", setor_id, "update", atendente.id)
    db.commit()
    db.refresh(setor)
    return _setor_para_read(setor)


@router.put("/{setor_id}/distribuicao", response_model=SetorDistribuicaoRead)
def atualizar_distribuicao_setor(
    setor_id: int,
    data: SetorDistribuicaoUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    setor = db.query(Setor).filter(Setor.id == setor_id, Setor.tenant_id == atendente.tenant_id).first()
    if not setor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")
    try:
        elegiveis = validar_atendentes_elegiveis(db, setor, data.atendentes_elegiveis)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    setor.distribuicao_modo = data.modo.value
    setor.distribuicao_timeout_minutos = data.timeout_minutos
    setor.distribuicao_estrategia = data.estrategia.value
    setor.distribuicao_atendentes_elegiveis = elegiveis
    registrar_audit(db, "setor", setor_id, "distribuicao_update", atendente.id)
    db.commit()
    db.refresh(setor)
    return setor_para_distribuicao_read(setor)


@router.delete("/{setor_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_setor(
    setor_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    setor = db.query(Setor).filter(Setor.id == setor_id).first()
    if not setor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado")
    db.delete(setor)
    db.commit()
