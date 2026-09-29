"""Serviço CRM — funil, leads e negociações (#322 / #336–#340)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_, update
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.models.crm import (
    ATIVIDADE_LIGACAO,
    ATIVIDADE_MUDANCA_ESTAGIO,
    ATIVIDADE_NOTA,
    ATIVIDADE_REUNIAO,
    ATIVIDADE_TIPOS,
    FUNIL_SEED,
    FUNIL_TIPOS,
    FUNIL_TIPO_PERDIDO,
    SLUG_DOCUMENTACAO,
    CrmLead,
    CrmNegociacao,
    CrmNegociacaoAtividade,
    CrmNegociacaoCnpjLinha,
    FunilEstagio,
)
from app.schemas.comercial_custo import CustoTefOverride
from app.schemas.crm import (
    CrmAtividadeCreate,
    CrmAtividadeRead,
    CrmAtividadeUpdate,
    CrmLeadCreate,
    CrmLeadUpdate,
    CrmLinhaCreate,
    CrmLinhaUpdate,
    CrmNegociacaoCreate,
    CrmNegociacaoUpdate,
    FunilEstagioCreate,
    FunilEstagioUpdate,
)
from app.services import comercial_custo as custo_svc

# O autor edita a própria nota até 5 minutos depois de salvar (#1098).
NOTA_EDICAO = timedelta(minutes=5)
# Sem confirmação do autor, outro aviso só depois desta folga (evita rajada entre workers).
LEMBRETE_RETRY = timedelta(minutes=2)
TIPOS_NOTA_EDITAVEIS = frozenset({ATIVIDADE_NOTA, ATIVIDADE_LIGACAO, ATIVIDADE_REUNIAO})


def ensure_funil_padrao(db: Session) -> None:
    """Garante estágios do funil (migration ou create_all em testes)."""
    if db.query(FunilEstagio).count() > 0:
        return
    for slug, nome, ordem, tipo in FUNIL_SEED:
        db.add(FunilEstagio(slug=slug, nome=nome, ordem=ordem, tipo=tipo, ativo=True))
    db.flush()


def obter_estagio(
    db: Session,
    *,
    estagio_id: int | None = None,
    slug: str | None = None,
    apenas_ativos: bool = True,
) -> FunilEstagio:
    ensure_funil_padrao(db)
    q = db.query(FunilEstagio)
    if apenas_ativos:
        q = q.filter(FunilEstagio.ativo.is_(True))
    if estagio_id is not None:
        row = q.filter(FunilEstagio.id == estagio_id).first()
    elif slug:
        row = q.filter(FunilEstagio.slug == slug).first()
    else:
        raise HTTPException(status_code=400, detail="Informe estagio_id ou estagio_slug.")
    if not row:
        raise HTTPException(status_code=404, detail="Estágio do funil não encontrado.")
    return row


def estagio_inicial(db: Session) -> FunilEstagio:
    ensure_funil_padrao(db)
    row = (
        db.query(FunilEstagio)
        .filter(FunilEstagio.ativo.is_(True), FunilEstagio.tipo != FUNIL_TIPO_PERDIDO)
        .order_by(FunilEstagio.ordem.asc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=500, detail="Funil sem estágios ativos.")
    return row


def listar_estagios(db: Session, *, incluir_inativos: bool = False) -> list[FunilEstagio]:
    ensure_funil_padrao(db)
    q = db.query(FunilEstagio)
    if not incluir_inativos:
        q = q.filter(FunilEstagio.ativo.is_(True))
    return q.order_by(FunilEstagio.ordem.asc(), FunilEstagio.id.asc()).all()


def criar_estagio(db: Session, data: FunilEstagioCreate) -> FunilEstagio:
    ensure_funil_padrao(db)
    tipo = (data.tipo or "").strip().lower()
    if tipo not in FUNIL_TIPOS:
        raise HTTPException(status_code=400, detail=f"tipo inválido: use {', '.join(sorted(FUNIL_TIPOS))}")
    slug = data.slug.strip().lower().replace(" ", "_")
    if db.query(FunilEstagio).filter(FunilEstagio.slug == slug).first():
        raise HTTPException(status_code=400, detail="Já existe estágio com este slug.")
    row = FunilEstagio(slug=slug, nome=data.nome.strip(), ordem=data.ordem, tipo=tipo, ativo=data.ativo)
    db.add(row)
    db.flush()
    return row


def atualizar_estagio(db: Session, row: FunilEstagio, data: FunilEstagioUpdate) -> FunilEstagio:
    payload = data.model_dump(exclude_unset=True)
    if "tipo" in payload:
        tipo = str(payload["tipo"]).strip().lower()
        if tipo not in FUNIL_TIPOS:
            raise HTTPException(status_code=400, detail=f"tipo inválido: use {', '.join(sorted(FUNIL_TIPOS))}")
        payload["tipo"] = tipo
    if "nome" in payload and payload["nome"] is not None:
        payload["nome"] = str(payload["nome"]).strip()
    for k, v in payload.items():
        setattr(row, k, v)
    db.flush()
    return row


def _estagio_exige_cnpj(db: Session, estagio: FunilEstagio) -> bool:
    """CNPJ obrigatório a partir de Documentação (#322)."""
    ensure_funil_padrao(db)
    doc = db.query(FunilEstagio).filter(FunilEstagio.slug == SLUG_DOCUMENTACAO).first()
    if not doc:
        return estagio.slug == SLUG_DOCUMENTACAO
    return estagio.ordem >= doc.ordem and estagio.tipo != FUNIL_TIPO_PERDIDO


def _validar_transicao(origem: FunilEstagio, destino: FunilEstagio) -> None:
    if origem.id == destino.id:
        raise HTTPException(status_code=400, detail="Negociação já está neste estágio.")
    if not destino.ativo:
        raise HTTPException(status_code=400, detail="Estágio de destino inativo.")
    # Grafo simples: qualquer estágio ativo → outro ativo (reabrir perdido permitido)
    # Bloqueio: não saltar de aberto para implantacao sem passar contrato? — v1 permissivo por ordem livre.


def _negociacao_ativa_do_lead(db: Session, lead_id: int) -> CrmNegociacao | None:
    return (
        db.query(CrmNegociacao)
        .filter(CrmNegociacao.lead_id == lead_id, CrmNegociacao.ativa.is_(True))
        .first()
    )


def _tef_override_dict(ov: CustoTefOverride | None) -> dict | None:
    if ov is None:
        return None
    return {k: str(v) if v is not None else None for k, v in ov.model_dump().items()}


def _tef_from_json(raw: dict | None) -> CustoTefOverride | None:
    if not raw:
        return None
    cleaned = {k: v for k, v in raw.items() if v is not None}
    if not cleaned:
        return None
    return CustoTefOverride(**cleaned)


def recalcular_linha(db: Session, linha: CrmNegociacaoCnpjLinha) -> None:
    """Atualiza snapshot_custo, total_custo e margem (#338)."""
    ids = list(linha.item_ids or [])
    if not ids:
        linha.snapshot_custo = None
        linha.total_custo = Decimal("0.00")
        linha.margem_calculada = Decimal(linha.valor_negociado or 0)
        return
    ov = _tef_from_json(linha.tef_override if isinstance(linha.tef_override, dict) else None)
    result = custo_svc.calcular_custo_pacote(
        db,
        item_ids=ids,
        quantidade_pdvs=int(linha.quantidade_pdvs or 1),
        desconto_posto_100k=bool(linha.desconto_posto_100k),
        tef_override=ov,
    )
    linha.snapshot_custo = result.snapshot
    linha.total_custo = result.total_custo
    linha.margem_calculada = (Decimal(linha.valor_negociado or 0) - Decimal(result.total_custo)).quantize(
        Decimal("0.01")
    )


def _validar_cnpjs_obrigatorios(db: Session, negociacao: CrmNegociacao, estagio: FunilEstagio) -> None:
    if not _estagio_exige_cnpj(db, estagio):
        return
    linhas = (
        db.query(CrmNegociacaoCnpjLinha).filter(CrmNegociacaoCnpjLinha.negociacao_id == negociacao.id).all()
    )
    if not linhas:
        raise HTTPException(
            status_code=400,
            detail="A partir de Documentação é obrigatório ter ao menos uma linha com CNPJ.",
        )
    for ln in linhas:
        if not ln.cnpj or len("".join(c for c in str(ln.cnpj) if c.isdigit())) != 14:
            raise HTTPException(
                status_code=400,
                detail="CNPJ obrigatório em todas as linhas a partir do estágio Documentação.",
            )


def _assert_responsavel_comercial(db: Session, responsavel_id: int) -> Atendente:
    a = db.query(Atendente).filter(Atendente.id == responsavel_id, Atendente.ativo.is_(True)).first()
    if not a:
        raise HTTPException(status_code=400, detail="Responsável não encontrado ou inativo.")
    if a.role not in ("admin", "comercial"):
        raise HTTPException(status_code=400, detail="Responsável deve ter perfil comercial ou admin.")
    return a


def lead_to_read(db: Session, lead: CrmLead) -> dict:
    est = lead.estagio
    neg = _negociacao_ativa_do_lead(db, lead.id)
    return {
        "id": lead.id,
        "nome": lead.nome,
        "telefone": lead.telefone,
        "email": lead.email,
        "empresa_texto": lead.empresa_texto,
        "origem": lead.origem,
        "notas": lead.notas,
        "responsavel_id": lead.responsavel_id,
        "estagio_id": lead.estagio_id,
        "estagio_slug": est.slug if est else None,
        "estagio_nome": est.nome if est else None,
        "perdido_em": lead.perdido_em,
        "ativo": lead.ativo,
        "negociacao_ativa_id": neg.id if neg else None,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
    }


def negociacao_to_read(neg: CrmNegociacao) -> dict:
    est = neg.estagio
    linhas = sorted(neg.linhas or [], key=lambda x: (x.ordem, x.id))
    return {
        "id": neg.id,
        "lead_id": neg.lead_id,
        "responsavel_id": neg.responsavel_id,
        "estagio_id": neg.estagio_id,
        "estagio_slug": est.slug if est else None,
        "estagio_nome": est.nome if est else None,
        "ativa": neg.ativa,
        "titulo": neg.titulo,
        "nome_base_webposto": neg.nome_base_webposto,
        "linhas": linhas,
        "created_at": neg.created_at,
        "updated_at": neg.updated_at,
    }


def listar_leads(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    q: str | None = None,
    responsavel_id: int | None = None,
    estagio_id: int | None = None,
    so_minhas: bool = False,
    ator_id: int | None = None,
    ativo: bool | None = True,
) -> tuple[list[CrmLead], int]:
    ensure_funil_padrao(db)
    query = db.query(CrmLead).options(joinedload(CrmLead.estagio))
    if ativo is not None:
        query = query.filter(CrmLead.ativo.is_(ativo))
    if so_minhas and ator_id is not None:
        query = query.filter(CrmLead.responsavel_id == ator_id)
    elif responsavel_id is not None:
        query = query.filter(CrmLead.responsavel_id == responsavel_id)
    if estagio_id is not None:
        query = query.filter(CrmLead.estagio_id == estagio_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                CrmLead.nome.ilike(term),
                CrmLead.telefone.ilike(term),
                CrmLead.email.ilike(term),
                CrmLead.empresa_texto.ilike(term),
            )
        )
    total = query.count()
    rows = query.order_by(CrmLead.id.desc()).offset(offset).limit(limit).all()
    return rows, total


