"""Hora extra WhatsApp após jornada (#965) + antecipada/teto (#966)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.audit import registrar_audit
from app.models.atendente import Atendente
from app.models.ponto_hora_extra import PontoHoraExtra
from app.schemas.ponto import PontoHoraExtraRead
from app.services import escala as escala_svc
from app.services.escala import PONTO_TZ

MODOS_APROVACAO = frozenset({"resto_do_dia", "ate_horario", "duracao"})


def _agora_tz(when: datetime | None = None) -> datetime:
    now = when or datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=PONTO_TZ)
    return now.astimezone(PONTO_TZ)


def fora_da_jornada(atendente: Atendente, when: datetime | None = None) -> bool:
    """True se a pessoa está fora do horário esperado (precisa HE para pegar WhatsApp)."""
    modo = escala_svc.modo_jornada(atendente)
    if modo == "nenhum" or not escala_svc.escala_configurada(atendente):
        return False
    agora = _agora_tz(when)
    dia = agora.date()
    if not escala_svc.eh_dia_de_trabalho(atendente, dia):
        return True
    saida = escala_svc.saida_prevista_em(atendente, dia)
    if saida is not None:
        return agora >= saida
    return not escala_svc.em_periodo_trabalho(atendente, agora)


def he_ativa(db: Session, atendente: Atendente, when: datetime | None = None) -> PontoHoraExtra | None:
    agora = _agora_tz(when)
    row = (
        db.query(PontoHoraExtra)
        .filter(
            PontoHoraExtra.atendente_id == atendente.id,
            PontoHoraExtra.estado == "aprovada",
        )
        .order_by(PontoHoraExtra.id.desc())
        .first()
    )
    if not row:
        return None
    if row.ate_em is None:
        return None
    ate = row.ate_em
    if ate.tzinfo is None:
        ate = ate.replace(tzinfo=timezone.utc)
    if agora.astimezone(timezone.utc) >= ate.astimezone(timezone.utc):
        row.estado = "expirada"
        db.flush()
        return None
    return row


def pode_pegar_whatsapp(db: Session, atendente: Atendente, when: datetime | None = None) -> bool:
    if not fora_da_jornada(atendente, when):
        return True
    return he_ativa(db, atendente, when) is not None


def exigir_pode_pegar_whatsapp(db: Session, atendente: Atendente) -> None:
    """Bloqueia assumir/iniciar WhatsApp fora da jornada sem HE (#965)."""
    if pode_pegar_whatsapp(db, atendente):
        return
    garantir_pedido_pendente(
        db,
        atendente,
        motivo="Tentativa de pegar chat WhatsApp após o fim da jornada.",
        commit=True,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Sua jornada já terminou. Peça hora extra a um administrador "
            "para pegar novos chats no WhatsApp."
        ),
    )


def _to_read(row: PontoHoraExtra) -> PontoHoraExtraRead:
    return PontoHoraExtraRead(
        id=row.id,
        atendente_id=row.atendente_id,
        atendente_nome=row.atendente.nome if row.atendente else None,
        estado=row.estado,
        motivo=row.motivo,
        modo=row.modo,
        ate_em=row.ate_em,
        origem=getattr(row, "origem", None) or "solicitacao",
        decidido_por_id=row.decidido_por_id,
        decidido_em=row.decidido_em,
        decisao_motivo=row.decisao_motivo,
        created_at=row.created_at,
    )


def _teto_minutos(atendente: Atendente) -> int | None:
    raw = getattr(atendente, "he_teto_minutos", None)
    if raw is None:
        return None
    v = int(raw)
    return v if v > 0 else None


def _aplicar_teto(atendente: Atendente, agora: datetime, ate: datetime) -> datetime:
    teto = _teto_minutos(atendente)
    if teto is None:
        return ate
    limite = agora + timedelta(minutes=teto)
    final = min(ate, limite)
    if final <= agora:
        raise HTTPException(
            status_code=400,
            detail=f"O teto de hora extra deste colaborador é de {teto} min — ajuste o horário ou o teto.",
        )
    return final


