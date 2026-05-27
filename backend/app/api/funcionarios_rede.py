from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.models import FuncionarioRede, FuncionarioRedeEmpresa, Ticket, Empresa
from app.models.atendente import Atendente
from app.schemas.funcionario_rede import (
    EmpresaOpcaoRead,
    FuncionarioRedeCreate,
    FuncionarioRedeRead,
    FuncionarioRedeUpdate,
    RemetenteFuncionarioResolveRead,
)
from app.services.funcionario_rede_resolver import assert_email_unico_por_rede, resolver_remetente_por_email
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import exigir_admin
from app.core.audit import registrar_audit

router = APIRouter(prefix="/funcionarios-rede", tags=["funcionarios-rede"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarFuncionariosPor(str, Enum):
    nome = "nome"
    email = "email"
    tipo = "tipo"
    ativo = "ativo"
    rede_id = "rede_id"


def _para_read(f: FuncionarioRede) -> FuncionarioRedeRead:
    empresa_ids = [e.empresa_id for e in f.empresas_supervisor] if f.tipo == "supervisor" else []
    return FuncionarioRedeRead(
        id=f.id,
        nome=f.nome,
        email=f.email,
        tipo=f.tipo,
        ativo=f.ativo,
        rede_id=f.rede_id,
        empresa_id=f.empresa_id,
        empresa_ids=empresa_ids,
        created_at=f.created_at,
        updated_at=f.updated_at,
    )


@router.get("", response_model=ListaPaginada[FuncionarioRedeRead])
def listar(
    rede_id: int | None = Query(None),
    empresa_id: int | None = Query(None),
    tipo: str | None = Query(None),
    incluir_inativos: bool = Query(False, description="Incluir funcionários inativos"),
    busca: str | None = Query(None, description="Filtra por nome ou e-mail"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarFuncionariosPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    q = db.query(FuncionarioRede)
    if rede_id is not None:
        q = q.filter(FuncionarioRede.rede_id == rede_id)
    if empresa_id is not None:
        q = q.filter(
            (FuncionarioRede.empresa_id == empresa_id) |
            (FuncionarioRede.id.in_(
                db.query(FuncionarioRedeEmpresa.funcionario_id).filter(
                    FuncionarioRedeEmpresa.empresa_id == empresa_id
                )
            ))
        )
    if tipo:
        q = q.filter(FuncionarioRede.tipo == tipo)
    if not incluir_inativos:
        q = q.filter(FuncionarioRede.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(FuncionarioRede.nome.ilike(term), FuncionarioRede.email.ilike(term)))
    total = q.count()
    if ordenar_por is None:
        order_cols = [FuncionarioRede.nome.asc(), FuncionarioRede.id.asc()]
    elif ordenar_por == OrdenarFuncionariosPor.nome:
        order_cols = [expr_ordem(FuncionarioRede.nome, ordem), expr_ordem(FuncionarioRede.id, ordem)]
    elif ordenar_por == OrdenarFuncionariosPor.email:
        order_cols = [expr_ordem(FuncionarioRede.email, ordem), expr_ordem(FuncionarioRede.id, ordem)]
    elif ordenar_por == OrdenarFuncionariosPor.tipo:
        order_cols = [expr_ordem(FuncionarioRede.tipo, ordem), expr_ordem(FuncionarioRede.id, ordem)]
    elif ordenar_por == OrdenarFuncionariosPor.ativo:
        order_cols = [expr_ordem(FuncionarioRede.ativo, ordem), expr_ordem(FuncionarioRede.id, ordem)]
    else:
        order_cols = [expr_ordem(FuncionarioRede.rede_id, ordem), expr_ordem(FuncionarioRede.id, ordem)]
    rows = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_para_read(f) for f in rows], total=total)


@router.get("/resolver-por-email", response_model=RemetenteFuncionarioResolveRead)
def resolver_por_email(
    email: str = Query(..., min_length=3, max_length=255),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    rem = resolver_remetente_por_email(db, email)
    empresas = []
    for eid in rem.empresa_ids_opcao:
        emp = db.query(Empresa).filter(Empresa.id == eid).first()
        if emp:
            empresas.append(EmpresaOpcaoRead(id=emp.id, nome=emp.nome))
    return RemetenteFuncionarioResolveRead(
        email=rem.email,
        requer_cadastro=rem.requer_cadastro,
        conflito_multiplas_redes=rem.conflito_multiplas_redes,
        funcionario_id=rem.funcionario_id,
        rede_id=rem.rede_id,
        empresa_id=rem.empresa_id,
        empresas_opcao=empresas,
    )


@router.post("", response_model=FuncionarioRedeRead, status_code=201)
def criar(
    data: FuncionarioRedeCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    if data.tipo == "socio" and not data.rede_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sócio deve ter rede_id")
    if data.tipo == "colaborador" and not data.empresa_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Colaborador deve ter empresa_id")
    if data.tipo == "supervisor" and not data.empresa_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supervisor deve ter ao menos uma empresa")
    rede_id_final = data.rede_id
    if data.tipo == "supervisor":
        emps = db.query(Empresa).filter(Empresa.id.in_(data.empresa_ids)).all()
        if len(emps) != len(set(data.empresa_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa inválida na lista")
        redes_emp = {e.rede_id for e in emps}
        if len(redes_emp) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supervisor: todas as empresas devem pertencer à mesma rede.",
            )
        rede_id_final = list(redes_emp)[0]
    elif data.tipo == "colaborador" and data.empresa_id:
        emp = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
        rede_id_final = emp.rede_id
    if rede_id_final is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rede_id não definido para o vínculo.")
    try:
        assert_email_unico_por_rede(db, email=str(data.email), rede_id=int(rede_id_final))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    f = FuncionarioRede(
        nome=data.nome,
        email=data.email,
        tipo=data.tipo,
        ativo=data.ativo,
        rede_id=rede_id_final,
        empresa_id=data.empresa_id,
    )
    db.add(f)
    db.flush()
    registrar_audit(db, "funcionario_rede", f.id, "create", atendente.id)
    if data.tipo == "supervisor":
        for emp_id in data.empresa_ids:
            db.add(FuncionarioRedeEmpresa(funcionario_id=f.id, empresa_id=emp_id))
    db.commit()
    db.refresh(f)
    return _para_read(f)


@router.get("/{funcionario_id}", response_model=FuncionarioRedeRead)
def obter(
    funcionario_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    f = db.query(FuncionarioRede).filter(FuncionarioRede.id == funcionario_id).first()
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")
    return _para_read(f)


@router.patch("/{funcionario_id}", response_model=FuncionarioRedeRead)
def atualizar(
    funcionario_id: int,
    data: FuncionarioRedeUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    f = db.query(FuncionarioRede).filter(FuncionarioRede.id == funcionario_id).first()
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")
    update = data.model_dump(exclude_unset=True)
    empresa_ids = update.pop("empresa_ids", None)
    for k, v in update.items():
        setattr(f, k, v)
    if empresa_ids is not None and f.tipo == "supervisor":
        if empresa_ids:
            emps = db.query(Empresa).filter(Empresa.id.in_(empresa_ids)).all()
            if len(emps) != len(set(empresa_ids)):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa inválida na lista")
            redes_emp = {e.rede_id for e in emps}
            if len(redes_emp) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Supervisor: todas as empresas devem pertencer à mesma rede.",
                )
            f.rede_id = list(redes_emp)[0]
        db.query(FuncionarioRedeEmpresa).filter(FuncionarioRedeEmpresa.funcionario_id == f.id).delete()
        for emp_id in empresa_ids:
            db.add(FuncionarioRedeEmpresa(funcionario_id=f.id, empresa_id=emp_id))
    if f.tipo == "colaborador" and f.empresa_id:
        emp = db.query(Empresa).filter(Empresa.id == f.empresa_id).first()
        if emp:
            f.rede_id = emp.rede_id
    if f.rede_id is not None:
        try:
            assert_email_unico_por_rede(
                db,
                email=str(f.email),
                rede_id=int(f.rede_id),
                ignorar_funcionario_id=f.id,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    registrar_audit(db, "funcionario_rede", funcionario_id, "update", atendente.id)
    db.commit()
    db.refresh(f)
    return _para_read(f)


@router.delete("/{funcionario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    funcionario_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    f = db.query(FuncionarioRede).filter(FuncionarioRede.id == funcionario_id).first()
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")
    tickets_vinculados = db.query(Ticket).filter(Ticket.aberto_por_id == funcionario_id).count()
    if tickets_vinculados > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir funcionário vinculado a ticket(s). Sugere-se inativar o registro.",
        )
    db.delete(f)
    db.commit()
