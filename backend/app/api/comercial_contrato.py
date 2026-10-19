"""API de contrato comercial (#324 / #349–#352)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_permissao
from app.services.permissao_grupos import tem_permissao
from app.database import get_db
from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.schemas.crm import DadosFiscaisLinha
from app.schemas.empresa import EmpresaRead
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
    _: Atendente = Depends(exigir_permissao("contratos.ver")),
):
    """Catálogo de placeholders {{chave}} para o modelo HTML do contrato."""
    return svc.catalogo_chaves_contrato()


@router.get("/contrato-templates", response_model=list[ContratoTemplateRead])
def listar_templates(
    incluir_inativos: bool = Query(False),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.ver")),
):
    if incluir_inativos and not tem_permissao(atendente, "contratos.modelos"):
        incluir_inativos = False
    svc.garantir_template_padrao(db)
    rows = svc.listar_templates(db, incluir_inativos=incluir_inativos)
    db.commit()
    return rows


@router.post("/contrato-templates", response_model=ContratoTemplateRead, status_code=201)
def criar_template(
    data: ContratoTemplateCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.modelos")),
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
    _: Atendente = Depends(exigir_permissao("contratos.modelos")),
):
    return ContratoTemplatePreviewOut(html=svc.preencher_template_preview(db, data.conteudo_html))


@router.patch("/contrato-templates/{template_id}", response_model=ContratoTemplateRead)
def atualizar_template(
    template_id: int,
    data: ContratoTemplateUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.modelos")),
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
    _: Atendente = Depends(exigir_permissao("contratos.ver")),
):
    row = svc.garantir_politica(db)
    db.commit()
    return row


@router.patch("/contrato-politica", response_model=ContratoPoliticaRead)
def atualizar_politica(
    data: ContratoPoliticaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.politica")),
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
    atendente: Atendente = Depends(exigir_permissao("contratos.ver")),
):
    ve_todos = tem_permissao(atendente, "contratos.ver_todos")
    if responsavel_id is not None and not ve_todos:
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para ver contratos de outra pessoa.",
        )
    filtrar_minhas = so_minhas
    if not ve_todos:
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


@router.get("/contratos/linhas/{linha_id}/empresa", response_model=EmpresaRead)
def obter_empresa_da_linha(
    linha_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.emitir")),
):
    linha = svc.obter_linha(db, linha_id)
    svc._assert_acesso_negociacao(linha.negociacao, atendente)
    if not linha.empresa_id:
        raise HTTPException(status_code=404, detail="Esta linha ainda não tem empresa cadastrada.")
    emp = db.query(Empresa).filter(Empresa.id == linha.empresa_id).first()
    if emp is None:
        raise HTTPException(status_code=404, detail="Esta linha ainda não tem empresa cadastrada.")
    return emp


@router.put("/contratos/linhas/{linha_id}/empresa", response_model=EmpresaRead)
def salvar_empresa_da_linha(
    linha_id: int,
    data: DadosFiscaisLinha,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.emitir")),
):
    linha = svc.obter_linha(db, linha_id)
    ja_tinha = linha.empresa_id is not None
    emp = svc.cadastrar_empresa_da_linha(db, linha, data, atendente)
    registrar_audit(
        db,
        "empresa",
        emp.id,
        "update" if ja_tinha else "create",
        atendente.id,
        payload={"linha_id": linha.id, "origem": "contrato"},
    )
    negociacao_id = linha.negociacao_id
    db.commit()
    db.refresh(emp)
    from app.services.whatsapp_chat_negociacao import emitir_fila_dos_chats

    emitir_fila_dos_chats(db, negociacao_id)
    return emp


@router.post("/contratos", response_model=ContratoRead, status_code=201)
def gerar_contrato(
    data: ContratoGerarIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.emitir")),
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
    atendente: Atendente = Depends(exigir_permissao("contratos.ver")),
):
    return svc.contrato_para_read(svc.obter_contrato(db, contrato_id, atendente=atendente), incluir_html=True)


@router.get("/contratos/{contrato_id}/pdf")
def baixar_pdf(
    contrato_id: int,
    pdf_id: int | None = Query(None),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.ver")),
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
    atendente: Atendente = Depends(exigir_permissao("contratos.emitir")),
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
    atendente: Atendente = Depends(exigir_permissao("contratos.ver")),
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
    atendente: Atendente = Depends(exigir_permissao("contratos.emitir")),
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
    atendente: Atendente = Depends(exigir_permissao("contratos.emitir")),
):
    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    row = svc.marcar_assinado(db, row, data, atendente)
    registrar_audit(
        db,
        "comercial_contrato",
        row.id,
        "update",
        atendente.id,
        payload={
            "status": row.status,
            "avancar_funil": data.avancar_funil,
            "abrir_ticket_implantacao": data.abrir_ticket_implantacao,
        },
    )
    from app.services.implantacao import ticket_por_contrato
    from app.services.ticket_distribuicao import pos_criar_ticket_na_fila

    ticket_impl = ticket_por_contrato(db, row.id)
    if ticket_impl:
        registrar_audit(
            db,
            "ticket",
            ticket_impl.id,
            "create",
            atendente.id,
            payload={"origem": "implantacao_contrato", "contrato_id": row.id},
        )
    negociacao_id = svc.obter_linha(db, row.negociacao_linha_cnpj_id).negociacao_id
    db.commit()
    db.refresh(row)
    from app.services.whatsapp_chat_negociacao import emitir_fila_dos_chats

    emitir_fila_dos_chats(db, negociacao_id)
    if ticket_impl:
        from app.models.ticket import Ticket

        ticket_impl = db.query(Ticket).filter(Ticket.id == ticket_impl.id).first()
        if ticket_impl:
            pos_criar_ticket_na_fila(db, ticket_impl)
    return svc.contrato_para_read(svc.obter_contrato(db, row.id, atendente=atendente), incluir_html=True)


@router.post("/contratos/{contrato_id}/cancelar", response_model=ContratoRead)
def cancelar_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.cancelar")),
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
