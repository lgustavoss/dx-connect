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
from app.services.ponto_geofence import POLITICAS_VALIDAS, locais_efetivos_ativos


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
    if "pausa_minima_minutos" in payload:
        m = payload["pausa_minima_minutos"]
        if m is None or m < 0 or m > 240:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pausa_minima_minutos deve estar entre 0 e 240.",
            )
    if "he_teto_mensal_minutos" in payload:
        m = payload["he_teto_mensal_minutos"]
        if m is not None and (m < 30 or m > 31 * 24 * 60):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="he_teto_mensal_minutos deve estar entre 30 e 44640, ou vazio.",
            )
    if "politica_geolocalizacao" in payload:
        p = (payload["politica_geolocalizacao"] or "").strip().lower()
        if p not in POLITICAS_VALIDAS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="politica_geolocalizacao deve ser opcional, recomendada ou obrigatoria.",
            )
        payload["politica_geolocalizacao"] = p
    if "he_destino_excedente" in payload:
        d = (payload["he_destino_excedente"] or "").strip().lower()
        if d not in ("banco", "pagamento", "misto"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="he_destino_excedente deve ser banco, pagamento ou misto.",
            )
        payload["he_destino_excedente"] = d
    if "he_banco_primeiros_minutos" in payload:
        m = payload["he_banco_primeiros_minutos"]
        if m is None or m < 0 or m > 24 * 60:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="he_banco_primeiros_minutos deve estar entre 0 e 1440.",
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


def settings_public_read(db: Session, atendente: Atendente) -> PontoSettingsPublicRead:
    row = get_or_create_settings(db, atendente.tenant_id)
    politica = (getattr(row, "politica_geolocalizacao", None) or "opcional").strip().lower()
    if politica not in POLITICAS_VALIDAS:
        politica = "opcional"
    tem = len(locais_efetivos_ativos(db, atendente)) > 0
    return PontoSettingsPublicRead(politica_geolocalizacao=politica, tem_locais_ativos=tem)


def _atendente_do_tenant(db: Session, tenant_id: int, atendente_id: int) -> Atendente:
    row = (
        db.query(Atendente)
        .filter(Atendente.id == atendente_id, Atendente.tenant_id == tenant_id)
        .first()
    )
    if not row or row.role == "saas_ops":
        raise HTTPException(status_code=404, detail="Atendente não encontrado")
    return row


def listar_locais(
    db: Session,
    tenant_id: int,
    *,
    atendente_id: int | None = None,
    so_orfos: bool = False,
) -> list[PontoLocalRead]:
    q = db.query(PontoLocal).filter(PontoLocal.tenant_id == tenant_id)
    if so_orfos:
        q = q.filter(PontoLocal.atendente_id.is_(None))
    elif atendente_id is not None:
        q = q.filter(PontoLocal.atendente_id == atendente_id)
    rows = q.order_by(PontoLocal.nome.asc(), PontoLocal.id.asc()).all()
    return [PontoLocalRead.model_validate(r) for r in rows]


