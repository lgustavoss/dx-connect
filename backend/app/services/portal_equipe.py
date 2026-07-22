"""Gestão de equipe pelo sócio no portal (#602).

Regras:
- Apenas `tipo=socio` acede à API.
- CRUD limitado à **rede** do sócio autenticado.
- Não é possível **criar** ou **promover** outro sócio pelo portal (só colaborador ↔ supervisor).
- Outros sócios aparecem na listagem (editáveis só em ativo/senha/notificações).
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_senha
from app.models.empresa import Empresa
from app.models.funcionario_rede import FuncionarioRede
from app.schemas.portal import (
    PortalEquipeFuncionarioCreate,
    PortalEquipeFuncionarioRead,
    PortalEquipeFuncionarioUpdate,
)
from app.services.funcionario_escopo import (
    escopo_efetivo,
    rede_id_efetiva,
    sincronizar_vinculos_empresas,
    validar_empresa_ids_na_rede,
)
from app.services.funcionario_rede_resolver import assert_email_unico_por_rede
from app.services.inbound_ticket_reconcile import reconciliar_tickets_pendentes_por_email

TIPOS_PORTAL_EQUIPE = frozenset({"colaborador", "supervisor"})


def _rede_id_socio(db: Session, socio: FuncionarioRede) -> int:
    rid = rede_id_efetiva(db, socio)
    if rid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rede não definida para o sócio.")
    return int(rid)


def _empresa_ids_leitura(f: FuncionarioRede) -> list[int]:
    if escopo_efetivo(f) == "all":
        return []
    ids = [e.empresa_id for e in f.empresas_supervisor]
    if f.empresa_id is not None and int(f.empresa_id) not in ids:
        ids.insert(0, int(f.empresa_id))
    return ids


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


def _para_read(f: FuncionarioRede, *, socio_id: int) -> PortalEquipeFuncionarioRead:
    tipo = (f.tipo or "").strip().lower()
    return PortalEquipeFuncionarioRead(
        id=f.id,
        nome=f.nome,
        email=f.email,
        telefone=getattr(f, "telefone", None),
        tipo=f.tipo,
        ativo=bool(f.ativo),
        empresa_id=f.empresa_id,
        empresa_ids=_empresa_ids_leitura(f),
        portal_habilitado=bool((getattr(f, "senha_hash", None) or "").strip()),
        must_change_password=bool(getattr(f, "must_change_password", False)),
        notificar_email_portal=bool(getattr(f, "notificar_email_portal", True)),
        editavel=tipo != "socio" or int(f.id) == int(socio_id),
    )


def _obter_na_rede(db: Session, socio: FuncionarioRede, funcionario_id: int) -> FuncionarioRede:
    rede_id = _rede_id_socio(db, socio)
    f = db.query(FuncionarioRede).filter(FuncionarioRede.id == funcionario_id).first()
    if not f or f.rede_id is None or int(f.rede_id) != rede_id:
        raise LookupError("Funcionário não encontrado")
    return f


def listar_funcionarios(
    db: Session,
    socio: FuncionarioRede,
    *,
    incluir_inativos: bool = False,
    busca: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[FuncionarioRede], int]:
    rede_id = _rede_id_socio(db, socio)
    q = db.query(FuncionarioRede).filter(FuncionarioRede.rede_id == rede_id)
    if not incluir_inativos:
        q = q.filter(FuncionarioRede.ativo.is_(True))
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.filter(or_(FuncionarioRede.nome.ilike(term), FuncionarioRede.email.ilike(term)))
    total = q.count()
    rows = q.order_by(FuncionarioRede.nome.asc(), FuncionarioRede.id.asc()).offset(offset).limit(limit).all()
    return rows, total


def criar_funcionario(db: Session, socio: FuncionarioRede, data: PortalEquipeFuncionarioCreate) -> FuncionarioRede:
    rede_id = _rede_id_socio(db, socio)
    tipo = data.tipo.strip().lower()
    if tipo not in TIPOS_PORTAL_EQUIPE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No portal só é possível cadastrar colaboradores ou supervisores.",
        )
    empresa_ids = list(dict.fromkeys(data.empresa_ids or []))
    if data.empresa_id and int(data.empresa_id) not in empresa_ids:
        empresa_ids.insert(0, int(data.empresa_id))
    if tipo == "colaborador":
        if len(empresa_ids) != 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selecione uma empresa para o colaborador.")
    elif not empresa_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Marque ao menos uma empresa para o supervisor.")
    try:
        validar_empresa_ids_na_rede(db, rede_id, empresa_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    try:
        assert_email_unico_por_rede(db, email=str(data.email), rede_id=rede_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    f = FuncionarioRede(
        nome=data.nome.strip(),
        email=str(data.email).strip().lower(),
        telefone=data.telefone,
        tipo=tipo,
        escopo_empresas="selected",
        ativo=data.ativo,
        rede_id=rede_id,
        empresa_id=empresa_ids[0] if tipo == "colaborador" else None,
    )
    db.add(f)
    db.flush()
    _aplicar_senha_portal(f, data.senha_portal, must_change=data.must_change_password)
    sincronizar_vinculos_empresas(db, f, escopo="selected", rede_id=rede_id, empresa_ids=empresa_ids)
    db.commit()
    db.refresh(f)
    if f.email:
        reconciliar_tickets_pendentes_por_email(db, f.email)
        db.commit()
    return f


def atualizar_funcionario(
    db: Session,
    socio: FuncionarioRede,
    funcionario_id: int,
    data: PortalEquipeFuncionarioUpdate,
) -> FuncionarioRede:
    f = _obter_na_rede(db, socio, funcionario_id)
    rede_id = _rede_id_socio(db, socio)
    update = data.model_dump(exclude_unset=True)
    empresa_ids = update.pop("empresa_ids", None)
    empresa_id_upd = update.pop("empresa_id", None)
    senha_portal = update.pop("senha_portal", None)
    must_change = update.pop("must_change_password", None)
    revogar = update.pop("revogar_sessoes_portal", None)
    tipo_upd = update.pop("tipo", None)

    alvo_socio = (f.tipo or "").strip().lower() == "socio"
    if alvo_socio:
        if tipo_upd is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A função de sócio não pode ser alterada pelo portal.",
            )
        if empresa_ids is not None or empresa_id_upd is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sócios têm acesso a toda a rede; vínculos por empresa não se aplicam.",
            )
        if int(f.id) != int(socio.id):
            permitidos = {"ativo", "notificar_email_portal"}
            if any(k not in permitidos for k in update):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Outros sócios só podem ter situação, senha e notificações alteradas pelo portal.",
                )
    else:
        if tipo_upd is not None:
            t = tipo_upd.strip().lower()
            if t not in TIPOS_PORTAL_EQUIPE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No portal só é possível alternar entre colaborador e supervisor.",
                )
            f.tipo = t

    for k, v in update.items():
        setattr(f, k, v)

    if senha_portal is not None:
        _aplicar_senha_portal(f, senha_portal, must_change=must_change)
    elif must_change is not None:
        f.must_change_password = bool(must_change)
    if revogar:
        f.token_version = int(getattr(f, "token_version", 0) or 0) + 1

    if not alvo_socio:
        tipo_eff = (f.tipo or "colaborador").strip().lower()
        ids = list(empresa_ids) if empresa_ids is not None else _empresa_ids_leitura(f)
        if empresa_id_upd is not None and int(empresa_id_upd) not in ids:
            ids.insert(0, int(empresa_id_upd))
        if tipo_eff == "colaborador":
            if empresa_ids is not None or empresa_id_upd is not None:
                if len(ids) != 1:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Colaborador deve ter uma empresa.")
        elif empresa_ids is not None or empresa_id_upd is not None:
            if not ids:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supervisor precisa de ao menos uma empresa.")
        if ids:
            try:
                validar_empresa_ids_na_rede(db, rede_id, ids)
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
            sincronizar_vinculos_empresas(
                db,
                f,
                escopo="selected",
                rede_id=rede_id,
                empresa_ids=ids,
            )

    if f.email:
        try:
            assert_email_unico_por_rede(
                db,
                email=str(f.email),
                rede_id=rede_id,
                ignorar_funcionario_id=f.id,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    db.commit()
    db.refresh(f)
    if f.email:
        reconciliar_tickets_pendentes_por_email(db, f.email)
        db.commit()
    return f


def empresas_da_rede(db: Session, socio: FuncionarioRede) -> list[Empresa]:
    rede_id = _rede_id_socio(db, socio)
    return (
        db.query(Empresa)
        .filter(Empresa.rede_id == rede_id, Empresa.ativo.is_(True))
        .order_by(Empresa.nome.asc())
        .all()
    )
