"""Proposta comercial: templates, montagem sem custo/margem e PDF (#323 / #345–#347)."""

from __future__ import annotations

import hashlib
import html
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.models.comercial_custo import CustoCatalogoItem
from app.models.comercial_proposta import (
    PROPOSTA_ENVIADA,
    PROPOSTA_RASCUNHO,
    PROPOSTA_SUBSTITUIDA,
    Proposta,
    PropostaTemplate,
)
from app.models.crm import ATIVIDADE_DOCUMENTO, CrmNegociacaoAtividade, CrmNegociacaoCnpjLinha
from app.models.empresa_sistema import EmpresaSistema
from app.schemas.comercial_proposta import (
    PropostaGerarIn,
    PropostaMarcarEnviadaIn,
    PropostaTemplateCreate,
    PropostaTemplateUpdate,
)
from app.services import crm as crm_svc
from app.services.system_logo_storage import caminho_absoluto_logo
from app.services.ticket_anexo_storage import caminho_absoluto_arquivo, gravar_bytes_em_disco

logger = logging.getLogger(__name__)

_TAGS_PERIGOSAS = re.compile(
    r"</?(?:script|iframe|object|embed|link|meta|form)(?:\s[^>]*)?>",
    re.IGNORECASE,
)
_ATTR_EVENTO = re.compile(r"\s+on\w+\s*=\s*(['\"]).*?\1", re.IGNORECASE | re.DOTALL)
_ATTR_JS = re.compile(r"\s+(href|src)\s*=\s*(['\"])\s*javascript:[^'\"]*\2", re.IGNORECASE)

# Termos internos que nunca podem ir ao documento do cliente.
_VAZAMENTO = re.compile(
    r"total_custo|valor_custo|margem_calculada|snapshot_custo|override_custo|lucro\s*bruto|tef_override",
    re.IGNORECASE,
)

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
  <h1>Proposta comercial</h1>
  <p><strong>Cliente:</strong> {{razao_social}} &nbsp; <strong>CNPJ:</strong> {{cnpj}}</p>
  <h2>Itens</h2>
  {{itens}}
  <p><strong>Valor mensal:</strong> {{valor_mensalidade}}</p>
  <h2>Condições</h2>
  <div>{{condicoes}}</div>