def criar_local(db: Session, admin: Atendente, data: PontoLocalCreate) -> PontoLocalRead:
    nome = (data.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome do local.")
    alvo = _atendente_do_tenant(db, admin.tenant_id, int(data.atendente_id))
    endereco = (data.endereco or "").strip() or None
    row = PontoLocal(
        tenant_id=admin.tenant_id,
        atendente_id=alvo.id,
        nome=nome[:255],
        endereco=endereco[:512] if endereco else None,
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
        payload={
            "nome": nome,
            "atendente_id": alvo.id,
            "latitude": data.latitude,
            "longitude": data.longitude,
        },
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
    if "endereco" in payload and payload["endereco"] is not None:
        end = str(payload["endereco"]).strip()
        payload["endereco"] = end[:512] if end else None
    if "atendente_id" in payload and payload["atendente_id"] is not None:
        alvo = _atendente_do_tenant(db, admin.tenant_id, int(payload["atendente_id"]))
        payload["atendente_id"] = alvo.id
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


def _data_mesma_md(ref: date, *, ano: int) -> date | None:
    """Projeta dia/mês de `ref` no `ano` (None se inválido, ex. 29/02 em ano não bissexto)."""
    try:
        return date(ano, ref.month, ref.day)
    except ValueError:
        return None


def feriado_custom_no_dia(db: Session, tenant_id: int, dia: date) -> PontoFeriado | None:
    """Feriado custom ativo no dia: data exata ou recorrente anual (mesmo dia/mês)."""
    exact = (
        db.query(PontoFeriado)
        .filter(
            PontoFeriado.tenant_id == tenant_id,
            PontoFeriado.data == dia,
            PontoFeriado.ativo.is_(True),
        )
        .first()
    )
    if exact:
        return exact
    candidatos = (
        db.query(PontoFeriado)
        .filter(
            PontoFeriado.tenant_id == tenant_id,
            PontoFeriado.ativo.is_(True),
            PontoFeriado.recorrente_anual.is_(True),
            PontoFeriado.data <= dia,
        )
        .all()
    )
    for row in candidatos:
        if row.data.month == dia.month and row.data.day == dia.day:
            return row
    return None


def eh_feriado(db: Session, tenant_id: int, dia: date) -> bool:
    """Feriado nacional (se ativo) ou custom da instância (inclui recorrente anual)."""
    settings = get_or_create_settings(db, tenant_id)
    if settings.usar_feriados_nacionais and is_feriado_nacional_br(dia):
        return True
    return feriado_custom_no_dia(db, tenant_id, dia) is not None


def listar_feriados(
    db: Session,
    tenant_id: int,
    *,
    ano: int | None = None,
) -> list[PontoFeriadoRead]:
    q = db.query(PontoFeriado).filter(PontoFeriado.tenant_id == tenant_id)
    rows = q.order_by(PontoFeriado.data.asc()).all()
    if ano is None:
        return [PontoFeriadoRead.model_validate(r) for r in rows]

    out: list[PontoFeriadoRead] = []
    md_vistos: set[tuple[int, int]] = set()
    # 1) Datas fixas do ano
    for r in rows:
        if r.data.year == ano:
            out.append(PontoFeriadoRead.model_validate(r))
            md_vistos.add((r.data.month, r.data.day))
    # 2) Recorrentes de outros anos (a partir do ano da data cadastrada)
    for r in rows:
        if not r.recorrente_anual or r.data.year > ano:
            continue
        if r.data.year == ano:
            continue  # já incluído
        proj = _data_mesma_md(r.data, ano=ano)
        if proj is None:
            continue
        key = (proj.month, proj.day)
        if key in md_vistos:
            continue
        md_vistos.add(key)
        out.append(
            PontoFeriadoRead(
                id=r.id,
                data=proj,
                nome=r.nome,
                ativo=r.ativo,
                recorrente_anual=True,
            )
        )
    out.sort(key=lambda x: x.data)
    return out


def _conflito_mes_dia(
    db: Session,
    tenant_id: int,
    *,
    data_ref: date,
    recorrente: bool,
) -> PontoFeriado | None:
    """Impede dois feriados no mesmo dia/mês quando um (ou o novo) é recorrente."""
    rows = (
        db.query(PontoFeriado)
        .filter(PontoFeriado.tenant_id == tenant_id)
        .all()
    )
    for r in rows:
        if r.data.month != data_ref.month or r.data.day != data_ref.day:
            continue
        if r.data == data_ref:
            return r
        if recorrente or r.recorrente_anual:
            return r
    return None


def criar_feriado(db: Session, admin: Atendente, data: PontoFeriadoCreate) -> PontoFeriadoRead:
    nome = (data.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome do feriado.")
    recorrente = bool(data.recorrente_anual) if data.recorrente_anual is not None else False
    conflito = _conflito_mes_dia(
        db, admin.tenant_id, data_ref=data.data, recorrente=recorrente
    )
    if conflito:
        if conflito.data == data.data:
            raise HTTPException(status_code=400, detail="Já existe feriado nesta data.")
        raise HTTPException(
            status_code=400,
            detail="Já existe feriado (recorrente ou nesta data) neste dia/mês.",
        )
    row = PontoFeriado(
        tenant_id=admin.tenant_id,
        data=data.data,
        nome=nome[:255],
        ativo=True if data.ativo is None else bool(data.ativo),
        recorrente_anual=recorrente,
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_feriado",
        row.id,
        "create",
        admin.id,
        payload={
            "data": data.data.isoformat(),
            "nome": nome,
            "recorrente_anual": recorrente,
        },
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
        payload={
            "data": row.data.isoformat(),
            "nome": row.nome,
            "recorrente_anual": bool(getattr(row, "recorrente_anual", False)),
        },
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
