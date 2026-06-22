"""Métricas analíticas do canal tickets (#283)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.core.ticket_prioridade import PrioridadeTicket
from app.models import Empresa, Rede, StatusTicket, Ticket
from app.models.atendente import Atendente
from app.models.ticket_avaliacao import TicketAvaliacao
from app.models.ticket_classificacao import TicketMotivo
from app.models.ticket import TicketHistorico, TicketMensagem
from app.schemas.dashboard import (
    ContagemCanal,
    ContagemIdNome,
    ContagemPrioridade,
    CsatDistribuicaoTickets,
    DashboardTicketsResponse,
    SerieVolumeDia,
)
from app.services.dashboard_drilldown import TicketDrillDown, apply_ticket_drill_down
from app.services.ticket_dashboard_filters import (
    apply_ticket_dashboard_filters,
    period_bounds,
    resolve_period,
)

CACHE_TTL_SECONDS = 60

_cache: dict[tuple, tuple[datetime, DashboardTicketsResponse]] = {}


def clear_dashboard_tickets_cache() -> None:
    _cache.clear()


def _canal_expr():
    email_exists = (
        select(TicketMensagem.id)
        .where(
            TicketMensagem.ticket_id == Ticket.id,
            TicketMensagem.tipo == "email_cliente",
        )
        .correlate(Ticket)
        .exists()
    )
    return case(
        (Ticket.parent_ticket_id.isnot(None), "filho_massa"),
        (email_exists, "email"),
        else_="manual",
    )


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def _filtros(
    db: Session,
    atendente: Atendente,
    rede_id: int | None,
    setor_id: int | None,
    prioridade: str | None,
    drill: TicketDrillDown,
):
    canal = _canal_expr()

    def apply(stmt, exclude: str | None = None):
        stmt = apply_ticket_dashboard_filters(
            stmt,
            db,
            atendente,
            rede_id=rede_id,
            setor_id=setor_id,
            prioridade=prioridade,
        )
        active = drill.without(exclude) if exclude else drill
        return apply_ticket_drill_down(stmt, active, canal_expr=canal)

    return apply


def _volume_por_dia(
    db: Session,
    atendente: Atendente,
    de: date,
    ate: date,
    rede_id: int | None,
    setor_id: int | None,
    prioridade: str | None,
    drill: TicketDrillDown,
) -> list[SerieVolumeDia]:
    de_dt, ate_dt = period_bounds(de, ate)
    abertos: dict[date, int] = {}
    fechados: dict[date, int] = {}
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)

    stmt_a = (
        select(func.date(Ticket.created_at).label("dia"), func.count())
        .select_from(Ticket)
        .where(Ticket.created_at >= de_dt, Ticket.created_at < ate_dt)
        .group_by(func.date(Ticket.created_at))
    )
    for dia, total in db.execute(filtrar(stmt_a)):
        abertos[_as_date(dia)] = int(total)

    stmt_f = (
        select(func.date(Ticket.fechado_em).label("dia"), func.count())
        .select_from(Ticket)
        .where(
            Ticket.fechado_em.isnot(None),
            Ticket.fechado_em >= de_dt,
            Ticket.fechado_em < ate_dt,
        )
        .group_by(func.date(Ticket.fechado_em))
    )
    for dia, total in db.execute(filtrar(stmt_f)):
        fechados[_as_date(dia)] = int(total)

    serie: list[SerieVolumeDia] = []
    cursor = de
    while cursor <= ate:
        serie.append(
            SerieVolumeDia(
                dia=cursor,
                abertos=abertos.get(cursor, 0),
                fechados=fechados.get(cursor, 0),
            )
        )
        cursor += timedelta(days=1)
    return serie


def _por_status(
    db: Session,
    atendente: Atendente,
    rede_id: int | None,
    setor_id: int | None,
    prioridade: str | None,
    drill: TicketDrillDown,
) -> list[ContagemIdNome]:
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)
    stmt = (
        select(Ticket.status_id, StatusTicket.nome, func.count())
        .select_from(Ticket)
        .join(StatusTicket, StatusTicket.id == Ticket.status_id)
        .where(Ticket.fechado_em.is_(None))
        .group_by(Ticket.status_id, StatusTicket.nome)
        .order_by(func.count().desc())
    )
    return [
        ContagemIdNome(id=int(sid), nome=nome, total=int(total))
        for sid, nome, total in db.execute(filtrar(stmt, "status"))
    ]


def _por_prioridade(
    db: Session,
    atendente: Atendente,
    rede_id: int | None,
    setor_id: int | None,
    prioridade: str | None,
    drill: TicketDrillDown,
) -> list[ContagemPrioridade]:
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)
    stmt = (
        select(Ticket.prioridade, func.count())
        .select_from(Ticket)
        .where(Ticket.fechado_em.is_(None))
        .group_by(Ticket.prioridade)
    )
    counts = {
        (p.value if hasattr(p, "value") else str(p)): int(n)
        for p, n in db.execute(filtrar(stmt, "prioridade"))
    }
    ordem = [p.value for p in PrioridadeTicket]
    if prioridade is not None:
        ordem = [prioridade]
    return [ContagemPrioridade(prioridade=p, total=counts.get(p, 0)) for p in ordem]


def _top_por_campo(
    db: Session,
    atendente: Atendente,
    de_dt: datetime,
    ate_dt: datetime,
    rede_id: int | None,
    setor_id: int | None,
    prioridade: str | None,
    drill: TicketDrillDown,
    *,
    exclude_dim: str,
    id_col,
    nome_expr,
    join_target,
) -> list[ContagemIdNome]:
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)
    stmt = (
        select(id_col, nome_expr, func.count())
        .select_from(Ticket)
        .outerjoin(join_target, join_target.id == id_col)
        .where(Ticket.created_at >= de_dt, Ticket.created_at < ate_dt)
        .group_by(id_col, nome_expr)
        .order_by(func.count().desc())
        .limit(10)
    )
    return [
        ContagemIdNome(
            id=int(rid) if rid is not None else 0,
            nome=str(nome),
            total=int(total),
        )
        for rid, nome, total in db.execute(filtrar(stmt, exclude_dim))
    ]


def _por_motivo(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill: TicketDrillDown):
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)
    stmt = (
        select(Ticket.motivo_id, func.coalesce(TicketMotivo.nome, "Sem motivo"), func.count())
        .select_from(Ticket)
        .outerjoin(TicketMotivo, TicketMotivo.id == Ticket.motivo_id)
        .where(Ticket.created_at >= de_dt, Ticket.created_at < ate_dt)
        .group_by(Ticket.motivo_id, TicketMotivo.nome)
        .order_by(func.count().desc())
        .limit(10)
    )
    return [
        ContagemIdNome(
            id=int(motivo_id) if motivo_id is not None else 0,
            nome=str(nome),
            total=int(total),
        )
        for motivo_id, nome, total in db.execute(filtrar(stmt, "motivo"))
    ]


def _por_rede(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill: TicketDrillDown):
    return _top_por_campo(
        db,
        atendente,
        de_dt,
        ate_dt,
        rede_id,
        setor_id,
        prioridade,
        drill,
        exclude_dim="rede",
        id_col=Ticket.rede_id,
        nome_expr=func.coalesce(Rede.nome, "Sem rede"),
        join_target=Rede,
    )


def _por_empresa(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill: TicketDrillDown):
    return _top_por_campo(
        db,
        atendente,
        de_dt,
        ate_dt,
        rede_id,
        setor_id,
        prioridade,
        drill,
        exclude_dim="empresa",
        id_col=Ticket.empresa_id,
        nome_expr=func.coalesce(Empresa.nome, "Sem empresa"),
        join_target=Empresa,
    )


def _mttr_horas(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill: TicketDrillDown):
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)
    duracao = func.extract("epoch", Ticket.fechado_em - Ticket.created_at)
    stmt = (
        select(func.avg(duracao))
        .select_from(Ticket)
        .where(
            Ticket.fechado_em.isnot(None),
            Ticket.fechado_em >= de_dt,
            Ticket.fechado_em < ate_dt,
        )
    )
    media_seg = db.execute(filtrar(stmt)).scalar_one_or_none()
    if media_seg is None:
        return None
    return round(float(media_seg) / 3600.0, 2)


def _fila_tempo_medio_horas(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill: TicketDrillDown):
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)
    first_assign = (
        select(func.min(TicketHistorico.created_at))
        .where(
            TicketHistorico.ticket_id == Ticket.id,
            TicketHistorico.campo == "atendente_id",
            or_(
                TicketHistorico.valor_antigo.is_(None),
                TicketHistorico.valor_antigo == "",
            ),
        )
        .correlate(Ticket)
        .scalar_subquery()
    )
    inicio_fila = func.coalesce(Ticket.fila_desde_at, Ticket.created_at)
    duracao = func.extract("epoch", first_assign - inicio_fila)
    stmt = (
        select(func.avg(duracao))
        .select_from(Ticket)
        .where(
            Ticket.atendente_id.isnot(None),
            Ticket.created_at >= de_dt,
            Ticket.created_at < ate_dt,
            first_assign.isnot(None),
        )
    )
    media_seg = db.execute(filtrar(stmt)).scalar_one_or_none()
    if media_seg is None:
        return None
    return round(float(media_seg) / 3600.0, 2)


def _csat(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill: TicketDrillDown):
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)
    stmt = (
        select(TicketAvaliacao.nota, func.count())
        .select_from(TicketAvaliacao)
        .join(Ticket, Ticket.id == TicketAvaliacao.ticket_id)
        .where(
            TicketAvaliacao.respondida_em >= de_dt,
            TicketAvaliacao.respondida_em < ate_dt,
        )
        .group_by(TicketAvaliacao.nota)
    )
    por_nota = {i: 0 for i in range(1, 6)}
    total = 0
    soma = 0
    for nota, qtd in db.execute(filtrar(stmt, "nota")):
        n = int(nota)
        c = int(qtd)
        if 1 <= n <= 5:
            por_nota[n] = c
            total += c
            soma += n * c
    media = round(soma / total, 2) if total > 0 else None
    return CsatDistribuicaoTickets(
        media=media,
        total_avaliacoes=total,
        por_nota=por_nota,
    )


def _por_canal(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill: TicketDrillDown):
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)
    canal = _canal_expr().label("canal")
    stmt = (
        select(canal, func.count())
        .select_from(Ticket)
        .where(Ticket.created_at >= de_dt, Ticket.created_at < ate_dt)
        .group_by(canal)
        .order_by(func.count().desc())
    )
    labels = {
        "manual": "Manual",
        "email": "E-mail",
        "filho_massa": "Filho em massa",
    }
    return [
        ContagemCanal(canal=str(c), rotulo=labels.get(str(c), str(c)), total=int(total))
        for c, total in db.execute(filtrar(stmt, "canal"))
    ]


def _por_atendente(
    db: Session,
    atendente: Atendente,
    de_dt: datetime,
    ate_dt: datetime,
    rede_id: int | None,
    setor_id: int | None,
    prioridade: str | None,
    drill: TicketDrillDown,
):
    if atendente.role != "admin":
        return []
    filtrar = _filtros(db, atendente, rede_id, setor_id, prioridade, drill)
    stmt = (
        select(Atendente.id, Atendente.nome, func.count())
        .select_from(Ticket)
        .join(Atendente, Atendente.id == Ticket.atendente_id)
        .where(
            Ticket.atendente_id.isnot(None),
            Ticket.created_at >= de_dt,
            Ticket.created_at < ate_dt,
        )
        .group_by(Atendente.id, Atendente.nome)
        .order_by(func.count().desc())
        .limit(15)
    )
    return [
        ContagemIdNome(id=int(aid), nome=str(nome), total=int(total))
        for aid, nome, total in db.execute(filtrar(stmt, "atendente"))
    ]


def _compute(
    db: Session,
    atendente: Atendente,
    de: date,
    ate: date,
    rede_id: int | None,
    setor_id: int | None,
    prioridade: str | None,
    drill: TicketDrillDown,
) -> DashboardTicketsResponse:
    de_dt, ate_dt = period_bounds(de, ate)
    agora = datetime.now(timezone.utc)
    return DashboardTicketsResponse(
        de=de,
        ate=ate,
        volume_por_dia=_volume_por_dia(db, atendente, de, ate, rede_id, setor_id, prioridade, drill),
        por_status=_por_status(db, atendente, rede_id, setor_id, prioridade, drill),
        por_prioridade=_por_prioridade(db, atendente, rede_id, setor_id, prioridade, drill),
        por_motivo=_por_motivo(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill),
        por_rede=_por_rede(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill),
        por_empresa=_por_empresa(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill),
        mttr_horas=_mttr_horas(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill),
        fila_tempo_medio_horas=_fila_tempo_medio_horas(
            db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill
        ),
        csat=_csat(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill),
        por_canal=_por_canal(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill),
        por_atendente=_por_atendente(db, atendente, de_dt, ate_dt, rede_id, setor_id, prioridade, drill),
        gerado_em=agora,
        cache_ttl_segundos=CACHE_TTL_SECONDS,
    )


def obter_dashboard_tickets(
    db: Session,
    atendente: Atendente,
    *,
    de: date | None = None,
    ate: date | None = None,
    rede_id: int | None = None,
    setor_id: int | None = None,
    prioridade: str | None = None,
    drill_tipo: str | None = None,
    drill_valor: str | None = None,
    atendente_filtro_id: int | None = None,
) -> DashboardTicketsResponse:
    inicio, fim = resolve_period(de, ate)
    drill = TicketDrillDown.parse(
        drill_tipo=drill_tipo,
        drill_valor=drill_valor,
        atendente_filtro_id=atendente_filtro_id,
    )
    chave = (
        atendente.id,
        atendente.role,
        inicio,
        fim,
        rede_id,
        setor_id,
        prioridade,
        drill.tipo,
        drill.valor,
    )
    agora = datetime.now(timezone.utc)
    em_cache = _cache.get(chave)
    if em_cache is not None:
        gerado_em, resposta = em_cache
        if (agora - gerado_em).total_seconds() < CACHE_TTL_SECONDS:
            return resposta
    resposta = _compute(db, atendente, inicio, fim, rede_id, setor_id, prioridade, drill)
    _cache[chave] = (agora, resposta)
    return resposta
