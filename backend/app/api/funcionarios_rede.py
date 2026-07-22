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
from app.services.funcionario_escopo import (
    escopo_efetivo,
    sincronizar_vinculos_empresas,
    validar_empresa_ids_na_rede,
)
from app.services.inbound_ticket_reconcile import reconciliar_tickets_pendentes_por_email
from app.services.funcionario_rede_resolver import assert_email_unico_por_rede, resolver_remetente_por_email
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import exigir_admin
from app.core.audit import registrar_audit
from app.core.security import hash_senha

router = APIRouter(prefix="/funcionarios-rede", tags=["funcionarios-rede"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarFuncionariosPor(str, Enum):
    nome = "nome"
    email = "email"
    tipo = "tipo"
    ativo = "ativo"
    rede_id = "rede_id"


def _empresa_ids_leitura(f: FuncionarioRede) -> list[int]:
    if escopo_efetivo(f) == "all":
        return []
    ids = [e.empresa_id for e in f.empresas_supervisor]
    if f.empresa_id is not None and int(f.empresa_id) not in ids:
        ids.insert(0, int(f.empresa_id))
    return ids


def _para_read(f: FuncionarioRede) -> FuncionarioRedeRead:
    return FuncionarioRedeRead(
        id=f.id,
        nome=f.nome,
        email=f.email,
        telefone=getattr(f, "telefone", None),
        tipo=f.tipo,
        escopo_empresas=escopo_efetivo(f),
        ativo=f.ativo,
        rede_id=f.rede_id,
        empresa_id=f.empresa_id,
        empresa_ids=_empresa_ids_leitura(f),
        portal_habilitado=bool((getattr(f, "senha_hash", None) or "").strip()),
        must_change_password=bool(getattr(f, "must_change_password", False)),
        notificar_email_portal=bool(getattr(f, "notificar_email_portal", True)),
        created_at=f.created_at,
        updated_at=f.updated_at,
    )


def _escopo_para_tipo(tipo: str, escopo_informado: str | None) -> str:
    """Sócio sempre enxerga toda a rede (escopo all), mesmo se o cliente omitir o campo."""
    tipo_eff = (tipo or "colaborador").strip().lower()
    if tipo_eff == "socio":
        return "all"
    escopo = (escopo_informado or "selected").strip().lower()
    return escopo if escopo in ("all", "selected") else "selected"


def _aplicar_senha_portal(f: FuncionarioRede, senha: str | None, *, must_change: bool | None) -> None:
    if senha is None:
        return
    senha_limpa = senha.strip()
    if not senha_limpa:
        return
    if len(senha_limpa) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha do portal deve ter ao menos 8 caracteres.",
        )
    if not (f.email or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o e-mail do funcionário para habilitar o portal.",
        )
    f.senha_hash = hash_senha(senha_limpa)
    f.must_change_password = True if must_change is None else bool(must_change)
    f.token_version = int(getattr(f, "token_version", 0) or 0) + 1


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
        emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not emp:
            return ListaPaginada(items=[], total=0)
        sub_junction = db.query(FuncionarioRedeEmpresa.funcionario_id).filter(
            FuncionarioRedeEmpresa.empresa_id == empresa_id
        )
        q = q.filter(
            FuncionarioRede.rede_id == emp.rede_id,
            or_(
                FuncionarioRede.escopo_empresas == "all",
                FuncionarioRede.tipo == "socio",
                FuncionarioRede.empresa_id == empresa_id,
                FuncionarioRede.id.in_(sub_junction),
            ),
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
    escopo = _escopo_para_tipo(data.tipo, data.escopo_empresas)
    if escopo not in ("all", "selected"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="escopo_empresas deve ser all ou selected")
    empresa_ids = list(data.empresa_ids or [])
    if data.empresa_id and data.empresa_id not in empresa_ids:
        empresa_ids.insert(0, data.empresa_id)
    rede_id_final = data.rede_id
    if escopo == "selected" and not empresa_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecione ao menos uma empresa ou marque todas as empresas da rede.",
        )
    if escopo == "selected":
        if rede_id_final is None and empresa_ids:
            emp = db.query(Empresa).filter(Empresa.id == empresa_ids[0]).first()
            if not emp:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
            rede_id_final = emp.rede_id
        try:
            validar_empresa_ids_na_rede(db, int(rede_id_final), empresa_ids)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    elif not rede_id_final:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe a rede.")
    if rede_id_final is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rede_id não definido para o vínculo.")
    email_eff = data.email
    if email_eff:
        try:
            assert_email_unico_por_rede(db, email=str(email_eff), rede_id=int(rede_id_final))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    f = FuncionarioRede(
        nome=data.nome,
        email=email_eff,
        telefone=data.telefone,
        tipo=data.tipo,
        escopo_empresas=escopo,
        ativo=data.ativo,
        rede_id=rede_id_final,
        empresa_id=data.empresa_id if escopo == "selected" and data.tipo == "colaborador" else None,
    )
    db.add(f)
    db.flush()
    _aplicar_senha_portal(f, data.senha_portal, must_change=data.must_change_password)
    registrar_audit(db, "funcionario_rede", f.id, "create", atendente.id)
    sincronizar_vinculos_empresas(
        db,
        f,
        escopo=escopo,
        rede_id=int(rede_id_final),
        empresa_ids=empresa_ids if escopo == "selected" else None,
    )
    db.commit()
    db.refresh(f)
    if f.email:
        reconciliar_tickets_pendentes_por_email(db, f.email)
    db.commit()
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
    empresa_id_upd = update.pop("empresa_id", None)
    escopo_upd = update.pop("escopo_empresas", None)
    senha_portal = update.pop("senha_portal", None)
    must_change = update.pop("must_change_password", None)
    revogar = update.pop("revogar_sessoes_portal", None)
    for k, v in update.items():
        setattr(f, k, v)
    if senha_portal is not None:
        _aplicar_senha_portal(f, senha_portal, must_change=must_change)
    elif must_change is not None:
        f.must_change_password = bool(must_change)
    if revogar:
        f.token_version = int(getattr(f, "token_version", 0) or 0) + 1
    escopo = _escopo_para_tipo(f.tipo, escopo_upd or escopo_efetivo(f))
    if escopo not in ("all", "selected"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="escopo_empresas deve ser all ou selected")
    ids = list(empresa_ids) if empresa_ids is not None else _empresa_ids_leitura(f)
    if empresa_id_upd is not None and empresa_id_upd not in ids:
        ids.insert(0, empresa_id_upd)
    rede_id = f.rede_id
    if escopo == "selected":
        if not ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selecione ao menos uma empresa ou marque todas as empresas da rede.",
            )
        if rede_id is None and ids:
            emp = db.query(Empresa).filter(Empresa.id == ids[0]).first()
            if emp:
                rede_id = emp.rede_id
        if rede_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rede_id não definido.")
        try:
            validar_empresa_ids_na_rede(db, int(rede_id), ids)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    elif rede_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe a rede.")
    sincronizar_vinculos_empresas(
        db,
        f,
        escopo=escopo,
        rede_id=int(rede_id),
        empresa_ids=ids if escopo == "selected" else None,
    )
    if f.rede_id is not None and f.email:
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
    if f.email:
        reconciliar_tickets_pendentes_por_email(db, f.email)
    db.commit()
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