def _calcular_ate_em(
    atendente: Atendente,
    agora: datetime,
    *,
    modo: str,
    ate_horario: str | None,
    duracao_minutos: int | None,
) -> datetime:
    m = (modo or "").strip().lower()
    if m not in MODOS_APROVACAO:
        raise HTTPException(
            status_code=400,
            detail="Escolha modo resto_do_dia, ate_horario ou duracao.",
        )
    if m == "resto_do_dia":
        ate = _fim_resto_do_dia(agora)
    elif m == "ate_horario":
        ate = _parse_ate_horario(agora.date(), ate_horario or "")
        if ate <= agora:
            raise HTTPException(
                status_code=400,
                detail="O horário limite da hora extra deve ser no futuro.",
            )
    else:
        mins = int(duracao_minutos or 0)
        if mins < 15 or mins > 24 * 60:
            raise HTTPException(
                status_code=400,
                detail="Informe a duração em minutos (entre 15 e 1440).",
            )
        ate = agora + timedelta(minutes=mins)
    return _aplicar_teto(atendente, agora, ate).astimezone(timezone.utc)


def _expirar_aprovadas_anteriores(db: Session, atendente_id: int) -> None:
    agora_utc = datetime.now(timezone.utc)
    rows = (
        db.query(PontoHoraExtra)
        .filter(PontoHoraExtra.atendente_id == atendente_id, PontoHoraExtra.estado == "aprovada")
        .all()
    )
    for r in rows:
        r.estado = "expirada"
        if r.ate_em is None or (
            (r.ate_em if r.ate_em.tzinfo else r.ate_em.replace(tzinfo=timezone.utc)) > agora_utc
        ):
            r.ate_em = agora_utc


def garantir_pedido_pendente(
    db: Session,
    atendente: Atendente,
    *,
    motivo: str | None = None,
    commit: bool = True,
) -> PontoHoraExtra:
    existente = (
        db.query(PontoHoraExtra)
        .filter(
            PontoHoraExtra.atendente_id == atendente.id,
            PontoHoraExtra.estado == "pendente",
        )
        .order_by(PontoHoraExtra.id.desc())
        .first()
    )
    if existente:
        if motivo and not (existente.motivo or "").strip():
            existente.motivo = (motivo or "")[:1000]
        if commit:
            db.commit()
            db.refresh(existente)
        return existente
    row = PontoHoraExtra(
        tenant_id=atendente.tenant_id,
        atendente_id=atendente.id,
        estado="pendente",
        origem="solicitacao",
        motivo=(motivo or "Pedido de hora extra para atendimento WhatsApp.")[:1000],
    )
    db.add(row)
    db.flush()
    registrar_audit(
        db,
        "ponto_hora_extra",
        row.id,
        "create",
        atendente.id,
        payload={"estado": "pendente", "origem": "solicitacao"},
    )
    if commit:
        db.commit()
        db.refresh(row)
        _notificar_admins(db, atendente.tenant_id)
    return row


def solicitar(
    db: Session,
    atendente: Atendente,
    *,
    motivo: str | None = None,
) -> PontoHoraExtraRead:
    if not fora_da_jornada(atendente):
        raise HTTPException(
            status_code=400,
            detail="Você ainda está dentro da jornada — não é necessário pedir hora extra.",
        )
    if he_ativa(db, atendente):
        raise HTTPException(status_code=400, detail="Você já tem hora extra ativa.")
    row = garantir_pedido_pendente(db, atendente, motivo=motivo, commit=True)
    row = (
        db.query(PontoHoraExtra)
        .options(joinedload(PontoHoraExtra.atendente))
        .filter(PontoHoraExtra.id == row.id)
        .first()
    )
    assert row is not None
    return _to_read(row)


