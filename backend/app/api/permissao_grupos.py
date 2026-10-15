from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_permissao
from app.database import get_db
from app.models import Atendente, PermissaoGrupo
from app.schemas.permissao_grupo import (
    PermissaoCatalogoItem,
    PermissaoGrupoCreate,
    PermissaoGrupoMembro,
    PermissaoGrupoMembroCreate,
    PermissaoGrupoRead,
    PermissaoGrupoUpdate,
)
from app.services import permissao_grupos as svc

router = APIRouter(prefix="/permissao-grupos", tags=["permissao-grupos"])


def _para_read(grupo: PermissaoGrupo) -> PermissaoGrupoRead:
    codigos = [item.codigo for item in (grupo.itens or [])]
    return PermissaoGrupoRead(
        id=grupo.id,
        nome=grupo.nome,
        slug=grupo.slug,
        sistema=bool(grupo.sistema),
        permissoes=codigos,
        membros=len(grupo.atendentes or []),
    )


@router.get("/catalogo", response_model=list[PermissaoCatalogoItem])
def catalogo(_: Atendente = Depends(exigir_permissao("grupos.ver"))):
    return [
        PermissaoCatalogoItem(
            modulo=modulo,
            codigo=codigo,
            nome=nome,
            descricao=descricao,
            pacote=pacote or None,
        )
        for modulo, codigo, nome, descricao, pacote in svc.CATALOGO
    ]


@router.get("", response_model=list[PermissaoGrupoRead])
def listar(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("grupos.ver")),
):
    grupos, mudou = svc.listar(db, atendente.tenant_id)
    if mudou:
        db.commit()
    return [_para_read(g) for g in grupos]


@router.post("", response_model=PermissaoGrupoRead, status_code=201)
def criar(
    data: PermissaoGrupoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("grupos.criar")),
):
    grupo = svc.criar(db, atendente.tenant_id, data.nome, data.permissoes)
    registrar_audit(db, "permissao_grupo", grupo.id, "create", atendente.id)
    db.commit()
    db.refresh(grupo)
    grupo = svc.obter(db, atendente.tenant_id, grupo.id)
    return _para_read(grupo)


def _membro(pessoa: Atendente) -> PermissaoGrupoMembro:
    return PermissaoGrupoMembro(id=pessoa.id, nome=pessoa.nome, email=pessoa.email, ativo=bool(pessoa.ativo))


@router.get("/{grupo_id}/membros", response_model=list[PermissaoGrupoMembro])
def listar_membros(
    grupo_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("grupos.ver")),
):
    grupo = svc.obter(db, atendente.tenant_id, grupo_id)
    return [_membro(pessoa) for pessoa in svc.listar_membros(grupo)]


@router.get("/{grupo_id}/candidatos", response_model=list[PermissaoGrupoMembro])
def listar_candidatos(
    grupo_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("atendentes.editar")),
):
    grupo = svc.obter(db, atendente.tenant_id, grupo_id)
    return [_membro(pessoa) for pessoa in svc.listar_candidatos(db, grupo)]


@router.post("/{grupo_id}/membros", response_model=PermissaoGrupoMembro, status_code=201)
def vincular_membro(
    grupo_id: int,
    data: PermissaoGrupoMembroCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("atendentes.editar")),
):
    grupo = svc.obter(db, atendente.tenant_id, grupo_id)
    pessoa = svc.vincular_membro(db, grupo, data.atendente_id)
    registrar_audit(db, "permissao_grupo", grupo.id, "update", atendente.id, payload={"membro_id": pessoa.id})
    db.commit()
    return _membro(pessoa)


@router.delete("/{grupo_id}/membros/{atendente_id}", status_code=status.HTTP_204_NO_CONTENT)
def desvincular_membro(
    grupo_id: int,
    atendente_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("atendentes.editar")),
):
    grupo = svc.obter(db, atendente.tenant_id, grupo_id)
    svc.desvincular_membro(db, grupo, atendente_id)
    registrar_audit(db, "permissao_grupo", grupo.id, "update", atendente.id, payload={"membro_id": atendente_id, "removido": True})
    db.commit()


@router.patch("/{grupo_id}", response_model=PermissaoGrupoRead)
def atualizar(
    grupo_id: int,
    data: PermissaoGrupoUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("grupos.editar")),
):
    grupo = svc.obter(db, atendente.tenant_id, grupo_id)
    campos = data.model_dump(exclude_unset=True)
    svc.atualizar(
        db,
        grupo,
        nome=campos.get("nome"),
        permissoes=campos.get("permissoes") if "permissoes" in campos else None,
    )
    registrar_audit(db, "permissao_grupo", grupo.id, "update", atendente.id)
    db.commit()
    grupo = svc.obter(db, atendente.tenant_id, grupo_id)
    return _para_read(grupo)


@router.delete("/{grupo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    grupo_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("grupos.excluir")),
):
    grupo = svc.obter(db, atendente.tenant_id, grupo_id)
    svc.excluir(db, grupo)
    registrar_audit(db, "permissao_grupo", grupo_id, "delete", atendente.id)
    db.commit()
