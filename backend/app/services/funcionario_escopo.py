"""Escopo de empresas/redes visíveis por funcionário da rede (ALL vs SELECTED).

Desde o #1407 o contato pode estar vinculado a mais de uma rede
(funcionario_rede_vinculo). redes_efetivas é a fonte da verdade; os campos
legados funcionario_rede.rede_id/empresa_id continuam como fallback de leitura
e como espelho da primeira rede.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.models.funcionario_rede import (
    FuncionarioRede,
    FuncionarioRedeEmpresa,
    FuncionarioRedeVinculo,
)
from app.models.rede import Rede

EscopoEmpresas = str  # "all" | "selected"


def escopo_efetivo(funcionario: FuncionarioRede) -> str:
    raw = (getattr(funcionario, "escopo_empresas", None) or "").strip().lower()
    if raw in ("all", "selected"):
        return raw
    return "all" if funcionario.tipo == "socio" else "selected"


def _dedupe(ids) -> list[int]:
    return list(dict.fromkeys(int(i) for i in ids if i is not None))


def _ids_redes_junction(db: Session, funcionario_id: int) -> list[int]:
    rows = (
        db.query(FuncionarioRedeVinculo.rede_id)
        .filter(FuncionarioRedeVinculo.funcionario_id == funcionario_id)
        .order_by(FuncionarioRedeVinculo.id.asc())
        .all()
    )
    return [int(r[0]) for r in rows]


def _ids_redes_legado(db: Session, funcionario: FuncionarioRede) -> list[int]:
    """Deriva redes dos campos 1:1 legados (sócio, colaborador e supervisão por empresa)."""
    ids: list[int] = []
    if funcionario.rede_id is not None:
        ids.append(int(funcionario.rede_id))
    if funcionario.empresa_id is not None:
        rede_id = (
            db.query(Empresa.rede_id)
            .filter(Empresa.id == funcionario.empresa_id)
            .scalar()
        )
        if rede_id is not None:
            ids.append(int(rede_id))
    rows = (
        db.query(Empresa.rede_id)
        .join(FuncionarioRedeEmpresa, FuncionarioRedeEmpresa.empresa_id == Empresa.id)
        .filter(FuncionarioRedeEmpresa.funcionario_id == funcionario.id)
        .order_by(FuncionarioRedeEmpresa.id.asc())
        .all()
    )
    for (rede_id,) in rows:
        if rede_id is not None:
            ids.append(int(rede_id))
    return ids


def redes_ids_efetivas(db: Session, funcionario: FuncionarioRede) -> list[int]:
    """IDs das redes do contato (junction), com fallback para o vínculo legado."""
    vinculos = funcionario.__dict__.get("vinculos_redes")
    if vinculos is not None:
        ids = [int(v.rede_id) for v in vinculos]
    else:
        ids = _ids_redes_junction(db, funcionario.id)
    if not ids:
        ids = _ids_redes_legado(db, funcionario)
    return _dedupe(ids)


def redes_efetivas(db: Session, funcionario: FuncionarioRede) -> list[Rede]:
    """Redes às quais o contato pertence, na ordem de vínculo (primeira = legado)."""
    vinculos = funcionario.__dict__.get("vinculos_redes")
    if vinculos:
        carregadas = [v.__dict__.get("rede") for v in vinculos]
        if all(rede is not None for rede in carregadas):
            return [rede for rede in carregadas if rede is not None]
    ids = redes_ids_efetivas(db, funcionario)
    if not ids:
        return []
    rows = db.query(Rede).filter(Rede.id.in_(ids)).all()
    por_id = {int(r.id): r for r in rows}
    return [por_id[i] for i in ids if i in por_id]


def rede_id_efetiva(db: Session, funcionario: FuncionarioRede) -> int | None:
    """Primeira rede do contato — compatibilidade com o campo legado 1:1."""
    ids = redes_ids_efetivas(db, funcionario)
    return int(ids[0]) if ids else None


def empresa_ids_vinculados(db: Session, funcionario: FuncionarioRede, *, apenas_ativas: bool = True) -> set[int]:
    escopo = escopo_efetivo(funcionario)
    rede_ids = redes_ids_efetivas(db, funcionario)
    if escopo == "all":
        if not rede_ids:
            return set()
        q = db.query(Empresa.id).filter(Empresa.rede_id.in_(rede_ids))
        if apenas_ativas:
            q = q.filter(Empresa.ativo.is_(True))
        return {int(r[0]) for r in q.all()}

    ids: set[int] = set()
    if funcionario.tipo == "colaborador" and funcionario.empresa_id is not None:
        ids.add(int(funcionario.empresa_id))
    rows = (
        db.query(FuncionarioRedeEmpresa.empresa_id)
        .filter(FuncionarioRedeEmpresa.funcionario_id == funcionario.id)
        .all()
    )
    ids |= {int(r[0]) for r in rows}
    if apenas_ativas and ids:
        ativos = {
            int(r[0])
            for r in db.query(Empresa.id)
            .filter(Empresa.id.in_(ids), Empresa.ativo.is_(True))
            .all()
        }
        return ativos
    return ids


def funcionario_visivel_na_empresa(db: Session, funcionario: FuncionarioRede, empresa_id: int) -> bool:
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        return False
    if int(emp.rede_id) not in redes_ids_efetivas(db, funcionario):
        return False
    return int(empresa_id) in empresa_ids_vinculados(db, funcionario, apenas_ativas=False)


def funcionario_visivel_no_tenant(
    db: Session,
    atendente: Atendente,
    funcionario_id: int,
    *,
    exigir_ativo: bool = True,
) -> FuncionarioRede | None:
    """Funcionário da rede acessível ao atendente (mesmo tenant), ou None."""
    func = db.query(FuncionarioRede).filter(FuncionarioRede.id == funcionario_id).first()
    if not func or (exigir_ativo and not func.ativo):
        return None
    rede_ids = redes_ids_efetivas(db, func)
    if rede_ids:
        rede = (
            db.query(Rede)
            .filter(Rede.id.in_(rede_ids), Rede.tenant_id == atendente.tenant_id)
            .first()
        )
        if rede:
            return func
    if func.empresa_id is not None:
        emp = (
            db.query(Empresa)
            .filter(Empresa.id == func.empresa_id, Empresa.tenant_id == atendente.tenant_id)
            .first()
        )
        if emp:
            return func
    vinculo = (
        db.query(FuncionarioRedeEmpresa)
        .join(Empresa, Empresa.id == FuncionarioRedeEmpresa.empresa_id)
        .filter(
            FuncionarioRedeEmpresa.funcionario_id == func.id,
            Empresa.tenant_id == atendente.tenant_id,
        )
        .first()
    )
    return func if vinculo else None


def _normalizar_rede_ids(rede_id) -> set[int]:
    if rede_id is None:
        return set()
    if isinstance(rede_id, int):
        return {int(rede_id)}
    return {int(x) for x in rede_id if x is not None}


def validar_empresa_ids_na_rede(db: Session, rede_id, empresa_ids: list[int]) -> None:
    """Valida que todas as empresas existem e pertencem a alguma rede vinculada ao contato."""
    if not empresa_ids:
        raise ValueError("Selecione ao menos uma empresa.")
    rede_ids = _normalizar_rede_ids(rede_id)
    if not rede_ids:
        raise ValueError("Informe a rede.")
    emps = db.query(Empresa).filter(Empresa.id.in_(empresa_ids)).all()
    if len(emps) != len({int(eid) for eid in empresa_ids}):
        raise ValueError("Empresa inválida na lista.")
    redes_das_empresas = {int(e.rede_id) for e in emps}
    if not redes_das_empresas.issubset(rede_ids):
        raise ValueError(
            "Todas as empresas devem pertencer às redes vinculadas ao contato."
        )


def sincronizar_vinculos_redes(
    db: Session,
    funcionario: FuncionarioRede,
    rede_ids: list[int],
) -> None:
    """Grava a junction de redes do contato, mantendo o campo legado na primeira rede."""
    ids = _dedupe(rede_ids)
    atuais = {
        int(r[0])
        for r in db.query(FuncionarioRedeVinculo.rede_id)
        .filter(FuncionarioRedeVinculo.funcionario_id == funcionario.id)
        .all()
    }
    remover = atuais - set(ids)
    if remover:
        db.query(FuncionarioRedeVinculo).filter(
            FuncionarioRedeVinculo.funcionario_id == funcionario.id,
            FuncionarioRedeVinculo.rede_id.in_(remover),
        ).delete(synchronize_session=False)
    for rede_id in ids:
        if rede_id not in atuais:
            db.add(FuncionarioRedeVinculo(funcionario_id=funcionario.id, rede_id=rede_id))
    if ids:
        funcionario.rede_id = int(ids[0])


def sincronizar_vinculos_empresas(
    db: Session,
    funcionario: FuncionarioRede,
    *,
    escopo: str,
    rede_id: int | None,
    empresa_ids: list[int] | None,
    rede_ids: list[int] | None = None,
) -> None:
    funcionario.escopo_empresas = escopo
    if rede_id is not None:
        funcionario.rede_id = int(rede_id)
    if escopo == "all":
        funcionario.empresa_id = None
        db.query(FuncionarioRedeEmpresa).filter(
            FuncionarioRedeEmpresa.funcionario_id == funcionario.id
        ).delete()
        return

    ids = _dedupe(empresa_ids or [])
    alvo = _dedupe(rede_ids) if rede_ids else _dedupe([rede_id] if rede_id is not None else [])
    validar_empresa_ids_na_rede(db, alvo, ids)
    if funcionario.tipo == "colaborador" and len(ids) == 1:
        funcionario.empresa_id = ids[0]
    else:
        funcionario.empresa_id = None
    db.query(FuncionarioRedeEmpresa).filter(
        FuncionarioRedeEmpresa.funcionario_id == funcionario.id
    ).delete()
    for eid in ids:
        db.add(FuncionarioRedeEmpresa(funcionario_id=funcionario.id, empresa_id=eid))
