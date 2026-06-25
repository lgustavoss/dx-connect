import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin
from app.core.ticket_prioridade import PrioridadeTicket
from app.database import get_db
from app.models.atendente import Atendente
from app.models.business_calendar import BusinessCalendar
from app.models.setor import Setor
from app.models.sla_policy import SlaPolicy
from app.models.ticket_classificacao import TicketNatureza
from app.schemas.sla import (
    BusinessCalendarCreate,
    BusinessCalendarRead,
    BusinessCalendarUpdate,
    SlaPolicyCreate,
    SlaPolicyRead,
    SlaPolicyUpdate,
    SlaPrioridadesDisponiveis,
)
from app.services.sla_policy import validar_metas_sla

router = APIRouter(prefix="/sla", tags=["sla"])


def _validar_setor(db: Session, tenant_id: int, setor_id: int) -> Setor:
    setor = db.query(Setor).filter(Setor.id == setor_id, Setor.tenant_id == tenant_id).first()
    if not setor:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setor não encontrado")
    return setor


def _validar_calendario(db: Session, tenant_id: int, calendar_id: int | None, *, exigir_ativo: bool = False) -> None:
    if calendar_id is None:
        return
    cal = (
        db.query(BusinessCalendar)
        .filter(BusinessCalendar.id == calendar_id, BusinessCalendar.tenant_id == tenant_id)
        .first()
    )
    if not cal:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Calendário comercial não encontrado")
    if exigir_ativo and not cal.ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calendário inativo não pode ser vinculado à política SLA.",
        )


def _prioridade_db(prioridade: PrioridadeTicket | None) -> str | None:
    if prioridade is None:
        return None
    return prioridade.value


