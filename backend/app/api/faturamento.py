"""Faturamento — faturas internas e aprovação (#326)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_financeiro_ou_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.faturamento import (
    ContratoElegivelRead,
    FaturaGerarCompetenciaIn,
    FaturaGerarCompetenciaOut,
    FaturaGerarIn,
    FaturaRead,
    FaturaRejeitarIn,
)
from app.services import faturamento as svc

router = APIRouter(prefix="/faturamento", tags=["faturamento"])


@router.get("/faturas", response_model=list[FaturaRead])
def listar_faturas(
    competencia: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_financeiro_ou_admin),
):
    rows = svc.listar_faturas(db, competencia=competencia, status_filtro=status)
    return [svc.fatura_para_read(db, r) for r in rows]


@router.get("/contratos-elegiveis", response_model=list[ContratoElegivelRead])
def listar_contratos_elegiveis(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_financeiro_ou_admin),
):
    return svc.listar_contratos_elegiveis(db)


@router.post("/faturas", response_model=FaturaRead)
def gerar_fatura(
    data: FaturaGerarIn,
    response: Response,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_financeiro_ou_admin),
):
    row, created = svc.gerar_fatura_contrato(db, data.contrato_id, data.competencia)
    registrar_audit(
        db,
        "faturamento_fatura",
        row.id,
        "create" if created else "update",
        atendente.id,
        payload={"contrato_id": row.contrato_id, "competencia": row.competencia},
    )
    db.commit()
    response.status_code = 201 if created else 200
    return svc.fatura_para_read(db, svc.obter_fatura(db, row.id))


@router.post("/faturas/gerar-competencia", response_model=FaturaGerarCompetenciaOut)
def gerar_competencia(
    data: FaturaGerarCompetenciaIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_financeiro_ou_admin),
):
    competencia, criadas, existentes, reabertas, audit_id = svc.gerar_competencia(
        db, data.competencia, reabrir_rejeitadas=True
    )
    if audit_id is not None:
        registrar_audit(
            db,
            "faturamento_fatura",
            audit_id,
            "create" if criadas else "update",
            atendente.id,
            payload={"competencia": competencia, "criadas": criadas, "reabertas": reabertas},
        )
    db.commit()
    return {
        "competencia": competencia,
        "criadas": criadas,
        "existentes": existentes,
        "reabertas": reabertas,
    }


@router.post("/faturas/{fatura_id}/aprovar", response_model=FaturaRead)
def aprovar_fatura(
    fatura_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_financeiro_ou_admin),
):
    row = svc.obter_fatura(db, fatura_id)
    row = svc.aprovar_fatura(db, row, atendente)
    registrar_audit(db, "faturamento_fatura", row.id, "update", atendente.id, payload={"status": row.status})
    db.commit()
    return svc.fatura_para_read(db, svc.obter_fatura(db, row.id))


@router.post("/faturas/{fatura_id}/rejeitar", response_model=FaturaRead)
def rejeitar_fatura(
    fatura_id: int,
    data: FaturaRejeitarIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_financeiro_ou_admin),
):
    row = svc.obter_fatura(db, fatura_id)
    row = svc.rejeitar_fatura(db, row, data.motivo)
    registrar_audit(
        db,
        "faturamento_fatura",
        row.id,
        "update",
        atendente.id,
        payload={"status": row.status},
    )
    db.commit()
    return svc.fatura_para_read(db, svc.obter_fatura(db, row.id))
