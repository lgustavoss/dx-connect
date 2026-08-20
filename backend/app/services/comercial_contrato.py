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
from sqlalchemy.orm import Session, joinedload, object_session

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
    ContratoPolitica,
    ContratoTemplate,
)
from app.models.crm import ATIVIDADE_DOCUMENTO, CrmNegociacao, CrmNegociacaoAtividade, CrmNegociacaoCnpjLinha
from app.models.empresa import Empresa
from app.models.empresa_sistema import EmpresaSistema
from app.models.rede import Rede
from app.schemas.comercial_contrato import (
    ContratoGerarIn,
    ContratoMarcarAssinadoIn,
    ContratoMarcarEnviadoIn,
    ContratoTemplateCreate,
    ContratoTemplateUpdate,
)
from app.services import comercial_proposta as proposta_svc
from app.services import crm as crm_svc
from app.services.ticket_anexo_storage import caminho_absoluto_arquivo, gravar_bytes_em_disco, validar_upload

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
  <div class="logo">{{contratada.logo}}</div>
  <h1>Contrato de prestação de serviços</h1>
  <h2>Contratada</h2>
  <p><strong>{{contratada.razao_social}}</strong> &nbsp; CNPJ {{contratada.cnpj}}</p>
  <p>{{contratada.endereco}}</p>
  <h2>Contratante</h2>
  <p><strong>{{contratante.razao_social}}</strong> &nbsp; CNPJ {{contratante.cnpj}}</p>
  <p>{{contratante.endereco}}</p>
  <p>Responsável legal: {{contratante.resp_legal}}</p>
  <p class="muted">Base WebPosto: {{contratante.nome_base_webposto}}</p>
  <h2>Objeto e valores</h2>
  {{contrato.itens}}
  <p><strong>Mensalidade:</strong> {{contrato.valor_mensalidade}}</p>
  {{contrato.setup_bloco}}
  <h2>Vigência e fidelidade</h2>
  <p>Início: {{contrato.data_inicio}} &nbsp; Fim da fidelidade: {{contrato.data_fim_fidelidade}}
    ({{contrato.fidelidade_meses}} meses).</p>
  <p>Em caso de rescisão antecipada, multa de até {{contrato.multa_max_mensalidades}} mensalidade(s)
    — ajuste este texto conforme o parecer do seu advogado.</p>
  <p>Após a fidelidade, renovação automática: {{contrato.reajuste}}.</p>
  <h2>Implantação</h2>
  {{contrato.clausula_deslocamento}}
  {{contrato.clausula_alimentacao}}
  {{contrato.clausula_hospedagem}}