def _validar_natureza(db: Session, tenant_id: int, natureza_id: int | None) -> None:
    if natureza_id is None:
        return
    row = (
        db.query(TicketNatureza)
        .filter(TicketNatureza.id == natureza_id, TicketNatureza.ativo.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Natureza inválida ou inativa")


def _assert_policy_unica(
    db: Session,
    *,
    tenant_id: int,
    setor_id: int,
    prioridade: PrioridadeTicket | None,
    natureza_id: int | None = None,
    exclude_id: int | None = None,
) -> None:
    q = db.query(SlaPolicy).filter(SlaPolicy.tenant_id == tenant_id, SlaPolicy.setor_id == setor_id)
    prio_db = _prioridade_db(prioridade)
    if prio_db is None:
        q = q.filter(SlaPolicy.prioridade.is_(None))
    else:
        q = q.filter(SlaPolicy.prioridade == prio_db)
    if natureza_id is None:
        q = q.filter(SlaPolicy.natureza_id.is_(None))
    else:
        q = q.filter(SlaPolicy.natureza_id == natureza_id)
    if exclude_id is not None:
        q = q.filter(SlaPolicy.id != exclude_id)
    if q.first():
        prio_label = prio_db or "padrão"
        nat_label = f"natureza #{natureza_id}" if natureza_id else "qualquer natureza"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Já existe política SLA para este setor (prioridade {prio_label}, {nat_label}).",
        )


def _policy_para_read(db: Session, policy: SlaPolicy) -> SlaPolicyRead:
    setor = db.query(Setor).filter(Setor.id == policy.setor_id).first()
    cal_nome = None
    if policy.business_calendar_id:
        cal = db.query(BusinessCalendar).filter(BusinessCalendar.id == policy.business_calendar_id).first()
        cal_nome = cal.nome if cal else None
    nat_nome = None
    if policy.natureza_id:
        nat = db.query(TicketNatureza).filter(TicketNatureza.id == policy.natureza_id).first()
        nat_nome = nat.nome if nat else None
    return SlaPolicyRead.from_row(
        policy,
        setor_nome=setor.nome if setor else None,
        calendar_nome=cal_nome,
        natureza_nome=nat_nome,
    )


def _calendar_para_read(row: BusinessCalendar) -> BusinessCalendarRead:
    return BusinessCalendarRead.from_row(row)


def _horario_semana_json(horario_semana: dict | None) -> str | None:
    if horario_semana is None:
        return None
    return json.dumps(horario_semana, ensure_ascii=False)


# --- Calendários comerciais (opcional #277) ---


@router.get("/calendars", response_model=list[BusinessCalendarRead])
def listar_calendarios(
    setor_id: int | None = Query(None),
    incluir_inativos: bool = Query(False),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    q = db.query(BusinessCalendar).filter(BusinessCalendar.tenant_id == atendente.tenant_id)
    if setor_id is not None:
        q = q.filter(BusinessCalendar.setor_id == setor_id)
    if not incluir_inativos:
        q = q.filter(BusinessCalendar.ativo.is_(True))
    rows = q.order_by(BusinessCalendar.nome.asc(), BusinessCalendar.id.asc()).all()
    return [_calendar_para_read(r) for r in rows]


@router.post("/calendars", response_model=BusinessCalendarRead, status_code=201)
def criar_calendario(
    data: BusinessCalendarCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    if data.setor_id is not None:
        _validar_setor(db, atendente.tenant_id, data.setor_id)
    row = BusinessCalendar(
        tenant_id=atendente.tenant_id,
        setor_id=data.setor_id,
        nome=data.nome.strip(),
        horario_timezone=data.horario_timezone.strip() or "America/Sao_Paulo",
        horario_inicio=data.horario_inicio,
        horario_fim=data.horario_fim,
        horario_semana_json=_horario_semana_json(data.horario_semana),
        usar_feriados_nacionais=data.usar_feriados_nacionais,
        ativo=data.ativo,
    )
    db.add(row)
    db.flush()
    registrar_audit(db, "business_calendar", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return _calendar_para_read(row)


@router.get("/calendars/{calendar_id}", response_model=BusinessCalendarRead)
def obter_calendario(
    calendar_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = (
        db.query(BusinessCalendar)
        .filter(BusinessCalendar.id == calendar_id, BusinessCalendar.tenant_id == atendente.tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendário não encontrado")
    return _calendar_para_read(row)


@router.put("/calendars/{calendar_id}", response_model=BusinessCalendarRead)
def atualizar_calendario(
    calendar_id: int,
    data: BusinessCalendarUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = (
        db.query(BusinessCalendar)
        .filter(BusinessCalendar.id == calendar_id, BusinessCalendar.tenant_id == atendente.tenant_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendário não encontrado")

    payload = data.model_dump(exclude_unset=True)
    if "nome" in payload and payload["nome"] is not None:
        row.nome = payload["nome"].strip()
    if "setor_id" in payload:
        if payload["setor_id"] is not None:
            _validar_setor(db, atendente.tenant_id, payload["setor_id"])
        row.setor_id = payload["setor_id"]
    if "horario_timezone" in payload and payload["horario_timezone"] is not None:
        row.horario_timezone = payload["horario_timezone"].strip() or "America/Sao_Paulo"
    if "horario_inicio" in payload:
        row.horario_inicio = payload["horario_inicio"]
    if "horario_fim" in payload:
        row.horario_fim = payload["horario_fim"]
    if "horario_semana" in payload:
        row.horario_semana_json = _horario_semana_json(payload["horario_semana"])
    if "usar_feriados_nacionais" in payload and payload["usar_feriados_nacionais"] is not None:
        row.usar_feriados_nacionais = payload["usar_feriados_nacionais"]
    if "ativo" in payload and payload["ativo"] is not None:
        row.ativo = payload["ativo"]

    registrar_audit(db, "business_calendar", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return _calendar_para_read(row)


# --- Políticas SLA ---


@router.get("/prioridades", response_model=SlaPrioridadesDisponiveis)
def listar_prioridades_sla(_: Atendente = Depends(exigir_admin)):
    return SlaPrioridadesDisponiveis()


@router.get("/policies", response_model=list[SlaPolicyRead])
def listar_policies(
    setor_id: int | None = Query(None),
    incluir_inativos: bool = Query(False),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    q = db.query(SlaPolicy).filter(SlaPolicy.tenant_id == atendente.tenant_id)
    if setor_id is not None:
        q = q.filter(SlaPolicy.setor_id == setor_id)
    if not incluir_inativos:
        q = q.filter(SlaPolicy.ativo.is_(True))
    rows = q.order_by(
        SlaPolicy.setor_id.asc(),
        SlaPolicy.prioridade.asc().nullsfirst(),
        SlaPolicy.natureza_id.asc().nullsfirst(),
        SlaPolicy.id.asc(),
    ).all()
    return [_policy_para_read(db, r) for r in rows]


@router.post("/policies", response_model=SlaPolicyRead, status_code=201)
def criar_policy(
    data: SlaPolicyCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    try:
        validar_metas_sla(
            meta_primeira_resposta_min=data.meta_primeira_resposta_min,
            meta_resolucao_min=data.meta_resolucao_min,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    _validar_setor(db, atendente.tenant_id, data.setor_id)
    _validar_calendario(db, atendente.tenant_id, data.business_calendar_id, exigir_ativo=True)
    _validar_natureza(db, atendente.tenant_id, data.natureza_id)
    _assert_policy_unica(
        db,
        tenant_id=atendente.tenant_id,
        setor_id=data.setor_id,
        prioridade=data.prioridade,
        natureza_id=data.natureza_id,
    )

    policy = SlaPolicy(
        tenant_id=atendente.tenant_id,
        setor_id=data.setor_id,
        prioridade=_prioridade_db(data.prioridade),
        natureza_id=data.natureza_id,
        business_calendar_id=data.business_calendar_id,
        meta_primeira_resposta_min=data.meta_primeira_resposta_min,
        meta_resolucao_min=data.meta_resolucao_min,
        ativo=data.ativo,
    )
    db.add(policy)
    db.flush()
    registrar_audit(db, "sla_policy", policy.id, "create", atendente.id)
    db.commit()
    db.refresh(policy)
    return _policy_para_read(db, policy)


@router.get("/policies/{policy_id}", response_model=SlaPolicyRead)
def obter_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    policy = (
        db.query(SlaPolicy)
        .filter(SlaPolicy.id == policy_id, SlaPolicy.tenant_id == atendente.tenant_id)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Política SLA não encontrada")
    return _policy_para_read(db, policy)


@router.put("/policies/{policy_id}", response_model=SlaPolicyRead)
def atualizar_policy(
    policy_id: int,
    data: SlaPolicyUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    policy = (
        db.query(SlaPolicy)
        .filter(SlaPolicy.id == policy_id, SlaPolicy.tenant_id == atendente.tenant_id)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Política SLA não encontrada")

    payload = data.model_dump(exclude_unset=True)
    if "setor_id" in payload and payload["setor_id"] is not None:
        _validar_setor(db, atendente.tenant_id, payload["setor_id"])
        policy.setor_id = payload["setor_id"]
    if "prioridade" in payload:
        policy.prioridade = _prioridade_db(payload["prioridade"])
    if "natureza_id" in payload:
        _validar_natureza(db, atendente.tenant_id, payload["natureza_id"])
        policy.natureza_id = payload["natureza_id"]
    if "business_calendar_id" in payload:
        _validar_calendario(db, atendente.tenant_id, payload["business_calendar_id"], exigir_ativo=True)
        policy.business_calendar_id = payload["business_calendar_id"]
    if "meta_primeira_resposta_min" in payload:
        policy.meta_primeira_resposta_min = payload["meta_primeira_resposta_min"]
    if "meta_resolucao_min" in payload:
        policy.meta_resolucao_min = payload["meta_resolucao_min"]
    if "ativo" in payload and payload["ativo"] is not None:
        policy.ativo = payload["ativo"]

    try:
        validar_metas_sla(
            meta_primeira_resposta_min=policy.meta_primeira_resposta_min,
            meta_resolucao_min=policy.meta_resolucao_min,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    _assert_policy_unica(
        db,
        tenant_id=atendente.tenant_id,
        setor_id=policy.setor_id,
        prioridade=PrioridadeTicket(policy.prioridade) if policy.prioridade else None,
        natureza_id=policy.natureza_id,
        exclude_id=policy.id,
    )

    registrar_audit(db, "sla_policy", policy.id, "update", atendente.id)
    db.commit()
    db.refresh(policy)
    return _policy_para_read(db, policy)
