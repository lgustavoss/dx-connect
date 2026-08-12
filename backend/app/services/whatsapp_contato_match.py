"""Match de contacto WhatsApp ↔ funcionário da rede por telefone/wa_id."""

from __future__ import annotations

import re

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.models.funcionario_rede import FuncionarioRede
from app.models.whatsapp_chat import WhatsappChat


def digits_wa(raw: str | None) -> str:
    return re.sub(r"\D", "", raw or "")


def variantes_wa_id(wa_id: str | None) -> set[str]:
    """
    Variantes do mesmo contacto WhatsApp.

    Cobre DDI 55 com/sem prefixo e o nono dígito BR em telemóveis
    (ex.: 5511988776655 ↔ 551188776655 ↔ 11988776655).
    """
    digits = digits_wa(wa_id)
    out: set[str] = set()
    if not digits:
        return out

    def add_with_ddi(d: str) -> None:
        if not d:
            return
        out.add(d)
        if d.startswith("55") and len(d) >= 12:
            out.add(d[2:])
        elif len(d) in (10, 11) and not d.startswith("55"):
            out.add("55" + d)

    add_with_ddi(digits)

    local = digits[2:] if digits.startswith("55") and len(digits) >= 12 else digits

    # Telemóvel BR: DDD(2) + 9 + 8 dígitos ↔ DDD(2) + 8 dígitos (legado)
    if len(local) == 11 and local[2] == "9":
        add_with_ddi(local[:2] + local[3:])
    elif len(local) == 10:
        add_with_ddi(local[:2] + "9" + local[2:])

    return out


def canonical_wa_id_para_lock(wa_id: str | None) -> str:
    """Representante estável entre variantes — mesmo lock para o mesmo contacto."""
    variants = variantes_wa_id(wa_id)
    if not variants:
        return digits_wa(wa_id) or (wa_id or "").strip()
    with_55 = [v for v in variants if v.startswith("55")]
    pool = with_55 or list(variants)
    # Preferir forma mais completa (com 55 + nono dígito quando existir)
    return max(pool, key=lambda v: (len(v), v))


def funcionario_por_wa_id(db: Session, wa_id: str | None) -> FuncionarioRede | None:
    """Encontra funcionário ativo cujo telefone corresponde ao wa_id (com/sem DDI 55 / nono dígito)."""
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
    return None


def chat_aberto_por_wa_id(
    db: Session,
    wa_id: str | None,
    *,
    excluir_classificacao_pendente: bool = False,
    load_options: Sequence[Any] | None = None,
) -> WhatsappChat | None:
    """Chat ativo (fila ou em atendimento) para o contacto, tolerando variantes de wa_id."""
    targets = variantes_wa_id(wa_id)
    if not targets:
        return None
    q = db.query(WhatsappChat)
    if load_options:
        q = q.options(*load_options)
    q = q.filter(
        WhatsappChat.wa_id.in_(targets),
        WhatsappChat.estado.in_(("aguardando_atendente", "em_atendimento")),
    )
    if excluir_classificacao_pendente:
        q = q.filter(WhatsappChat.classificacao_demanda_pendente.is_(False))
    return q.order_by(WhatsappChat.id.desc()).first()


def chat_aguardando_avaliacao_por_wa_id(db: Session, wa_id: str | None) -> WhatsappChat | None:
    targets = variantes_wa_id(wa_id)
    if not targets:
        return None
    return (
        db.query(WhatsappChat)
        .filter(
            WhatsappChat.wa_id.in_(targets),
            WhatsappChat.estado == "aguardando_avaliacao",
        )
        .order_by(WhatsappChat.id.desc())
        .first()
    )
