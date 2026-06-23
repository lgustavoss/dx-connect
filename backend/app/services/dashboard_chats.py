"""Métricas analíticas do canal WhatsApp (#284 / D-03)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models.atendente import Atendente
from app.models.whatsapp_chat import WhatsappChat, WhatsappChatTicket, WhatsappMensagem
from app.schemas.dashboard import (
    ContagemEncerramentoChat,
    ContagemIdNome,
    ContagemRotulo,
    CsatDistribuicaoTickets,
    DashboardChatsResponse,
    SerieVolumeDia,
    SnapshotCanais,
)
from app.services.chat_dashboard_filters import apply_chat_dashboard_filters, period_bounds, resolve_period
from app.services.dashboard_drilldown import ChatDrillDown, apply_chat_drill_down
from app.services.whatsapp_chat_demandas import agregar_demandas_por_motivo, agregar_demandas_por_natureza

CACHE_TTL_SECONDS = 60

_cache: dict[tuple, tuple[datetime, DashboardChatsResponse]] = {}


def clear_dashboard_chats_cache() -> None:
    _cache.clear()


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def _filtrar(db: Session, atendente: Atendente, setor_id: int | None, drill: ChatDrillDown):
    def apply(stmt, exclude: str | None = None):
        stmt = apply_chat_dashboard_filters(stmt, db, atendente, setor_id=setor_id)
        active = drill.without(exclude) if exclude else drill
        return apply_chat_drill_down(stmt, active)

    return apply


def _volume_por_dia(
    db: Session,
    atendente: Atendente,
    de: date,
    ate: date,
    setor_id: int | None,
    drill: ChatDrillDown,
) -> list[SerieVolumeDia]:
    de_dt, ate_dt = period_bounds(de, ate)
    abertos: dict[date, int] = {}
    encerrados: dict[date, int] = {}
    filtrar = _filtrar(db, atendente, setor_id, drill)

    stmt_a = (
        select(func.date(WhatsappChat.created_at).label("dia"), func.count())
        .select_from(WhatsappChat)
        .where(WhatsappChat.created_at >= de_dt, WhatsappChat.created_at < ate_dt)
        .group_by(func.date(WhatsappChat.created_at))
    )
    for dia, total in db.execute(filtrar(stmt_a)):
        abertos[_as_date(dia)] = int(total)

    stmt_e = (
        select(func.date(WhatsappChat.encerramento_at).label("dia"), func.count())
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.encerramento_at.isnot(None),
            WhatsappChat.encerramento_at >= de_dt,
            WhatsappChat.encerramento_at < ate_dt,
        )
        .group_by(func.date(WhatsappChat.encerramento_at))
    )
    for dia, total in db.execute(filtrar(stmt_e)):
        encerrados[_as_date(dia)] = int(total)

    serie: list[SerieVolumeDia] = []
    cursor = de
    while cursor <= ate:
        serie.append(
            SerieVolumeDia(
                dia=cursor,
                abertos=abertos.get(cursor, 0),
                fechados=encerrados.get(cursor, 0),
            )
        )
        cursor += timedelta(days=1)
    return serie


def _tempo_espera_medio_horas(
    db: Session,
    atendente: Atendente,
    de_dt: datetime,
    ate_dt: datetime,
    setor_id: int | None,
    drill: ChatDrillDown,
) -> float | None:
    filtrar = _filtrar(db, atendente, setor_id, drill)
    duracao = func.extract(
        "epoch",
        WhatsappChat.atendimento_inicio_at - WhatsappChat.created_at,
    )
    stmt = (
        select(func.avg(duracao))
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.atendimento_inicio_at.isnot(None),
            WhatsappChat.atendimento_inicio_at >= de_dt,
            WhatsappChat.atendimento_inicio_at < ate_dt,
        )
    )
    media_seg = db.execute(filtrar(stmt)).scalar_one_or_none()
    if media_seg is None:
        return None
    return round(float(media_seg) / 3600.0, 2)


def _tempo_atendimento_medio_horas(
    db: Session,
    atendente: Atendente,
    de_dt: datetime,
    ate_dt: datetime,
    setor_id: int | None,
    drill: ChatDrillDown,
) -> float | None:
    filtrar = _filtrar(db, atendente, setor_id, drill)
    duracao = func.extract(
        "epoch",
        WhatsappChat.encerramento_at - WhatsappChat.atendimento_inicio_at,
    )
    stmt = (
        select(func.avg(duracao))
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.atendimento_inicio_at.isnot(None),
            WhatsappChat.encerramento_at.isnot(None),
            WhatsappChat.encerramento_at >= de_dt,
            WhatsappChat.encerramento_at < ate_dt,
        )
    )
    media_seg = db.execute(filtrar(stmt)).scalar_one_or_none()
    if media_seg is None:
        return None
    return round(float(media_seg) / 3600.0, 2)


def _avaliacoes(
    db: Session,
    atendente: Atendente,
    de_dt: datetime,
    ate_dt: datetime,
    setor_id: int | None,
    drill: ChatDrillDown,
) -> CsatDistribuicaoTickets:
    filtrar = _filtrar(db, atendente, setor_id, drill)
    stmt = (
        select(WhatsappChat.avaliacao_nota, func.count())
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.avaliacao_nota.isnot(None),
            WhatsappChat.avaliacao_respondida_at.isnot(None),
            WhatsappChat.avaliacao_respondida_at >= de_dt,
            WhatsappChat.avaliacao_respondida_at < ate_dt,
        )
        .group_by(WhatsappChat.avaliacao_nota)
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


def _encerramentos(
    db: Session,
    atendente: Atendente,
    de_dt: datetime,
    ate_dt: datetime,
    setor_id: int | None,
    drill: ChatDrillDown,
) -> list[ContagemEncerramentoChat]:
    filtrar = _filtrar(db, atendente, setor_id, drill)
    base = (
        select(WhatsappChat.id)
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.encerramento_at.isnot(None),
            WhatsappChat.encerramento_at >= de_dt,
            WhatsappChat.encerramento_at < ate_dt,
        )
    )
    base = filtrar(base, "encerramento")
    ids_encerrados = [row[0] for row in db.execute(base)]
    if not ids_encerrados:
        return [
            ContagemEncerramentoChat(tipo="manual", rotulo="Encerrado pelo atendente", total=0),
            ContagemEncerramentoChat(tipo="inatividade", rotulo="Encerrado por inatividade", total=0),
        ]

    stmt_inat = (
        select(func.count(func.distinct(WhatsappMensagem.chat_id)))
        .select_from(WhatsappMensagem)
        .where(
            WhatsappMensagem.chat_id.in_(ids_encerrados),
            WhatsappMensagem.evento_sistema == "auto_encerrado_inatividade",
        )
    )
    inat_total = int(db.execute(stmt_inat).scalar_one() or 0)
    manual_total = max(len(ids_encerrados) - inat_total, 0)
    return [
        ContagemEncerramentoChat(tipo="manual", rotulo="Encerrado pelo atendente", total=manual_total),
        ContagemEncerramentoChat(tipo="inatividade", rotulo="Encerrado por inatividade", total=inat_total),
    ]


def _pct_com_ticket_vinculado(
    db: Session,
    atendente: Atendente,
    de_dt: datetime,
    ate_dt: datetime,
    setor_id: int | None,
    drill: ChatDrillDown,
) -> float | None:
    filtrar = _filtrar(db, atendente, setor_id, drill)
    stmt_total = (
        select(func.count())
        .select_from(WhatsappChat)
        .where(WhatsappChat.created_at >= de_dt, WhatsappChat.created_at < ate_dt)
    )
    total = int(db.execute(filtrar(stmt_total)).scalar_one() or 0)
    if total == 0:
        return None
    vinculado = exists(
        select(WhatsappChatTicket.id).where(WhatsappChatTicket.chat_id == WhatsappChat.id)
    )
    stmt_v = (
        select(func.count())
        .select_from(WhatsappChat)
        .where(
            WhatsappChat.created_at >= de_dt,
            WhatsappChat.created_at < ate_dt,
            vinculado,
        )
    )
    com_ticket = int(db.execute(filtrar(stmt_v)).scalar_one() or 0)
    return round(com_ticket * 100.0 / total, 1)


def _por_atendente(
    db: Session,
    atendente: Atendente,
    de_dt: datetime,
    ate_dt: datetime,
    setor_id: int | None,
    drill: ChatDrillDown,
) -> list[ContagemIdNome]:
    if atendente.role != "admin":
        return []
    filtrar = _filtrar(db, atendente, setor_id, drill)
    stmt = (
        select(
            Atendente.id,
            Atendente.nome,
            func.count(),
        )
        .select_from(WhatsappChat)
        .join(Atendente, Atendente.id == WhatsappChat.atendente_id)
        .where(
            WhatsappChat.atendimento_inicio_at.isnot(None),
            WhatsappChat.atendimento_inicio_at >= de_dt,
            WhatsappChat.atendimento_inicio_at < ate_dt,
        )
        .group_by(Atendente.id, Atendente.nome)
        .order_by(func.count().desc())
        .limit(15)
    )
    return [
        ContagemIdNome(id=int(aid), nome=str(nome), total=int(total))
        for aid, nome, total in db.execute(filtrar(stmt, "atendente"))
    ]


def _por_estado_atual(
    db: Session,
    atendente: Atendente,
    setor_id: int | None,
    drill: ChatDrillDown,
) -> list[ContagemRotulo]:
    filtrar = _filtrar(db, atendente, setor_id, drill)
    labels = {
        "aguardando_atendente": "Aguardando atendente",
        "em_atendimento": "Em atendimento",
        "aguardando_avaliacao": "Aguardando avaliação",
    }
    stmt = (
        select(WhatsappChat.estado, func.count())
        .select_from(WhatsappChat)
        .where(WhatsappChat.estado.in_(list(labels.keys())))
        .group_by(WhatsappChat.estado)
    )
    counts = {estado: int(total) for estado, total in db.execute(filtrar(stmt, "estado"))}
    return [
        ContagemRotulo(chave=estado, rotulo=labels[estado], total=counts.get(estado, 0))
        for estado in labels
    ]


def _snapshot_canais(db: Session, atendente: Atendente) -> SnapshotCanais:
    from app.services.dashboard_geral import _count_chats_por_estado, _count_tickets_abertos, _count_tickets_sem_responsavel

    return SnapshotCanais(
        tickets_abertos=_count_tickets_abertos(db, atendente),
        tickets_sem_responsavel=_count_tickets_sem_responsavel(db, atendente),
        chats_aguardando=_count_chats_por_estado(db, atendente, "aguardando_atendente"),
        chats_em_atendimento=_count_chats_por_estado(db, atendente, "em_atendimento"),
    )


def _compute(
    db: Session,
    atendente: Atendente,
    de: date,
    ate: date,
    setor_id: int | None,
    drill: ChatDrillDown,
    *,
    empresa_id: int | None = None,
    rede_id: int | None = None,
) -> DashboardChatsResponse:
    de_dt, ate_dt = period_bounds(de, ate)
    agora = datetime.now(timezone.utc)
    filtros_demanda = dict(
        de=de,
        ate=ate,
        setor_id=setor_id,
        empresa_id=empresa_id,
        rede_id=rede_id,
    )
    return DashboardChatsResponse(
        de=de,
        ate=ate,
        volume_por_dia=_volume_por_dia(db, atendente, de, ate, setor_id, drill),
        tempo_espera_medio_horas=_tempo_espera_medio_horas(db, atendente, de_dt, ate_dt, setor_id, drill),
        tempo_atendimento_medio_horas=_tempo_atendimento_medio_horas(
            db, atendente, de_dt, ate_dt, setor_id, drill
        ),
        avaliacoes=_avaliacoes(db, atendente, de_dt, ate_dt, setor_id, drill),
        encerramentos=_encerramentos(db, atendente, de_dt, ate_dt, setor_id, drill),
        pct_com_ticket_vinculado=_pct_com_ticket_vinculado(db, atendente, de_dt, ate_dt, setor_id, drill),
        por_atendente=_por_atendente(db, atendente, de_dt, ate_dt, setor_id, drill),
        por_estado_atual=_por_estado_atual(db, atendente, setor_id, drill),
        demandas_por_natureza=agregar_demandas_por_natureza(db, atendente, **filtros_demanda),
        demandas_por_motivo=agregar_demandas_por_motivo(db, atendente, **filtros_demanda),
        snapshot=_snapshot_canais(db, atendente),
        gerado_em=agora,
        cache_ttl_segundos=CACHE_TTL_SECONDS,
    )


def obter_dashboard_chats(
    db: Session,
    atendente: Atendente,
    *,
    de: date | None = None,
    ate: date | None = None,
    setor_id: int | None = None,
    empresa_id: int | None = None,
    rede_id: int | None = None,
    drill_tipo: str | None = None,
    drill_valor: str | None = None,
    atendente_filtro_id: int | None = None,
) -> DashboardChatsResponse:
    inicio, fim = resolve_period(de, ate)
    drill = ChatDrillDown.parse(
        drill_tipo=drill_tipo,
        drill_valor=drill_valor,
        atendente_filtro_id=atendente_filtro_id,
    )
    chave = (atendente.id, atendente.role, inicio, fim, setor_id, empresa_id, rede_id, drill.tipo, drill.valor)
    agora = datetime.now(timezone.utc)
    em_cache = _cache.get(chave)
    if em_cache is not None:
        gerado_em, resposta = em_cache
        if (agora - gerado_em).total_seconds() < CACHE_TTL_SECONDS:
            return resposta
    resposta = _compute(
        db,
        atendente,
        inicio,
        fim,
        setor_id,
        drill,
        empresa_id=empresa_id,
        rede_id=rede_id,
    )
    _cache[chave] = (agora, resposta)
    return resposta
