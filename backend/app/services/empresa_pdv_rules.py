"""Regras de negócio para PDVs por empresa."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.empresa_pdv import EmpresaPdv, EmpresaPdvAcessoRemoto
from app.services.catalogo_vinculos import recusar_desativar_em_uso


def validar_papel_principal_auxiliar(
    db: Session,
    empresa_id: int,
    *,
    ignorar_pdv_id: int | None = None,
) -> None:
    q = db.query(EmpresaPdv).filter(EmpresaPdv.empresa_id == empresa_id, EmpresaPdv.ativo.is_(True))
    if ignorar_pdv_id is not None:
        q = q.filter(EmpresaPdv.id != ignorar_pdv_id)
    rows = q.all()
    tem_auxiliar = any(r.papel == "auxiliar" for r in rows)
    tem_principal = any(r.papel == "principal" for r in rows)
    if tem_auxiliar and not tem_principal:
        raise ValueError(
            "Com pelo menos um PDV auxiliar ativo, a empresa precisa de ao menos um PDV principal ativo."
        )


def contar_pdvs_do_rotulo(db: Session, rotulo_id: int) -> int:
    return db.query(func.count(EmpresaPdv.id)).filter(EmpresaPdv.rotulo_id == rotulo_id).scalar() or 0


def garantir_rotulo_pode_desativar(db: Session, rotulo_id: int) -> None:
    recusar_desativar_em_uso(
        contar_pdvs_do_rotulo(db, rotulo_id),
        um="Não é possível desativar este rótulo: 1 PDV ainda o usa.",
        varios="Não é possível desativar este rótulo: {n} PDVs ainda o usam.",
    )


def contar_pdvs_do_tipo_acesso(db: Session, tipo_id: int) -> int:
    n = (
        db.query(func.count(func.distinct(EmpresaPdv.id)))
        .outerjoin(EmpresaPdvAcessoRemoto, EmpresaPdvAcessoRemoto.pdv_id == EmpresaPdv.id)
        .filter(
            or_(
                EmpresaPdv.tipo_acesso_remoto_id == tipo_id,
                EmpresaPdvAcessoRemoto.tipo_acesso_remoto_id == tipo_id,
            )
        )
        .scalar()
        or 0
    )
    return int(n)


def garantir_tipo_acesso_pode_desativar(db: Session, tipo_id: int) -> None:
    recusar_desativar_em_uso(
        contar_pdvs_do_tipo_acesso(db, tipo_id),
        um="Não é possível desativar este tipo de acesso: 1 PDV ainda o usa.",
        varios="Não é possível desativar este tipo de acesso: {n} PDVs ainda o usam.",
    )
