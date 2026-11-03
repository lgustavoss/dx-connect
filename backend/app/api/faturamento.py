"""Faturamento — faturas internas, aprovação e documentos manuais (#326)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_faturamento
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.faturamento import (
    ContratoElegivelRead,
    FaturaDocumentosIn,
    FaturaGerarCompetenciaIn,
    FaturaGerarCompetenciaOut,
    FaturaGerarIn,
    FaturaRead,
    FaturaRejeitarIn,
    TituloBaixaIn,
    TituloReceberRead,
)
from app.services import faturamento as svc
from app.services import faturamento_anexo_storage as anexo_storage

router = APIRouter(prefix="/faturamento", tags=["faturamento"])


@router.get("/faturas", response_model=list[FaturaRead])
def listar_faturas(
    competencia: str | None = Query(None),
    status: str | None = Query(None),
    emite_nfse: bool | None = Query(None),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_faturamento("faturamento.ver")),
):
    rows = svc.listar_faturas(db, competencia=competencia, status_filtro=status, emite_nfse=emite_nfse)
    return [svc.fatura_para_read(db, r) for r in rows]


@router.get("/faturas/{fatura_id}", response_model=FaturaRead)
def obter_fatura(
    fatura_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_faturamento("faturamento.ver")),
):
    row = svc.obter_fatura(db, fatura_id)
    return svc.fatura_para_read(db, row)


@router.get("/contratos-elegiveis", response_model=list[ContratoElegivelRead])
def listar_contratos_elegiveis(
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_faturamento("faturamento.ver")),
):
    return svc.listar_contratos_elegiveis(db)


@router.post("/faturas", response_model=FaturaRead)
def gerar_fatura(
    data: FaturaGerarIn,
    response: Response,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_faturamento("faturamento.gerar")),
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
    atendente: Atendente = Depends(exigir_faturamento("faturamento.gerar")),
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
    atendente: Atendente = Depends(exigir_faturamento("faturamento.aprovar")),
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
    atendente: Atendente = Depends(exigir_faturamento("faturamento.aprovar")),
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


@router.patch("/faturas/{fatura_id}/documentos", response_model=FaturaRead)
def atualizar_documentos(
    fatura_id: int,
    data: FaturaDocumentosIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_faturamento("faturamento.gerar")),
):
    row = svc.obter_fatura(db, fatura_id)
    row = svc.atualizar_documentos(
        db,
        row,
        boleto_linha_digitavel=data.boleto_linha_digitavel,
        boleto_nosso_numero=data.boleto_nosso_numero,
        nfse_numero=data.nfse_numero,
    )
    registrar_audit(
        db,
        "faturamento_fatura",
        row.id,
        "update",
        atendente.id,
        payload={"documentos": True},
    )
    db.commit()
    return svc.fatura_para_read(db, svc.obter_fatura(db, row.id))


@router.post("/faturas/{fatura_id}/anexos", response_model=FaturaRead, status_code=201)
def enviar_anexo(
    fatura_id: int,
    file: UploadFile = File(...),
    tipo: str = Form(...),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_faturamento("faturamento.gerar")),
):
    row = svc.obter_fatura(db, fatura_id)
    data = file.file.read()
    svc.gravar_anexo(
        db,
        row,
        tipo=tipo,
        data=data,
        nome_original=file.filename,
        content_type=file.content_type,
        ator=atendente,
    )
    registrar_audit(
        db,
        "faturamento_fatura",
        row.id,
        "update",
        atendente.id,
        payload={"anexo_tipo": tipo},
    )
    db.commit()
    return svc.fatura_para_read(db, svc.obter_fatura(db, row.id))


@router.get("/faturas/{fatura_id}/anexos/{anexo_id}/download")
def baixar_anexo(
    fatura_id: int,
    anexo_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_faturamento("faturamento.ver")),
):
    row = svc.obter_fatura(db, fatura_id)
    anexo = svc.obter_anexo(db, row, anexo_id)
    p = anexo_storage.caminho_absoluto_arquivo(anexo.storage_key)
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado no armazenamento. Envie o documento de novo.",
        )
    return FileResponse(
        path=str(p),
        filename=anexo.nome_original,
        media_type="application/octet-stream",
    )


@router.get("/titulos", response_model=list[TituloReceberRead])
def listar_titulos(
    competencia: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_faturamento("faturamento.ver")),
):
    rows = svc.listar_titulos(db, competencia=competencia, status_filtro=status)
    return [svc.titulo_para_read(db, r) for r in rows]


@router.post("/titulos/{titulo_id}/baixar", response_model=TituloReceberRead)
def baixar_titulo(
    titulo_id: int,
    data: TituloBaixaIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_faturamento("faturamento.aprovar")),
):
    row = svc.obter_titulo(db, titulo_id)
    row = svc.baixar_titulo(
        db,
        row,
        atendente,
        pago_em=data.pago_em,
        valor_pago=data.valor_pago,
        observacao=data.observacao,
    )
    registrar_audit(
        db,
        "faturamento_titulo",
        row.id,
        "update",
        atendente.id,
        payload={"status": row.status, "valor_pago": str(row.valor_pago)},
    )
    db.commit()
    return svc.titulo_para_read(db, svc.obter_titulo(db, row.id))


@router.delete("/faturas/{fatura_id}/anexos/{anexo_id}", response_model=FaturaRead)
def excluir_anexo(
    fatura_id: int,
    anexo_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_faturamento("faturamento.gerar")),
):
    row = svc.obter_fatura(db, fatura_id)
    svc.remover_anexo(db, row, anexo_id)
    registrar_audit(
        db,
        "faturamento_fatura",
        row.id,
        "update",
        atendente.id,
        payload={"anexo_id": anexo_id, "removido": True},
    )
    db.commit()
    return svc.fatura_para_read(db, svc.obter_fatura(db, row.id))
