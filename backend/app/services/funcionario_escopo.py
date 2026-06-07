"""Escopo de empresas visíveis por funcionário da rede (ALL vs SELECTED)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa

EscopoEmpresas = str  # "all" | "selected"


def escopo_efetivo(funcionario: FuncionarioRede) -> str:
    raw = (getattr(funcionario, "escopo_empresas", None) or "").strip().lower()
    if raw in ("all", "selected"):
        return raw
    return "all" if funcionario.tipo == "socio" else "selected"


def rede_id_efetiva(db: Session, funcionario: FuncionarioRede) -> int | None:
    if funcionario.rede_id is not None:
        return int(funcionario.rede_id)
    if funcionario.tipo == "colaborador" and funcionario.empresa_id is not None:
        emp = db.query(Empresa).filter(Empresa.id == funcionario.empresa_id).first()
        return int(emp.rede_id) if emp else None
    rows = (
        db.query(FuncionarioRedeEmpresa)
        .filter(FuncionarioRedeEmpresa.funcionario_id == funcionario.id)
        .all()
    )
    if not rows:
        return None
    emp = db.query(Empresa).filter(Empresa.id == rows[0].empresa_id).first()
    return int(emp.rede_id) if emp else None


def empresa_ids_vinculados(db: Session, funcionario: FuncionarioRede, *, apenas_ativas: bool = True) -> set[int]:
    escopo = escopo_efetivo(funcionario)
    rede_id = rede_id_efetiva(db, funcionario)
    if escopo == "all":
        if rede_id is None:
            return set()
        q = db.query(Empresa.id).filter(Empresa.rede_id == rede_id)
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
    rede_id = rede_id_efetiva(db, funcionario)
    if rede_id is None or int(emp.rede_id) != int(rede_id):
        return False
    return int(empresa_id) in empresa_ids_vinculados(db, funcionario, apenas_ativas=False)


def validar_empresa_ids_na_rede(db: Session, rede_id: int, empresa_ids: list[int]) -> None:
    if not empresa_ids:
        raise ValueError("Selecione ao menos uma empresa.")
    emps = db.query(Empresa).filter(Empresa.id.in_(empresa_ids)).all()
    if len(emps) != len(set(empresa_ids)):
        raise ValueError("Empresa inválida na lista.")
    redes = {int(e.rede_id) for e in emps}
    if len(redes) != 1 or int(rede_id) not in redes:
        raise ValueError("Todas as empresas devem pertencer à mesma rede.")


def sincronizar_vinculos_empresas(
    db: Session,
    funcionario: FuncionarioRede,
    *,
    escopo: str,
    rede_id: int,
    empresa_ids: list[int] | None,
) -> None:
    funcionario.escopo_empresas = escopo
    funcionario.rede_id = rede_id
    if escopo == "all":
        funcionario.empresa_id = None
        db.query(FuncionarioRedeEmpresa).filter(
            FuncionarioRedeEmpresa.funcionario_id == funcionario.id
        ).delete()
        return

    ids = list(dict.fromkeys(empresa_ids or []))
    validar_empresa_ids_na_rede(db, rede_id, ids)
    if funcionario.tipo == "colaborador" and len(ids) == 1:
        funcionario.empresa_id = ids[0]
    else:
        funcionario.empresa_id = None
    db.query(FuncionarioRedeEmpresa).filter(
        FuncionarioRedeEmpresa.funcionario_id == funcionario.id
    ).delete()
    for eid in ids:
        db.add(FuncionarioRedeEmpresa(funcionario_id=funcionario.id, empresa_id=eid))
