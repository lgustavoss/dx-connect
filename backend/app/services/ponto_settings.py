"""Settings, feriados e fecho automático do ponto (#779 / #781 / #782)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.business_calendar import is_feriado_nacional_br
from app.models.atendente import Atendente
from app.models.ponto_settings import PontoFeriado, PontoLocal, PontoSettings
from app.schemas.ponto import (
    PontoFeriadoCreate,
    PontoFeriadoRead,
    PontoLocalCreate,
    PontoLocalRead,
    PontoLocalUpdate,
    PontoSettingsPublicRead,
    PontoSettingsRead,
    PontoSettingsUpdate,
)
from app.services.ponto_geofence import POLITICAS_VALIDAS, locais_ativos


def get_or_create_settings(db: Session, tenant_id: int) -> PontoSettings:
    row = db.query(PontoSettings).filter(PontoSettings.tenant_id == tenant_id).first()
    if row:
        return row
    row = PontoSettings(
        tenant_id=tenant_id,
        usar_feriados_nacionais=True,
        fecho_automatico_ativo=False,
        fecho_apos_horas=14,
        jornada_diaria_minutos=480,
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
    if "fecho_margem_pos_saida_minutos" in payload:
        m = payload["fecho_margem_pos_saida_minutos"]
        if m is None or m < 0 or m > 240:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fecho_margem_pos_saida_minutos deve estar entre 0 e 240.",
            )
    if "jornada_diaria_minutos" in payload:
        m = payload["jornada_diaria_minutos"]
        if m is None or m < 60 or m > 1440:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="jornada_diaria_minutos deve estar entre 60 e 1440.",
            )
    if "politica_geolocalizacao" in payload:
        p = (payload["politica_geolocalizacao"] or "").strip().lower()
        if p not in POLITICAS_VALIDAS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="politica_geolocalizacao deve ser opcional, recomendada ou obrigatoria.",
            )
        payload["politica_geolocalizacao"] = p
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


def settings_public_read(db: Session, tenant_id: int) -> PontoSettingsPublicRead:
    row = get_or_create_settings(db, tenant_id)
    politica = (getattr(row, "politica_geolocalizacao", None) or "opcional").strip().lower()
    if politica not in POLITICAS_VALIDAS:
        politica = "opcional"
    tem = len(locais_ativos(db, tenant_id)) > 0
    return PontoSettingsPublicRead(politica_geolocalizacao=politica, tem_locais_ativos=tem)


def listar_locais(db: Session, tenant_id: int) -> list[PontoLocalRead]:
    rows = (
        db.query(PontoLocal)
        .filter(PontoLocal.tenant_id == tenant_id)
        .order_by(PontoLocal.nome.asc(), PontoLocal.id.asc())
        .all()
    )
    return [PontoLocalRead.model_validate(r) for r in rows]


def criar_local(db: Session, admin: Atendente, data: PontoLocalCreate) -> PontoLocalRead:
    nome = (data.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome do local.")
    row = PontoLocal(
        tenant_id=admin.tenant_id,
        nome=nome[:255],
        latitude=float(data.latitude),
        longitude=float(data.longitude),
        raio_metros=int(data.raio_metros or 200),
        ativo=True if data.ativo is None else bool(data.ativo),
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_local",
        row.id,
        "create",
        admin.id,
        payload={"nome": nome, "latitude": data.latitude, "longitude": data.longitude},
    )
    db.commit()
    db.refresh(row)
    return PontoLocalRead.model_validate(row)


def atualizar_local(
    db: Session,
    admin: Atendente,
    local_id: int,
    data: PontoLocalUpdate,
) -> PontoLocalRead:
    row = (
        db.query(PontoLocal)
        .filter(PontoLocal.id == local_id, PontoLocal.tenant_id == admin.tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Local não encontrado")
    payload = data.model_dump(exclude_unset=True)
    if "nome" in payload:
        nome = (payload["nome"] or "").strip()
        if not nome:
            raise HTTPException(status_code=400, detail="Informe o nome do local.")
        payload["nome"] = nome[:255]
    for k, v in payload.items():
        setattr(row, k, v)
    registrar_audit(
        db,
        "ponto_local",
        row.id,
        "update",
        admin.id,
        payload=payload,
    )
    db.commit()
    db.refresh(row)
    return PontoLocalRead.model_validate(row)


def remover_local(db: Session, admin: Atendente, local_id: int) -> None:
    row = (
        db.query(PontoLocal)
        .filter(PontoLocal.id == local_id, PontoLocal.tenant_id == admin.tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Local não encontrado")
    registrar_audit(
        db,
        "ponto_local",
        row.id,
        "delete",
        admin.id,
        payload={"nome": row.nome},
    )
    db.delete(row)
    db.commit()


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
    """Fecha jornadas esquecidas: N horas abertas OU após saída prevista + margem (#961)."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    from app.services import escala as escala_svc
    from app.services import ponto as ponto_svc

    PONTO_TZ = ZoneInfo("America/Sao_Paulo")

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
        margem = max(0, int(getattr(st, "fecho_margem_pos_saida_minutos", 30) or 0))
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
            por_horas = (agora - reg).total_seconds() >= horas * 3600
            criterios: list[str] = []
            if por_horas:
                criterios.append("n_horas")
            dia = reg.astimezone(PONTO_TZ).date()
            saida_prev = escala_svc.saida_prevista_em(a, dia)
            if saida_prev is not None:
                limite_saida = saida_prev + timedelta(minutes=margem)
                if agora.astimezone(PONTO_TZ) >= limite_saida:
                    criterios.append("saida_prevista")
            if not criterios:
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
                "esquecimento",
                None,
                payload={
                    "atendente_id": a.id,
                    "tenant_id": st.tenant_id,
                    "fecho_apos_horas": horas,
                    "fecho_margem_pos_saida_minutos": margem,
                    "criterios": criterios,
                    "entrada_em": reg.isoformat(),
                    "motivo": "esquecimento",
                },
            )
            fechados += 1
    if fechados:
        db.flush()
    return fechados
