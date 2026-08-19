"""API de proposta comercial (#323 / #345–#347)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, exigir_comercial_ou_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.comercial_proposta import (
    PropostaGerarIn,
    PropostaMarcarEnviadaIn,
    PropostaRead,
    PropostaTemplateCreate,
    PropostaTemplatePreviewIn,
    PropostaTemplatePreviewOut,
    PropostaTemplateRead,
    PropostaTemplateUpdate,
)
from app.services import comercial_proposta as svc

router = APIRouter(prefix="/comercial", tags=["comercial-propostas"])


@router.get("/proposta-templates", response_model=list[PropostaTemplateRead])
def listar_templates(
    incluir_inativos: bool = Query(False),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    if incluir_inativos and atendente.role != "admin":
        incluir_inativos = False
    svc.garantir_template_padrao(db)
    rows = svc.listar_templates(db, incluir_inativos=incluir_inativos)
    db.commit()
    return rows


@router.post("/proposta-templates", response_model=PropostaTemplateRead, status_code=201)
def criar_template(
    data: PropostaTemplateCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.criar_template(db, data)
    registrar_audit(db, "comercial_proposta_template", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.post("/proposta-templates/preview", response_model=PropostaTemplatePreviewOut)
def preview_template(
    data: PropostaTemplatePreviewIn,
    _: Atendente = Depends(exigir_admin),
):
    return PropostaTemplatePreviewOut(html=svc.sanitize_html(data.conteudo_html))


@router.patch("/proposta-templates/{template_id}", response_model=PropostaTemplateRead)
def atualizar_template(
    template_id: int,
    data: PropostaTemplateUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.obter_template(db, template_id, apenas_ativos=False)
    row = svc.atualizar_template(db, row, data)
    registrar_audit(db, "comercial_proposta_template", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.get("/propostas", response_model=list[PropostaRead])
def listar_propostas(
    negociacao_id: int = Query(...),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_comercial_ou_admin),
):
    return [svc.proposta_para_read(r) for r in svc.listar_propostas(db, negociacao_id)]


@router.post("/propostas", response_model=PropostaRead, status_code=201)
def gerar_proposta(
    data: PropostaGerarIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.gerar_proposta(db, data, atendente)
    registrar_audit(
        db,
        "comercial_proposta",
        row.id,
        "create",
        atendente.id,
        payload={"negociacao_id": row.negociacao_id, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return svc.proposta_para_read(row)


@router.get("/propostas/{proposta_id}", response_model=PropostaRead)
def obter_proposta(
    proposta_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_comercial_ou_admin),
):
    return svc.proposta_para_read(svc.obter_proposta(db, proposta_id))


@router.get("/propostas/{proposta_id}/pdf")
def baixar_pdf(
    proposta_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.obter_proposta(db, proposta_id)
    pdf = svc.garantir_pdf(db, row)
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="proposta-{row.id}.pdf"'},
    )


@router.post("/propostas/{proposta_id}/marcar-enviada", response_model=PropostaRead)
def marcar_enviada(
    proposta_id: int,
    data: PropostaMarcarEnviadaIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.obter_proposta(db, proposta_id)
    row = svc.marcar_enviada(db, row, data, atendente)
    registrar_audit(
        db,
        "comercial_proposta",
        row.id,
        "update",
        atendente.id,
        payload={"status": row.status, "canal": row.canal, "avancar_funil": data.avancar_funil},
    )
    db.commit()
    db.refresh(row)
    return svc.proposta_para_read(row)
