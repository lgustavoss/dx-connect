"""API de contrato comercial (#324 / #349–#352)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, exigir_comercial_ou_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.comercial_contrato import (
    ContratoChaveCatalogoItem,
    ContratoGerarIn,
    ContratoMarcarAssinadoIn,
    ContratoMarcarEnviadoIn,
    ContratoPoliticaRead,
    ContratoPoliticaUpdate,
    ContratoRead,
    ContratoTemplateCreate,
    ContratoTemplatePreviewIn,
    ContratoTemplatePreviewOut,
    ContratoTemplateRead,
    ContratoTemplateUpdate,
)
from app.services import comercial_contrato as svc

router = APIRouter(prefix="/comercial", tags=["comercial-contratos"])


@router.get("/contrato-templates/chaves", response_model=list[ContratoChaveCatalogoItem])
def listar_chaves_template(
    _: Atendente = Depends(exigir_comercial_ou_admin),
):
    """Catálogo de placeholders {{chave}} para o modelo HTML do contrato."""
    return svc.catalogo_chaves_contrato()


@router.get("/contrato-templates", response_model=list[ContratoTemplateRead])
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


@router.post("/contrato-templates", response_model=ContratoTemplateRead, status_code=201)
def criar_template(
    data: ContratoTemplateCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.criar_template(db, data)
    registrar_audit(db, "comercial_contrato_template", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.post("/contrato-templates/preview", response_model=ContratoTemplatePreviewOut)
def preview_template(
    data: ContratoTemplatePreviewIn,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    return ContratoTemplatePreviewOut(html=svc.preencher_template_preview(db, data.conteudo_html))


@router.patch("/contrato-templates/{template_id}", response_model=ContratoTemplateRead)
def atualizar_template(
    template_id: int,
    data: ContratoTemplateUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.obter_template(db, template_id, apenas_ativos=False)
    row = svc.atualizar_template(db, row, data)
    registrar_audit(db, "comercial_contrato_template", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.get("/contrato-politica", response_model=ContratoPoliticaRead)
def obter_politica(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.garantir_politica(db)
    db.commit()
    return row


@router.patch("/contrato-politica", response_model=ContratoPoliticaRead)
def atualizar_politica(
    data: ContratoPoliticaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.atualizar_politica(db, data)
    registrar_audit(db, "comercial_contrato_politica", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.get("/contratos", response_model=list[ContratoRead])
def listar_contratos(
    negociacao_id: int | None = Query(None),
    status: str | None = Query(None),
    cnpj: str | None = Query(None),
    so_minhas: bool | None = Query(None),
    responsavel_id: int | None = Query(None),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    filtrar_minhas = so_minhas
    if atendente.role != "admin":
        filtrar_minhas = True
    elif filtrar_minhas is None:
        filtrar_minhas = False
    incluir_html = negociacao_id is not None
    return [
        svc.contrato_para_read(r, incluir_html=incluir_html)
        for r in svc.listar_contratos(
            db,
            negociacao_id=negociacao_id,
            status=status,
            cnpj=cnpj,
            responsavel_id=responsavel_id,
            so_minhas=bool(filtrar_minhas),
            atendente=atendente,
        )
    ]


@router.post("/contratos", response_model=ContratoRead, status_code=201)
def gerar_contrato(
    data: ContratoGerarIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.gerar_contrato(db, data, atendente)
    registrar_audit(
        db,
        "comercial_contrato",
        row.id,
        "create",
        atendente.id,
        payload={"linha_id": row.negociacao_linha_cnpj_id, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return svc.contrato_para_read(svc.obter_contrato(db, row.id, atendente=atendente), incluir_html=True)


@router.get("/contratos/{contrato_id}", response_model=ContratoRead)
def obter_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    return svc.contrato_para_read(svc.obter_contrato(db, contrato_id, atendente=atendente), incluir_html=True)


@router.get("/contratos/{contrato_id}/pdf")
def baixar_pdf(
    contrato_id: int,
    pdf_id: int | None = Query(None),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    pdf_row, pdf = svc.garantir_pdf(db, row, pdf_id=pdf_id)
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="contrato-{row.id}-{pdf_row.id}.pdf"'},
    )


@router.post("/contratos/{contrato_id}/pdf-assinado", response_model=ContratoRead)
def anexar_pdf_assinado(
    contrato_id: int,
    arquivo: UploadFile = File(...),
    referencia_externa: str | None = Form(None),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    conteudo = arquivo.file.read()
    row = svc.anexar_pdf_assinado(
        db,
        row,
        conteudo=conteudo,
        nome_original=arquivo.filename,
        content_type=arquivo.content_type,
        referencia_externa=referencia_externa,
        ator=atendente,
    )
    registrar_audit(
        db,
        "comercial_contrato",
        row.id,
        "update",
        atendente.id,
        payload={"pdf_assinado": True},
    )
    db.commit()
    return svc.contrato_para_read(svc.obter_contrato(db, row.id, atendente=atendente), incluir_html=True)


@router.get("/contratos/{contrato_id}/pdf-assinado")
def baixar_pdf_assinado(
    contrato_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    pdf, nome = svc.bytes_pdf_assinado(row)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.post("/contratos/{contrato_id}/marcar-enviado", response_model=ContratoRead)
def marcar_enviado(
    contrato_id: int,
    data: ContratoMarcarEnviadoIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    row = svc.marcar_enviado(db, row, data, atendente)
    registrar_audit(
        db,
        "comercial_contrato",
        row.id,
        "update",
        atendente.id,
        payload={"status": row.status},
    )
    db.commit()
    db.refresh(row)
    return svc.contrato_para_read(svc.obter_contrato(db, row.id, atendente=atendente), incluir_html=True)


@router.post("/contratos/{contrato_id}/marcar-assinado", response_model=ContratoRead)
def marcar_assinado(
    contrato_id: int,
    data: ContratoMarcarAssinadoIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    row = svc.marcar_assinado(db, row, data, atendente)
    registrar_audit(
        db,
        "comercial_contrato",
        row.id,
        "update",
        atendente.id,
        payload={"status": row.status, "avancar_funil": data.avancar_funil},
    )
    db.commit()
    db.refresh(row)
    return svc.contrato_para_read(svc.obter_contrato(db, row.id, atendente=atendente), incluir_html=True)


@router.post("/contratos/{contrato_id}/cancelar", response_model=ContratoRead)
def cancelar_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    era_assinado = row.status == "assinado"
    estimativa = svc.estimar_multa_rescisao(row) if era_assinado else None
    row = svc.cancelar_contrato(db, row, atendente)
    payload_multa = None
    if estimativa is not None:
        payload_multa = {
            **estimativa,
            "valor_mensalidade": str(estimativa["valor_mensalidade"]),
            "valor_estimado": (
                str(estimativa["valor_estimado"]) if estimativa["valor_estimado"] is not None else None
            ),
        }
    registrar_audit(
        db,
        "comercial_contrato",
        row.id,
        "update",
        atendente.id,
        payload={
            "status": row.status,
            "rescisao": era_assinado,
            "multa_rescisao": payload_multa,
        },
    )
    db.commit()
    db.refresh(row)
    return svc.contrato_para_read(svc.obter_contrato(db, row.id, atendente=atendente), incluir_html=True)
