"""Timeline 360 e saúde do cliente da carteira (#912 / #914).

Não existe tabela de eventos no MVP: a timeline é **derivada** das tabelas já
existentes (CRM, proposta/contrato, implantação via checklist do ticket e
suporte via tickets/histórico). O vínculo empresa → jornada usa:

- `CrmNegociacaoCnpjLinha.empresa_id` (preenchido quando o contrato cadastra a
  empresa da linha, #324) → negociações, atividades, propostas e leads;
- `Contrato.empresa_id` (e o fallback pela linha do contrato) → marcos de contrato;
- `Ticket.empresa_id` → chamados de suporte e o ticket de implantação
  (`Ticket.contrato_id` preenchido).

Empresas sem linha de negociação vinculada aparecem apenas com os eventos de
ticket — a limitação é registrada no relatório do lote, sem inventar vínculo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Contrato,
    CrmLead,
    CrmNegociacao,
    CrmNegociacaoAtividade,
    CrmNegociacaoCnpjLinha,
    Empresa,
    Proposta,
    Ticket,
    TicketChecklistItem,
    TicketHistorico,
)
from app.schemas.operacao_timeline import (
    CategoriaEvento,
    EventoTimelineRead,
    SaudeEmpresaRead,
    SaudeStatus,
    SinalSaudeRead,
)

# ---------------------------------------------------------------------------
# Cortes do health (#914) — dias corridos, contados de «agora».
# Mantidos como constantes para o time conferir/ajustar sem caçar números no
# meio do código; a explicação de cada sinal repete o corte na resposta da API.
# ---------------------------------------------------------------------------

# Movimentação registrada (qualquer marco da timeline).
CONTATO_ATENCAO_DIAS = 30
CONTATO_RISCO_DIAS = 60

# Implantação aberta com item obrigatório pendente, sem movimento.
IMPLANTACAO_ATENCAO_DIAS = 15
IMPLANTACAO_RISCO_DIAS = 30

# Chamados abertos (fechado_em vazio) na empresa.
TICKETS_ABERTOS_ATENCAO = 5

# Reaberturas de chamado (TicketHistorico de fechado_em voltando a vazio).
REABERTURAS_JANELA_DIAS = 90
REABERTURAS_ATENCAO = 1
REABERTURAS_RISCO = 2

_CATEGORIA_VALORES = frozenset(c.value for c in CategoriaEvento)

_NIVEL_ORDEM = {"info": 0, "saudavel": 1, "atencao": 2, "risco": 3}

_TIPO_ATIVIDADE_EVENTO: dict[str, tuple[str, str]] = {
    "mudanca_estagio": ("negociacao_mudanca_estagio", "Mudança de etapa no CRM"),
    "documento_anexado": ("negociacao_documento", "Documento anexado ao negócio"),
    "nota": ("negociacao_nota", "Nota registrada"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _aware(valor: datetime | None) -> datetime | None:
    """Normaliza datas do banco (SQLite devolve naive) para UTC aware."""
    if valor is None:
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _dias_desde(momento: datetime | None, agora: datetime) -> int | None:
    normal = _aware(momento)
    if normal is None:
        return None
    return max(0, (agora - normal).days)


def _fmt_data(momento: datetime | None) -> str:
    normal = _aware(momento)
    return normal.strftime("%d/%m/%Y") if normal else "—"


def _moeda(valor: object) -> str:
    try:
        numero = Decimal(valor)  # type: ignore[arg-type]
    except (InvalidOperation, TypeError, ValueError):
        return "—"
    texto = f"{numero:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _corta(texto: str | None, limite: int = 280) -> str | None:
    if texto is None:
        return None
    limpo = " ".join(str(texto).split())
    if not limpo:
        return None
    return limpo if len(limpo) <= limite else f"{limpo[: limite - 1].rstrip()}…"


def _nome_negocio(neg: CrmNegociacao) -> str:
    lead_nome = neg.lead.nome if neg.lead is not None else None
    return neg.titulo or lead_nome or f"Negociação #{neg.id}"


def _empresa_da_carteira(db: Session, empresa_id: int, tenant_id: int) -> Empresa:
    empresa = (
        db.query(Empresa)
        .options(joinedload(Empresa.rede))
        .filter(Empresa.id == empresa_id, Empresa.tenant_id == tenant_id)
        .first()
    )
    if empresa is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return empresa


# ---------------------------------------------------------------------------
# Vínculos empresa → jornada
# ---------------------------------------------------------------------------


def _linhas_da_empresa(db: Session, empresa_id: int) -> list[CrmNegociacaoCnpjLinha]:
    return (
        db.query(CrmNegociacaoCnpjLinha)
        .filter(CrmNegociacaoCnpjLinha.empresa_id == empresa_id)
        .order_by(CrmNegociacaoCnpjLinha.id.asc())
        .all()
    )


def _negociacao_ids(linhas: list[CrmNegociacaoCnpjLinha]) -> list[int]:
    return sorted({ln.negociacao_id for ln in linhas if ln.negociacao_id is not None})


def _contratos_da_empresa(db: Session, empresa_id: int, linha_ids: list[int]) -> list[Contrato]:
    filtros = [Contrato.empresa_id == empresa_id]
    if linha_ids:
        filtros.append(Contrato.negociacao_linha_cnpj_id.in_(linha_ids))
    return (
        db.query(Contrato)
        .filter(or_(*filtros))
        .order_by(Contrato.id.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Coleta de eventos
# ---------------------------------------------------------------------------


def _eventos_crm(
    db: Session,
    neg_ids: list[int],
) -> list[EventoTimelineRead]:
    if not neg_ids:
        return []

    eventos: list[EventoTimelineRead] = []

    negociacoes = (
        db.query(CrmNegociacao)
        .options(joinedload(CrmNegociacao.lead))
        .filter(CrmNegociacao.id.in_(neg_ids))
        .all()
    )
    negociacoes_por_id = {neg.id: neg for neg in negociacoes}

    for neg in negociacoes:
        if neg.lead is None:
            continue
        lead: CrmLead = neg.lead
        detalhe = f"Origem: {lead.origem}." if lead.origem else "Novo contato no CRM."
        eventos.append(
            EventoTimelineRead(
                id=f"lead_criado-{lead.id}",
                em=_aware(lead.created_at) or _aware(neg.created_at) or _agora(),
                categoria=CategoriaEvento.crm,
                tipo="lead_criado",
                titulo=f"Lead «{lead.nome}» criado",
                detalhe=detalhe,
                ref_tipo="crm_negociacao",
                ref_id=neg.id,
            )
        )

    atividades = (
        db.query(CrmNegociacaoAtividade)
        .filter(CrmNegociacaoAtividade.negociacao_id.in_(neg_ids))
        .order_by(CrmNegociacaoAtividade.id.asc())
        .all()
    )
    for atividade in atividades:
        mapa = _TIPO_ATIVIDADE_EVENTO.get((atividade.tipo or "").strip().lower())
        if mapa is None:
            continue
        tipo_evento, titulo_base = mapa
        neg = negociacoes_por_id.get(atividade.negociacao_id)
        nome = _nome_negocio(neg) if neg is not None else f"negociação #{atividade.negociacao_id}"
        eventos.append(
            EventoTimelineRead(
                id=f"crm_atividade-{atividade.id}",
                em=_aware(atividade.created_at) or _agora(),
                categoria=CategoriaEvento.crm,
                tipo=tipo_evento,
                titulo=f"{titulo_base} — {nome}",
                detalhe=_corta(atividade.texto),
                ref_tipo="crm_negociacao",
                ref_id=atividade.negociacao_id,
            )
        )

    propostas = (
        db.query(Proposta)
        .filter(Proposta.negociacao_id.in_(neg_ids))
        .order_by(Proposta.id.asc())
        .all()
    )
    for proposta in propostas:
        neg = negociacoes_por_id.get(proposta.negociacao_id)
        nome = _nome_negocio(neg) if neg is not None else f"negociação #{proposta.negociacao_id}"
        eventos.append(
            EventoTimelineRead(
                id=f"proposta_gerada-{proposta.id}",
                em=_aware(proposta.created_at) or _agora(),
                categoria=CategoriaEvento.crm,
                tipo="proposta_gerada",
                titulo=f"Proposta gerada — {nome}",
                detalhe=None,
                ref_tipo="comercial_proposta",
                ref_id=proposta.id,
            )
        )
        enviado_em = _aware(proposta.enviado_em)
        if enviado_em is not None:
            canal = f"Canal: {proposta.canal}." if proposta.canal else None
            eventos.append(
                EventoTimelineRead(
                    id=f"proposta_enviada-{proposta.id}",
                    em=enviado_em,
                    categoria=CategoriaEvento.crm,
                    tipo="proposta_enviada",
                    titulo=f"Proposta enviada — {nome}",
                    detalhe=canal,
                    ref_tipo="comercial_proposta",
                    ref_id=proposta.id,
                )
            )

    return eventos


def _eventos_contrato(contratos: list[Contrato]) -> list[EventoTimelineRead]:
    eventos: list[EventoTimelineRead] = []
    for contrato in contratos:
        detalhe_criacao = f"Mensalidade {_moeda(contrato.valor_mensalidade)}."
        eventos.append(
            EventoTimelineRead(
                id=f"contrato_gerado-{contrato.id}",
                em=_aware(contrato.created_at) or _agora(),
                categoria=CategoriaEvento.crm,
                tipo="contrato_gerado",
                titulo=f"Contrato #{contrato.id} gerado",
                detalhe=detalhe_criacao,
                ref_tipo="comercial_contrato",
                ref_id=contrato.id,
            )
        )
        enviado_em = _aware(contrato.enviado_em)
        if enviado_em is not None:
            eventos.append(
                EventoTimelineRead(
                    id=f"contrato_enviado-{contrato.id}",
                    em=enviado_em,
                    categoria=CategoriaEvento.crm,
                    tipo="contrato_enviado",
                    titulo=f"Contrato #{contrato.id} enviado ao cliente",
                    detalhe=None,
                    ref_tipo="comercial_contrato",
                    ref_id=contrato.id,
                )
            )
        assinado_em = _aware(contrato.assinado_em)
        if assinado_em is not None:
            eventos.append(
                EventoTimelineRead(
                    id=f"contrato_assinado-{contrato.id}",
                    em=assinado_em,
                    categoria=CategoriaEvento.crm,
                    tipo="contrato_assinado",
                    titulo=f"Contrato #{contrato.id} assinado",
                    detalhe="Cliente liberado para implantação.",
                    ref_tipo="comercial_contrato",
                    ref_id=contrato.id,
                )
            )
        if (contrato.status or "").lower() == "cancelado":
            # Não existe coluna `cancelado_em`: o evento usa a última atualização
            # do contrato e o detalhe deixa isso explícito (sem data inventada).
            eventos.append(
                EventoTimelineRead(
                    id=f"contrato_cancelado-{contrato.id}",
                    em=_aware(contrato.updated_at) or _aware(contrato.created_at) or _agora(),
                    categoria=CategoriaEvento.crm,
                    tipo="contrato_cancelado",
                    titulo=f"Contrato #{contrato.id} cancelado",
                    detalhe="Registro de cancelamento (data da última atualização do contrato).",
                    ref_tipo="comercial_contrato",
                    ref_id=contrato.id,
                )
            )
    return eventos


def _categoria_ticket(ticket: Ticket) -> CategoriaEvento:
    """Ticket aberto pelo contrato é o ticket de implantação; o resto é suporte."""
    return CategoriaEvento.implantacao if ticket.contrato_id else CategoriaEvento.suporte


def _eventos_suporte(
    db: Session,
    empresa_id: int,
    tenant_id: int,
) -> list[EventoTimelineRead]:
    tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.checklist_itens))
        .filter(Ticket.tenant_id == tenant_id, Ticket.empresa_id == empresa_id)
        .order_by(Ticket.id.asc())
        .all()
    )
    if not tickets:
        return []

    eventos: list[EventoTimelineRead] = []
    for ticket in tickets:
        categoria = _categoria_ticket(ticket)
        rotulo = "Ticket de implantação" if categoria is CategoriaEvento.implantacao else "Chamado"
        referencia = f"{ticket.protocolo} · {ticket.assunto}"
        eventos.append(
            EventoTimelineRead(
                id=f"ticket_criado-{ticket.id}",
                em=_aware(ticket.created_at) or _agora(),
                categoria=categoria,
                tipo="ticket_criado",
                titulo=f"{rotulo} aberto",
                detalhe=_corta(referencia),
                ref_tipo="ticket",
                ref_id=ticket.id,
            )
        )
        fechado_em = _aware(ticket.fechado_em)
        if fechado_em is not None:
            eventos.append(
                EventoTimelineRead(
                    id=f"ticket_fechado-{ticket.id}",
                    em=fechado_em,
                    categoria=categoria,
                    tipo="ticket_fechado",
                    titulo=f"{rotulo} fechado",
                    detalhe=_corta(referencia),
                    ref_tipo="ticket",
                    ref_id=ticket.id,
                )
            )

        for item in ticket.checklist_itens:
            concluido_em = _aware(item.concluido_em)
            if not item.concluido or concluido_em is None:
                continue
            eventos.append(
                EventoTimelineRead(
                    id=f"checklist_item-{item.id}",
                    em=concluido_em,
                    categoria=CategoriaEvento.implantacao,
                    tipo="implantacao_item_concluido",
                    titulo=f"Checklist de implantação: «{item.titulo}» concluído",
                    detalhe=_corta(f"Ticket {ticket.protocolo}"),
                    ref_tipo="ticket",
                    ref_id=ticket.id,
                )
            )

    ticket_ids = [t.id for t in tickets]
    reaberturas = (
        db.query(TicketHistorico)
        .filter(
            TicketHistorico.ticket_id.in_(ticket_ids),
            TicketHistorico.campo == "fechado_em",
        )
        .order_by(TicketHistorico.id.asc())
        .all()
    )
    tickets_por_id = {t.id: t for t in tickets}
    for historico in reaberturas:
        # `reabrir` registra fechado_em -> "" (ver app/api/tickets.py).
        if (historico.valor_novo or "").strip():
            continue
        if not (historico.valor_antigo or "").strip():
            continue
        ticket = tickets_por_id.get(historico.ticket_id)
        if ticket is None:
            continue
        categoria = _categoria_ticket(ticket)
        eventos.append(
            EventoTimelineRead(
                id=f"ticket_reaberto-{historico.id}",
                em=_aware(historico.created_at) or _agora(),
                categoria=categoria,
                tipo="ticket_reaberto",
                titulo=f"{'Ticket de implantação' if categoria is CategoriaEvento.implantacao else 'Chamado'} reaberto",
                detalhe=_corta(f"{ticket.protocolo} · {ticket.assunto}"),
                ref_tipo="ticket",
                ref_id=ticket.id,
            )
        )
    return eventos


def coletar_eventos(
    db: Session,
    empresa_id: int,
    tenant_id: int,
    *,
    categorias: list[str] | None = None,
) -> list[EventoTimelineRead]:
    """Eventos derivados da empresa, com as fontes filtradas por categoria.

    Sem `categorias` devolve tudo. Com filtro, só consulta as fontes que podem
    gerar aquelas categorias (evita carregar ticket/checklist quando a tela
    pede só CRM). O filtro por período continua no nível da timeline — o
    volume de eventos por cliente ainda é modesto; se crescer, paginar no SQL.
    """
    cats = set(categorias or [])
    quer_suporte = not cats or CategoriaEvento.suporte.value in cats or CategoriaEvento.implantacao.value in cats
    quer_crm = not cats or CategoriaEvento.crm.value in cats

    eventos: list[EventoTimelineRead] = []
    if quer_crm:
        linhas = _linhas_da_empresa(db, empresa_id)
        neg_ids = _negociacao_ids(linhas)
        contratos = _contratos_da_empresa(db, empresa_id, [ln.id for ln in linhas])
        eventos.extend(_eventos_crm(db, neg_ids))
        eventos.extend(_eventos_contrato(contratos))
    if quer_suporte:
        eventos.extend(_eventos_suporte(db, empresa_id, tenant_id))

    # Deduplicação por id estável (tipo + origem) e ordem cronológica.
    vistos: set[str] = set()
    unicos: list[EventoTimelineRead] = []
    for evento in eventos:
        if evento.id in vistos:
            continue
        vistos.add(evento.id)
        unicos.append(evento)
    unicos.sort(key=lambda e: (_aware(e.em), e.id))
    return unicos


# ---------------------------------------------------------------------------
# Timeline paginada
# ---------------------------------------------------------------------------


def normalizar_categorias(categorias: list[str] | None) -> list[str] | None:
    """Aceita `?categorias=crm&categorias=suporte` e `?categorias=crm,suporte`."""
    if not categorias:
        return None
    valores: list[str] = []
    for bruto in categorias:
        for parte in str(bruto).split(","):
            valor = parte.strip().lower()
            if not valor:
                continue
            if valor not in _CATEGORIA_VALORES:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Categoria inválida: {valor!r}. "
                        f"Use {', '.join(sorted(_CATEGORIA_VALORES))}."
                    ),
                )
            if valor not in valores:
                valores.append(valor)
    return valores or None


def timeline_empresa(
    db: Session,
    *,
    empresa_id: int,
    tenant_id: int,
    categorias: list[str] | None = None,
    de: datetime | None = None,
    ate: datetime | None = None,
    ordem: str = "desc",
    offset: int = 0,
    limit: int = 50,
) -> tuple[Empresa, list[EventoTimelineRead], int]:
    empresa = _empresa_da_carteira(db, empresa_id, tenant_id)
    # Filtro de categoria também na coleta: evita consultar ticket quando a tela
    # pede só CRM (e vice-versa). O filtro abaixo mantém o contrato da API.
    eventos = coletar_eventos(db, empresa.id, tenant_id, categorias=categorias)

    if categorias:
        permitidas = set(categorias)
        eventos = [e for e in eventos if e.categoria.value in permitidas]
    de_norm = _aware(de)
    if de_norm is not None:
        eventos = [e for e in eventos if (_aware(e.em) or de_norm) >= de_norm]
    ate_norm = _aware(ate)
    if ate_norm is not None:
        eventos = [e for e in eventos if (_aware(e.em) or ate_norm) <= ate_norm]

    decrescente = (ordem or "desc").lower() != "asc"
    eventos.sort(key=lambda e: (_aware(e.em), e.id), reverse=decrescente)
    total = len(eventos)
    pagina = eventos[offset : offset + limit]
    return empresa, pagina, total


# ---------------------------------------------------------------------------
# Saúde do cliente (#914)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Sinal:
    codigo: str
    rotulo: str
    valor: str
    nivel: str
    explicacao: str | None = None


def _sinal(codigo: str, rotulo: str, valor: str, nivel: str, explicacao: str | None = None) -> _Sinal:
    return _Sinal(codigo=codigo, rotulo=rotulo, valor=valor, nivel=nivel, explicacao=explicacao)


def _nivel_por_dias(dias: int, atencao: int, risco: int) -> str:
    if dias >= risco:
        return "risco"
    if dias >= atencao:
        return "atencao"
    return "saudavel"


def _sinais_saude(
    db: Session,
    empresa: Empresa,
    tenant_id: int,
    eventos: list[EventoTimelineRead],
    agora: datetime,
) -> tuple[list[_Sinal], datetime | None, int | None]:
    sinais: list[_Sinal] = []

    ultimo_evento = max((_aware(e.em) for e in eventos if _aware(e.em) is not None), default=None)
    dias_sem_movimento = _dias_desde(ultimo_evento, agora)

    if ultimo_evento is None:
        sinais.append(
            _sinal(
                "sem_historico",
                "Histórico operacional",
                "Nenhum marco registrado",
                "atencao",
                "Não há eventos de CRM, implantação ou suporte deriváveis para este cliente.",
            )
        )
    else:
        nivel = _nivel_por_dias(dias_sem_movimento or 0, CONTATO_ATENCAO_DIAS, CONTATO_RISCO_DIAS)
        sinais.append(
            _sinal(
                "dias_sem_movimento",
                "Dias desde a última movimentação",
                f"{dias_sem_movimento} dia(s)",
                nivel,
                (
                    f"Último marco em {_fmt_data(ultimo_evento)}. "
                    f"Cortes: atenção ≥{CONTATO_ATENCAO_DIAS} dias, risco ≥{CONTATO_RISCO_DIAS} dias."
                ),
            )
        )

    # Tickets da empresa: abertos, reaberturas e implantação parada.
    tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.checklist_itens))
        .filter(Ticket.tenant_id == tenant_id, Ticket.empresa_id == empresa.id)
        .all()
    )
    tickets_abertos = [t for t in tickets if t.fechado_em is None]
    nivel_tickets = "atencao" if len(tickets_abertos) >= TICKETS_ABERTOS_ATENCAO else "saudavel"
    sinais.append(
        _sinal(
            "tickets_abertos",
            "Chamados abertos",
            f"{len(tickets_abertos)} em aberto",
            nivel_tickets,
            f"Chamados com fechado_em vazio. Corte: atenção ≥{TICKETS_ABERTOS_ATENCAO} abertos.",
        )
    )

    ticket_ids = [t.id for t in tickets]
    reaberturas_90d = 0
    if ticket_ids:
        desde = agora - timedelta(days=REABERTURAS_JANELA_DIAS)
        historicos = (
            db.query(TicketHistorico)
            .filter(
                TicketHistorico.ticket_id.in_(ticket_ids),
                TicketHistorico.campo == "fechado_em",
                TicketHistorico.created_at >= desde,
            )
            .all()
        )
        reaberturas_90d = sum(
            1
            for h in historicos
            if not (h.valor_novo or "").strip() and (h.valor_antigo or "").strip()
        )
    if reaberturas_90d >= REABERTURAS_RISCO:
        nivel_reabertura = "risco"
    elif reaberturas_90d >= REABERTURAS_ATENCAO:
        nivel_reabertura = "atencao"
    else:
        nivel_reabertura = "saudavel"
    sinais.append(
        _sinal(
            "reaberturas",
            "Reaberturas de chamados",
            f"{reaberturas_90d} nos últimos {REABERTURAS_JANELA_DIAS} dias",
            nivel_reabertura,
            (
                f"Reabertura = registro de fechado_em voltando a vazio. "
                f"Cortes: atenção ≥{REABERTURAS_ATENCAO}, risco ≥{REABERTURAS_RISCO}."
            ),
        )
    )

    implantacao_aberta = [t for t in tickets_abertos if t.contrato_id]
    if implantacao_aberta:
        pendencias = sum(
            1
            for ticket in implantacao_aberta
            for item in ticket.checklist_itens
            if item.obrigatorio and not item.concluido
        )
        # Movimento da implantação = último evento ligado a algum ticket de implantação.
        tickets_impl_ids = {t.id for t in implantacao_aberta}
        ultimo_impl = max(
            (
                _aware(e.em)
                for e in eventos
                if e.categoria is CategoriaEvento.implantacao
                and e.ref_id in tickets_impl_ids
                and _aware(e.em) is not None
            ),
            default=None,
        )
        if ultimo_impl is None:
            ultimo_impl = min(
                (_aware(t.created_at) for t in implantacao_aberta if t.created_at is not None),
                default=None,
            )
        dias_parada = _dias_desde(ultimo_impl, agora) or 0
        nivel_impl = _nivel_por_dias(dias_parada, IMPLANTACAO_ATENCAO_DIAS, IMPLANTACAO_RISCO_DIAS)
        sinais.append(
            _sinal(
                "implantacao",
                "Implantação em andamento",
                f"{dias_parada} dia(s) sem movimento · {pendencias} item(ns) obrigatório(s) pendente(s)",
                nivel_impl,
                (
                    f"{len(implantacao_aberta)} ticket(s) de implantação em aberto. "
                    f"Cortes de parada: atenção ≥{IMPLANTACAO_ATENCAO_DIAS} dias, "
                    f"risco ≥{IMPLANTACAO_RISCO_DIAS} dias."
                ),
            )
        )

    # Tempo CRM → assinatura do contrato mais recente da empresa. Informativo:
    # é um indicador histórico de fluidez, não um sinal de saúde atual.
    assinatura = (
        db.query(Contrato.assinado_em, CrmLead.created_at)
        .join(CrmNegociacaoCnpjLinha, Contrato.negociacao_linha_cnpj_id == CrmNegociacaoCnpjLinha.id)
        .join(CrmNegociacao, CrmNegociacaoCnpjLinha.negociacao_id == CrmNegociacao.id)
        .join(CrmLead, CrmNegociacao.lead_id == CrmLead.id)
        .filter(
            or_(Contrato.empresa_id == empresa.id, CrmNegociacaoCnpjLinha.empresa_id == empresa.id),
            Contrato.assinado_em.isnot(None),
        )
        .order_by(Contrato.assinado_em.desc())
        .first()
    )
    if assinatura is not None:
        assinado_em, lead_em = _aware(assinatura[0]), _aware(assinatura[1])
        dias_crm = _dias_desde(lead_em, assinado_em) if assinado_em else None
        sinais.append(
            _sinal(
                "tempo_crm_assinatura",
                "Tempo entre lead e assinatura",
                f"{dias_crm} dia(s)" if dias_crm is not None else "—",
                "info",
                "Do cadastro do lead até a assinatura do contrato mais recente. Informativo.",
            )
        )
    else:
        sinais.append(
            _sinal(
                "tempo_crm_assinatura",
                "Tempo entre lead e assinatura",
                "Sem contrato assinado vinculado",
                "info",
                "Nenhum contrato assinado com vínculo de empresa/negociação foi encontrado.",
            )
        )

    return sinais, ultimo_evento, dias_sem_movimento


def saude_da_empresa(
    db: Session,
    empresa: Empresa,
    tenant_id: int,
    *,
    agora: datetime | None = None,
) -> SaudeEmpresaRead:
    agora = _aware(agora) or _agora()
    eventos = coletar_eventos(db, empresa.id, tenant_id)
    sinais, ultimo_evento, dias_sem_movimento = _sinais_saude(
        db, empresa, tenant_id, eventos, agora
    )

    niveis = [s.nivel for s in sinais if s.nivel in _NIVEL_ORDEM and s.nivel != "info"]
    status = SaudeStatus.saudavel
    if niveis:
        status = SaudeStatus(max(niveis, key=lambda n: _NIVEL_ORDEM[n]))

    if status is SaudeStatus.saudavel:
        motivos = ["Nenhum sinal de atenção ou risco nas regras atuais."]
    else:
        motivos = [f"{s.rotulo}: {s.valor}" for s in sinais if s.nivel == status.value]

    return SaudeEmpresaRead(
        empresa_id=empresa.id,
        empresa_nome=empresa.nome,
        rede_id=empresa.rede_id,
        rede_nome=empresa.rede.nome if empresa.rede is not None else None,
        ativo=bool(empresa.ativo),
        status=status,
        motivos=motivos,
        sinais=[
            SinalSaudeRead(
                codigo=s.codigo,
                rotulo=s.rotulo,
                valor=s.valor,
                nivel=s.nivel,
                explicacao=s.explicacao,
            )
            for s in sinais
        ],
        ultimo_evento_em=ultimo_evento,
        dias_sem_movimento=dias_sem_movimento,
        atualizado_em=agora,
    )


def listar_carteira(
    db: Session,
    *,
    tenant_id: int,
    busca: str | None = None,
    status_filtro: SaudeStatus | None = None,
    incluir_inativos: bool = False,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[SaudeEmpresaRead], int]:
    """Empresas da carteira com status de saúde.

    Sem filtro de status a paginação vai direto ao banco (health calculado só na
    página). Com filtro de status o health é calculado para todas as empresas
    que casam com a busca, porque o status é derivado — ver relatório do lote
    como limitação de performance do MVP.
    """
    q = (
        db.query(Empresa)
        .options(joinedload(Empresa.rede))
        .filter(Empresa.tenant_id == tenant_id)
    )
    if not incluir_inativos:
        q = q.filter(Empresa.ativo.is_(True))
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                Empresa.nome.ilike(termo),
                Empresa.razao_social.ilike(termo),
                Empresa.nome_fantasia.ilike(termo),
                Empresa.cnpj_cpf.ilike(termo),
            )
        )

    ordenacao = (Empresa.nome.asc(), Empresa.id.asc())

    if status_filtro is None:
        total = q.count()
        empresas = q.order_by(*ordenacao).offset(offset).limit(limit).all()
        itens = [saude_da_empresa(db, empresa, tenant_id) for empresa in empresas]
        return itens, total

    empresas = q.order_by(*ordenacao).all()
    itens = [saude_da_empresa(db, empresa, tenant_id) for empresa in empresas]
    filtrados = [item for item in itens if item.status == status_filtro]
    return filtrados[offset : offset + limit], len(filtrados)


def saude_da_empresa_por_id(
    db: Session,
    *,
    empresa_id: int,
    tenant_id: int,
    agora: datetime | None = None,
) -> SaudeEmpresaRead:
    empresa = _empresa_da_carteira(db, empresa_id, tenant_id)
    return saude_da_empresa(db, empresa, tenant_id, agora=agora)
