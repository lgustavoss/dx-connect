from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, asc

from app.database import get_db
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.models import Rede, Empresa, FuncionarioRede, FuncionarioRedeEmpresa
from app.models.atendente import Atendente
from app.schemas.rede import RedeCreate, RedeUpdate, RedeRead
from app.schemas.funcionario_rede import FuncionarioRedeComVinculo
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import obter_atendente_atual, exigir_admin
from app.core.audit import registrar_audit

router = APIRouter(prefix="/redes", tags=["redes"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarRedesPor(str, Enum):
    nome = "nome"
    ativo = "ativo"
    created_at = "created_at"


@router.get("", response_model=ListaPaginada[RedeRead])
def listar_redes(
    incluir_inativos: bool = Query(False, description="Incluir redes inativas"),
    busca: str | None = Query(None, description="Filtra por nome"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarRedesPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    q = db.query(Rede).filter(Rede.tenant_id == atendente.tenant_id)
    if not incluir_inativos:
        q = q.filter(Rede.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(Rede.nome.ilike(term))
    total = q.count()
    if ordenar_por is None:
        order_cols = [Rede.nome.asc(), Rede.id.asc()]
    else:
        if ordenar_por == OrdenarRedesPor.nome:
            primary = expr_ordem(Rede.nome, ordem)
        elif ordenar_por == OrdenarRedesPor.ativo:
            primary = expr_ordem(Rede.ativo, ordem)
        else:
            primary = expr_ordem(Rede.created_at, ordem)
        order_cols = [primary, expr_ordem(Rede.id, ordem)]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=items, total=total)


@router.post("", response_model=RedeRead, status_code=201)
def criar_rede(
    data: RedeCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    rede = Rede(**data.model_dump(), tenant_id=atendente.tenant_id)
    db.add(rede)
    db.flush()
    registrar_audit(db, "rede", rede.id, "create", atendente.id)
    db.commit()
    db.refresh(rede)
    return rede


class OrdenarFuncRedePor(str, Enum):
    nome = "nome"
    email = "email"
    tipo = "tipo"


@router.get("/{rede_id}/funcionarios", response_model=ListaPaginada[FuncionarioRedeComVinculo])
def listar_funcionarios_da_rede(
    rede_id: int,
    incluir_inativos: bool = Query(False, description="Incluir funcionários inativos"),
    busca: str | None = Query(None, description="Filtra por nome ou e-mail"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarFuncRedePor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    rede = db.query(Rede).filter(Rede.id == rede_id).first()
    if not rede:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rede não encontrada")
    ids_empresas_da_rede = [r[0] for r in db.query(Empresa.id).filter(Empresa.rede_id == rede_id).all()]
    # Sócios da rede, colaboradores de alguma empresa da rede, supervisores vinculados a alguma empresa da rede
    condicoes = [FuncionarioRede.rede_id == rede_id]
    if ids_empresas_da_rede:
        condicoes.append(FuncionarioRede.empresa_id.in_(ids_empresas_da_rede))
        condicoes.append(
            FuncionarioRede.id.in_(
                db.query(FuncionarioRedeEmpresa.funcionario_id).filter(
                    FuncionarioRedeEmpresa.empresa_id.in_(ids_empresas_da_rede)
                )
            )
        )
    q = (
        db.query(FuncionarioRede)
        .options(joinedload(FuncionarioRede.empresas_supervisor).joinedload(FuncionarioRedeEmpresa.empresa))
        .filter(or_(*condicoes))
    )
    if not incluir_inativos:
        q = q.filter(FuncionarioRede.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(FuncionarioRede.nome.ilike(term), FuncionarioRede.email.ilike(term)))
    total = q.count()
    if ordenar_por is None:
        order_cols = [FuncionarioRede.nome.asc(), FuncionarioRede.id.asc()]
    elif ordenar_por == OrdenarFuncRedePor.nome:
        order_cols = [expr_ordem(FuncionarioRede.nome, ordem), expr_ordem(FuncionarioRede.id, ordem)]
    elif ordenar_por == OrdenarFuncRedePor.email:
        order_cols = [expr_ordem(FuncionarioRede.email, ordem), expr_ordem(FuncionarioRede.id, ordem)]
    else:
        order_cols = [expr_ordem(FuncionarioRede.tipo, ordem), expr_ordem(FuncionarioRede.id, ordem)]
    rows = q.order_by(*order_cols).offset(offset).limit(limit).all()
    result = []
    for f in rows:
        if f.tipo == "socio":
            vinculado_a = "Sócio da rede"
        elif f.tipo == "colaborador" and f.empresa_id:
            emp = db.query(Empresa).filter(Empresa.id == f.empresa_id).first()
            vinculado_a = emp.nome if emp else "—"
        elif f.tipo == "supervisor":
            nomes = [
                e.empresa.nome
                for e in f.empresas_supervisor
                if e.empresa_id in ids_empresas_da_rede
            ]
            vinculado_a = ", ".join(nomes) if nomes else "—"
        else:
            vinculado_a = "—"
        result.append(
            FuncionarioRedeComVinculo(
                id=f.id,
                nome=f.nome,
                email=f.email,
                telefone=getattr(f, "telefone", None),
                tipo=f.tipo,
                ativo=f.ativo,
                rede_id=f.rede_id,
                empresa_id=f.empresa_id,
                empresa_ids=[e.empresa_id for e in f.empresas_supervisor],
                created_at=f.created_at,
                updated_at=f.updated_at,
                vinculado_a=vinculado_a,
            )
        )
    return ListaPaginada(items=result, total=total)


@router.get("/{rede_id}", response_model=RedeRead)
def obter_rede(
    rede_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    rede = db.query(Rede).filter(Rede.id == rede_id).first()
    if not rede:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rede não encontrada")
    return rede


@router.patch("/{rede_id}", response_model=RedeRead)
def atualizar_rede(
    rede_id: int,
    data: RedeUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    rede = db.query(Rede).filter(Rede.id == rede_id).first()
    if not rede:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rede não encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(rede, k, v)
    registrar_audit(db, "rede", rede_id, "update", atendente.id)
    db.commit()
    db.refresh(rede)
    return rede


@router.delete("/{rede_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_rede(
    rede_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    rede = db.query(Rede).filter(Rede.id == rede_id).first()
    if not rede:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rede não encontrada")
    empresas_na_rede = db.query(Empresa).filter(Empresa.rede_id == rede_id).count()
    if empresas_na_rede > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir uma rede que possua empresas ativas. Remova ou transfira as empresas antes. Sugere-se inativar o registro.",
        )
    db.delete(rede)
    db.commit()
