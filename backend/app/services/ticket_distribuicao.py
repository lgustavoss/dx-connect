"""Distribuição automática de tickets na fila por setor."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.distribuicao_ticket import DistribuicaoModo, DistribuicaoEstrategia
from app.core.setor_scope import ids_setores_mesmo_nome
from app.models import Setor, Ticket, TicketHistorico
from app.models.atendente import Atendente, atendente_setor
from app.models.setor_distribuicao_round_robin import SetorDistribuicaoRoundRobin
from app.services.notificacao_atendente_email import notificar_ticket_atribuido
from app.services.realtime_emit import emit_notificacao_after_counter_change, emit_ticket_fila

logger = logging.getLogger(__name__)

CAMPO_HISTORICO_DISTRIBUICAO_AUTOMATICA = "distribuicao_automatica"
TEXTO_HISTORICO_DISTRIBUICAO_AUTOMATICA = "Atribuído automaticamente"


def setor_para_distribuicao_read(setor: Setor):
    from app.schemas.setor_distribuicao import SetorDistribuicaoRead

    return SetorDistribuicaoRead(
        modo=setor.distribuicao_modo or DistribuicaoModo.manual.value,
        timeout_minutos=int(setor.distribuicao_timeout_minutos or 30),
        estrategia=setor.distribuicao_estrategia or DistribuicaoEstrategia.round_robin.value,
        atendentes_elegiveis=setor.distribuicao_atendentes_elegiveis,
    )


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def sincronizar_fila_desde_at(ticket: Ticket, *, reset: bool = False) -> None:
    """Atualiza ``fila_desde_at`` conforme o ticket está ou não na fila."""
    if ticket.atendente_id is None and ticket.fechado_em is None:
        if reset or ticket.fila_desde_at is None:
            ticket.fila_desde_at = _agora_utc()
    else:
        ticket.fila_desde_at = None


def _registrar_historico_atribuicao(
    db: Session,
    ticket_id: int,
    valor_antigo: str | None,
    valor_novo: str,
) -> None:
    db.add(
        TicketHistorico(
            ticket_id=ticket_id,
            atendente_id=None,
            campo="atendente_id",
            valor_antigo=valor_antigo,
            valor_novo=valor_novo,
        )
    )


def _registrar_historico_distribuicao_automatica(db: Session, ticket_id: int) -> None:
    db.add(
        TicketHistorico(
            ticket_id=ticket_id,
            atendente_id=None,
            campo=CAMPO_HISTORICO_DISTRIBUICAO_AUTOMATICA,
            valor_antigo=None,
            valor_novo=TEXTO_HISTORICO_DISTRIBUICAO_AUTOMATICA,
        )
    )


def listar_atendentes_elegiveis_distribuicao(db: Session, setor: Setor) -> list[Atendente]:
    """Atendentes ativos do setor (homônimos), excluindo admin."""
    ids_setor = ids_setores_mesmo_nome(db, setor.id)
    q = (
        db.query(Atendente)
        .join(atendente_setor, atendente_setor.c.atendente_id == Atendente.id)
        .filter(
            Atendente.tenant_id == setor.tenant_id,
            Atendente.ativo.is_(True),
            Atendente.role != "admin",
            atendente_setor.c.setor_id.in_(ids_setor),
        )
        .distinct()
    )
    elegiveis = setor.distribuicao_atendentes_elegiveis
    if elegiveis is not None:
        q = q.filter(Atendente.id.in_(elegiveis))
    return sorted(q.all(), key=lambda a: (a.nome.lower(), a.id))


def _contar_tickets_abertos_por_atendente(
    db: Session,
    atendente_ids: list[int],
    *,
    tenant_id: int,
    setor_ids: set[int] | None = None,
) -> dict[int, int]:
    """Conta tickets abertos por atendente. ``setor_ids=None`` = carga total no tenant."""
    if not atendente_ids:
        return {}
    q = db.query(Ticket.atendente_id, func.count(Ticket.id)).filter(
        Ticket.tenant_id == tenant_id,
        Ticket.atendente_id.in_(atendente_ids),
        Ticket.fechado_em.is_(None),
    )
    if setor_ids is not None:
        q = q.filter(Ticket.setor_id.in_(setor_ids))
    rows = q.group_by(Ticket.atendente_id).all()
    out = {aid: 0 for aid in atendente_ids}
    for aid, cnt in rows:
        if aid is not None:
            out[aid] = int(cnt)
    return out


def _escolher_menor_carga(
    db: Session,
    setor: Setor,
    candidatos: list[Atendente],
    *,
    escopo_setor: bool,
) -> Atendente | None:
    if not candidatos:
        return None
    setor_ids = {setor.id} if escopo_setor else None
    cargas = _contar_tickets_abertos_por_atendente(
        db,
        [c.id for c in candidatos],
        tenant_id=setor.tenant_id,
        setor_ids=setor_ids,
    )
    return min(candidatos, key=lambda a: (cargas.get(a.id, 0), a.nome.lower(), a.id))


def _escolher_round_robin(db: Session, setor_id: int, candidatos: list[Atendente]) -> Atendente | None:
    if not candidatos:
        return None
    state = (
        db.query(SetorDistribuicaoRoundRobin)
        .filter(SetorDistribuicaoRoundRobin.setor_id == setor_id)
        .with_for_update()
        .first()
    )
    if not state:
        state = SetorDistribuicaoRoundRobin(setor_id=setor_id)
        db.add(state)
        db.flush()

    ids_candidatos = [c.id for c in candidatos]
    last = state.last_atendente_id
    if last is None or last not in ids_candidatos:
        escolhido = candidatos[0]
    else:
        idx = ids_candidatos.index(last)
        escolhido = candidatos[(idx + 1) % len(candidatos)]
    state.last_atendente_id = escolhido.id
    return escolhido


def _escolher_atendente(db: Session, setor: Setor, candidatos: list[Atendente]) -> Atendente | None:
    estrategia = setor.distribuicao_estrategia or DistribuicaoEstrategia.round_robin.value
    if estrategia == DistribuicaoEstrategia.menor_carga_abertos.value:
        return _escolher_menor_carga(db, setor, candidatos, escopo_setor=False)
    if estrategia == DistribuicaoEstrategia.menor_carga_setor.value:
        return _escolher_menor_carga(db, setor, candidatos, escopo_setor=True)
    return _escolher_round_robin(db, setor.id, candidatos)


def atribuir_ticket_automaticamente(
    db: Session,
    ticket: Ticket,
    setor: Setor,
    *,
    actor_id: int | None = None,
) -> int | None:
    """Atribui responsável automaticamente. Retorna o id do atendente ou None."""
    if ticket.atendente_id is not None or ticket.fechado_em is not None:
        return None
    candidatos = listar_atendentes_elegiveis_distribuicao(db, setor)
    escolhido = _escolher_atendente(db, setor, candidatos)
    if not escolhido:
        return None

    antigo = str(ticket.atendente_id) if ticket.atendente_id else ""
    ticket.atendente_id = escolhido.id
    ticket.fila_desde_at = None
    _registrar_historico_atribuicao(db, ticket.id, antigo or None, str(escolhido.id))
    _registrar_historico_distribuicao_automatica(db, ticket.id)
    db.flush()
    notificar_ticket_atribuido(
        db,
        ticket=ticket,
        novo_atendente_id=escolhido.id,
        actor_id=actor_id,
    )
    return escolhido.id


def tentar_distribuicao_imediata(db: Session, ticket: Ticket, *, actor_id: int | None = None) -> bool:
    """Tenta atribuição imediata se o setor estiver em ``auto_imediato``."""
    setor = db.query(Setor).filter(Setor.id == ticket.setor_id).first()
    if not setor or not setor.ativo:
        return False
    modo = setor.distribuicao_modo or DistribuicaoModo.manual.value
    if modo != DistribuicaoModo.auto_imediato.value:
        return False
    novo = atribuir_ticket_automaticamente(db, ticket, setor, actor_id=actor_id)
    return novo is not None


def pos_entrada_fila(db: Session, ticket: Ticket, *, reset_fila: bool = False) -> None:
    """Chamado quando o ticket entra (ou retorna) à fila sem responsável."""
    sincronizar_fila_desde_at(ticket, reset=reset_fila)
    db.flush()
    if tentar_distribuicao_imediata(db, ticket):
        emit_notificacao_after_counter_change(db)
    elif ticket.atendente_id is None and ticket.fechado_em is None:
        emit_ticket_fila(db, ticket)


def fila_info_para_ticket(ticket: Ticket, setor: Setor | None) -> dict:
    if ticket.atendente_id is not None or ticket.fechado_em is not None or setor is None:
        return {
            "fila_desde_at": None,
            "distribuicao_modo_setor": None,
            "distribuicao_auto_em_minutos": None,
        }
    fila_desde = _as_utc(ticket.fila_desde_at or ticket.created_at)
    modo = setor.distribuicao_modo or DistribuicaoModo.manual.value
    minutos_restantes: int | None = None
    if modo == DistribuicaoModo.auto_apos_timeout.value and fila_desde is not None:
        timeout = int(setor.distribuicao_timeout_minutos or 30)
        decorridos = int((_agora_utc() - fila_desde).total_seconds() // 60)
        minutos_restantes = max(0, timeout - decorridos)
    return {
        "fila_desde_at": fila_desde,
        "distribuicao_modo_setor": modo,
        "distribuicao_auto_em_minutos": minutos_restantes,
    }


def processar_distribuicao_timeout(db: Session, *, limit: int = 50) -> int:
    """Worker: atribui tickets que excederam o timeout de fila."""
    agora = _agora_utc()
    atribuidos = 0
    setores = (
        db.query(Setor)
        .filter(
            Setor.ativo.is_(True),
            Setor.distribuicao_modo == DistribuicaoModo.auto_apos_timeout.value,
        )
        .all()
    )
    for setor in setores:
        timeout = max(1, int(setor.distribuicao_timeout_minutos or 30))
        cutoff = agora - timedelta(minutes=timeout)
        q = (
            db.query(Ticket)
            .filter(
                Ticket.setor_id == setor.id,
                Ticket.atendente_id.is_(None),
                Ticket.fechado_em.is_(None),
                Ticket.fila_desde_at.isnot(None),
                Ticket.fila_desde_at <= cutoff,
            )
            .order_by(Ticket.fila_desde_at.asc(), Ticket.id.asc())
            .limit(limit)
        )
        try:
            tickets = q.with_for_update(skip_locked=True).all()
        except Exception:
            tickets = q.all()

        for ticket in tickets:
            if atribuidos >= limit:
                return atribuidos
            novo = atribuir_ticket_automaticamente(db, ticket, setor)
            if novo is not None:
                atribuidos += 1

    if atribuidos:
        emit_notificacao_after_counter_change(db)
    return atribuidos


def validar_atendentes_elegiveis(
    db: Session,
    setor: Setor,
    atendentes_elegiveis: list[int] | None,
) -> list[int] | None:
    if atendentes_elegiveis is None:
        return None
    if not atendentes_elegiveis:
        raise ValueError("Informe ao menos um atendente elegível ou deixe vazio para todos do setor.")
    ids_setor = ids_setores_mesmo_nome(db, setor.id)
    vinculados = {
        r[0]
        for r in db.query(Atendente.id)
        .join(atendente_setor, atendente_setor.c.atendente_id == Atendente.id)
        .filter(
            Atendente.tenant_id == setor.tenant_id,
            Atendente.ativo.is_(True),
            Atendente.role != "admin",
            atendente_setor.c.setor_id.in_(ids_setor),
            Atendente.id.in_(atendentes_elegiveis),
        )
        .all()
    }
    invalidos = [i for i in atendentes_elegiveis if i not in vinculados]
    if invalidos:
        raise ValueError(f"Atendentes não elegíveis para o setor: {invalidos}")
    return atendentes_elegiveis


def pos_criar_ticket_na_fila(db: Session, ticket: Ticket) -> None:
    """Hook pós-criação: sincroniza fila e tenta distribuição imediata."""
    if ticket.atendente_id is not None or ticket.fechado_em is not None:
        return
    sincronizar_fila_desde_at(ticket)
    db.commit()
    if tentar_distribuicao_imediata(db, ticket):
        db.commit()
        emit_notificacao_after_counter_change(db)
    else:
        emit_ticket_fila(db, ticket)
