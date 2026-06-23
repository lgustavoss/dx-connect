"""Testes do dashboard geral (#282)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Ticket
from app.models.ticket_avaliacao import TicketAvaliacao
from app.models.whatsapp_chat import WhatsappChat
from app.services.dashboard_geral import CACHE_TTL_SECONDS, clear_dashboard_geral_cache


@pytest.fixture(autouse=True)
def _limpar_cache_dashboard():
    clear_dashboard_geral_cache()
    yield
    clear_dashboard_geral_cache()


def _criar_ticket(db_session, seed_base, *, setor_id, atendente_id=None, fechado=False):
    t = Ticket(
        tenant_id=1,
        protocolo=f"T{setor_id}-{atendente_id or 0}-{datetime.now().timestamp()}",
        empresa_id=seed_base["empresa"].id,
        setor_id=setor_id,
        status_id=seed_base["status"].id,
        atendente_id=atendente_id,
        assunto="Teste dashboard",
        fechado_em=datetime.now(timezone.utc) if fechado else None,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


def _criar_chat(db_session, seed_base, *, estado, setor_id=None, nota=None):
    suf = datetime.now().timestamp()
    c = WhatsappChat(
        protocolo=f"W{suf}",
        wa_id=f"5511999{suf}",
        estado=estado,
        setor_id=setor_id,
        avaliacao_nota=nota,
        avaliacao_respondida_at=datetime.now(timezone.utc) if nota is not None else None,
    )
    db_session.add(c)
    db_session.commit()
    return c


def test_dashboard_geral_admin_ve_global(client, seed_base, auth_headers, db_session):
    _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id)
    _criar_ticket(db_session, seed_base, setor_id=seed_base["setor2"].id, atendente_id=None)
    _criar_chat(db_session, seed_base, estado="aguardando_atendente", setor_id=seed_base["setor1"].id)
    _criar_chat(db_session, seed_base, estado="em_atendimento", setor_id=seed_base["setor2"].id)

    r = client.get("/v1/dashboard/geral", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["tickets_abertos"] == 2
    assert body["tickets_sem_responsavel"] == 2
    assert body["chats_aguardando_atendente"] == 1
    assert body["chats_em_atendimento"] == 1
    assert body["sla_violacoes_abertas"] == 0
    assert body["cache_ttl_segundos"] == CACHE_TTL_SECONDS
    assert body["csat_tickets"]["total_avaliacoes"] == 0
    assert body["csat_tickets"]["media"] is None


def test_dashboard_geral_atendente_escopo_setor(client, seed_base, auth_headers, db_session):
    _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id)
    _criar_ticket(db_session, seed_base, setor_id=seed_base["setor2"].id)
    _criar_chat(db_session, seed_base, estado="aguardando_atendente", setor_id=seed_base["setor1"].id)
    _criar_chat(db_session, seed_base, estado="aguardando_atendente", setor_id=seed_base["setor2"].id)

    r = client.get("/v1/dashboard/geral", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    assert body["tickets_abertos"] == 1
    assert body["chats_aguardando_atendente"] == 1

    r2 = client.get("/v1/dashboard/geral", headers=auth_headers["a2"])
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["tickets_abertos"] == 1
    assert body2["chats_aguardando_atendente"] == 1


def test_dashboard_geral_csat_7_dias(client, seed_base, auth_headers, db_session):
    t = _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id, fechado=True)
    db_session.add(
        TicketAvaliacao(
            ticket_id=t.id,
            atendente_id=seed_base["admin"].id,
            nota=5,
            respondida_em=datetime.now(timezone.utc) - timedelta(days=2),
        )
    )
    _criar_chat(db_session, seed_base, estado="encerrado", setor_id=seed_base["setor1"].id, nota=4)
    db_session.commit()

    r = client.get("/v1/dashboard/geral", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["csat_tickets"]["total_avaliacoes"] == 1
    assert body["csat_tickets"]["media"] == 5.0
    assert body["csat_chats"]["total_avaliacoes"] == 1
    assert body["csat_chats"]["media"] == 4.0


def test_dashboard_geral_requer_autenticacao(client):
    r = client.get("/v1/dashboard/geral")
    assert r.status_code == 401


def test_dashboard_geral_sla_violacoes_abertas(client, seed_base, auth_headers, db_session):
    _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id)
    violado_s1 = _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id)
    violado_s2 = _criar_ticket(db_session, seed_base, setor_id=seed_base["setor2"].id)
    fechado_violado = _criar_ticket(
        db_session, seed_base, setor_id=seed_base["setor1"].id, fechado=True
    )
    violado_s1.sla_violado = True
    violado_s2.sla_violado = True
    fechado_violado.sla_violado = True
    db_session.commit()

    r_admin = client.get("/v1/dashboard/geral", headers=auth_headers["admin"])
    assert r_admin.status_code == 200
    assert r_admin.json()["sla_violacoes_abertas"] == 2

    r_a1 = client.get("/v1/dashboard/geral", headers=auth_headers["a1"])
    assert r_a1.status_code == 200
    assert r_a1.json()["sla_violacoes_abertas"] == 1
