"""Regras de negócio para PDVs por empresa."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.empresa_pdv import EmpresaPdv


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
