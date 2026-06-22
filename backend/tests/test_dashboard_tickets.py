"""Testes do dashboard tickets (#283)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Ticket
from app.models.ticket_avaliacao import TicketAvaliacao
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.models.ticket import TicketHistorico, TicketMensagem
from app.services.dashboard_tickets import CACHE_TTL_SECONDS, clear_dashboard_tickets_cache


@pytest.fixture(autouse=True)
def _limpar_cache_dashboard_tickets():
    clear_dashboard_tickets_cache()
    yield
    clear_dashboard_tickets_cache()


def _criar_ticket(
    db_session,
    seed_base,
    *,
    setor_id,
    atendente_id=None,
    fechado=False,
    created_at=None,
    fechado_em=None,
    parent_ticket_id=None,
    motivo_id=None,
    prioridade="normal",
    rede_id=None,
):
    agora = datetime.now(timezone.utc)
    t = Ticket(
        tenant_id=1,
        protocolo=f"T{setor_id}-{datetime.now().timestamp()}",
        empresa_id=seed_base["empresa"].id,
        rede_id=rede_id or seed_base["rede"].id,
        setor_id=setor_id,
        status_id=seed_base["status"].id,
        atendente_id=atendente_id,
        parent_ticket_id=parent_ticket_id,
        motivo_id=motivo_id,
        prioridade=prioridade,
        assunto="Teste dashboard tickets",
        fechado_em=fechado_em or (agora if fechado else None),
        created_at=created_at or agora,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


def test_dashboard_tickets_periodo_default_e_volume(client, seed_base, auth_headers, db_session):
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id, created_at=ontem)
    _criar_ticket(
        db_session,
        seed_base,
        setor_id=seed_base["setor1"].id,
        fechado=True,
        created_at=ontem,
        fechado_em=ontem + timedelta(hours=2),
    )

    r = client.get("/v1/dashboard/tickets", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["cache_ttl_segundos"] == CACHE_TTL_SECONDS
    assert len(body["volume_por_dia"]) >= 2
    assert sum(d["abertos"] for d in body["volume_por_dia"]) >= 2
    assert sum(d["fechados"] for d in body["volume_por_dia"]) >= 1
    assert body["mttr_horas"] is not None


def test_dashboard_tickets_atendente_escopo_setor(client, seed_base, auth_headers, db_session):
    _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id)
    _criar_ticket(db_session, seed_base, setor_id=seed_base["setor2"].id)

    r = client.get("/v1/dashboard/tickets", headers=auth_headers["a1"])
    assert r.status_code == 200
    assert sum(d["abertos"] for d in r.json()["volume_por_dia"]) == 1

    r2 = client.get(
        "/v1/dashboard/tickets",
        headers=auth_headers["a1"],
        params={"setor_id": seed_base["setor2"].id},
    )
    assert r2.status_code == 200
    assert sum(d["abertos"] for d in r2.json()["volume_por_dia"]) == 0


def test_dashboard_tickets_motivo_canal_csat(client, seed_base, auth_headers, db_session):
    nat = TicketNatureza(nome="Operação", slug="operacao", ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    motivo = TicketMotivo(natureza_id=nat.id, nome="Falha PDV", slug="falha_pdv", ordem=1, ativo=True)
    db_session.add(motivo)
    db_session.flush()

    parent = _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id)
    filho = _criar_ticket(
        db_session,
        seed_base,
        setor_id=seed_base["setor1"].id,
        parent_ticket_id=parent.id,
    )
    email_t = _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id, motivo_id=motivo.id)
    db_session.add(
        TicketMensagem(
            ticket_id=email_t.id,
            atendente_id=None,
            tipo="email_cliente",
            corpo="Corpo e-mail",
        )
    )
    fechado = _criar_ticket(
        db_session,
        seed_base,
        setor_id=seed_base["setor1"].id,
        fechado=True,
        atendente_id=seed_base["admin"].id,
    )
    db_session.add(
        TicketAvaliacao(
            ticket_id=fechado.id,
            atendente_id=seed_base["admin"].id,
            nota=4,
            respondida_em=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        TicketHistorico(
            ticket_id=fechado.id,
            atendente_id=seed_base["admin"].id,
            campo="atendente_id",
            valor_antigo=None,
            valor_novo=str(seed_base["admin"].id),
            created_at=fechado.created_at + timedelta(minutes=30),
        )
    )
    db_session.commit()

    r = client.get("/v1/dashboard/tickets", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    canais = {c["canal"]: c["total"] for c in body["por_canal"]}
    assert canais.get("filho_massa", 0) >= 1
    assert canais.get("email", 0) >= 1
    assert any(m["nome"] == "Falha PDV" for m in body["por_motivo"])
    assert body["csat"]["total_avaliacoes"] >= 1
    assert body["csat"]["media"] == 4.0
    assert body["fila_tempo_medio_horas"] is not None
    assert filho.id  # evita lint unused


def test_dashboard_tickets_requer_autenticacao(client):
    r = client.get("/v1/dashboard/tickets")
    assert r.status_code == 401


def test_dashboard_tickets_filtro_prioridade(client, seed_base, auth_headers, db_session):
    _criar_ticket(
        db_session,
        seed_base,
        setor_id=seed_base["setor1"].id,
        prioridade="urgente",
    )
    _criar_ticket(
        db_session,
        seed_base,
        setor_id=seed_base["setor1"].id,
        prioridade="baixa",
    )

    r = client.get(
        "/v1/dashboard/tickets",
        headers=auth_headers["admin"],
        params={"prioridade": "urgente"},
    )
    assert r.status_code == 200
    body = r.json()
    assert sum(d["abertos"] for d in body["volume_por_dia"]) == 1
    assert body["por_prioridade"] == [{"prioridade": "urgente", "total": 1}]


def test_dashboard_tickets_top_empresa(client, seed_base, auth_headers, db_session):
    _criar_ticket(db_session, seed_base, setor_id=seed_base["setor1"].id)
    r = client.get("/v1/dashboard/tickets", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert len(body["por_empresa"]) >= 1
    assert body["por_empresa"][0]["nome"] == "Empresa Teste"
