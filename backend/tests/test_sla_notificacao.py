"""Alertas SLA in-app e e-mail (#279)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.atendente_notificacao import NotificacaoEmailOutbox
from app.models.sla_alerta_emitido import SlaAlertaEmitido
from app.models.sla_policy import SlaPolicy
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket
from app.services.sla_notificacao import EVENTO_EM_RISCO, EVENTO_VIOLADO, META_PRIMEIRA, processar_alertas_sla


def _criar_ticket_sla(
    db_session,
    seed_base,
    *,
    meta_min: int = 100,
    minutos_decorridos: int,
    atendente_id: int | None = None,
) -> Ticket:
    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade=None,
        meta_primeira_resposta_min=meta_min,
        meta_resolucao_min=480,
        ativo=True,
    )
    db_session.add(policy)
    db_session.flush()
    st = db_session.query(StatusTicket).first()
    now = datetime.now(timezone.utc)
    inicio = now - timedelta(minutes=minutos_decorridos)
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-SLA-ALERT",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="SLA alerta",
        prioridade="normal",
        atendente_id=atendente_id or seed_base["a1"].id,
        sla_policy_id=policy.id,
        sla_meta_primeira_resposta_min=meta_min,
        sla_primeira_resposta_vence_em=inicio + timedelta(minutes=meta_min),
        sla_meta_resolucao_min=480,
        sla_resolucao_vence_em=inicio + timedelta(minutes=480),
        created_at=inicio,
    )
    db_session.add(ticket)
    db_session.commit()
    return ticket


def test_alerta_em_risco_enfileira_email_e_registra_emitido(db_session, seed_base):
    ticket = _criar_ticket_sla(db_session, seed_base, minutos_decorridos=85)

    n = processar_alertas_sla(db_session)
    db_session.commit()

    assert n >= 1
    emitido = (
        db_session.query(SlaAlertaEmitido)
        .filter(
            SlaAlertaEmitido.ticket_id == ticket.id,
            SlaAlertaEmitido.meta == META_PRIMEIRA,
            SlaAlertaEmitido.evento == EVENTO_EM_RISCO,
        )
        .first()
    )
    assert emitido is not None

    rows = (
        db_session.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.ticket_id == ticket.id,
            NotificacaoEmailOutbox.tipo == "sla_em_risco",
        )
        .all()
    )
    assert len(rows) >= 1
    assert seed_base["a1"].id in {r.atendente_id for r in rows}


def test_alerta_violado_debounce_nao_repete(db_session, seed_base):
    ticket = _criar_ticket_sla(db_session, seed_base, minutos_decorridos=120)

    n1 = processar_alertas_sla(db_session)
    db_session.commit()
    assert n1 >= 1

    n2 = processar_alertas_sla(db_session)
    db_session.commit()
    assert n2 == 0

    count = (
        db_session.query(SlaAlertaEmitido)
        .filter(
            SlaAlertaEmitido.ticket_id == ticket.id,
            SlaAlertaEmitido.meta == META_PRIMEIRA,
            SlaAlertaEmitido.evento == EVENTO_VIOLADO,
        )
        .count()
    )
    assert count == 1


def test_preferencias_sla_desligam_email(client, seed_base, auth_headers, db_session):
    client.patch(
        "/v1/notificacoes/preferencias",
        headers=auth_headers["a1"],
        json={"email_sla_em_risco": False, "email_sla_violado": False},
    )
    ticket = _criar_ticket_sla(db_session, seed_base, minutos_decorridos=85)

    processar_alertas_sla(db_session)
    db_session.commit()

    rows = (
        db_session.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.ticket_id == ticket.id,
            NotificacaoEmailOutbox.tipo.in_(["sla_em_risco", "sla_violado"]),
        )
        .all()
    )
    assert all(r.atendente_id != seed_base["a1"].id for r in rows)

    emitido = (
        db_session.query(SlaAlertaEmitido)
        .filter(SlaAlertaEmitido.ticket_id == ticket.id)
        .first()
    )
    assert emitido is not None