def criar_lead(db: Session, data: CrmLeadCreate, ator: Atendente) -> CrmLead:
    ensure_funil_padrao(db)
    responsavel_id = data.responsavel_id or ator.id
    _assert_responsavel_comercial(db, responsavel_id)
    est = estagio_inicial(db)
    lead = CrmLead(
        nome=data.nome.strip(),
        telefone=(data.telefone or None),
        email=(data.email or None),
        empresa_texto=(data.empresa_texto or None),
        origem=(data.origem or None),
        notas=data.notas,
        responsavel_id=responsavel_id,
        estagio_id=est.id,
        ativo=True,
    )
    db.add(lead)
    db.flush()
    if data.criar_negociacao:
        neg = CrmNegociacao(
            lead_id=lead.id,
            responsavel_id=responsavel_id,
            estagio_id=est.id,
            ativa=True,
            titulo=data.titulo_negociacao or f"Negociação — {lead.nome}",
        )
        db.add(neg)
        db.flush()
        db.add(
            CrmNegociacaoAtividade(
                negociacao_id=neg.id,
                autor_id=ator.id,
                tipo=ATIVIDADE_MUDANCA_ESTAGIO,
                texto=f"Negociação criada no estágio «{est.nome}».",
            )
        )
    db.flush()
    return lead


