"""
Resolve remetente de e-mail inbound → funcionário, rede e empresa(s).

Regras:
- Um e-mail não pode estar activo em mais de uma rede.
- Colaborador: uma empresa; supervisor: N empresas na mesma rede; sócio: rede sem empresa fixa.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.funcionario_rede import FuncionarioRede
from app.services.funcionario_escopo import empresa_ids_vinculados, escopo_efetivo, rede_id_efetiva


@dataclass(frozen=True)
class RemetenteFuncionarioResolve:
    email: str
    requer_cadastro: bool
    conflito_multiplas_redes: bool = False
    funcionario_id: int | None = None
    rede_id: int | None = None
    empresa_id: int | None = None
    empresa_ids_opcao: tuple[int, ...] = ()


def _normalizar_email(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    return str(raw).strip().lower()


def _empresas_do_funcionario(db: Session, f: FuncionarioRede) -> set[int]:
    return empresa_ids_vinculados(db, f)


def resolver_remetente_por_email(db: Session, email_raw: str | None) -> RemetenteFuncionarioResolve:
    email = _normalizar_email(email_raw)
    if not email:
        return RemetenteFuncionarioResolve(email="", requer_cadastro=True)

    rows = (
        db.query(FuncionarioRede)
        .filter(FuncionarioRede.ativo.is_(True))
        .filter(FuncionarioRede.email.ilike(email))
        .all()
    )
    if not rows:
        return RemetenteFuncionarioResolve(email=email, requer_cadastro=True)

    rede_ids: set[int] = set()
    for f in rows:
        if f.rede_id is not None:
            rede_ids.add(int(f.rede_id))
        elif f.tipo == "colaborador" and f.empresa_id is not None:
            emp = db.query(Empresa).filter(Empresa.id == f.empresa_id).first()
            if emp:
                rede_ids.add(int(emp.rede_id))

    if len(rede_ids) > 1:
        return RemetenteFuncionarioResolve(
            email=email,
            requer_cadastro=True,
            conflito_multiplas_redes=True,
        )

    rede_id = next(iter(rede_ids)) if rede_ids else None
    empresa_ids: set[int] = set()
    for f in rows:
        if f.rede_id is not None and rede_id is not None and int(f.rede_id) != rede_id:
            continue
        empresa_ids |= _empresas_do_funcionario(db, f)

    if rede_id is not None and not empresa_ids and any(escopo_efetivo(f) == "all" for f in rows):
        ids_rede = (
            db.query(Empresa.id)
            .filter(Empresa.rede_id == rede_id, Empresa.ativo.is_(True))
            .all()
        )
        empresa_ids = {int(i[0]) for i in ids_rede}

    funcionario_id = rows[0].id if len(rows) == 1 else None
    if funcionario_id is None and rows:
        funcionario_id = rows[0].id

    if len(empresa_ids) == 1:
        eid = next(iter(empresa_ids))
        return RemetenteFuncionarioResolve(
            email=email,
            requer_cadastro=False,
            funcionario_id=funcionario_id,
            rede_id=rede_id,
            empresa_id=eid,
            empresa_ids_opcao=(eid,),
        )

    return RemetenteFuncionarioResolve(
        email=email,
        requer_cadastro=False,
        funcionario_id=funcionario_id,
        rede_id=rede_id,
        empresa_id=None,
        empresa_ids_opcao=tuple(sorted(empresa_ids)),
    )


def assert_email_unico_por_rede(
    db: Session,
    *,
    email: str,
    rede_id: int,
    ignorar_funcionario_id: int | None = None,
) -> None:
    """Levanta ValueError se o e-mail já existir activo noutra rede."""
    email_n = _normalizar_email(email)
    if not email_n:
        return
    q = db.query(FuncionarioRede).filter(
        FuncionarioRede.ativo.is_(True),
        FuncionarioRede.email.ilike(email_n),
    )
    if ignorar_funcionario_id is not None:
        q = q.filter(FuncionarioRede.id != ignorar_funcionario_id)
    for f in q.all():
        rid = f.rede_id
        if f.tipo == "colaborador" and f.empresa_id and rid is None:
            emp = db.query(Empresa).filter(Empresa.id == f.empresa_id).first()
            rid = emp.rede_id if emp else None
        if rid is not None and int(rid) != int(rede_id):
            raise ValueError(
                "Este e-mail já está cadastrado em outra rede. "
                "Um funcionário não pode pertencer a duas redes diferentes."
            )
