"""Settings, feriados e fecho automático do ponto (#779 / #781 / #782)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.business_calendar import is_feriado_nacional_br
from app.models.atendente import Atendente
from app.models.ponto_settings import PontoFeriado, PontoSettings
from app.schemas.ponto import (
    PontoFeriadoCreate,
    PontoFeriadoRead,
    PontoSettingsRead,
    PontoSettingsUpdate,
)


def get_or_create_settings(db: Session, tenant_id: int) -> PontoSettings:
    row = db.query(PontoSettings).filter(PontoSettings.tenant_id == tenant_id).first()
    if row:
        return row
    row = PontoSettings(
        tenant_id=tenant_id,
        usar_feriados_nacionais=True,
        fecho_automatico_ativo=False,
        fecho_apos_horas=14,
    )
    db.add(row)
    db.flush()
    return row


def settings_read(db: Session, tenant_id: int) -> PontoSettingsRead:
    row = get_or_create_settings(db, tenant_id)
    return PontoSettingsRead.model_validate(row)


def settings_update(db: Session, admin: Atendente, data: PontoSettingsUpdate) -> PontoSettingsRead:
    row = get_or_create_settings(db, admin.tenant_id)
    payload = data.model_dump(exclude_unset=True)
    if "fecho_apos_horas" in payload:
        h = payload["fecho_apos_horas"]
        if h is None or h < 4 or h > 48:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fecho_apos_horas deve estar entre 4 e 48.",
            )
    for k, v in payload.items():
        setattr(row, k, v)
    registrar_audit(
        db,
        "ponto_settings",
        row.id,
        "update",
        admin.id,
        payload=payload,
    )
    db.commit()
    db.refresh(row)
    return PontoSettingsRead.model_validate(row)


def eh_feriado(db: Session, tenant_id: int, dia: date) -> bool:
    """Feriado nacional (se ativo) ou custom da instância."""
    settings = get_or_create_settings(db, tenant_id)
    if settings.usar_feriados_nacionais and is_feriado_nacional_br(dia):
        return True
    custom = (
        db.query(PontoFeriado)
        .filter(
            PontoFeriado.tenant_id == tenant_id,
            PontoFeriado.data == dia,
            PontoFeriado.ativo.is_(True),
        )
        .first()
    )
    return custom is not None


def listar_feriados(
    db: Session,
    tenant_id: int,
    *,
    ano: int | None = None,
) -> list[PontoFeriadoRead]:
    q = db.query(PontoFeriado).filter(PontoFeriado.tenant_id == tenant_id)
    if ano is not None:
        q = q.filter(PontoFeriado.data >= date(ano, 1, 1), PontoFeriado.data <= date(ano, 12, 31))
    rows = q.order_by(PontoFeriado.data.asc()).all()
    return [PontoFeriadoRead.model_validate(r) for r in rows]


def criar_feriado(db: Session, admin: Atendente, data: PontoFeriadoCreate) -> PontoFeriadoRead:
    nome = (data.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome do feriado.")
    exists = (
        db.query(PontoFeriado)
        .filter(PontoFeriado.tenant_id == admin.tenant_id, PontoFeriado.data == data.data)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Já existe feriado nesta data.")
    row = PontoFeriado(
        tenant_id=admin.tenant_id,
        data=data.data,
        nome=nome[:255],
        ativo=True if data.ativo is None else bool(data.ativo),
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_feriado",
        row.id,
        "create",
        admin.id,
        payload={"data": data.data.isoformat(), "nome": nome},
    )
    db.commit()
    db.refresh(row)
    return PontoFeriadoRead.model_validate(row)


def remover_feriado(db: Session, admin: Atendente, feriado_id: int) -> None:
    row = (
        db.query(PontoFeriado)
        .filter(PontoFeriado.id == feriado_id, PontoFeriado.tenant_id == admin.tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Feriado não encontrado")
    registrar_audit(
        db,
        "ponto_feriado",
        row.id,
        "delete",
        admin.id,
        payload={"data": row.data.isoformat(), "nome": row.nome},
    )
    db.delete(row)
    db.commit()


def processar_fecho_automatico(db: Session, *, limit: int = 100) -> int:
    """Fecha jornadas abertas além do limite, só onde a política está ativa."""
    from app.services import ponto as ponto_svc

    settings_rows = (
        db.query(PontoSettings)
        .filter(PontoSettings.fecho_automatico_ativo.is_(True))
        .all()
    )
    if not settings_rows:
        return 0

    agora = datetime.now(timezone.utc)
    fechados = 0
    for st in settings_rows:
        horas = max(4, int(st.fecho_apos_horas or 14))
        limite = agora.timestamp() - horas * 3600
        atendentes = (
            db.query(Atendente)
            .filter(Atendente.tenant_id == st.tenant_id, Atendente.ativo.is_(True))
            .all()
        )
        for a in atendentes:
            if fechados >= limit:
                return fechados
            entrada = ponto_svc._entrada_da_jornada_aberta(db, a.id)
            if entrada is None:
                continue
            reg = ponto_svc._as_utc(entrada.registrado_em)
            if reg.timestamp() > limite:
                continue
            if ponto_svc.em_pausa_aberta(db, a.id):
                ponto_svc.bater(
                    db,
                    a,
                    "pausa_fim",
                    origem="sistema",
                    registrado_em=agora,
                    commit=False,
                )
            saida = ponto_svc.bater(
                db,
                a,
                "saida",
                origem="sistema",
                registrado_em=agora,
                commit=False,
            )
            registrar_audit(
                db,
                "ponto_batida",
                saida.id,
                "fecho_automatico",
                None,
                payload={
                    "atendente_id": a.id,
                    "tenant_id": st.tenant_id,
                    "fecho_apos_horas": horas,
                    "entrada_em": reg.isoformat(),
                },
            )
            fechados += 1
    if fechados:
        db.flush()
    return fechados
