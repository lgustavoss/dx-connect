"""Testes de distribuição automática de tickets (#257)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import Setor, Ticket, TicketHistorico
from app.models.atendente_notificacao import NotificacaoEmailOutbox
from app.models.setor_distribuicao_round_robin import SetorDistribuicaoRoundRobin
from app.services.ticket_distribuicao import (
    atribuir_ticket_automaticamente,
    processar_distribuicao_timeout,
    tentar_distribuicao_imediata,
)


def _criar_ticket_fila(db, seed_base, *, setor_id=None, fila_desde_at=None):
    setor_id = setor_id or seed_base["setor1"].id
    t = Ticket(
        tenant_id=1,
        protocolo=f"T-TEST-{db.query(Ticket).count() + 1}",
        empresa_id=seed_base["empresa"].id,
        rede_id=seed_base["rede"].id,
        setor_id=setor_id,
        status_id=seed_base["status"].id,
        assunto="Teste fila",
        fila_desde_at=fila_desde_at or datetime.now(timezone.utc),
    )
    db.add(t)
    db.flush()
    return t


def test_put_distribuicao_setor(client, seed_base, auth_headers, db_session):
    setor_id = seed_base["setor1"].id
    r = client.put(
        f"/v1/setores/{setor_id}/distribuicao",
        headers=auth_headers["admin"],
        json={
            "modo": "auto_apos_timeout",
            "timeout_minutos": 15,
            "estrategia": "round_robin",
            "atendentes_elegiveis": None,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["modo"] == "auto_apos_timeout"
    assert body["timeout_minutos"] == 15

    s = db_session.query(Setor).filter(Setor.id == setor_id).first()
    db_session.refresh(s)
    assert s.distribuicao_modo == "auto_apos_timeout"
    assert s.distribuicao_timeout_minutos == 15


def test_distribuicao_imediata_round_robin(client, seed_base, auth_headers, db_session):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    setor.distribuicao_estrategia = "round_robin"
    db_session.commit()

    t1 = _criar_ticket_fila(db_session, seed_base)
    t2 = _criar_ticket_fila(db_session, seed_base)
    db_session.commit()

    assert tentar_distribuicao_imediata(db_session, t1) is True
    db_session.commit()
    assert t1.atendente_id == seed_base["a1"].id

    assert tentar_distribuicao_imediata(db_session, t2) is True
    db_session.commit()
    assert t2.atendente_id == seed_base["a1"].id

    state = db_session.query(SetorDistribuicaoRoundRobin).filter(SetorDistribuicaoRoundRobin.setor_id == setor.id).first()
    assert state is not None
    assert state.last_atendente_id == seed_base["a1"].id


def test_distribuicao_nao_atribui_admin(db_session, seed_base):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    db_session.commit()

    admin = seed_base["admin"]
    admin.setores.append(setor)
    db_session.commit()

    ticket = _criar_ticket_fila(db_session, seed_base)
    db_session.commit()

    ok = atribuir_ticket_automaticamente(db_session, ticket, setor)
    db_session.commit()
    assert ok == seed_base["a1"].id
    assert ticket.atendente_id != admin.id


def test_worker_timeout_atribui(client, seed_base, db_session):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_apos_timeout"
    setor.distribuicao_timeout_minutos = 5
    db_session.commit()

    antigo = datetime.now(timezone.utc) - timedelta(minutes=10)
    ticket = _criar_ticket_fila(db_session, seed_base, fila_desde_at=antigo)
    db_session.commit()

    n = processar_distribuicao_timeout(db_session, limit=10)
    db_session.commit()
    assert n == 1
    db_session.refresh(ticket)
    assert ticket.atendente_id == seed_base["a1"].id

    hist = (
        db_session.query(TicketHistorico)
        .filter(TicketHistorico.ticket_id == ticket.id, TicketHistorico.campo == "atendente_id")
        .first()
    )
    assert hist is not None
    assert hist.valor_novo == str(seed_base["a1"].id)


def test_atribuicao_automatica_notifica(client, seed_base, db_session):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    db_session.commit()

    ticket = _criar_ticket_fila(db_session, seed_base)
    db_session.commit()

    atribuir_ticket_automaticamente(db_session, ticket, setor)
    db_session.commit()

    outbox = (
        db_session.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.ticket_id == ticket.id,
            NotificacaoEmailOutbox.tipo == "ticket_atribuido",
        )
        .first()
    )
    assert outbox is not None


def test_criar_ticket_auto_imediato_via_api(client, seed_base, auth_headers, db_session):
    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": setor.id,
            "assunto": "Novo com auto",
            "descricao": "Corpo",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["atendente_id"] == seed_base["a1"].id
