"""Contrato comercial: templates, snapshot por CNPJ e PDF (#324 / #349–#352)."""

from __future__ import annotations

import calendar
import hashlib
import html
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.models.comercial_contrato import (
    CONTRATO_ASSINADO,
    CONTRATO_CANCELADO,
    CONTRATO_ENVIADO,
    CONTRATO_RASCUNHO,
    CONTRATO_STATUS_ATIVOS,
    FIDELIDADE_MESES_PADRAO,
    MULTA_MAX_MENSALIDADES_PADRAO,
    Contrato,
    ContratoPdf,
    ContratoTemplate,
)
from app.models.crm import ATIVIDADE_DOCUMENTO, CrmNegociacao, CrmNegociacaoAtividade, CrmNegociacaoCnpjLinha
from app.schemas.comercial_contrato import (
    ContratoGerarIn,
    ContratoMarcarAssinadoIn,
    ContratoMarcarEnviadoIn,
    ContratoTemplateCreate,
    ContratoTemplateUpdate,
)
from app.services import comercial_proposta as proposta_svc
from app.services import crm as crm_svc
from app.services.ticket_anexo_storage import caminho_absoluto_arquivo, gravar_bytes_em_disco

TEMPLATE_PADRAO_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <style>
    body { font-family: DejaVu Sans, Arial, sans-serif; color: #1e293b; margin: 24px; font-size: 13px; }
    h1 { font-size: 20px; margin: 0 0 8px; }
    h2 { font-size: 14px; margin: 20px 0 8px; }
    table { width: 100%; border-collapse: collapse; margin: 8px 0 16px; }
    th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: left; }
    th { background: #f1f5f9; }
    .muted { color: #64748b; font-size: 12px; }
    .logo img { max-height: 72px; }
  </style>
</head>
<body>
  <div class="logo">{{logo}}</div>
  <p class="muted">{{empresa_sistema}}</p>
  <h1>Contrato de prestação de serviços</h1>
  <p><strong>Contratante:</strong> {{razao_social}} &nbsp; <strong>CNPJ:</strong> {{cnpj}}</p>
  <h2>Objeto e valores</h2>
  {{itens}}
  <p><strong>Mensalidade:</strong> {{valor_mensalidade}}</p>
  {{setup_bloco}}
  <h2>Vigência e fidelidade</h2>
  <p>Início: {{data_inicio}} &nbsp; Fim da fidelidade: {{data_fim_fidelidade}} ({{fidelidade_meses}} meses).</p>
  <div>{{fidelidade}}</div>
  <div>{{multa}}</div>
  <div>{{igpm}}</div>
  <h2>Implantação</h2>
  {{clausula_deslocamento}}
  {{clausula_alimentacao}}
  {{clausula_hospedagem}}
</body>
</html>
"""


def sanitize_html(fragment: str) -> str:
    return proposta_svc.sanitize_html(fragment)


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _hash_html(conteudo: str) -> str:
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def garantir_template_padrao(db: Session) -> ContratoTemplate:
    row = (
        db.query(ContratoTemplate)
        .filter(ContratoTemplate.ativo.is_(True))
        .order_by(ContratoTemplate.id.asc())
        .first()
    )
    if row:
        return row
    row = ContratoTemplate(
        nome="Padrão",
        versao=1,
        conteudo_html=TEMPLATE_PADRAO_HTML,
        vigencia_inicio=datetime.now(timezone.utc),
        ativo=True,
    )
    db.add(row)
    db.flush()
    return row


def listar_templates(db: Session, *, incluir_inativos: bool = False) -> list[ContratoTemplate]:
    garantir_template_padrao(db)
    q = db.query(ContratoTemplate)
    if not incluir_inativos:
        q = q.filter(ContratoTemplate.ativo.is_(True))
    return q.order_by(ContratoTemplate.nome.asc(), ContratoTemplate.versao.desc()).all()


def obter_template(db: Session, template_id: int, *, apenas_ativos: bool = False) -> ContratoTemplate:
    q = db.query(ContratoTemplate).filter(ContratoTemplate.id == template_id)
    if apenas_ativos:
        q = q.filter(ContratoTemplate.ativo.is_(True))
    row = q.first()
    if not row:
        raise HTTPException(status_code=404, detail="Modelo de contrato não encontrado.")
    return row


def _proxima_versao(db: Session, nome: str) -> int:
    atual = db.query(func.max(ContratoTemplate.versao)).filter(ContratoTemplate.nome == nome).scalar()
    return int(atual or 0) + 1


def criar_template(db: Session, data: ContratoTemplateCreate) -> ContratoTemplate:
    nome = data.nome.strip()
    row = ContratoTemplate(
        nome=nome,
        versao=_proxima_versao(db, nome),
        conteudo_html=sanitize_html(data.conteudo_html),
        vigencia_inicio=data.vigencia_inicio or datetime.now(timezone.utc),
        ativo=data.ativo,
    )
    db.add(row)
    db.flush()
    return row


def atualizar_template(db: Session, row: ContratoTemplate, data: ContratoTemplateUpdate) -> ContratoTemplate:
    payload = data.model_dump(exclude_unset=True)
    html_mudou = False
    if "conteudo_html" in payload and payload["conteudo_html"] is not None:
        novo_html = sanitize_html(payload["conteudo_html"])
        html_mudou = novo_html != (row.conteudo_html or "")
        row.conteudo_html = novo_html
    if "nome" in payload and payload["nome"] is not None:
        row.nome = payload["nome"].strip()
    if html_mudou:
        row.versao = _proxima_versao(db, row.nome)
    if "vigencia_inicio" in payload:
        row.vigencia_inicio = payload["vigencia_inicio"]
    if "ativo" in payload and payload["ativo"] is not None:
        row.ativo = payload["ativo"]
    db.flush()
    return row


def obter_linha(db: Session, linha_id: int) -> CrmNegociacaoCnpjLinha:
    row = db.query(CrmNegociacaoCnpjLinha).filter(CrmNegociacaoCnpjLinha.id == linha_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Linha CNPJ da negociação não encontrada.")
    return row


def _contrato_ativo_da_linha(db: Session, linha_id: int) -> Contrato | None:
    return (
        db.query(Contrato)
        .options(joinedload(Contrato.template), joinedload(Contrato.pdfs), joinedload(Contrato.linha))
        .filter(
            Contrato.negociacao_linha_cnpj_id == linha_id,
            Contrato.status.in_(tuple(CONTRATO_STATUS_ATIVOS)),
        )
        .order_by(Contrato.id.desc())
        .first()
    )


def _opts_contrato():
    return (
        joinedload(Contrato.template),
        joinedload(Contrato.pdfs),
        joinedload(Contrato.linha)
        .joinedload(CrmNegociacaoCnpjLinha.negociacao)
        .joinedload(CrmNegociacao.responsavel),
        joinedload(Contrato.linha)
        .joinedload(CrmNegociacaoCnpjLinha.negociacao)
        .joinedload(CrmNegociacao.lead),
    )


def obter_contrato(db: Session, contrato_id: int) -> Contrato:
    row = (
        db.query(Contrato)
        .options(*_opts_contrato())
        .filter(Contrato.id == contrato_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    return row


def listar_contratos(
    db: Session,
    *,
    negociacao_id: int | None = None,
    status: str | None = None,
    cnpj: str | None = None,
    responsavel_id: int | None = None,
    so_minhas: bool = False,
    atendente: Atendente | None = None,
) -> list[Contrato]:
    if negociacao_id is not None:
        crm_svc.obter_negociacao(db, negociacao_id)
    q = (
        db.query(Contrato)
        .options(*_opts_contrato())
        .join(CrmNegociacaoCnpjLinha, Contrato.negociacao_linha_cnpj_id == CrmNegociacaoCnpjLinha.id)
        .join(CrmNegociacao, CrmNegociacaoCnpjLinha.negociacao_id == CrmNegociacao.id)
    )
    if negociacao_id is not None:
        q = q.filter(CrmNegociacaoCnpjLinha.negociacao_id == negociacao_id)
    if status:
        q = q.filter(Contrato.status == status.strip())
    if cnpj and cnpj.strip():
        term = f"%{cnpj.strip()}%"
        q = q.filter(
            (CrmNegociacaoCnpjLinha.cnpj.ilike(term)) | (CrmNegociacaoCnpjLinha.razao_social.ilike(term))
        )
    if so_minhas and atendente is not None:
        q = q.filter(CrmNegociacao.responsavel_id == atendente.id)
    elif responsavel_id is not None:
        q = q.filter(CrmNegociacao.responsavel_id == responsavel_id)
    return q.order_by(Contrato.created_at.desc()).all()


def _p(texto: str) -> str:
    return f"<p>{texto}</p>"


def _setup_bloco(*, setup_isento: bool, setup_valor: Decimal | None) -> str:
    if setup_isento:
        return _p("Setup de implantação: <strong>isento</strong> (não há cobrança avulsa de implantação).")
    if setup_valor is not None:
        return _p(
            "Setup de implantação (cobrança única, <strong>fora</strong> da mensalidade): "
            + html.escape(proposta_svc._money_br(setup_valor))
        )
    return _p("Setup de implantação: conforme negociação (fora da mensalidade).")


def _clausula_custo_cliente(ativo: bool, titulo: str) -> str:
    if not ativo:
        return ""
    return _p(html.escape(f"{titulo} por conta do contratante."))


def preencher_template(db: Session, template_html: str, contrato: Contrato, linha: CrmNegociacaoCnpjLinha) -> str:
    nomes = proposta_svc._nomes_itens_cliente(db, linha)
    itens_txt = html.escape(", ".join(nomes) if nomes else "—")
    tabela = (
        "<table><thead><tr><th>Razão social</th><th>CNPJ</th><th>Itens</th><th>Mensalidade</th></tr></thead>"
        "<tbody><tr>"
        f"<td>{html.escape(linha.razao_social or '—')}</td>"
        f"<td>{html.escape(proposta_svc._formatar_cnpj(linha.cnpj))}</td>"
        f"<td>{itens_txt}</td>"
        f"<td>{html.escape(proposta_svc._money_br(contrato.valor_mensalidade))}</td>"
        "</tr></tbody></table>"
    )
    fid = int(contrato.fidelidade_meses or FIDELIDADE_MESES_PADRAO)
    multa_n = int(contrato.multa_max_mensalidades or MULTA_MAX_MENSALIDADES_PADRAO)
    valores = {
        "logo": proposta_svc._logo_html(db),
        "empresa_sistema": proposta_svc._empresa_sistema_texto(db),
        "razao_social": html.escape(linha.razao_social or "—"),
        "cnpj": html.escape(proposta_svc._formatar_cnpj(linha.cnpj)),
        "itens": tabela,
        "valor_mensalidade": html.escape(proposta_svc._money_br(contrato.valor_mensalidade)),
        "data_inicio": html.escape(contrato.data_inicio.strftime("%d/%m/%Y")),
        "data_fim_fidelidade": html.escape(contrato.data_fim_fidelidade.strftime("%d/%m/%Y")),
        "fidelidade_meses": html.escape(str(fid)),
        "setup_bloco": _setup_bloco(setup_isento=bool(contrato.setup_isento), setup_valor=contrato.setup_valor),
        "fidelidade": _p(
            html.escape(
                f"O contratante permanece vinculado por {fid} meses de fidelidade, "
                "contados da data de início."
            )
        ),
        "multa": _p(
            html.escape(
                f"Em caso de rescisão antecipada, a multa é de até {multa_n} mensalidade(s), "
                "a validar juridicamente."
            )
        ),
        "igpm": _p(
            "Após o período de fidelidade, a renovação é automática, sem nova fidelidade, "
            "com reajuste pelo IGPM acumulado em 12 meses."
        ),
        "clausula_deslocamento": _clausula_custo_cliente(bool(contrato.deslocamento_cliente), "Deslocamento"),
        "clausula_alimentacao": _clausula_custo_cliente(bool(contrato.alimentacao_cliente), "Alimentação"),
        "clausula_hospedagem": _clausula_custo_cliente(bool(contrato.hospedagem_cliente), "Hospedagem"),
    }
    html_out = sanitize_html(template_html)
    for chave, valor in valores.items():
        html_out = html_out.replace("{{" + chave + "}}", valor)
    if proposta_svc._VAZAMENTO.search(html_out):
        raise HTTPException(
            status_code=500,
            detail="O contrato gerado continha dados internos e foi bloqueado. Contacte o suporte.",
        )
    return html_out


def _montar_snapshots(db: Session, linha: CrmNegociacaoCnpjLinha, data: ContratoGerarIn) -> dict[str, Any]:
    nomes = proposta_svc._nomes_itens_cliente(db, linha)
    snap_custo = linha.snapshot_custo if isinstance(linha.snapshot_custo, dict) else None
    return {
        "valor_mensalidade": Decimal(str(linha.valor_negociado or 0)),
        "snapshot_custo": snap_custo,
        "snapshot_itens": [{"nome": n} for n in nomes],
        "snapshot_comercial": {
            "valor_mensalidade": str(Decimal(str(linha.valor_negociado or 0))),
            "setup_valor": str(data.setup_valor) if data.setup_valor is not None else None,
            "setup_isento": data.setup_isento,
            "fidelidade_meses": data.fidelidade_meses,
            "multa_max_mensalidades": data.multa_max_mensalidades,
            "deslocamento_cliente": data.deslocamento_cliente,
            "alimentacao_cliente": data.alimentacao_cliente,
            "hospedagem_cliente": data.hospedagem_cliente,
        },
    }


def _aplicar_campos_geracao(row: Contrato, data: ContratoGerarIn, snaps: dict[str, Any], tmpl: ContratoTemplate) -> None:
    inicio = data.data_inicio or date.today()
    meses = int(data.fidelidade_meses or FIDELIDADE_MESES_PADRAO)
    row.template_id = tmpl.id
    row.valor_mensalidade = snaps["valor_mensalidade"]
    row.snapshot_custo = snaps["snapshot_custo"]
    row.snapshot_itens = snaps["snapshot_itens"]
    snap_com = dict(snaps["snapshot_comercial"] or {})
    snap_com["template_id"] = tmpl.id
    snap_com["template_versao"] = tmpl.versao
    row.snapshot_comercial = snap_com
    row.data_inicio = inicio
    row.data_fim_fidelidade = _add_months(inicio, meses)
    row.fidelidade_meses = meses
    row.setup_valor = data.setup_valor
    row.setup_isento = data.setup_isento
    row.deslocamento_cliente = data.deslocamento_cliente
    row.alimentacao_cliente = data.alimentacao_cliente
    row.hospedagem_cliente = data.hospedagem_cliente
    row.multa_max_mensalidades = data.multa_max_mensalidades


def _gravar_pdf_versao(db: Session, contrato: Contrato, html_doc: str, ator: Atendente) -> ContratoPdf:
    pdf_row = ContratoPdf(
        contrato_id=contrato.id,
        gerado_por_id=ator.id,
        conteudo_html_snapshot=html_doc,
        conteudo_hash=_hash_html(html_doc),
    )
    db.add(pdf_row)
    db.flush()
    return pdf_row


def gerar_contrato(db: Session, data: ContratoGerarIn, ator: Atendente) -> Contrato:
    linha = obter_linha(db, data.linha_id)
    if not (linha.razao_social or "").strip() or not (linha.cnpj or "").strip():
        raise HTTPException(status_code=400, detail="A linha precisa de razão social e CNPJ para gerar o contrato.")
    if data.template_id:
        tmpl = obter_template(db, data.template_id, apenas_ativos=True)
    else:
        tmpl = garantir_template_padrao(db)

    existente = _contrato_ativo_da_linha(db, linha.id)
    if existente and existente.status == CONTRATO_ASSINADO:
        raise HTTPException(
            status_code=400,
            detail="Contrato já assinado: o snapshot não é editável (aditivo fica para uma issue futura).",
        )
    if existente and existente.status == CONTRATO_ENVIADO:
        raise HTTPException(
            status_code=400,
            detail="Contrato já enviado. Não é possível regenerar; cancele ou marque como assinado.",
        )

    snaps = _montar_snapshots(db, linha, data)
    if existente:
        row = existente
        _aplicar_campos_geracao(row, data, snaps, tmpl)
        texto_ativ = f"Contrato #{row.id} regenerado (rascunho)."
    else:
        row = Contrato(
            negociacao_linha_cnpj_id=linha.id,
            empresa_id=linha.empresa_id,
            gerado_por_id=ator.id,
            status=CONTRATO_RASCUNHO,
        )
        _aplicar_campos_geracao(row, data, snaps, tmpl)
        db.add(row)
        db.flush()
        texto_ativ = f"Contrato #{row.id} gerado (rascunho)."

    snapshot_html = preencher_template(db, tmpl.conteudo_html, row, linha)
    _gravar_pdf_versao(db, row, snapshot_html, ator)
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=linha.negociacao_id,
            autor_id=ator.id,
            tipo=ATIVIDADE_DOCUMENTO,
            texto=texto_ativ,
        )
    )
    db.flush()
    return obter_contrato(db, row.id)


def _pdf_mais_recente(row: Contrato) -> ContratoPdf | None:
    pdfs = list(row.pdfs or [])
    if not pdfs:
        return None
    return max(pdfs, key=lambda p: p.id)


def garantir_pdf(db: Session, row: Contrato, *, pdf_id: int | None = None) -> tuple[ContratoPdf, bytes]:
    if pdf_id is not None:
        pdf_row = next((p for p in (row.pdfs or []) if p.id == pdf_id), None)
        if not pdf_row:
            raise HTTPException(status_code=404, detail="Versão de PDF não encontrada.")
    else:
        pdf_row = _pdf_mais_recente(row)
        if not pdf_row:
            raise HTTPException(status_code=400, detail="Este contrato ainda não tem PDF gerado.")
    if pdf_row.pdf_storage_key:
        path = caminho_absoluto_arquivo(pdf_row.pdf_storage_key)
        if path:
            return pdf_row, path.read_bytes()
    pdf = proposta_svc.html_para_pdf(pdf_row.conteudo_html_snapshot)
    try:
        key = gravar_bytes_em_disco(pdf, mimetype="application/pdf", nome_original=f"contrato-{row.id}-{pdf_row.id}.pdf")
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Não foi possível guardar o PDF.") from exc
    pdf_row.pdf_storage_key = key
    db.flush()
    return pdf_row, pdf


def marcar_enviado(db: Session, row: Contrato, data: ContratoMarcarEnviadoIn, ator: Atendente) -> Contrato:
    if row.status != CONTRATO_RASCUNHO:
        raise HTTPException(status_code=400, detail="Só o rascunho pode ser marcado como enviado.")
    row.status = CONTRATO_ENVIADO
    row.enviado_em = data.enviado_em or datetime.now(timezone.utc)
    linha = row.linha or obter_linha(db, row.negociacao_linha_cnpj_id)
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=linha.negociacao_id,
            autor_id=ator.id,
            tipo=ATIVIDADE_DOCUMENTO,
            texto=f"Contrato #{row.id} marcado como enviado.",
        )
    )
    db.flush()
    return row


def marcar_assinado(db: Session, row: Contrato, data: ContratoMarcarAssinadoIn, ator: Atendente) -> Contrato:
    if row.status not in {CONTRATO_RASCUNHO, CONTRATO_ENVIADO}:
        raise HTTPException(status_code=400, detail="Só rascunho ou enviado podem ser marcados como assinados.")
    row.status = CONTRATO_ASSINADO
    row.assinado_em = data.assinado_em or datetime.now(timezone.utc)
    linha = row.linha or obter_linha(db, row.negociacao_linha_cnpj_id)
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=linha.negociacao_id,
            autor_id=ator.id,
            tipo=ATIVIDADE_DOCUMENTO,
            texto=f"Contrato #{row.id} marcado como assinado (registro manual).",
        )
    )
    if data.avancar_funil:
        neg = crm_svc.obter_negociacao(db, linha.negociacao_id)
        atual = crm_svc.obter_estagio(db, estagio_id=neg.estagio_id)
        if atual.slug != "contrato_assinado":
            crm_svc.mover_estagio(
                db,
                neg,
                ator=ator,
                estagio_slug="contrato_assinado",
                nota="Contrato assinado (registro manual).",
            )
    db.flush()
    return row


def cancelar_contrato(db: Session, row: Contrato, ator: Atendente) -> Contrato:
    if row.status in {CONTRATO_CANCELADO, CONTRATO_ASSINADO}:
        raise HTTPException(
            status_code=400,
            detail="Contrato assinado ou já cancelado não pode ser cancelado nesta tela.",
        )
    row.status = CONTRATO_CANCELADO
    linha = row.linha or obter_linha(db, row.negociacao_linha_cnpj_id)
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=linha.negociacao_id,
            autor_id=ator.id,
            tipo=ATIVIDADE_DOCUMENTO,
            texto=f"Contrato #{row.id} cancelado.",
        )
    )
    db.flush()
    return row


def _interno_read(row: Contrato, linha: CrmNegociacaoCnpjLinha | None) -> dict[str, Any] | None:
    if linha is None:
        return None
    valor = Decimal(str(row.valor_mensalidade or 0))
    custo = Decimal(str(linha.total_custo)) if linha.total_custo is not None else None
    lucro = None
    margem_pct = None
    if custo is not None:
        lucro = (valor - custo).quantize(Decimal("0.01"))
        if valor != 0:
            margem_pct = ((lucro / valor) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "total_custo": linha.total_custo,
        "margem_calculada": linha.margem_calculada,
        "margem_percentual": margem_pct,
        "lucro_bruto": lucro,
    }


def contrato_para_read(row: Contrato, *, incluir_html: bool = False) -> dict[str, Any]:
    tmpl = row.template
    linha = row.linha
    neg = linha.negociacao if linha else None
    pdfs = sorted(row.pdfs or [], key=lambda p: p.id)
    atual = pdfs[-1] if pdfs else None
    dias: int | None = None
    if row.data_fim_fidelidade:
        dias = (row.data_fim_fidelidade - date.today()).days
    snap_com = row.snapshot_comercial if isinstance(row.snapshot_comercial, dict) else {}
    versao_snapshot = snap_com.get("template_versao")
    try:
        template_versao = int(versao_snapshot) if versao_snapshot is not None else (tmpl.versao if tmpl else None)
    except (TypeError, ValueError):
        template_versao = tmpl.versao if tmpl else None
    return {
        "id": row.id,
        "negociacao_linha_cnpj_id": row.negociacao_linha_cnpj_id,
        "negociacao_id": linha.negociacao_id if linha else None,
        "empresa_id": row.empresa_id,
        "template_id": row.template_id,
        "template_nome": tmpl.nome if tmpl else None,
        "template_versao": template_versao,
        "gerado_por_id": row.gerado_por_id,
        "status": row.status,
        "valor_mensalidade": row.valor_mensalidade,
        "snapshot_itens": list(row.snapshot_itens or []),
        "data_inicio": row.data_inicio,
        "data_fim_fidelidade": row.data_fim_fidelidade,
        "fidelidade_meses": row.fidelidade_meses,
        "setup_valor": row.setup_valor,
        "setup_isento": row.setup_isento,
        "deslocamento_cliente": row.deslocamento_cliente,
        "alimentacao_cliente": row.alimentacao_cliente,
        "hospedagem_cliente": row.hospedagem_cliente,
        "multa_max_mensalidades": row.multa_max_mensalidades,
        "enviado_em": row.enviado_em,
        "assinado_em": row.assinado_em,
        "created_at": row.created_at,
        "pdf_atual_id": atual.id if atual else None,
        "pdfs": [
            {
                "id": p.id,
                "contrato_id": p.contrato_id,
                "gerado_por_id": p.gerado_por_id,
                "conteudo_hash": p.conteudo_hash,
                "created_at": p.created_at,
            }
            for p in pdfs
        ],
        "cnpj": linha.cnpj if linha else None,
        "razao_social": linha.razao_social if linha else None,
        "responsavel_id": neg.responsavel_id if neg else None,
        "responsavel_nome": neg.responsavel.nome if neg and neg.responsavel else None,
        "lead_nome": neg.lead.nome if neg and neg.lead else None,
        "conteudo_html_snapshot": atual.conteudo_html_snapshot if incluir_html and atual else None,
        "dias_restantes_fidelidade": dias,
        "interno": _interno_read(row, linha),
    }