</body>
</html>
"""

# Catálogo documentado na UI / GET .../contrato-templates/chaves (fonte única).
CATALOGO_CHAVES_CONTRATO: tuple[dict[str, str], ...] = (
    {"grupo": "contratada", "chave": "contratada.logo", "descricao": "Logo da empresa nas configurações do DeskRudder"},
    {"grupo": "contratada", "chave": "contratada.razao_social", "descricao": "Razão social da contratada (empresa do sistema)"},
    {"grupo": "contratada", "chave": "contratada.nome_fantasia", "descricao": "Nome fantasia da contratada"},
    {"grupo": "contratada", "chave": "contratada.cnpj", "descricao": "CNPJ da contratada"},
    {"grupo": "contratada", "chave": "contratada.email", "descricao": "E-mail da contratada"},
    {"grupo": "contratada", "chave": "contratada.telefone", "descricao": "Telefone da contratada"},
    {"grupo": "contratada", "chave": "contratada.endereco", "descricao": "Endereço completo formatado da contratada"},
    {"grupo": "contratada", "chave": "contratada.bloco", "descricao": "Bloco resumo (nome, CNPJ e endereço) da contratada"},
    {"grupo": "contratante", "chave": "contratante.razao_social", "descricao": "Razão social da linha CNPJ / lead"},
    {"grupo": "contratante", "chave": "contratante.cnpj", "descricao": "CNPJ do contratante"},
    {"grupo": "contratante", "chave": "contratante.endereco", "descricao": "Endereço fiscal do contratante"},
    {"grupo": "contratante", "chave": "contratante.email", "descricao": "E-mail (dados fiscais ou lead)"},
    {"grupo": "contratante", "chave": "contratante.telefone", "descricao": "Telefone (dados fiscais ou lead)"},
    {"grupo": "contratante", "chave": "contratante.resp_legal_nome", "descricao": "Nome do responsável legal"},
    {"grupo": "contratante", "chave": "contratante.resp_legal_cpf", "descricao": "CPF do responsável legal"},
    {"grupo": "contratante", "chave": "contratante.resp_legal", "descricao": "Responsável legal (nome · CPF)"},
    {"grupo": "contratante", "chave": "contratante.nome_base_webposto", "descricao": "Nome da base WebPosto (Rede)"},
    {"grupo": "contrato", "chave": "contrato.itens", "descricao": "Tabela HTML com itens e mensalidade"},
    {"grupo": "contrato", "chave": "contrato.valor_mensalidade", "descricao": "Mensalidade formatada (R$)"},
    {"grupo": "contrato", "chave": "contrato.data_inicio", "descricao": "Data de início (dd/mm/aaaa)"},
    {"grupo": "contrato", "chave": "contrato.data_fim_fidelidade", "descricao": "Fim do período de fidelidade"},
    {"grupo": "contrato", "chave": "contrato.fidelidade_meses", "descricao": "Meses de fidelidade (número)"},
    {"grupo": "contrato", "chave": "contrato.multa_max_mensalidades", "descricao": "Teto de multa em mensalidades (número; use no texto do seu modelo)"},
    {"grupo": "contrato", "chave": "contrato.reajuste_percentual", "descricao": "Percentual de reajuste (ex.: 5,50)"},
    {"grupo": "contrato", "chave": "contrato.reajuste_rotulo", "descricao": "Rótulo do reajuste (ex.: IGPM)"},
    {"grupo": "contrato", "chave": "contrato.reajuste", "descricao": "Resumo curto: «8,50% (IGPM)» ou «sem reajuste»"},
    {"grupo": "contrato", "chave": "contrato.setup_valor", "descricao": "Valor do setup (ou — se isento/ausente)"},
    {"grupo": "contrato", "chave": "contrato.setup_isento", "descricao": "«sim» ou «não»"},
    {"grupo": "contrato", "chave": "contrato.setup_bloco", "descricao": "Parágrafo HTML pronto sobre setup/implantação"},
    {"grupo": "contrato", "chave": "contrato.clausula_deslocamento", "descricao": "Linha HTML se deslocamento for do contratante"},
    {"grupo": "contrato", "chave": "contrato.clausula_alimentacao", "descricao": "Linha HTML se alimentação for do contratante"},
    {"grupo": "contrato", "chave": "contrato.clausula_hospedagem", "descricao": "Linha HTML se hospedagem for do contratante"},
    {"grupo": "legado", "chave": "logo", "descricao": "Alias de contratada.logo"},
    {"grupo": "legado", "chave": "empresa_sistema", "descricao": "Alias de contratada.bloco"},
    {"grupo": "legado", "chave": "razao_social", "descricao": "Alias de contratante.razao_social"},
    {"grupo": "legado", "chave": "cnpj", "descricao": "Alias de contratante.cnpj"},
    {"grupo": "legado", "chave": "endereco_contratante", "descricao": "Alias de contratante.endereco"},
    {"grupo": "legado", "chave": "resp_legal", "descricao": "Alias de contratante.resp_legal"},
    {"grupo": "legado", "chave": "nome_base_webposto", "descricao": "Alias de contratante.nome_base_webposto"},
    {"grupo": "legado", "chave": "itens", "descricao": "Alias de contrato.itens"},
    {"grupo": "legado", "chave": "valor_mensalidade", "descricao": "Alias de contrato.valor_mensalidade"},
    {"grupo": "legado", "chave": "data_inicio", "descricao": "Alias de contrato.data_inicio"},
    {"grupo": "legado", "chave": "data_fim_fidelidade", "descricao": "Alias de contrato.data_fim_fidelidade"},
    {"grupo": "legado", "chave": "fidelidade_meses", "descricao": "Alias de contrato.fidelidade_meses"},
    {"grupo": "legado", "chave": "fidelidade", "descricao": "Alias numérico (meses); não gera cláusula jurídica"},
    {"grupo": "legado", "chave": "multa", "descricao": "Alias de contrato.multa_max_mensalidades (só o número)"},
    {"grupo": "legado", "chave": "igpm", "descricao": "Alias de contrato.reajuste"},
    {"grupo": "legado", "chave": "reajuste", "descricao": "Alias de contrato.reajuste"},
    {"grupo": "legado", "chave": "setup_bloco", "descricao": "Alias de contrato.setup_bloco"},
    {"grupo": "legado", "chave": "clausula_deslocamento", "descricao": "Alias de contrato.clausula_deslocamento"},
    {"grupo": "legado", "chave": "clausula_alimentacao", "descricao": "Alias de contrato.clausula_alimentacao"},
    {"grupo": "legado", "chave": "clausula_hospedagem", "descricao": "Alias de contrato.clausula_hospedagem"},
)


CAMPOS_FISCAIS_OBRIGATORIOS = (
    "endereco",
    "numero",
    "bairro",
    "cidade",
    "estado",
    "cep",
    "resp_legal_nome",
    "resp_legal_cpf",
)


def _digits(valor: str | None) -> str:
    return "".join(c for c in str(valor or "") if c.isdigit())


def _fiscal_dict(linha: CrmNegociacaoCnpjLinha) -> dict[str, str]:
    raw = linha.dados_fiscais if isinstance(linha.dados_fiscais, dict) else {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if v is None:
            continue
        s = str(v).strip()
        if s:
            out[str(k)] = s
    return out


def assert_pronto_para_contrato(db: Session, linha: CrmNegociacaoCnpjLinha) -> CrmNegociacao:
    neg = linha.negociacao or crm_svc.obter_negociacao(db, linha.negociacao_id)
    if not (neg.nome_base_webposto or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Informe o nome da base WebPosto na negociação antes de gerar o contrato.",
        )
    if not (linha.razao_social or "").strip() or not _digits(linha.cnpj):
        raise HTTPException(
            status_code=400,
            detail="A linha precisa de razão social e CNPJ para gerar o contrato.",
        )
    fiscal = _fiscal_dict(linha)
    if any(not fiscal.get(c) for c in CAMPOS_FISCAIS_OBRIGATORIOS):
        raise HTTPException(
            status_code=400,
            detail="Preencha os dados fiscais da linha (endereço completo e responsável legal) antes de gerar o contrato.",
        )
    return neg


def garantir_politica(db: Session) -> ContratoPolitica:
    row = db.query(ContratoPolitica).order_by(ContratoPolitica.id.asc()).first()
    if row:
        return row
    row = ContratoPolitica(id=1, reajuste_percentual=Decimal("0"), reajuste_rotulo="")
    db.add(row)
    db.flush()
    return row


def atualizar_politica(db: Session, data) -> ContratoPolitica:
    row = garantir_politica(db)
    payload = data.model_dump(exclude_unset=True)
    if "reajuste_percentual" in payload and payload["reajuste_percentual"] is not None:
        row.reajuste_percentual = payload["reajuste_percentual"]
    if "reajuste_rotulo" in payload and payload["reajuste_rotulo"] is not None:
        row.reajuste_rotulo = payload["reajuste_rotulo"].strip()
    db.flush()
    return row


def _resolver_reajuste(db: Session, data: ContratoGerarIn) -> tuple[Decimal, str]:
    pol = garantir_politica(db)
    rotulo_pol = (pol.reajuste_rotulo or "").strip()
    if data.sem_reajuste:
        rotulo = (data.reajuste_rotulo or "").strip()
        return Decimal("0"), rotulo
    if data.reajuste_percentual is not None:
        rotulo = data.reajuste_rotulo.strip() if data.reajuste_rotulo is not None else rotulo_pol
        return Decimal(str(data.reajuste_percentual)), rotulo
    rotulo = data.reajuste_rotulo.strip() if data.reajuste_rotulo is not None else rotulo_pol
    return Decimal(str(pol.reajuste_percentual or 0)), rotulo


def _fmt_pct(valor: Decimal) -> str:
    q = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{q}".replace(".", ",")


def _endereco_formatado(fiscal: dict[str, str], *, prefixo: str = "") -> str:
    def g(chave: str) -> str:
        return fiscal.get(f"{prefixo}{chave}" if prefixo else chave, "") or fiscal.get(chave, "")

    linha1 = " ".join(p for p in (g("endereco"), g("numero"), g("complemento")) if p)
    cid = " / ".join(p for p in (g("cidade"), g("estado")) if p)
    partes = [p for p in (linha1, g("bairro"), cid, g("cep")) if p]
    return html.escape(" · ".join(partes) if partes else "—")


def _bloco_empresa_sistema(db: Session) -> str:
    emp = db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()
    if not emp:
        return ""
    nomes = [p for p in (emp.razao_social, emp.nome_fantasia or emp.nome) if p]
    fiscal = {
        "endereco": emp.endereco or "",
        "numero": emp.numero or "",
        "complemento": emp.complemento or "",
        "bairro": emp.bairro or "",
        "cidade": emp.cidade or "",
        "estado": emp.estado or "",
        "cep": emp.cep or "",
    }
    bits = [html.escape(" · ".join(dict.fromkeys(nomes)))]
    if emp.cnpj:
        bits.append(html.escape(f"CNPJ {proposta_svc._formatar_cnpj(emp.cnpj)}"))
    end = _endereco_formatado(fiscal)
    if end and end != "—":
        bits.append(end)
    return " — ".join(bits)


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
    row = (
        db.query(CrmNegociacaoCnpjLinha)
        .options(
            joinedload(CrmNegociacaoCnpjLinha.negociacao).joinedload(CrmNegociacao.lead),
        )
        .filter(CrmNegociacaoCnpjLinha.id == linha_id)
        .first()
    )
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


def obter_contrato(db: Session, contrato_id: int, *, atendente: Atendente | None = None) -> Contrato:
    row = (
        db.query(Contrato)
        .options(*_opts_contrato())
        .filter(Contrato.id == contrato_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    _assert_acesso_contrato(row, atendente)
    return row


def _assert_acesso_negociacao(neg: CrmNegociacao | None, atendente: Atendente | None) -> None:
    if atendente is None or atendente.role == "admin":
        return
    if neg is None or neg.responsavel_id != atendente.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para este contrato.")


def _assert_acesso_contrato(row: Contrato, atendente: Atendente | None) -> None:
    if atendente is None or atendente.role == "admin":
        return
    linha = row.linha
    neg = linha.negociacao if linha else None
    _assert_acesso_negociacao(neg, atendente)


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


def _reajuste_curto(pct: Decimal, rotulo: str) -> str:
    """Valor curto para o modelo — a cláusula jurídica fica no HTML do cliente."""
    if pct <= 0:
        return "sem reajuste"
    rot = (rotulo or "").strip() or "índice do contrato"
    return f"{_fmt_pct(pct)}% ({html.escape(rot)})"


def _clausula_custo_cliente(ativo: bool, titulo: str) -> str:
    if not ativo:
        return ""
    return _p(html.escape(f"{titulo} por conta do contratante."))


def _empresa_sistema_row(db: Session) -> EmpresaSistema | None:
    return db.query(EmpresaSistema).order_by(EmpresaSistema.id.asc()).first()


def _esc(valor: str | None, *, default: str = "—") -> str:
    s = (valor or "").strip()
    return html.escape(s) if s else default


def montar_valores_template(
    db: Session, contrato: Contrato, linha: CrmNegociacaoCnpjLinha
) -> dict[str, str]:
    """Mapa chave → valor para substituição {{chave}} (prefixos + aliases legados)."""
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
    fiscal = _fiscal_dict(linha)
    neg = linha.negociacao
    nome_base = (neg.nome_base_webposto if neg else "") or ""
    pct = Decimal(str(contrato.reajuste_percentual or 0))
    reaj = _reajuste_curto(pct, contrato.reajuste_rotulo or "")
    resp_nome = fiscal.get("resp_legal_nome") or ""
    resp_cpf = fiscal.get("resp_legal_cpf") or ""
    resp_txt = "—"
    if resp_nome:
        resp_txt = html.escape(resp_nome)
        if resp_cpf:
            resp_txt += html.escape(f" · CPF {resp_cpf}")

    emp = _empresa_sistema_row(db)
    emp_fiscal = {
        "endereco": (emp.endereco if emp else "") or "",
        "numero": (emp.numero if emp else "") or "",
        "complemento": (emp.complemento if emp else "") or "",
        "bairro": (emp.bairro if emp else "") or "",
        "cidade": (emp.cidade if emp else "") or "",
        "estado": (emp.estado if emp else "") or "",
        "cep": (emp.cep if emp else "") or "",
    }
    logo = proposta_svc._logo_html(db)
    bloco_emp = _bloco_empresa_sistema(db) or proposta_svc._empresa_sistema_texto(db)
    endereco_contratante = _endereco_formatado(fiscal)
    endereco_contratada = _endereco_formatado(emp_fiscal)
    setup_bloco = _setup_bloco(setup_isento=bool(contrato.setup_isento), setup_valor=contrato.setup_valor)
    setup_valor_txt = (
        "—"
        if contrato.setup_isento or contrato.setup_valor is None
        else html.escape(proposta_svc._money_br(contrato.setup_valor))
    )
    email_ctr = fiscal.get("email") or (neg.lead.email if neg and neg.lead else "") or ""
    tel_ctr = fiscal.get("telefone") or (neg.lead.telefone if neg and neg.lead else "") or ""

    contratada = {
        "contratada.logo": logo,
        "contratada.razao_social": _esc(emp.razao_social if emp else None),
        "contratada.nome_fantasia": _esc((emp.nome_fantasia or emp.nome) if emp else None),
        "contratada.cnpj": (
            html.escape(proposta_svc._formatar_cnpj(emp.cnpj)) if emp and emp.cnpj else "—"
        ),
        "contratada.email": _esc(emp.email if emp else None),
        "contratada.telefone": _esc(emp.telefone if emp else None),
        "contratada.endereco": endereco_contratada,
        "contratada.bloco": bloco_emp or "—",
    }
    contratante = {
        "contratante.razao_social": html.escape(linha.razao_social or "—"),
        "contratante.cnpj": html.escape(proposta_svc._formatar_cnpj(linha.cnpj)),
        "contratante.endereco": endereco_contratante,
        "contratante.email": _esc(email_ctr),
        "contratante.telefone": _esc(tel_ctr),
        "contratante.resp_legal_nome": _esc(resp_nome),
        "contratante.resp_legal_cpf": _esc(resp_cpf),
        "contratante.resp_legal": resp_txt,
        "contratante.nome_base_webposto": html.escape(nome_base.strip() or "—"),
    }
    contrato_vals = {
        "contrato.itens": tabela,
        "contrato.valor_mensalidade": html.escape(proposta_svc._money_br(contrato.valor_mensalidade)),
        "contrato.data_inicio": html.escape(contrato.data_inicio.strftime("%d/%m/%Y")),
        "contrato.data_fim_fidelidade": html.escape(contrato.data_fim_fidelidade.strftime("%d/%m/%Y")),
        "contrato.fidelidade_meses": html.escape(str(fid)),
        "contrato.multa_max_mensalidades": html.escape(str(multa_n)),
        "contrato.reajuste_percentual": html.escape(_fmt_pct(pct)),
        "contrato.reajuste_rotulo": html.escape((contrato.reajuste_rotulo or "").strip() or "—"),
        "contrato.reajuste": reaj,
        "contrato.setup_valor": setup_valor_txt,
        "contrato.setup_isento": "sim" if contrato.setup_isento else "não",
        "contrato.setup_bloco": setup_bloco,
        "contrato.clausula_deslocamento": _clausula_custo_cliente(
            bool(contrato.deslocamento_cliente), "Deslocamento"
        ),
        "contrato.clausula_alimentacao": _clausula_custo_cliente(
            bool(contrato.alimentacao_cliente), "Alimentação"
        ),
        "contrato.clausula_hospedagem": _clausula_custo_cliente(
            bool(contrato.hospedagem_cliente), "Hospedagem"
        ),
    }
    legado = {
        "logo": contratada["contratada.logo"],
        "empresa_sistema": contratada["contratada.bloco"],
        "razao_social": contratante["contratante.razao_social"],
        "cnpj": contratante["contratante.cnpj"],
        "endereco_contratante": contratante["contratante.endereco"],
        "resp_legal": contratante["contratante.resp_legal"],
        "nome_base_webposto": contratante["contratante.nome_base_webposto"],
        "itens": contrato_vals["contrato.itens"],
        "valor_mensalidade": contrato_vals["contrato.valor_mensalidade"],
        "data_inicio": contrato_vals["contrato.data_inicio"],
        "data_fim_fidelidade": contrato_vals["contrato.data_fim_fidelidade"],
        "fidelidade_meses": contrato_vals["contrato.fidelidade_meses"],
        "fidelidade": contrato_vals["contrato.fidelidade_meses"],
        "multa": contrato_vals["contrato.multa_max_mensalidades"],
        "igpm": contrato_vals["contrato.reajuste"],
        "reajuste": contrato_vals["contrato.reajuste"],
        "setup_bloco": contrato_vals["contrato.setup_bloco"],
        "clausula_deslocamento": contrato_vals["contrato.clausula_deslocamento"],
        "clausula_alimentacao": contrato_vals["contrato.clausula_alimentacao"],
        "clausula_hospedagem": contrato_vals["contrato.clausula_hospedagem"],
    }
    return {**contratada, **contratante, **contrato_vals, **legado}


def catalogo_chaves_contrato() -> list[dict[str, str]]:
    return [dict(item) for item in CATALOGO_CHAVES_CONTRATO]


def _aplicar_valores_no_html(template_html: str, valores: dict[str, str]) -> str:
    html_out = sanitize_html(template_html)
    for chave in sorted(valores.keys(), key=lambda k: (-k.count("."), -len(k), k)):
        html_out = html_out.replace("{{" + chave + "}}", valores[chave])
    if proposta_svc._VAZAMENTO.search(html_out):
        raise HTTPException(
            status_code=500,
            detail="O contrato gerado continha dados internos e foi bloqueado. Contacte o suporte.",
        )
    return html_out


def montar_valores_preview_exemplo(db: Session) -> dict[str, str]:
    """Mesmas chaves da geração, com dados fictícios (contratada real da instância quando existir)."""
    emp = _empresa_sistema_row(db)
    emp_fiscal = {
        "endereco": (emp.endereco if emp else "") or "Av. Exemplo",
        "numero": (emp.numero if emp else "") or "100",
        "complemento": (emp.complemento if emp else "") or "",
        "bairro": (emp.bairro if emp else "") or "Centro",
        "cidade": (emp.cidade if emp else "") or "São Paulo",
        "estado": (emp.estado if emp else "") or "SP",
        "cep": (emp.cep if emp else "") or "01000-000",
    }
    logo = proposta_svc._logo_html(db)
    bloco_emp = _bloco_empresa_sistema(db) or proposta_svc._empresa_sistema_texto(db)
    if not bloco_emp:
        bloco_emp = html.escape("Empresa Exemplo LTDA · CNPJ 00.000.000/0001-91")

    razao_ctr = "Posto Exemplo LTDA"
    cnpj_ctr = "12.345.678/0001-95"
    itens_txt = "Licença mensal, Suporte"
    tabela = (
        "<table><thead><tr><th>Razão social</th><th>CNPJ</th><th>Itens</th><th>Mensalidade</th></tr></thead>"
        "<tbody><tr>"
        f"<td>{html.escape(razao_ctr)}</td>"
        f"<td>{html.escape(cnpj_ctr)}</td>"
        f"<td>{html.escape(itens_txt)}</td>"
        f"<td>{html.escape('R$ 1.200,00')}</td>"
        "</tr></tbody></table>"
    )
    setup_bloco = _setup_bloco(setup_isento=False, setup_valor=Decimal("1500.00"))
    reaj = _reajuste_curto(Decimal("5.5"), "IGPM")
    endereco_contratante = _endereco_formatado(
        {
            "endereco": "Rua do Cliente",
            "numero": "50",
            "complemento": "Sala 2",
            "bairro": "Industrial",
            "cidade": "Campinas",
            "estado": "SP",
            "cep": "13000-000",
        }
    )
    resp_txt = html.escape("Maria Silva · CPF 123.456.789-00")

    contratada = {
        "contratada.logo": logo,
        "contratada.razao_social": _esc(emp.razao_social if emp else None, default=html.escape("Empresa Exemplo LTDA")),
        "contratada.nome_fantasia": _esc(
            (emp.nome_fantasia or emp.nome) if emp else None,
            default=html.escape("Empresa Exemplo"),
        ),
        "contratada.cnpj": (
            html.escape(proposta_svc._formatar_cnpj(emp.cnpj))
            if emp and emp.cnpj
            else html.escape("00.000.000/0001-91")
        ),
        "contratada.email": _esc(emp.email if emp else None, default=html.escape("contato@exemplo.com")),
        "contratada.telefone": _esc(emp.telefone if emp else None, default=html.escape("(11) 3000-0000")),
        "contratada.endereco": _endereco_formatado(emp_fiscal),
        "contratada.bloco": bloco_emp or "—",
    }
    contratante = {
        "contratante.razao_social": html.escape(razao_ctr),
        "contratante.cnpj": html.escape(cnpj_ctr),
        "contratante.endereco": endereco_contratante,
        "contratante.email": html.escape("cliente@exemplo.com"),
        "contratante.telefone": html.escape("(19) 98888-0000"),
        "contratante.resp_legal_nome": html.escape("Maria Silva"),
        "contratante.resp_legal_cpf": html.escape("123.456.789-00"),
        "contratante.resp_legal": resp_txt,
        "contratante.nome_base_webposto": html.escape("base_exemplo"),
    }
    contrato_vals = {
        "contrato.itens": tabela,
        "contrato.valor_mensalidade": html.escape("R$ 1.200,00"),
        "contrato.data_inicio": html.escape("01/01/2026"),
        "contrato.data_fim_fidelidade": html.escape("01/01/2027"),
        "contrato.fidelidade_meses": html.escape("12"),
        "contrato.multa_max_mensalidades": html.escape("3"),
        "contrato.reajuste_percentual": html.escape("5,50"),
        "contrato.reajuste_rotulo": html.escape("IGPM"),
        "contrato.reajuste": reaj,
        "contrato.setup_valor": html.escape("R$ 1.500,00"),
        "contrato.setup_isento": "não",
        "contrato.setup_bloco": setup_bloco,
        "contrato.clausula_deslocamento": _clausula_custo_cliente(True, "Deslocamento"),
        "contrato.clausula_alimentacao": _clausula_custo_cliente(True, "Alimentação"),
        "contrato.clausula_hospedagem": _clausula_custo_cliente(True, "Hospedagem"),
    }
    legado = {
        "logo": contratada["contratada.logo"],
        "empresa_sistema": contratada["contratada.bloco"],
        "razao_social": contratante["contratante.razao_social"],
        "cnpj": contratante["contratante.cnpj"],
        "endereco_contratante": contratante["contratante.endereco"],
        "resp_legal": contratante["contratante.resp_legal"],
        "nome_base_webposto": contratante["contratante.nome_base_webposto"],
        "itens": contrato_vals["contrato.itens"],
        "valor_mensalidade": contrato_vals["contrato.valor_mensalidade"],
        "data_inicio": contrato_vals["contrato.data_inicio"],
        "data_fim_fidelidade": contrato_vals["contrato.data_fim_fidelidade"],
        "fidelidade_meses": contrato_vals["contrato.fidelidade_meses"],
        "fidelidade": contrato_vals["contrato.fidelidade_meses"],
        "multa": contrato_vals["contrato.multa_max_mensalidades"],
        "igpm": contrato_vals["contrato.reajuste"],
        "reajuste": contrato_vals["contrato.reajuste"],
        "setup_bloco": contrato_vals["contrato.setup_bloco"],
        "clausula_deslocamento": contrato_vals["contrato.clausula_deslocamento"],
        "clausula_alimentacao": contrato_vals["contrato.clausula_alimentacao"],
        "clausula_hospedagem": contrato_vals["contrato.clausula_hospedagem"],
    }
    return {**contratada, **contratante, **contrato_vals, **legado}


def preencher_template_preview(db: Session, template_html: str) -> str:
    return _aplicar_valores_no_html(template_html, montar_valores_preview_exemplo(db))


def preencher_template(db: Session, template_html: str, contrato: Contrato, linha: CrmNegociacaoCnpjLinha) -> str:
    return _aplicar_valores_no_html(template_html, montar_valores_template(db, contrato, linha))


def _montar_snapshots(
    db: Session,
    linha: CrmNegociacaoCnpjLinha,
    data: ContratoGerarIn,
    *,
    reajuste_percentual: Decimal,
    reajuste_rotulo: str,
    nome_base: str,
) -> dict[str, Any]:
    nomes = proposta_svc._nomes_itens_cliente(db, linha)
    snap_custo = linha.snapshot_custo if isinstance(linha.snapshot_custo, dict) else None
    fiscal = _fiscal_dict(linha)
    return {
        "valor_mensalidade": Decimal(str(linha.valor_negociado or 0)),
        "snapshot_custo": snap_custo,
        "snapshot_itens": [{"nome": n} for n in nomes],
        "reajuste_percentual": reajuste_percentual,
        "reajuste_rotulo": reajuste_rotulo,
        "snapshot_comercial": {
            "valor_mensalidade": str(Decimal(str(linha.valor_negociado or 0))),
            "setup_valor": str(data.setup_valor) if data.setup_valor is not None else None,
            "setup_isento": data.setup_isento,
            "fidelidade_meses": data.fidelidade_meses,
            "multa_max_mensalidades": data.multa_max_mensalidades,
            "deslocamento_cliente": data.deslocamento_cliente,
            "alimentacao_cliente": data.alimentacao_cliente,
            "hospedagem_cliente": data.hospedagem_cliente,
            "reajuste_percentual": str(reajuste_percentual),
            "reajuste_rotulo": reajuste_rotulo,
            "nome_base_webposto": nome_base,
            "dados_fiscais": fiscal,
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
    row.reajuste_percentual = snaps["reajuste_percentual"]
    row.reajuste_rotulo = snaps["reajuste_rotulo"]


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
    neg = assert_pronto_para_contrato(db, linha)
    _assert_acesso_negociacao(neg, ator)
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

    pct, rotulo = _resolver_reajuste(db, data)
    snaps = _montar_snapshots(
        db,
        linha,
        data,
        reajuste_percentual=pct,
        reajuste_rotulo=rotulo,
        nome_base=(neg.nome_base_webposto or "").strip(),
    )
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
    if not (row.pdf_assinado_storage_key or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Anexe o PDF assinado antes de marcar o contrato como assinado.",
        )
    if data.referencia_externa is not None:
        row.referencia_externa = data.referencia_externa.strip() or None
    row.status = CONTRATO_ASSINADO
    row.assinado_em = data.assinado_em or datetime.now(timezone.utc)
    linha = row.linha or obter_linha(db, row.negociacao_linha_cnpj_id)
    converter_pos_assinatura(db, row, linha, ator)
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
    return obter_contrato(db, row.id)


def cancelar_contrato(db: Session, row: Contrato, ator: Atendente) -> Contrato:
    if row.status == CONTRATO_CANCELADO:
        raise HTTPException(status_code=400, detail="Este contrato já está cancelado.")
    if row.status not in {CONTRATO_RASCUNHO, CONTRATO_ENVIADO, CONTRATO_ASSINADO}:
        raise HTTPException(
            status_code=400,
            detail="Só é possível cancelar ou rescindir contratos em rascunho, enviado ou assinado.",
        )

    era_assinado = row.status == CONTRATO_ASSINADO
    estimativa = estimar_multa_rescisao(row) if era_assinado else None
    row.status = CONTRATO_CANCELADO
    linha = row.linha or obter_linha(db, row.negociacao_linha_cnpj_id)

    if era_assinado and estimativa is not None:
        if estimativa["aplicavel"] and estimativa["valor_estimado"] is not None:
            texto = (
                f"Contrato #{row.id} rescindido. Estimativa de multa: "
                f"{estimativa['mensalidades_estimadas']} mensalidade(s) = "
                f"{proposta_svc._money_br(estimativa['valor_estimado'])} "
                f"(ajuda operacional; não é cobrança)."
            )
        elif estimativa["dentro_fidelidade"] and estimativa["multa_max_mensalidades"] <= 0:
            texto = (
                f"Contrato #{row.id} rescindido dentro da fidelidade; "
                "teto de multa é 0 — sem estimativa."
            )
        else:
            texto = (
                f"Contrato #{row.id} rescindido fora do período de fidelidade "
                "(ou sem meses restantes) — sem estimativa de multa."
            )
    else:
        texto = f"Contrato #{row.id} cancelado."

    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=linha.negociacao_id,
            autor_id=ator.id,
            tipo=ATIVIDADE_DOCUMENTO,
            texto=texto,
        )
    )
    db.flush()
    return row


AVISO_MULTA_RESCISAO = (
    "Estimativa operacional do DeskRudder. Não constitui cobrança, boleto nem parecer jurídico — "
    "confirme com o contrato do cliente e o processo interno."
)


def _meses_restantes_fidelidade(data_fim: date, hoje: date) -> int:
    """Meses restantes aproximados (teto por 30 dias), para estimativa de multa."""
    dias = (data_fim - hoje).days
    if dias <= 0:
        return 0
    return (dias + 29) // 30


def estimar_multa_rescisao(row: Contrato, *, hoje: date | None = None) -> dict[str, Any]:
    """
    Ajuda operacional: min(meses_restantes, multa_max) × mensalidade.
    Só aplicável dentro da fidelidade e com teto > 0.
    """
    ref = hoje or date.today()
    fim = row.data_fim_fidelidade
    max_m = int(row.multa_max_mensalidades or 0)
    valor = Decimal(str(row.valor_mensalidade or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    meses = _meses_restantes_fidelidade(fim, ref) if fim else 0
    fid = int(getattr(row, "fidelidade_meses", None) or 0)
    if fid > 0:
        meses = min(meses, fid)
    dentro = meses > 0
    aplicavel = dentro and max_m > 0
    cobradas = min(meses, max_m) if aplicavel else 0
    estimado = (valor * Decimal(cobradas)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if aplicavel else None
    return {
        "aplicavel": aplicavel,
        "dentro_fidelidade": dentro,
        "meses_restantes": meses,
        "multa_max_mensalidades": max_m,
        "mensalidades_estimadas": cobradas,
        "valor_mensalidade": valor,
        "valor_estimado": estimado,
        "aviso": AVISO_MULTA_RESCISAO,
    }


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
    rede_id = None
    if row.empresa_id:
        sess = object_session(row)
        if sess is not None:
            emp = sess.query(Empresa).filter(Empresa.id == row.empresa_id).first()
            if emp is not None:
                rede_id = emp.rede_id
    return {
        "id": row.id,
        "negociacao_linha_cnpj_id": row.negociacao_linha_cnpj_id,
        "negociacao_id": linha.negociacao_id if linha else None,
        "empresa_id": row.empresa_id,
        "rede_id": rede_id,
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
        "reajuste_percentual": row.reajuste_percentual,
        "reajuste_rotulo": row.reajuste_rotulo or "",
        "pdf_assinado_nome_original": row.pdf_assinado_nome_original,
        "tem_pdf_assinado": bool(row.pdf_assinado_storage_key),
        "referencia_externa": row.referencia_externa,
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
        "multa_rescisao": estimar_multa_rescisao(row),
        "interno": _interno_read(row, linha),
    }


def anexar_pdf_assinado(
    db: Session,
    row: Contrato,
    *,
    conteudo: bytes,
    nome_original: str | None,
    content_type: str | None,
    referencia_externa: str | None,
    ator: Atendente,
) -> Contrato:
    if row.status not in {CONTRATO_RASCUNHO, CONTRATO_ENVIADO}:
        raise HTTPException(
            status_code=400,
            detail="Só é possível anexar o PDF assinado em contrato rascunho ou enviado.",
        )
    try:
        nome, mime = validar_upload(nome_original, content_type, len(conteudo))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if mime and mime != "application/pdf":
        raise HTTPException(status_code=400, detail="O anexo assinado deve ser um PDF.")
    if not (nome.lower().endswith(".pdf") or mime == "application/pdf"):
        raise HTTPException(status_code=400, detail="O anexo assinado deve ser um PDF.")
    try:
        key = gravar_bytes_em_disco(conteudo, mimetype="application/pdf", nome_original=nome)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row.pdf_assinado_storage_key = key
    row.pdf_assinado_nome_original = nome
    if referencia_externa is not None:
        row.referencia_externa = referencia_externa.strip() or None
    linha = row.linha or obter_linha(db, row.negociacao_linha_cnpj_id)
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=linha.negociacao_id,
            autor_id=ator.id,
            tipo=ATIVIDADE_DOCUMENTO,
            texto=f"PDF assinado anexado ao contrato #{row.id}.",
        )
    )
    db.flush()
    return obter_contrato(db, row.id)


def bytes_pdf_assinado(row: Contrato) -> tuple[bytes, str]:
    if not row.pdf_assinado_storage_key:
        raise HTTPException(status_code=404, detail="Este contrato ainda não tem PDF assinado anexado.")
    path = caminho_absoluto_arquivo(row.pdf_assinado_storage_key)
    if not path:
        raise HTTPException(status_code=404, detail="Ficheiro do PDF assinado não encontrado.")
    nome = row.pdf_assinado_nome_original or f"contrato-{row.id}-assinado.pdf"
    return path.read_bytes(), nome


def _contato_conversao(fiscal: dict[str, str], lead: Any) -> tuple[str | None, str | None]:
    email = (fiscal.get("email") or "").strip()
    if not email and lead is not None:
        email = (getattr(lead, "email", None) or "").strip()
    email = email.lower() or None
    tel = _digits(fiscal.get("telefone"))
    if not tel and lead is not None:
        tel = _digits(getattr(lead, "telefone", None))
    tel = tel[:20] or None
    return email, tel


def _aplicar_contato_empresa(empresa: Empresa, email: str | None, telefone: str | None) -> None:
    if email and not (empresa.email or "").strip():
        empresa.email = email[:255]
    if telefone and not _digits(empresa.telefone):
        empresa.telefone = telefone[:20]


def _vincular_contato_chat(db: Session, empresa: Empresa, rede: Rede, fiscal: dict[str, str], lead: Any) -> None:
    """Cria ou reutiliza um colaborador com e-mail/telefone para o chat encontrar o posto."""
    from app.models.funcionario_rede import FuncionarioRede
    from app.services.funcionario_escopo import sincronizar_vinculos_empresas
    from app.services.funcionario_rede_resolver import assert_email_unico_por_rede

    email, telefone = _contato_conversao(fiscal, lead)
    if not email and not telefone:
        return
    nome = (fiscal.get("resp_legal_nome") or "").strip()
    if not nome and lead is not None:
        nome = (getattr(lead, "nome", None) or "").strip()
    if not nome:
        nome = (empresa.nome or "").strip() or "Contacto comercial"
    existente = None
    if telefone:
        for f in db.query(FuncionarioRede).filter(FuncionarioRede.ativo.is_(True), FuncionarioRede.rede_id == rede.id):
            if _digits(f.telefone) == telefone:
                existente = f
                break
    if existente is None and email:
        existente = (
            db.query(FuncionarioRede)
            .filter(
                FuncionarioRede.ativo.is_(True),
                FuncionarioRede.rede_id == rede.id,
                func.lower(FuncionarioRede.email) == email,
            )
            .first()
        )
    if existente:
        if not _digits(existente.telefone) and telefone:
            existente.telefone = telefone
        if not (existente.email or "").strip() and email:
            existente.email = email
        return
    email_func = email
    if email_func:
        try:
            assert_email_unico_por_rede(db, email=email_func, rede_id=rede.id)
        except ValueError:
            email_func = None
        if not email_func and not telefone:
            return
    f = FuncionarioRede(
        nome=nome[:255],
        email=email_func,
        telefone=telefone,
        tipo="colaborador",
        escopo_empresas="selected",
        ativo=True,
        rede_id=rede.id,
        empresa_id=empresa.id,
    )
    db.add(f)
    db.flush()
    sincronizar_vinculos_empresas(db, f, escopo="selected", rede_id=rede.id, empresa_ids=[empresa.id])


def converter_pos_assinatura(db: Session, contrato: Contrato, linha: CrmNegociacaoCnpjLinha, ator: Atendente) -> None:
    """Cria ou vincula Rede + Empresa a partir do snapshot da linha (#357). Sem PDVs."""
    if contrato.empresa_id and linha.empresa_id:
        return
    neg = linha.negociacao or crm_svc.obter_negociacao(db, linha.negociacao_id)
    nome_base = (neg.nome_base_webposto or "").strip()
    if not nome_base:
        raise HTTPException(
            status_code=400,
            detail="Informe o nome da base WebPosto na negociação para criar a Rede.",
        )
    cnpj_digits = _digits(linha.cnpj)
    if not cnpj_digits:
        raise HTTPException(status_code=400, detail="A linha precisa de CNPJ para criar a Empresa.")
    tenant_id = ator.tenant_id
    fiscal = _fiscal_dict(linha)
    snap = contrato.snapshot_comercial if isinstance(contrato.snapshot_comercial, dict) else {}
    if isinstance(snap.get("dados_fiscais"), dict):
        fiscal = {**fiscal, **{k: str(v).strip() for k, v in snap["dados_fiscais"].items() if v}}
    lead = neg.lead
    email_contato, telefone_contato = _contato_conversao(fiscal, lead)

    existente = None
    for emp in db.query(Empresa).filter(Empresa.tenant_id == tenant_id).all():
        if _digits(emp.cnpj_cpf) == cnpj_digits:
            existente = emp
            break
    if existente:
        # CNPJ já cadastrado: vincula a Empresa existente e o contacto na Rede dela
        # (não forçar a Rede do nome_base_webposto se for outra).
        _aplicar_contato_empresa(existente, email_contato, telefone_contato)
        contrato.empresa_id = existente.id
        linha.empresa_id = existente.id
        rede_emp = db.query(Rede).filter(Rede.id == existente.rede_id).first()
        if rede_emp is None:
            raise HTTPException(
                status_code=400,
                detail="A Empresa deste CNPJ não tem Rede válida no cadastro.",
            )
        try:
            _vincular_contato_chat(db, existente, rede_emp, fiscal, lead)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        db.flush()
        return

    rede = (
        db.query(Rede)
        .filter(Rede.tenant_id == tenant_id, func.lower(Rede.nome) == nome_base.lower())
        .order_by(Rede.id.asc())
        .first()
    )
    if not rede:
        rede = Rede(tenant_id=tenant_id, nome=nome_base, ativo=True)
        db.add(rede)
        db.flush()

    nome_emp = fiscal.get("nome") or fiscal.get("nome_fantasia") or (linha.razao_social or "").strip() or nome_base
    empresa = Empresa(
        tenant_id=tenant_id,
        rede_id=rede.id,
        nome=nome_emp[:255],
        cnpj_cpf=proposta_svc._formatar_cnpj(cnpj_digits) if len(cnpj_digits) == 14 else cnpj_digits,
        razao_social=(linha.razao_social or "").strip() or None,
        nome_fantasia=fiscal.get("nome_fantasia") or None,
        inscricao_estadual=fiscal.get("inscricao_estadual") or None,
        endereco=fiscal.get("endereco") or None,
        numero=fiscal.get("numero") or None,
        complemento=fiscal.get("complemento") or None,
        bairro=fiscal.get("bairro") or None,
        cidade=fiscal.get("cidade") or None,
        estado=(fiscal.get("estado") or "")[:2] or None,
        cep=fiscal.get("cep") or None,
        email=email_contato,
        telefone=telefone_contato,
        resp_legal_nome=fiscal.get("resp_legal_nome") or None,
        resp_legal_cpf=fiscal.get("resp_legal_cpf") or None,
        resp_legal_rg=fiscal.get("resp_legal_rg") or None,
        resp_legal_orgao_emissor=fiscal.get("resp_legal_orgao_emissor") or None,
        resp_legal_nacionalidade=fiscal.get("resp_legal_nacionalidade") or None,
        resp_legal_estado_civil=fiscal.get("resp_legal_estado_civil") or None,
        resp_legal_cargo=fiscal.get("resp_legal_cargo") or None,
        resp_legal_email=fiscal.get("resp_legal_email") or None,
        resp_legal_telefone=fiscal.get("resp_legal_telefone") or None,
        resp_legal_endereco=fiscal.get("resp_legal_endereco") or None,
        resp_legal_numero=fiscal.get("resp_legal_numero") or None,
        resp_legal_complemento=fiscal.get("resp_legal_complemento") or None,
        resp_legal_bairro=fiscal.get("resp_legal_bairro") or None,
        resp_legal_cidade=fiscal.get("resp_legal_cidade") or None,
        resp_legal_estado=(fiscal.get("resp_legal_estado") or "")[:2] or None,
        resp_legal_cep=fiscal.get("resp_legal_cep") or None,
        ativo=True,
    )
    db.add(empresa)
    db.flush()
    contrato.empresa_id = empresa.id
    linha.empresa_id = empresa.id
    try:
        _vincular_contato_chat(db, empresa, rede, fiscal, lead)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.flush()

