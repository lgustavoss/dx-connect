"""Dia convocado — trabalho fora da grade (#985)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.core.business_calendar import parse_hhmm
from app.models.atendente import Atendente
from app.models.ponto_dia_convocado import PontoDiaConvocado
from app.schemas.ponto import PontoDiaConvocadoRead
from app.services import escala as escala_svc
from app.services.escala import PONTO_TZ


def _to_read(row: PontoDiaConvocado) -> PontoDiaConvocadoRead:
    return PontoDiaConvocadoRead(
        id=row.id,
        atendente_id=row.atendente_id,
        atendente_nome=row.atendente.nome if row.atendente else None,
        data_ref=row.data_ref,
        inicio=row.inicio,
        fim=row.fim,
        tolerancia_minutos=row.tolerancia_minutos,
        motivo=row.motivo,
        estado=row.estado,
        criado_por_id=row.criado_por_id,
        created_at=row.created_at,
        cancelado_por_id=row.cancelado_por_id,
        cancelado_em=row.cancelado_em,
    )


def _validar_horario(inicio: str, fim: str) -> tuple[str, str]:
    ini = parse_hhmm(inicio)
    fim_p = parse_hhmm(fim)
    if not ini or not fim_p:
        raise HTTPException(status_code=400, detail="Horários inválidos (use HH:MM).")
    if (ini[0], ini[1]) >= (fim_p[0], fim_p[1]):
        raise HTTPException(status_code=400, detail="O início deve ser anterior ao fim (sem cruzar meia-noite).")
    return f"{ini[0]:02d}:{ini[1]:02d}", f"{fim_p[0]:02d}:{fim_p[1]:02d}"


def janela_horario(row: PontoDiaConvocado) -> tuple[tuple[int, int], tuple[int, int]] | None:
    ini = parse_hhmm(row.inicio)
    fim = parse_hhmm(row.fim)
    if ini and fim and (fim[0], fim[1]) > (ini[0], ini[1]):
        return ini, fim
    return None


def tolerancia_efetiva(atendente: Atendente, row: PontoDiaConvocado) -> int:
    if row.tolerancia_minutos is not None:
        return max(0, int(row.tolerancia_minutos))
    return int(getattr(atendente, "tolerancia_atraso_minutos", 0) or 0)


def segundos_esperados_convocado(row: PontoDiaConvocado) -> int:
    janela = janela_horario(row)
    if not janela:
        return 0
    pe, ps = janela
    ini = pe[0] * 3600 + pe[1] * 60
    fim = ps[0] * 3600 + ps[1] * 60
    return max(0, fim - ini)


def limite_atraso_em(
    atendente: Atendente, dia: date, conv: PontoDiaConvocado | None
) -> datetime | None:
    if conv:
        janela = janela_horario(conv)
        if not janela:
            return None
        pe, _ = janela
        tol = tolerancia_efetiva(atendente, conv)
        return datetime.combine(dia, time(hour=pe[0], minute=pe[1]), tzinfo=PONTO_TZ) + timedelta(
            minutes=tol
        )
    return escala_svc.limite_atraso_em(atendente, dia)


def liberacao_entrada_em(
    atendente: Atendente, dia: date, conv: PontoDiaConvocado | None
) -> datetime | None:
    if conv:
        janela = janela_horario(conv)
        if not janela:
            return None
        pe, _ = janela
        tol = tolerancia_efetiva(atendente, conv)
        return datetime.combine(dia, time(hour=pe[0], minute=pe[1]), tzinfo=PONTO_TZ) - timedelta(
            minutes=tol
        )
    return escala_svc.liberacao_entrada_em(atendente, dia)


def saida_prevista_em(
    atendente: Atendente, dia: date, conv: PontoDiaConvocado | None
) -> datetime | None:
    if conv:
        janela = janela_horario(conv)
        if not janela:
            return None
        _, ps = janela
        return datetime.combine(dia, time(hour=ps[0], minute=ps[1]), tzinfo=PONTO_TZ)
    return escala_svc.saida_prevista_em(atendente, dia)


def liberacao_saida_lembrete_em(
    atendente: Atendente, dia: date, conv: PontoDiaConvocado | None
) -> datetime | None:
    saida = saida_prevista_em(atendente, dia, conv)
    if saida is None:
        return None
    if conv:
        tol = tolerancia_efetiva(atendente, conv)
        return saida - timedelta(minutes=tol)
    return escala_svc.liberacao_saida_lembrete_em(atendente, dia)


def convocado_ativo_no_dia(db: Session, atendente_id: int, dia: date) -> PontoDiaConvocado | None:
    return (
        db.query(PontoDiaConvocado)
        .filter(
            PontoDiaConvocado.atendente_id == atendente_id,
            PontoDiaConvocado.data_ref == dia,
            PontoDiaConvocado.estado == "ativa",
        )
        .first()
    )


def mapa_convocados(
    db: Session, atendente_id: int, *, desde: date, ate: date
) -> dict[date, PontoDiaConvocado]:
    rows = (
        db.query(PontoDiaConvocado)
        .filter(
            PontoDiaConvocado.atendente_id == atendente_id,
            PontoDiaConvocado.estado == "ativa",
            PontoDiaConvocado.data_ref >= desde,
            PontoDiaConvocado.data_ref <= ate,
        )
        .all()
    )
    return {r.data_ref: r for r in rows}


def eh_dia_esperado_efetivo(db: Session, atendente: Atendente, dia: date) -> bool:
    """Dia esperado incluindo convocação (#985) e cobertura (#970)."""
    if convocado_ativo_no_dia(db, atendente.id, dia):
        return True
    from app.services import ponto_cobertura as cob_svc

    return cob_svc.eh_dia_esperado_efetivo(db, atendente, dia)


def segundos_esperados_efetivo(
    db: Session, atendente: Atendente, dia: date, conv: PontoDiaConvocado | None = None
) -> int:
    row = conv or convocado_ativo_no_dia(db, atendente.id, dia)
    if row:
        seg = segundos_esperados_convocado(row)
        if seg > 0:
            return seg
    return escala_svc.segundos_esperados_dia(atendente, dia)


def _atendente_tenant(db: Session, tenant_id: int, atendente_id: int) -> Atendente:
    a = (
        db.query(Atendente)
        .filter(
            Atendente.id == atendente_id,
            Atendente.tenant_id == tenant_id,
            Atendente.role != "saas_ops",
            Atendente.ativo.is_(True),
        )
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Atendente não encontrado")
    return a


def _checar_conflitos(
    db: Session,
    *,
    tenant_id: int,
    atendente_id: int,
    data_ref: date,
) -> None:
    from app.services import ponto_ausencia as ausencia_svc

    if ausencia_svc.tipo_ausencia_aprovada_no_dia(db, atendente_id, data_ref):
        raise HTTPException(
            status_code=400,
            detail="Já há férias ou folga programada nesta data.",
        )
    existente = convocado_ativo_no_dia(db, atendente_id, data_ref)
    if existente:
        raise HTTPException(status_code=400, detail="Já existe convocação ativa nesta data.")


def criar_admin(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int,
    data_ref: date,
    inicio: str,
    fim: str,
    motivo: str,
    tolerancia_minutos: int | None = None,
) -> PontoDiaConvocadoRead:
    if data_ref < date.today():
        raise HTTPException(status_code=400, detail="A data deve ser hoje ou futura.")
    motivo_limpo = (motivo or "").strip()
    if len(motivo_limpo) < 3:
        raise HTTPException(status_code=400, detail="Informe o motivo (mínimo 3 caracteres).")
    ini_s, fim_s = _validar_horario(inicio, fim)
    alvo = _atendente_tenant(db, admin.tenant_id, atendente_id)
    _checar_conflitos(db, tenant_id=admin.tenant_id, atendente_id=alvo.id, data_ref=data_ref)
    if tolerancia_minutos is not None and tolerancia_minutos < 0:
        raise HTTPException(status_code=400, detail="Tolerância inválida.")
    row = PontoDiaConvocado(
        tenant_id=admin.tenant_id,
        atendente_id=alvo.id,
        data_ref=data_ref,
        inicio=ini_s,
        fim=fim_s,
        tolerancia_minutos=tolerancia_minutos,
        motivo=motivo_limpo[:1000],
        estado="ativa",
        criado_por_id=admin.id,
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_dia_convocado",
        row.id,
        "create",
        admin.id,
        payload={
            "atendente_id": alvo.id,
            "data_ref": str(data_ref),
            "inicio": ini_s,
            "fim": fim_s,
            "motivo": motivo_limpo,
        },
    )
    db.commit()
    return _to_read(
        db.query(PontoDiaConvocado)
        .options(joinedload(PontoDiaConvocado.atendente))
        .filter(PontoDiaConvocado.id == row.id)
        .first()  # type: ignore[arg-type]
    )


def listar_admin(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int | None = None,
    desde: date | None = None,
    ate: date | None = None,
    estado: str | None = "ativa",
) -> list[PontoDiaConvocadoRead]:
    q = (
        db.query(PontoDiaConvocado)
        .options(joinedload(PontoDiaConvocado.atendente))
        .filter(PontoDiaConvocado.tenant_id == admin.tenant_id)
    )
    if atendente_id is not None:
        q = q.filter(PontoDiaConvocado.atendente_id == atendente_id)
    if desde is not None:
        q = q.filter(PontoDiaConvocado.data_ref >= desde)
    if ate is not None:
        q = q.filter(PontoDiaConvocado.data_ref <= ate)
    if estado:
        q = q.filter(PontoDiaConvocado.estado == estado)
    rows = q.order_by(PontoDiaConvocado.data_ref.asc(), PontoDiaConvocado.id.asc()).limit(200).all()
    return [_to_read(r) for r in rows]


def cancelar_admin(db: Session, admin: Atendente, convocado_id: int) -> PontoDiaConvocadoRead:
    row = (
        db.query(PontoDiaConvocado)
        .options(joinedload(PontoDiaConvocado.atendente))
        .filter(
            PontoDiaConvocado.id == convocado_id,
            PontoDiaConvocado.tenant_id == admin.tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Convocação não encontrada")
    if row.estado != "ativa":
        raise HTTPException(status_code=400, detail="Esta convocação já foi cancelada.")
    if row.data_ref < date.today():
        raise HTTPException(status_code=400, detail="Só é possível cancelar convocações de hoje em diante.")
    row.estado = "cancelada"
    row.cancelado_por_id = admin.id
    row.cancelado_em = datetime.now(timezone.utc)
    registrar_audit(
        db,
        "ponto_dia_convocado",
        row.id,
        "cancelar",
        admin.id,
        payload={"atendente_id": row.atendente_id, "data_ref": str(row.data_ref)},
    )
    db.commit()
    db.refresh(row)
    return _to_read(row)
