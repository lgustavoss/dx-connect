"""Alcance de setor: trata duplicatas no cadastro (mesmo nome, IDs diferentes)."""

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import Setor
from app.models.atendente import Atendente


def ids_setores_mesmo_nome(db: Session, setor_id: int) -> set[int]:
    """Todos os IDs de setor com o mesmo nome (trim + case-insensitive) que o setor indicado."""
    s = db.query(Setor).filter(Setor.id == setor_id).first()
    if not s:
        return {setor_id}
    alvo = (s.nome or "").strip().lower()
    rows = (
        db.query(Setor.id)
        .filter(func.lower(func.trim(Setor.nome)) == alvo)
        .all()
    )
    out = {r[0] for r in rows}
    return out if out else {setor_id}


def ids_setores_visiveis_atendente(db: Session, atendente: Atendente) -> set[int]:
    """IDs de setor que o atendente enxerga (inclui duplicatas de nome dos vínculos dele)."""
    out: set[int] = set()
    for s in atendente.setores:
        out |= ids_setores_mesmo_nome(db, s.id)
    return out


def atendente_atende_algum_id_setor(db: Session, atendente_id: int, setor_id: int) -> bool:
    """True se o atendente está vinculado a algum setor com o mesmo nome que setor_id."""
    ids_alvo = ids_setores_mesmo_nome(db, setor_id)
    a = (
        db.query(Atendente)
        .options(joinedload(Atendente.setores))
        .filter(Atendente.id == atendente_id)
        .first()
    )
    if not a:
        return False
    atend_ids = {s.id for s in a.setores}
    return bool(atend_ids & ids_alvo)


def responsavel_elegivel_para_setor_do_ticket(db: Session, responsavel_id: int, setor_id: int) -> bool:
    """True se o usuário pode ser responsável por um ticket neste setor.

    - `admin`: sempre elegível (operam sem vínculo obrigatório ao setor do ticket; issue #38).
    - demais: devem atender o setor (incluindo homônimos).
    """
    alvo = (
        db.query(Atendente)
        .options(joinedload(Atendente.setores))
        .filter(Atendente.id == responsavel_id)
        .first()
    )
    if not alvo:
        return False
    if alvo.role == "admin":
        return True
    return atendente_atende_algum_id_setor(db, responsavel_id, setor_id)
