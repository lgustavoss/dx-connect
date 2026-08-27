"""Ausências programadas: férias / folga (#976)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.ponto_ausencia import PontoAusencia
from app.schemas.ponto import PontoAusenciaRead
from app.services import ponto as ponto_svc

TIPOS = frozenset({"ferias", "folga_programada"})
ESTADOS = frozenset({"pendente", "aprovada", "rejeitada"})


def _to_read(row: PontoAusencia) -> PontoAusenciaRead:
    return PontoAusenciaRead(
        id=row.id,
        atendente_id=row.atendente_id,
        atendente_nome=row.atendente.nome if row.atendente else None,
        tipo=row.tipo,
        desde=row.desde,
        ate=row.ate,
        motivo=row.motivo,
        estado=row.estado,
        origem=row.origem or "solicitacao",
        decidido_por_id=row.decidido_por_id,
        decidido_em=row.decidido_em,
        decisao_motivo=row.decisao_motivo,
        created_at=row.created_at,
    )


def _validar_periodo(desde: date, ate: date) -> None:
    if ate < desde:
        raise HTTPException(status_code=400, detail="A data final deve ser igual ou posterior à inicial.")
    if (ate - desde).days > 366:
        raise HTTPException(status_code=400, detail="Período máximo de 366 dias.")


def _validar_tipo(tipo: str) -> str:
    t = (tipo or "").strip().lower()
    if t not in TIPOS:
        raise HTTPException(status_code=400, detail="Tipo deve ser ferias ou folga_programada.")
    return t


def tipo_ausencia_aprovada_no_dia(db: Session, atendente_id: int, dia: date) -> str | None:
    """Retorna tipo (ferias|folga_programada) se houver ausência aprovada cobrindo o dia."""
    row = (
        db.query(PontoAusencia)
        .filter(
            PontoAusencia.atendente_id == atendente_id,
            PontoAusencia.estado == "aprovada",
            PontoAusencia.desde <= dia,
            PontoAusencia.ate >= dia,
        )
        .order_by(PontoAusencia.id.desc())
        .first()
    )
    return row.tipo if row else None


def mapa_ausencias_aprovadas(
    db: Session, atendente_id: int, *, desde: date, ate: date
) -> dict[date, str]:
    """Mapa dia → tipo para o período (útil no calendário)."""
    rows = (
        db.query(PontoAusencia)
        .filter(
            PontoAusencia.atendente_id == atendente_id,
            PontoAusencia.estado == "aprovada",
            PontoAusencia.ate >= desde,
            PontoAusencia.desde <= ate,
        )
        .all()
    )
    out: dict[date, str] = {}
    for r in rows:
        d = max(r.desde, desde)
        fim = min(r.ate, ate)
        cur = d
        while cur <= fim:
            out[cur] = r.tipo
            cur = date.fromordinal(cur.toordinal() + 1)
    return out


def solicitar(
    db: Session,
    atendente: Atendente,
    *,
    tipo: str,
    desde: date,
    ate: date,
    motivo: str | None = None,
) -> PontoAusenciaRead:
    ponto_svc.exigir_acesso_ponto(atendente)
    t = _validar_tipo(tipo)
    _validar_periodo(desde, ate)
    row = PontoAusencia(
        tenant_id=atendente.tenant_id,
        atendente_id=atendente.id,
        tipo=t,
        desde=desde,
        ate=ate,
        motivo=(motivo or "").strip()[:1000] or None,
        estado="pendente",
        origem="solicitacao",
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_ausencia",
        row.id,
        "create",
        atendente.id,
        payload={"tipo": t, "desde": str(desde), "ate": str(ate), "estado": "pendente"},
    )
    db.commit()
    db.refresh(row)
    row = (
        db.query(PontoAusencia)
        .options(joinedload(PontoAusencia.atendente))
        .filter(PontoAusencia.id == row.id)
        .first()
    )
    assert row is not None
    return _to_read(row)


def conceder_admin(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int,
    tipo: str,
    desde: date,
    ate: date,
    motivo: str | None = None,
) -> PontoAusenciaRead:
    t = _validar_tipo(tipo)
    _validar_periodo(desde, ate)
    alvo = (
        db.query(Atendente)
        .filter(
            Atendente.id == atendente_id,
            Atendente.tenant_id == admin.tenant_id,
            Atendente.role != "saas_ops",
        )
        .first()
    )
    if not alvo:
        raise HTTPException(status_code=404, detail="Atendente não encontrado")
    agora = datetime.now(timezone.utc)
    row = PontoAusencia(
        tenant_id=admin.tenant_id,
        atendente_id=alvo.id,
        tipo=t,
        desde=desde,
        ate=ate,
        motivo=(motivo or "").strip()[:1000] or "Ausência agendada pelo administrador.",
        estado="aprovada",
        origem="admin",
        decidido_por_id=admin.id,
        decidido_em=agora,
        decisao_motivo="Agendamento direto",
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_ausencia",
        row.id,
        "conceder",
        admin.id,
        payload={"atendente_id": alvo.id, "tipo": t, "desde": str(desde), "ate": str(ate)},
    )
    db.commit()
    db.refresh(row)
    row = (
        db.query(PontoAusencia)
        .options(joinedload(PontoAusencia.atendente))
        .filter(PontoAusencia.id == row.id)
        .first()
    )
    assert row is not None
    return _to_read(row)


def decidir(
    db: Session,
    admin: Atendente,
    ausencia_id: int,
    *,
    aprovar: bool,
    decisao_motivo: str | None = None,
) -> PontoAusenciaRead:
    row = (
        db.query(PontoAusencia)
        .options(joinedload(PontoAusencia.atendente))
        .filter(PontoAusencia.id == ausencia_id, PontoAusencia.tenant_id == admin.tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Ausência não encontrada")
    if row.estado != "pendente":
        raise HTTPException(status_code=400, detail="Este pedido já foi decidido.")
    row.decidido_por_id = admin.id
    row.decidido_em = datetime.now(timezone.utc)
    row.decisao_motivo = (decisao_motivo or "").strip()[:1000] or None
    if aprovar:
        row.estado = "aprovada"
        if not row.decisao_motivo:
            row.decisao_motivo = "Aprovado pelo administrador"
    else:
        row.estado = "rejeitada"
        if not row.decisao_motivo:
            row.decisao_motivo = "Negado pelo administrador"
    registrar_audit(
        db,
        "ponto_ausencia",
        row.id,
        "decidir",
        admin.id,
        payload={"estado": row.estado},
    )
    db.commit()
    db.refresh(row)
    return _to_read(row)


def listar_me(db: Session, atendente: Atendente) -> list[PontoAusenciaRead]:
    ponto_svc.exigir_acesso_ponto(atendente)
    rows = (
        db.query(PontoAusencia)
        .options(joinedload(PontoAusencia.atendente))
        .filter(PontoAusencia.atendente_id == atendente.id)
        .order_by(PontoAusencia.desde.desc(), PontoAusencia.id.desc())
        .limit(100)
        .all()
    )
    return [_to_read(r) for r in rows]


def listar_admin(
    db: Session,
    admin: Atendente,
    *,
    estado: str | None = "pendente",
) -> list[PontoAusenciaRead]:
    q = (
        db.query(PontoAusencia)
        .options(joinedload(PontoAusencia.atendente))
        .filter(PontoAusencia.tenant_id == admin.tenant_id)
    )
    if estado:
        if estado not in ESTADOS:
            raise HTTPException(status_code=400, detail="Estado inválido.")
        q = q.filter(PontoAusencia.estado == estado)
    rows = q.order_by(PontoAusencia.created_at.asc()).limit(200).all()
    return [_to_read(r) for r in rows]


def remover_admin(db: Session, admin: Atendente, ausencia_id: int) -> None:
    """Remove ausência aprovada/agendada (correção)."""
    row = (
        db.query(PontoAusencia)
        .filter(PontoAusencia.id == ausencia_id, PontoAusencia.tenant_id == admin.tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Ausência não encontrada")
    registrar_audit(
        db,
        "ponto_ausencia",
        row.id,
        "delete",
        admin.id,
        payload={"tipo": row.tipo, "desde": str(row.desde), "ate": str(row.ate)},
    )
    db.delete(row)
    db.commit()