def atualizar_lead(db: Session, lead: CrmLead, data: CrmLeadUpdate) -> CrmLead:
    payload = data.model_dump(exclude_unset=True)
    if "responsavel_id" in payload and payload["responsavel_id"] is not None:
        _assert_responsavel_comercial(db, payload["responsavel_id"])
    if "nome" in payload and payload["nome"]:
        payload["nome"] = str(payload["nome"]).strip()
    for k, v in payload.items():
        setattr(lead, k, v)
    db.flush()
    return lead


def obter_lead(db: Session, lead_id: int) -> CrmLead:
    lead = (
        db.query(CrmLead)
        .options(joinedload(CrmLead.estagio))
        .filter(CrmLead.id == lead_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    return lead


def listar_negociacoes(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    lead_id: int | None = None,
    responsavel_id: int | None = None,
    estagio_id: int | None = None,
    ativa: bool | None = True,
    q: str | None = None,
    so_minhas: bool = False,
    ator_id: int | None = None,
) -> tuple[list[CrmNegociacao], int]:
    ensure_funil_padrao(db)
    query = db.query(CrmNegociacao).options(
        joinedload(CrmNegociacao.estagio),
        joinedload(CrmNegociacao.linhas),
    )
    if lead_id is not None:
        query = query.filter(CrmNegociacao.lead_id == lead_id)
    if ativa is not None:
        query = query.filter(CrmNegociacao.ativa.is_(ativa))
    if so_minhas and ator_id is not None:
        query = query.filter(CrmNegociacao.responsavel_id == ator_id)
    elif responsavel_id is not None:
        query = query.filter(CrmNegociacao.responsavel_id == responsavel_id)
    if estagio_id is not None:
        query = query.filter(CrmNegociacao.estagio_id == estagio_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.outerjoin(CrmNegociacaoCnpjLinha).filter(
            or_(
                CrmNegociacao.titulo.ilike(term),
                CrmNegociacaoCnpjLinha.cnpj.ilike(term),
                CrmNegociacaoCnpjLinha.razao_social.ilike(term),
            )
        )
    total = query.distinct().count()
    rows = (
        query.distinct()
        .order_by(CrmNegociacao.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def obter_negociacao(db: Session, negociacao_id: int) -> CrmNegociacao:
    neg = (
        db.query(CrmNegociacao)
        .options(joinedload(CrmNegociacao.estagio), joinedload(CrmNegociacao.linhas))
        .filter(CrmNegociacao.id == negociacao_id)
        .first()
    )
    if not neg:
        raise HTTPException(status_code=404, detail="Negociação não encontrada.")
    return neg


def criar_negociacao(db: Session, data: CrmNegociacaoCreate, ator: Atendente) -> CrmNegociacao:
    lead = obter_lead(db, data.lead_id)
    if _negociacao_ativa_do_lead(db, lead.id):
        raise HTTPException(
            status_code=400,
            detail="Já existe uma negociação ativa para este lead. Encerre a atual antes de criar outra.",
        )
    responsavel_id = data.responsavel_id or lead.responsavel_id
    _assert_responsavel_comercial(db, responsavel_id)
    est = estagio_inicial(db)
    neg = CrmNegociacao(
        lead_id=lead.id,
        responsavel_id=responsavel_id,
        estagio_id=est.id,
        ativa=True,
        titulo=data.titulo or f"Negociação — {lead.nome}",
    )
    db.add(neg)
    db.flush()
    # Sincroniza estágio do lead com a nova negociação
    lead.estagio_id = est.id
    lead.perdido_em = None
    for ln_data in data.linhas:
        add_linha(db, neg, ln_data)
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=neg.id,
            autor_id=ator.id,
            tipo=ATIVIDADE_MUDANCA_ESTAGIO,
            texto=f"Negociação criada no estágio «{est.nome}».",
        )
    )
    db.flush()
    return obter_negociacao(db, neg.id)


def _linha_tem_contrato_assinado(db: Session, linha_id: int) -> bool:
    from app.models.comercial_contrato import CONTRATO_ASSINADO, Contrato

    return (
        db.query(Contrato.id)
        .filter(Contrato.negociacao_linha_cnpj_id == linha_id, Contrato.status == CONTRATO_ASSINADO)
        .first()
        is not None
    )


def _negociacao_tem_contrato_assinado(db: Session, negociacao_id: int) -> bool:
    from app.models.comercial_contrato import CONTRATO_ASSINADO, Contrato

    return (
        db.query(Contrato.id)
        .join(CrmNegociacaoCnpjLinha, Contrato.negociacao_linha_cnpj_id == CrmNegociacaoCnpjLinha.id)
        .filter(
            CrmNegociacaoCnpjLinha.negociacao_id == negociacao_id,
            Contrato.status == CONTRATO_ASSINADO,
        )
        .first()
        is not None
    )


def atualizar_negociacao(db: Session, neg: CrmNegociacao, data: CrmNegociacaoUpdate) -> CrmNegociacao:
    payload = data.model_dump(exclude_unset=True)
    if "nome_base_webposto" in payload:
        atual = (neg.nome_base_webposto or "").strip() or None
        raw = payload.get("nome_base_webposto")
        novo = str(raw).strip() or None if raw is not None else None
        if novo != atual and _negociacao_tem_contrato_assinado(db, neg.id):
            raise HTTPException(
                status_code=400,
                detail="O nome da Rede não pode ser alterado depois de um contrato assinado.",
            )
    if "responsavel_id" in payload and payload["responsavel_id"] is not None:
        _assert_responsavel_comercial(db, payload["responsavel_id"])
    for k, v in payload.items():
        setattr(neg, k, v)
    db.flush()
    return obter_negociacao(db, neg.id)


def add_linha(db: Session, neg: CrmNegociacao, data: CrmLinhaCreate) -> CrmNegociacaoCnpjLinha:
    est = obter_estagio(db, estagio_id=neg.estagio_id)
    if _estagio_exige_cnpj(db, est) and not data.cnpj:
        raise HTTPException(status_code=400, detail="CNPJ obrigatório neste estágio do funil.")
    linha = CrmNegociacaoCnpjLinha(
        negociacao_id=neg.id,
        cnpj=data.cnpj,
        razao_social=data.razao_social,
        dados_fiscais=(data.dados_fiscais.model_dump(exclude_none=True) if data.dados_fiscais else {}),
        item_ids=list(data.item_ids or []),
        quantidade_pdvs=data.quantidade_pdvs,
        desconto_posto_100k=data.desconto_posto_100k,
        tef_override=_tef_override_dict(data.tef_override),
        valor_negociado=data.valor_negociado,
        ordem=data.ordem,
    )
    db.add(linha)
    db.flush()
    recalcular_linha(db, linha)
    db.flush()
    return linha


def atualizar_linha(db: Session, linha: CrmNegociacaoCnpjLinha, data: CrmLinhaUpdate) -> CrmNegociacaoCnpjLinha:
    if _linha_tem_contrato_assinado(db, linha.id):
        raise HTTPException(
            status_code=400,
            detail="Esta linha tem contrato assinado. Pacote, valores e dados fiscais não podem ser alterados.",
        )
    neg = obter_negociacao(db, linha.negociacao_id)
    est = obter_estagio(db, estagio_id=neg.estagio_id)
    payload = data.model_dump(exclude_unset=True, exclude={"limpar_tef_override", "tef_override"})
    if "dados_fiscais" in payload and payload["dados_fiscais"] is not None:
        payload["dados_fiscais"] = (
            payload["dados_fiscais"]
            if isinstance(payload["dados_fiscais"], dict)
            else data.dados_fiscais.model_dump(exclude_none=True)
        )
    if data.limpar_tef_override:
        linha.tef_override = None
    elif data.tef_override is not None:
        linha.tef_override = _tef_override_dict(data.tef_override)
    for k, v in payload.items():
        setattr(linha, k, v)
    if _estagio_exige_cnpj(db, est) and not linha.cnpj:
        raise HTTPException(status_code=400, detail="CNPJ obrigatório neste estágio do funil.")
    recalcular_linha(db, linha)
    db.flush()
    return linha


def excluir_linha(db: Session, linha: CrmNegociacaoCnpjLinha) -> None:
    if _linha_tem_contrato_assinado(db, linha.id):
        raise HTTPException(
            status_code=400,
            detail="Não é possível remover uma linha com contrato assinado.",
        )
    neg = obter_negociacao(db, linha.negociacao_id)
    est = obter_estagio(db, estagio_id=neg.estagio_id)
    restantes = [
        r
        for r in db.query(CrmNegociacaoCnpjLinha)
        .filter(CrmNegociacaoCnpjLinha.negociacao_id == neg.id)
        .all()
        if r.id != linha.id
    ]
    if _estagio_exige_cnpj(db, est):
        if not restantes or any(not r.cnpj for r in restantes):
            raise HTTPException(
                status_code=400,
                detail="Não é possível remover: neste estágio todas as linhas precisam de CNPJ.",
            )
    db.delete(linha)
    db.flush()


def mover_estagio(
    db: Session,
    neg: CrmNegociacao,
    *,
    ator: Atendente,
    estagio_id: int | None = None,
    estagio_slug: str | None = None,
    nota: str | None = None,
) -> CrmNegociacao:
    origem = obter_estagio(db, estagio_id=neg.estagio_id)
    destino = obter_estagio(db, estagio_id=estagio_id, slug=estagio_slug)
    _validar_transicao(origem, destino)
    _validar_cnpjs_obrigatorios(db, neg, destino)

    neg.estagio_id = destino.id
    lead = obter_lead(db, neg.lead_id)
    lead.estagio_id = destino.id
    if destino.tipo == FUNIL_TIPO_PERDIDO:
        lead.perdido_em = datetime.now(timezone.utc)
        # Mantém histórico; soft-archive via perdido_em (lead continua ativo=True)
        neg.ativa = False
    else:
        lead.perdido_em = None
        if not neg.ativa:
            # Reabrir: só se não houver outra ativa
            outra = _negociacao_ativa_do_lead(db, lead.id)
            if outra and outra.id != neg.id:
                raise HTTPException(
                    status_code=400,
                    detail="Já existe outra negociação ativa neste lead.",
                )
            neg.ativa = True

    texto = f"Estágio: «{origem.nome}» → «{destino.nome}»."
    if nota:
        texto = f"{texto} {nota.strip()}"
    db.add(
        CrmNegociacaoAtividade(
            negociacao_id=neg.id,
            autor_id=ator.id,
            tipo=ATIVIDADE_MUDANCA_ESTAGIO,
            texto=texto,
        )
    )
    db.flush()
    return obter_negociacao(db, neg.id)


def _como_utc(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _validar_lembrete_futuro(quando: datetime) -> datetime:
    momento = _como_utc(quando)
    if momento <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="O lembrete precisa ser uma data e hora futuras.")
    return momento


def nota_pode_editar(row: CrmNegociacaoAtividade, ator: Atendente, *, agora: datetime | None = None) -> bool:
    if row.autor_id != ator.id or row.tipo not in TIPOS_NOTA_EDITAVEIS or row.created_at is None:
        return False
    agora = agora or datetime.now(timezone.utc)
    return agora - _como_utc(row.created_at) <= NOTA_EDICAO


def serializar_atividade(row: CrmNegociacaoAtividade, ator: Atendente) -> CrmAtividadeRead:
    autor = row.autor
    return CrmAtividadeRead(
        id=row.id,
        negociacao_id=row.negociacao_id,
        autor_id=row.autor_id,
        autor_nome=autor.nome if autor is not None else None,
        tipo=row.tipo,
        texto=row.texto,
        created_at=row.created_at,
        updated_at=row.updated_at,
        lembrete_em=row.lembrete_em,
        lembrete_disparado_em=row.lembrete_disparado_em,
        pode_editar=nota_pode_editar(row, ator),
    )


def listar_atividades(
    db: Session, negociacao_id: int, *, offset: int = 0, limit: int = 50
) -> tuple[list[CrmNegociacaoAtividade], int]:
    obter_negociacao(db, negociacao_id)
    filtro = CrmNegociacaoAtividade.negociacao_id == negociacao_id
    total = db.query(CrmNegociacaoAtividade).filter(filtro).count()
    rows = (
        db.query(CrmNegociacaoAtividade)
        .options(joinedload(CrmNegociacaoAtividade.autor))
        .filter(filtro)
        .order_by(CrmNegociacaoAtividade.created_at.desc(), CrmNegociacaoAtividade.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def criar_atividade(
    db: Session, negociacao_id: int, data: CrmAtividadeCreate, ator: Atendente
) -> CrmNegociacaoAtividade:
    obter_negociacao(db, negociacao_id)
    tipo = (data.tipo or "nota").strip().lower()
    if tipo not in ATIVIDADE_TIPOS:
        raise HTTPException(
            status_code=400,
            detail=f"tipo inválido: use {', '.join(sorted(ATIVIDADE_TIPOS))}",
        )
    if tipo == ATIVIDADE_MUDANCA_ESTAGIO:
        raise HTTPException(status_code=400, detail="Use POST .../mover-estagio para mudança de estágio.")
    lembrete = _validar_lembrete_futuro(data.lembrete_em) if data.lembrete_em is not None else None
    row = CrmNegociacaoAtividade(
        negociacao_id=negociacao_id,
        autor_id=ator.id,
        tipo=tipo,
        texto=data.texto.strip(),
        lembrete_em=lembrete,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def editar_atividade(
    db: Session,
    negociacao_id: int,
    atividade_id: int,
    data: CrmAtividadeUpdate,
    ator: Atendente,
) -> CrmNegociacaoAtividade:
    row = (
        db.query(CrmNegociacaoAtividade)
        .options(joinedload(CrmNegociacaoAtividade.autor))
        .filter(
            CrmNegociacaoAtividade.id == atividade_id,
            CrmNegociacaoAtividade.negociacao_id == negociacao_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada.")
    if row.tipo not in TIPOS_NOTA_EDITAVEIS:
        raise HTTPException(status_code=400, detail="Só é possível editar notas, ligações e reuniões.")
    if row.autor_id != ator.id:
        raise HTTPException(status_code=403, detail="Só o autor pode editar esta nota.")
    if not nota_pode_editar(row, ator):
        raise HTTPException(status_code=400, detail="O prazo de 5 minutos para editar esta nota já passou.")
    campos = data.model_fields_set
    if not campos:
        raise HTTPException(status_code=400, detail="Nada para atualizar.")
    if "texto" in campos:
        texto = (data.texto or "").strip()
        if not texto:
            raise HTTPException(status_code=400, detail="O texto da nota não pode ficar vazio.")
        row.texto = texto
    if "lembrete_em" in campos:
        if data.lembrete_em is None:
            row.lembrete_em = None
            row.lembrete_tentativa_em = None
            row.lembrete_disparado_em = None
        else:
            row.lembrete_em = _validar_lembrete_futuro(data.lembrete_em)
            row.lembrete_tentativa_em = None
            row.lembrete_disparado_em = None
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    db.refresh(row)
    return row


def _filtro_lembrete_vencido(agora: datetime):
    return (
        CrmNegociacaoAtividade.lembrete_em.isnot(None),
        CrmNegociacaoAtividade.lembrete_em <= agora,
        CrmNegociacaoAtividade.lembrete_disparado_em.is_(None),
    )


def _payload_lembrete(row: CrmNegociacaoAtividade) -> dict:
    lead = row.negociacao.lead if row.negociacao is not None else None
    texto = (row.texto or "").strip()
    if len(texto) > 140:
        texto = texto[:137] + "..."
    quando = row.lembrete_em
    return {
        "autor_id": row.autor_id,
        "atividade_id": row.id,
        "negociacao_id": row.negociacao_id,
        "texto": texto,
        "lead_nome": lead.nome if lead is not None else None,
        "lembrete_em": quando.isoformat() if quando is not None else None,
    }


def listar_lembretes_pendentes(db: Session, ator: Atendente, *, limit: int = 20) -> list[dict]:
    """Lembretes vencidos que o autor ainda não confirmou — o painel busca ao abrir."""
    agora = datetime.now(timezone.utc)
    rows = (
        db.query(CrmNegociacaoAtividade)
        .options(joinedload(CrmNegociacaoAtividade.negociacao).joinedload(CrmNegociacao.lead))
        .filter(
            CrmNegociacaoAtividade.autor_id == ator.id,
            *_filtro_lembrete_vencido(agora),
        )
        .order_by(CrmNegociacaoAtividade.lembrete_em.asc(), CrmNegociacaoAtividade.id.asc())
        .limit(limit)
        .all()
    )
    return [_payload_lembrete(row) for row in rows]


def confirmar_lembrete(db: Session, atividade_id: int, ator: Atendente) -> None:
    row = db.query(CrmNegociacaoAtividade).filter(CrmNegociacaoAtividade.id == atividade_id).first()
    if row is None or row.lembrete_em is None:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado.")
    if row.autor_id != ator.id:
        raise HTTPException(status_code=403, detail="Só o autor confirma este lembrete.")
    if row.lembrete_disparado_em is None:
        row.lembrete_disparado_em = datetime.now(timezone.utc)
        db.flush()


def reivindicar_lembretes_vencidos(db: Session, *, limit: int = 50) -> list[dict]:
    """Reserva o aviso com UPDATE condicional. Não marca como visto — isso é a confirmação do autor."""
    agora = datetime.now(timezone.utc)
    limite_retry = agora - LEMBRETE_RETRY
    candidatos = (
        db.query(CrmNegociacaoAtividade.id)
        .filter(
            *_filtro_lembrete_vencido(agora),
            or_(
                CrmNegociacaoAtividade.lembrete_tentativa_em.is_(None),
                CrmNegociacaoAtividade.lembrete_tentativa_em <= limite_retry,
            ),
        )
        .order_by(CrmNegociacaoAtividade.lembrete_em.asc(), CrmNegociacaoAtividade.id.asc())
        .limit(limit)
        .all()
    )
    reservados: list[int] = []
    for (atividade_id,) in candidatos:
        result = db.execute(
            update(CrmNegociacaoAtividade)
            .where(
                CrmNegociacaoAtividade.id == atividade_id,
                CrmNegociacaoAtividade.lembrete_disparado_em.is_(None),
                or_(
                    CrmNegociacaoAtividade.lembrete_tentativa_em.is_(None),
                    CrmNegociacaoAtividade.lembrete_tentativa_em <= limite_retry,
                ),
            )
            .values(lembrete_tentativa_em=agora)
            .execution_options(synchronize_session=False)
        )
        if (result.rowcount or 0) > 0:
            reservados.append(atividade_id)
    if not reservados:
        return []
    db.flush()
    db.expire_all()
    rows = (
        db.query(CrmNegociacaoAtividade)
        .options(joinedload(CrmNegociacaoAtividade.negociacao).joinedload(CrmNegociacao.lead))
        .filter(CrmNegociacaoAtividade.id.in_(reservados))
        .all()
    )
    return [_payload_lembrete(row) for row in rows]
