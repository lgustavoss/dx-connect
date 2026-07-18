"""Match de contacto WhatsApp ↔ funcionário da rede por telefone/wa_id."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.funcionario_rede import FuncionarioRede


def digits_wa(raw: str | None) -> str:
    return re.sub(r"\D", "", raw or "")


def variantes_wa_id(wa_id: str | None) -> set[str]:
    digits = digits_wa(wa_id)
    out: set[str] = set()
    if not digits:
        return out
    out.add(digits)
    if digits.startswith("55") and len(digits) >= 12:
        out.add(digits[2:])
    elif len(digits) in (10, 11):
        out.add("55" + digits)
    return out


def funcionario_por_wa_id(db: Session, wa_id: str | None) -> FuncionarioRede | None:
    """Encontra funcionário ativo cujo telefone corresponde ao wa_id (com/sem DDI 55)."""
    targets = variantes_wa_id(wa_id)
    if not targets:
        return None
    # Sufixo para pré-filtrar no SQL (evita full scan com LIKE amplo)
    sample = next(iter(targets))
    suffix = sample[-8:] if len(sample) >= 8 else sample
    candidatos = (
        db.query(FuncionarioRede)
        .filter(
            FuncionarioRede.ativo.is_(True),
            FuncionarioRede.telefone.isnot(None),
            FuncionarioRede.telefone != "",
            FuncionarioRede.telefone.ilike(f"%{suffix}%"),
        )
        .order_by(FuncionarioRede.id.desc())
        .limit(80)
        .all()
    )
    for func in candidatos:
        f_digits = digits_wa(getattr(func, "telefone", None))
        if not f_digits:
            continue
        if f_digits in targets or targets & variantes_wa_id(f_digits):
            return func
        # Últimos 11 dígitos (BR sem/com 9 extra)
        if len(f_digits) >= 11 and len(sample) >= 11 and f_digits[-11:] == sample[-11:]:
            return func
    return None