</body>
</html>
"""


def sanitize_html(fragment: str) -> str:
    s = _TAGS_PERIGOSAS.sub("", fragment or "")
    s = _ATTR_EVENTO.sub("", s)
    s = _ATTR_JS.sub("", s)
    return s


def _money_br(valor: Decimal | int | float | str | None) -> str:
    try:
        n = Decimal(str(valor if valor is not None else 0))
    except Exception:
        n = Decimal("0")
    q = f"{n.quantize(Decimal('0.01')):,.2f}"
    return "R$ " + q.replace(",", "X").replace(".", ",").replace("X", ".")


def _formatar_cnpj(digits: str | None) -> str:
    d = "".join(c for c in (digits or "") if c.isdigit())
    if len(d) != 14:
        return digits or "—"
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def _hash_html(conteudo: str) -> str:
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def garantir_template_padrao(db: Session) -> PropostaTemplate:
    row = (
        db.query(PropostaTemplate)
        .filter(PropostaTemplate.ativo.is_(True))
        .order_by(PropostaTemplate.id.asc())
        .first()
    )
    if row:
        return row
    row = PropostaTemplate(
        nome="Padrão",
        versao=1,
        conteudo_html=TEMPLATE_PADRAO_HTML,
        vigencia_inicio=datetime.now(timezone.utc),
        ativo=True,
    )
    db.add(row)
    db.flush()
    return row


def listar_templates(db: Session, *, incluir_inativos: bool = False) -> list[PropostaTemplate]:
    garantir_template_padrao(db)
    q = db.query(PropostaTemplate)
    if not incluir_inativos:
        q = q.filter(PropostaTemplate.ativo.is_(True))
    return q.order_by(PropostaTemplate.nome.asc(), PropostaTemplate.versao.desc()).all()


def obter_template(db: Session, template_id: int, *, apenas_ativos: bool = False) -> PropostaTemplate:
    q = db.query(PropostaTemplate).filter(PropostaTemplate.id == template_id)
    if apenas_ativos:
        q = q.filter(PropostaTemplate.ativo.is_(True))
    row = q.first()
    if not row:
        raise HTTPException(status_code=404, detail="Modelo de proposta não encontrado.")
    return row


def _proxima_versao(db: Session, nome: str) -> int:
    atual = db.query(func.max(PropostaTemplate.versao)).filter(PropostaTemplate.nome == nome).scalar()
    return int(atual or 0) + 1


def criar_template(db: Session, data: PropostaTemplateCreate) -> PropostaTemplate:
    nome = data.nome.strip()
    row = PropostaTemplate(
        nome=nome,
        versao=_proxima_versao(db, nome),
        conteudo_html=sanitize_html(data.conteudo_html),
        vigencia_inicio=data.vigencia_inicio or datetime.now(timezone.utc),
        ativo=data.ativo,
    )
    db.add(row)
    db.flush()
    return row


def atualizar_template(db: Session, row: PropostaTemplate, data: PropostaTemplateUpdate) -> PropostaTemplate:
    payload = data.model_dump(exclude_unset=True)
    if "conteudo_html" in payload and payload["conteudo_html"] is not None:
        row.conteudo_html = sanitize_html(payload["conteudo_html"])
    if "nome" in payload and payload["nome"] is not None:
        row.nome = payload["nome"].strip()
    if "vigencia_inicio" in payload:
        row.vigencia_inicio = payload["vigencia_inicio"]
    if "ativo" in payload and payload["ativo"] is not None:
        row.ativo = payload["ativo"]
    db.flush()
    return row


def _logo_html(db: Session) -> str:
    emp = db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()
    if not emp or not emp.logo_filename:
        return ""
    path = caminho_absoluto_logo(emp.logo_filename)
    if not path:
        return ""
    import base64

    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    mime = (emp.logo_mimetype or "image/png").split(";")[0].strip()
    b64 = base64.b64encode(raw).decode("ascii")
    return f'<img src="data:{mime};base64,{b64}" alt=""/>'


def _empresa_sistema_texto(db: Session) -> str:
    emp = db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()
    if not emp:
        return ""
    partes = [p for p in (emp.nome_fantasia or emp.nome, emp.razao_social) if p]
    return html.escape(" · ".join(dict.fromkeys(partes)))


def _nomes_itens_cliente(db: Session, linha: CrmNegociacaoCnpjLinha) -> list[str]:
    """Só nomes visíveis ao cliente — nunca custo/margem do snapshot interno."""
    nomes: list[str] = []
    snap = linha.snapshot_custo if isinstance(linha.snapshot_custo, dict) else {}
    for item in snap.get("itens") or []:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("nome") or "").strip()
        if nome:
            nomes.append(nome)
    if nomes:
        return nomes
    ids = [int(i) for i in (linha.item_ids or []) if i is not None]
    if not ids:
        return []
    rows = db.query(CustoCatalogoItem).filter(CustoCatalogoItem.id.in_(ids)).all()
    by_id = {int(r.id): str(r.nome) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


def _tabela_itens(db: Session, linhas: list[CrmNegociacaoCnpjLinha]) -> str:
    rows: list[str] = []
    for ln in linhas:
        nomes = _nomes_itens_cliente(db, ln)
        itens = html.escape(", ".join(nomes) if nomes else "—")
        razao = html.escape(ln.razao_social or "—")
        cnpj = html.escape(_formatar_cnpj(ln.cnpj))
        valor = html.escape(_money_br(ln.valor_negociado))
        rows.append(
            f"<tr><td>{razao}</td><td>{cnpj}</td><td>{itens}</td><td>{valor}</td></tr>"
        )
    corpo = "".join(rows) or "<tr><td colspan='4'>—</td></tr>"
    return (
        "<table><thead><tr>"
        "<th>Razão social</th><th>CNPJ</th><th>Itens</th><th>Valor mensal</th>"
        "</tr></thead><tbody>"
        f"{corpo}</tbody></table>"
    )


def _condicoes_html(raw: str | None) -> str:
    s = (raw or "").strip()
    if not s:
        return "<p>—</p>"
    if "<" in s:
        return sanitize_html(s) or "<p>—</p>"
    return "<p>" + html.escape(s).replace("\n", "<br/>") + "</p>"


def preencher_template(
    db: Session,
    template_html: str,
    linhas: list[CrmNegociacaoCnpjLinha],
    *,
    condicoes: str | None,
) -> str:
    if not linhas:
        raise HTTPException(status_code=400, detail="Selecione pelo menos uma linha CNPJ.")
    razoes = [ln.razao_social for ln in linhas if (ln.razao_social or "").strip()]
    cnpjs = [_formatar_cnpj(ln.cnpj) for ln in linhas]
    total = sum((Decimal(str(ln.valor_negociado or 0)) for ln in linhas), Decimal("0"))
    valores = {
        "razao_social": html.escape(" / ".join(razoes) if razoes else "—"),
        "cnpj": html.escape(" / ".join(cnpjs) if cnpjs else "—"),
        "itens": _tabela_itens(db, linhas),
        "valor_mensalidade": html.escape(_money_br(total)),
        "condicoes": _condicoes_html(condicoes),
        "logo": _logo_html(db),
        "empresa_sistema": _empresa_sistema_texto(db),
    }
    html_out = sanitize_html(template_html)
    for chave, valor in valores.items():
        html_out = html_out.replace("{{" + chave + "}}", valor)
    if _VAZAMENTO.search(html_out):
        raise HTTPException(
            status_code=500,
            detail="A proposta gerada continha dados internos e foi bloqueada. Contacte o suporte.",
        )
    return html_out


def html_para_pdf(html_doc: str) -> bytes:
    """Converte o snapshot HTML em PDF. WeasyPrint no Docker/produção; testes podem substituir."""
    try:
        from weasyprint import HTML  # type: ignore
    except Exception as exc:  # pragma: no cover - ambiente sem libs nativas
        logger.warning("WeasyPrint indisponível: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Geração de PDF indisponível neste ambiente. Use o preview HTML ou instale as bibliotecas do WeasyPrint.",
        ) from exc
    try:
        pdf = HTML(string=html_doc, encoding="utf-8").write_pdf()
    except Exception as exc:
        logger.exception("Falha ao gerar PDF da proposta")
        raise HTTPException(status_code=500, detail="Não foi possível gerar o PDF.") from exc
    if not pdf:
        raise HTTPException(status_code=500, detail="Não foi possível gerar o PDF.")
    return pdf


def listar_propostas(db: Session, negociacao_id: int) -> list[Proposta]:
    crm_svc.obter_negociacao(db, negociacao_id)
    return (
        db.query(Proposta)
        .options(joinedload(Proposta.template))
        .filter(Proposta.negociacao_id == negociacao_id)
        .order_by(Proposta.created_at.desc())
        .all()
    )


def obter_proposta(db: Session, proposta_id: int) -> Proposta:
    row = (
        db.query(Proposta)
        .options(joinedload(Proposta.template))
        .filter(Proposta.id == proposta_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Proposta não encontrada.")
    return row


def gerar_proposta(db: Session, data: PropostaGerarIn, ator: Atendente) -> Proposta:
    neg = crm_svc.obter_negociacao(db, data.negociacao_id)
    linhas_all: list[CrmNegociacaoCnpjLinha] = list(neg.linhas or [])
    if not linhas_all:
        raise HTTPException(status_code=400, detail="A negociação não tem linhas CNPJ.")
    if data.linha_ids:
        wanted = set(data.linha_ids)
        linhas = [ln for ln in linhas_all if ln.id in wanted]
        if len(linhas) != len(wanted):
            raise HTTPException(status_code=400, detail="Uma ou mais linhas não pertencem a esta negociação.")
    else:
        linhas = sorted(linhas_all, key=lambda ln: (ln.ordem or 0, ln.id))
    if data.template_id:
        tmpl = obter_template(db, data.template_id, apenas_ativos=True)
    else:
        tmpl = garantir_template_padrao(db)

    snapshot = preencher_template(db, tmpl.conteudo_html, linhas, condicoes=data.condicoes)

    anteriores = (
        db.query(Proposta)
        .filter(Proposta.negociacao_id == neg.id, Proposta.status == PROPOSTA_RASCUNHO)
        .all()
    )
    for ant in anteriores:
        ant.status = PROPOSTA_SUBSTITUIDA

    row = Proposta(
        negociacao_id=neg.id,
        template_id=tmpl.id,
        gerado_por_id=ator.id,
        status=PROPOSTA_RASCUNHO,
        conteudo_html_snapshot=snapshot,
        conteudo_hash=_hash_html(snapshot),
        linha_ids=[ln.id for ln in linhas],
    )
    db.add(row)
    db.flush()
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=neg.id,
            autor_id=ator.id,
            tipo=ATIVIDADE_DOCUMENTO,
            texto=f"Proposta #{row.id} gerada (rascunho).",
        )
    )
    db.flush()
    return row


def garantir_pdf(db: Session, row: Proposta) -> bytes:
    if row.pdf_storage_key:
        path = caminho_absoluto_arquivo(row.pdf_storage_key)
        if path:
            return path.read_bytes()
    pdf = html_para_pdf(row.conteudo_html_snapshot)
    try:
        key = gravar_bytes_em_disco(pdf, mimetype="application/pdf", nome_original=f"proposta-{row.id}.pdf")
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Não foi possível guardar o PDF.") from exc
    row.pdf_storage_key = key
    db.flush()
    return pdf


def marcar_enviada(db: Session, row: Proposta, data: PropostaMarcarEnviadaIn, ator: Atendente) -> Proposta:
    if row.status == PROPOSTA_SUBSTITUIDA:
        raise HTTPException(status_code=400, detail="Esta proposta foi substituída por uma versão mais recente.")
    row.status = PROPOSTA_ENVIADA
    row.canal = data.canal
    row.enviado_em = data.enviado_em or datetime.now(timezone.utc)
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=row.negociacao_id,
            autor_id=ator.id,
            tipo=ATIVIDADE_DOCUMENTO,
            texto=f"Proposta #{row.id} marcada como enviada ({row.canal}).",
        )
    )
    if data.avancar_funil:
        neg = crm_svc.obter_negociacao(db, row.negociacao_id)
        atual = crm_svc.obter_estagio(db, estagio_id=neg.estagio_id)
        if atual.slug != "proposta_enviada":
            crm_svc.mover_estagio(db, neg, ator=ator, estagio_slug="proposta_enviada", nota="Proposta enviada ao cliente.")
    db.flush()
    return row


def proposta_para_read(row: Proposta) -> dict[str, Any]:
    tmpl = row.template
    return {
        "id": row.id,
        "negociacao_id": row.negociacao_id,
        "template_id": row.template_id,
        "template_nome": tmpl.nome if tmpl else None,
        "template_versao": tmpl.versao if tmpl else None,
        "gerado_por_id": row.gerado_por_id,
        "status": row.status,
        "conteudo_html_snapshot": row.conteudo_html_snapshot,
        "conteudo_hash": row.conteudo_hash,
        "linha_ids": list(row.linha_ids or []),
        "canal": row.canal,
        "enviado_em": row.enviado_em,
        "created_at": row.created_at,
    }
