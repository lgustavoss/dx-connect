"""API de contrato comercial (#324 / #349–#352)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_permissao, obter_atendente_atual
from app.services.permissao_grupos import tem_permissao
from app.database import get_db
from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.schemas.crm import DadosFiscaisLinha
from app.schemas.empresa import EmpresaRead
from app.schemas.comercial_contrato import (
    ContratoChaveCatalogoItem,
    ContratoCobrancaUpdate,
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
from app.schemas.contrato_assinatura import ContratoAssinaturaEnviarIn, ContratoAssinaturaRead
from app.services import comercial_contrato as svc

router = APIRouter(prefix="/comercial", tags=["comercial-contratos"])


def exigir_cobranca_contrato(
    atendente: Atendente = Depends(obter_atendente_atual),
    db: Session = Depends(get_db),
) -> Atendente:
    """Cobrança do contrato (#1340): quem emite contrato ou quem gera fatura, e o Financeiro."""
    from app.core.setor_scope import atendente_e_financeiro

    if tem_permissao(atendente, "contratos.emitir") or tem_permissao(atendente, "faturamento.gerar"):
        return atendente
    if atendente_e_financeiro(db, atendente):
        return atendente
    raise HTTPException(status_code=403, detail="Sem permissão para editar a cobrança do contrato.")


def _contrato_para_cobranca(db: Session, contrato_id: int, atendente: Atendente):
    """Financeiro/gerador de fatura enxerga qualquer contrato; comercial só o próprio (#1340)."""
    from app.core.setor_scope import atendente_e_financeiro

    if atendente_e_financeiro(db, atendente) or tem_permissao(atendente, "faturamento.gerar"):
        return svc.obter_contrato(db, contrato_id)
    return svc.obter_contrato(db, contrato_id, atendente=atendente)


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
    rows = svc.listar_contratos(
        db,
        negociacao_id=negociacao_id,
        status=status,
        cnpj=cnpj,
        responsavel_id=responsavel_id,
        so_minhas=bool(filtrar_minhas),
        atendente=atendente,
    )
    # Multa de rescisão resolvida em lote: a listagem não faz uma query por contrato (#1386).
    from app.services import faturamento as faturamento_svc

    titulos_multa = faturamento_svc.titulos_multa_por_contrato(db, [r.id for r in rows])
    payloads = [
        svc.contrato_para_read(
            r,
            incluir_html=incluir_html,
            titulo_multa=titulos_multa.get(r.id),
            consultar_titulo_multa=False,
        )
        for r in rows
    ]
    svc.marcar_vigentes(db, payloads)
    return payloads


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
    payload = svc.contrato_para_read(
        svc.obter_contrato(db, contrato_id, atendente=atendente), incluir_html=True
    )
    svc.marcar_vigentes(db, [payload])
    return payload


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


@router.patch("/contratos/{contrato_id}/cobranca", response_model=ContratoRead)
def atualizar_cobranca_contrato(
    contrato_id: int,
    data: ContratoCobrancaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_cobranca_contrato),
):
    """Primeira venda no PDV e overrides de cobrança da negociação (#1340)."""
    row = _contrato_para_cobranca(db, contrato_id, atendente)
    row = svc.atualizar_cobranca(db, row, data, atendente)
    alterados = {
        k: (v.isoformat() if hasattr(v, "isoformat") else v)
        for k, v in data.model_dump(exclude_unset=True).items()
    }
    registrar_audit(
        db,
        "comercial_contrato",
        row.id,
        "update",
        atendente.id,
        payload={"cobranca": alterados},
    )
    db.commit()
    db.refresh(row)
    return svc.contrato_para_read(_contrato_para_cobranca(db, row.id, atendente), incluir_html=True)


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
            "cobranca_cancelada": getattr(row, "pendencias_cobranca_canceladas", None),
        },
    )
    db.commit()
    db.refresh(row)
    return svc.contrato_para_read(svc.obter_contrato(db, row.id, atendente=atendente), incluir_html=True)


@router.post("/contratos/{contrato_id}/assinatura/enviar", response_model=ContratoAssinaturaRead)
def enviar_assinatura(
    contrato_id: int,
    data: ContratoAssinaturaEnviarIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.emitir")),
):
    """Fluxo A (#1380 / #1429): envelope DocuSeal multiparte."""
    from app.models.contrato_assinatura import STATUS_ERRO
    from app.services import contrato_assinatura as assinatura_svc

    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    env = assinatura_svc.enviar_para_assinatura(db, row, data, atendente)
    env_id = env.id
    db.commit()
    env = assinatura_svc.obter_assinatura(db, env_id)
    if env.status == STATUS_ERRO:
        raise HTTPException(
            status_code=502,
            detail=env.ultimo_erro or "Falha ao criar envelope no DocuSeal.",
        )
    return assinatura_svc.to_read(env)


@router.post("/contratos/{contrato_id}/assinatura/cancelar", response_model=ContratoAssinaturaRead)
def cancelar_assinatura(
    contrato_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.emitir")),
):
    from app.services import contrato_assinatura as assinatura_svc

    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    env = assinatura_svc.cancelar_envelope(db, row, atendente)
    db.commit()
    db.refresh(env)
    return assinatura_svc.to_read(env)


@router.get("/contratos/{contrato_id}/assinatura", response_model=ContratoAssinaturaRead)
def obter_assinatura_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.ver")),
):
    from app.services import contrato_assinatura as assinatura_svc

    svc.obter_contrato(db, contrato_id, atendente=atendente)
    assinatura_svc.sincronizar_expiracao(db, contrato_id)
    env = assinatura_svc.envelope_ativo(db, contrato_id) or assinatura_svc.ultima_assinatura(db, contrato_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Nenhuma assinatura registrada neste contrato.")
    return assinatura_svc.to_read(env)


@router.post("/contratos/{contrato_id}/assinatura/partes/{parte_id}/enviar-email")
def enviar_email_convite_assinatura(
    contrato_id: int,
    parte_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.emitir")),
):
    """Envia o link de assinatura da parte por e-mail (modelo A / mercado)."""
    from app.services import contrato_assinatura as assinatura_svc

    row = svc.obter_contrato(db, contrato_id, atendente=atendente)
    parte = assinatura_svc.obter_parte(db, contrato_id, parte_id)
    assinatura_svc.enviar_convite_email_parte(db, row, parte, atendente)
    db.commit()
    return {"ok": True, "parte_id": parte_id, "email": parte.email}


@router.get("/contratos/{contrato_id}/assinatura/evidencias/{tipo}")
def baixar_evidencia_assinatura(
    contrato_id: int,
    tipo: str,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("contratos.ver")),
):
    """Download auditado de PDF assinado / trilha / selfie (#1380)."""
    from app.services import contrato_assinatura as assinatura_svc

    svc.obter_contrato(db, contrato_id, atendente=atendente)
    env = assinatura_svc.ultima_assinatura(db, contrato_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Nenhuma assinatura registrada neste contrato.")
    if env.provedor == "externo" and tipo in {"audit", "selfie"}:
        raise HTTPException(
            status_code=404,
            detail="Assinatura externa não tem trilha de auditoria nem selfie no DeskRudder.",
        )
    conteudo, nome, media = assinatura_svc.bytes_evidencia(env, tipo)
    registrar_audit(
        db,
        "contrato_assinatura",
        env.id,
        "download",
        atendente.id,
        payload={"tipo": tipo, "contrato_id": contrato_id},
    )
    db.commit()
    return Response(
        content=conteudo,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