def listar_admin(
    db: Session,
    admin: Atendente,
    *,
    estado: str | None = "pendente",
) -> list[PontoHoraExtraRead]:
    q = (
        db.query(PontoHoraExtra)
        .options(joinedload(PontoHoraExtra.atendente))
        .filter(PontoHoraExtra.tenant_id == admin.tenant_id)
    )
    if estado:
        q = q.filter(PontoHoraExtra.estado == estado)
    rows = q.order_by(PontoHoraExtra.created_at.desc(), PontoHoraExtra.id.desc()).limit(100).all()
    return [_to_read(r) for r in rows]


def listar_me(db: Session, atendente: Atendente) -> list[PontoHoraExtraRead]:
    rows = (
        db.query(PontoHoraExtra)
        .options(joinedload(PontoHoraExtra.atendente))
        .filter(PontoHoraExtra.atendente_id == atendente.id)
        .order_by(PontoHoraExtra.id.desc())
        .limit(30)
        .all()
    )
    return [_to_read(r) for r in rows]


def me_status(db: Session, atendente: Atendente) -> dict:
    fora = fora_da_jornada(atendente)
    ativa = he_ativa(db, atendente)
    pendente = (
        db.query(PontoHoraExtra)
        .filter(PontoHoraExtra.atendente_id == atendente.id, PontoHoraExtra.estado == "pendente")
        .order_by(PontoHoraExtra.id.desc())
        .first()
    )
    restante = None
    if ativa and ativa.ate_em is not None:
        agora = _agora_tz()
        ate = ativa.ate_em
        if ate.tzinfo is None:
            ate = ate.replace(tzinfo=timezone.utc)
        restante = max(0, int((ate.astimezone(PONTO_TZ) - agora).total_seconds() // 60))
    return {
        "fora_da_jornada": fora,
        "pode_pegar_whatsapp": (not fora) or ativa is not None,
        "he_ativa": _to_read(ativa) if ativa else None,
        "pedido_pendente": _to_read(pendente) if pendente else None,
        "he_teto_minutos": _teto_minutos(atendente),
        "he_restante_minutos": restante,
    }


def _fim_resto_do_dia(agora: datetime) -> datetime:
    dia = agora.astimezone(PONTO_TZ).date()
    return datetime.combine(dia, time(23, 59, 59), tzinfo=PONTO_TZ)


def _parse_ate_horario(dia: date, hhmm: str) -> datetime:
    parts = (hhmm or "").strip().split(":")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Informe o horário no formato HH:MM.")
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Horário inválido.") from e
    if h < 0 or h > 23 or m < 0 or m > 59:
        raise HTTPException(status_code=400, detail="Horário inválido.")
    return datetime.combine(dia, time(hour=h, minute=m), tzinfo=PONTO_TZ)


def decidir(
    db: Session,
    admin: Atendente,
    he_id: int,
    *,
    aprovar: bool,
    modo: str | None = None,
    ate_horario: str | None = None,
    duracao_minutos: int | None = None,
    decisao_motivo: str | None = None,
) -> PontoHoraExtraRead:
    row = (
        db.query(PontoHoraExtra)
        .options(joinedload(PontoHoraExtra.atendente))
        .filter(PontoHoraExtra.id == he_id, PontoHoraExtra.tenant_id == admin.tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Pedido de hora extra não encontrado")
    if row.estado != "pendente":
        raise HTTPException(status_code=400, detail="Este pedido já foi decidido.")
    agora = _agora_tz()
    alvo = row.atendente
    assert alvo is not None
    row.decidido_por_id = admin.id
    row.decidido_em = datetime.now(timezone.utc)
    row.decisao_motivo = (decisao_motivo or "").strip()[:1000] or None
    if not aprovar:
        row.estado = "rejeitada"
        row.modo = None
        row.ate_em = None
    else:
        m = (modo or "").strip().lower()
        ate = _calcular_ate_em(
            alvo, agora, modo=m, ate_horario=ate_horario, duracao_minutos=duracao_minutos
        )
        _expirar_aprovadas_anteriores(db, alvo.id)
        row.estado = "aprovada"
        row.modo = m
        row.ate_em = ate
    registrar_audit(
        db,
        "ponto_hora_extra",
        row.id,
        "decidir",
        admin.id,
        payload={"estado": row.estado, "modo": row.modo, "ate_em": str(row.ate_em)},
    )
    db.commit()
    db.refresh(row)
    _notificar_admins(db, admin.tenant_id)
    return _to_read(row)


def conceder_admin(
    db: Session,
    admin: Atendente,
    *,
    atendente_id: int,
    modo: str,
    ate_horario: str | None = None,
    duracao_minutos: int | None = None,
    motivo: str | None = None,
) -> PontoHoraExtraRead:
    """Admin concede HE antecipada (#966) — sem pedido pendente."""
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
    agora = _agora_tz()
    m = (modo or "").strip().lower()
    ate = _calcular_ate_em(
        alvo, agora, modo=m, ate_horario=ate_horario, duracao_minutos=duracao_minutos
    )
    _expirar_aprovadas_anteriores(db, alvo.id)

    pendentes = (
        db.query(PontoHoraExtra)
        .filter(PontoHoraExtra.atendente_id == alvo.id, PontoHoraExtra.estado == "pendente")
        .order_by(PontoHoraExtra.id.asc())
        .all()
    )
    row: PontoHoraExtra
    if pendentes:
        row = pendentes[0]
        for extra in pendentes[1:]:
            extra.estado = "rejeitada"
            extra.decidido_por_id = admin.id
            extra.decidido_em = datetime.now(timezone.utc)
            extra.decisao_motivo = "Substituído por concessão do administrador"
        row.estado = "aprovada"
        row.origem = "admin"
        row.modo = m
        row.ate_em = ate
        row.motivo = (motivo or row.motivo or "Hora extra concedida pelo administrador.")[:1000]
        row.decidido_por_id = admin.id
        row.decidido_em = datetime.now(timezone.utc)
        row.decisao_motivo = "Concessão antecipada"
        registrar_audit(
            db,
            "ponto_hora_extra",
            row.id,
            "conceder",
            admin.id,
            payload={"atendente_id": alvo.id, "modo": m, "ate_em": str(ate), "via": "pendente"},
        )
    else:
        row = PontoHoraExtra(
            tenant_id=admin.tenant_id,
            atendente_id=alvo.id,
            estado="aprovada",
            origem="admin",
            modo=m,
            ate_em=ate,
            motivo=(motivo or "Hora extra concedida pelo administrador.")[:1000],
            decidido_por_id=admin.id,
            decidido_em=datetime.now(timezone.utc),
            decisao_motivo="Concessão antecipada",
        )
        db.add(row)
        db.flush()
        registrar_audit(
            db,
            "ponto_hora_extra",
            row.id,
            "conceder",
            admin.id,
            payload={"atendente_id": alvo.id, "modo": m, "ate_em": str(ate)},
        )

    db.commit()
    row = (
        db.query(PontoHoraExtra)
        .options(joinedload(PontoHoraExtra.atendente))
        .filter(PontoHoraExtra.id == row.id)
        .first()
    )
    assert row is not None
    _notificar_admins(db, admin.tenant_id)
    return _to_read(row)


def contar_pendentes_admin(db: Session, tenant_id: int) -> int:
    return (
        db.query(PontoHoraExtra)
        .filter(PontoHoraExtra.tenant_id == tenant_id, PontoHoraExtra.estado == "pendente")
        .count()
    )


def _notificar_admins(db: Session, tenant_id: int) -> None:
    try:
        from app.services.realtime_emit import emit_notificacao_contagem

        ids = [
            a.id
            for a in db.query(Atendente)
            .filter(
                Atendente.tenant_id == tenant_id,
                Atendente.role == "admin",
                Atendente.ativo.is_(True),
            )
            .all()
        ]
        if ids:
            emit_notificacao_contagem(db, ids)
    except Exception:
        pass
