"""Testes SLA — modelo e políticas (#277)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.sla_policy import SlaPolicy
from app.models.ticket import Ticket
from app.services.sla_policy import aplicar_sla_snapshot_ao_ticket, resolve_sla_policy


def _criar_policy(db, seed_base, *, prioridade=None, primeira=60, resolucao=480):
    policy = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade=prioridade,
        meta_primeira_resposta_min=primeira,
        meta_resolucao_min=resolucao,
        ativo=True,
    )
    db.add(policy)
    db.flush()
    return policy


def test_criar_policy_via_api(client, seed_base, auth_headers):
    r = client.post(
        "/v1/sla/policies",
        headers=auth_headers["admin"],
        json={
            "setor_id": seed_base["setor1"].id,
            "prioridade": "alta",
            "meta_primeira_resposta_min": 30,
            "meta_resolucao_min": 240,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["setor_id"] == seed_base["setor1"].id
    assert body["prioridade"] == "alta"
    assert body["meta_primeira_resposta_min"] == 30
    assert body["meta_resolucao_min"] == 240


def test_policy_duplicada_rejeitada(client, seed_base, auth_headers, db_session):
    _criar_policy(db_session, seed_base, prioridade="normal")
    db_session.commit()

    r = client.post(
        "/v1/sla/policies",
        headers=auth_headers["admin"],
        json={
            "setor_id": seed_base["setor1"].id,
            "prioridade": "normal",
            "meta_primeira_resposta_min": 15,
            "meta_resolucao_min": 120,
        },
    )
    assert r.status_code == 400
    assert "Já existe" in r.json()["detail"]


def test_listar_e_atualizar_policy(client, seed_base, auth_headers, db_session):
    policy = _criar_policy(db_session, seed_base, prioridade=None, primeira=45, resolucao=300)
    db_session.commit()

    r = client.get("/v1/sla/policies", headers=auth_headers["admin"])
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert policy.id in ids

    r2 = client.put(
        f"/v1/sla/policies/{policy.id}",
        headers=auth_headers["admin"],
        json={"meta_primeira_resposta_min": 50, "ativo": False},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["meta_primeira_resposta_min"] == 50
    assert r2.json()["ativo"] is False


def test_resolve_prioridade_especifica_sobre_default(db_session, seed_base):
    _criar_policy(db_session, seed_base, prioridade=None, primeira=120, resolucao=600)
    especifica = _criar_policy(db_session, seed_base, prioridade="urgente", primeira=10, resolucao=60)
    db_session.commit()

    resolved = resolve_sla_policy(
        db_session,
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade="urgente",
    )
    assert resolved is not None
    assert resolved.id == especifica.id


def test_resolve_policy_por_natureza(db_session, seed_base):
    from app.models.ticket_classificacao import TicketMotivo, TicketNatureza

    padrao = _criar_policy(db_session, seed_base, prioridade="normal", primeira=120, resolucao=600)
    nat = TicketNatureza(nome="Erro SLA", slug="erro-sla-test", ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    mot = TicketMotivo(natureza_id=nat.id, nome="PDV", slug="pdv-sla-test", ordem=1, ativo=True)
    db_session.add(mot)
    db_session.flush()
    especifica = SlaPolicy(
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade="normal",
        natureza_id=nat.id,
        meta_primeira_resposta_min=15,
        meta_resolucao_min=90,
        ativo=True,
    )
    db_session.add(especifica)
    db_session.commit()

    resolved = resolve_sla_policy(
        db_session,
        tenant_id=1,
        setor_id=seed_base["setor1"].id,
        prioridade="normal",
        natureza_id=nat.id,
    )
    assert resolved is not None
    assert resolved.id == especifica.id
    assert resolved.id != padrao.id


def test_snapshot_na_criacao_ticket(client, seed_base, auth_headers, db_session):
    _criar_policy(db_session, seed_base, prioridade=None, primeira=60, resolucao=480)
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Ticket com SLA",
            "descricao": "Teste snapshot",
            "prioridade": "normal",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sla_policy_id"] is not None
    assert body["sla_meta_primeira_resposta_min"] == 60
    assert body["sla_meta_resolucao_min"] == 480
    assert body["sla_primeira_resposta_vence_em"] is not None
    assert body["sla_resolucao_vence_em"] is not None
    assert body["sla_violado"] is False


def test_aplicar_snapshot_em_ticket_existente(db_session, seed_base):
    from app.models.status_ticket import StatusTicket

    _criar_policy(db_session, seed_base, prioridade="alta", primeira=20, resolucao=100)
    st = db_session.query(StatusTicket).first()
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-SLA1",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="SLA unit",
        prioridade="alta",
    )
    db_session.add(ticket)
    db_session.flush()
    base = datetime(2026, 6, 23, 10, 0, tzinfo=timezone.utc)
    ticket.created_at = base
    aplicar_sla_snapshot_ao_ticket(db_session, ticket, base_time=base)
    assert ticket.sla_meta_primeira_resposta_min == 20
    assert ticket.sla_primeira_resposta_vence_em == base + timedelta(minutes=20)


def test_criar_calendario_comercial(client, seed_base, auth_headers):
    r = client.post(
        "/v1/sla/calendars",
        headers=auth_headers["admin"],
        json={
            "nome": "Comercial setor 1",
            "setor_id": seed_base["setor1"].id,
            "horario_inicio": "09:00",
            "horario_fim": "18:00",
            "usar_feriados_nacionais": True,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["nome"] == "Comercial setor 1"
    assert body["horario_inicio"] == "09:00"


def test_policy_com_calendario(client, seed_base, auth_headers):
    cal = client.post(
        "/v1/sla/calendars",
        headers=auth_headers["admin"],
        json={"nome": "Cal SLA", "horario_inicio": "08:00", "horario_fim": "17:00"},
    )
    assert cal.status_code == 201
    calendar_id = cal.json()["id"]

    r = client.post(
        "/v1/sla/policies",
        headers=auth_headers["admin"],
        json={
            "setor_id": seed_base["setor2"].id,
            "business_calendar_id": calendar_id,
            "meta_primeira_resposta_min": 45,
            "meta_resolucao_min": 360,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["business_calendar_id"] == calendar_id
    assert r.json()["business_calendar_nome"] == "Cal SLA"


def test_policy_rejeita_calendario_inativo(client, seed_base, auth_headers):
    cal = client.post(
        "/v1/sla/calendars",
        headers=auth_headers["admin"],
        json={"nome": "Cal inativo", "horario_inicio": "08:00", "horario_fim": "17:00", "ativo": False},
    )
    assert cal.status_code == 201
    calendar_id = cal.json()["id"]

    r = client.post(
        "/v1/sla/policies",
        headers=auth_headers["admin"],
        json={
            "setor_id": seed_base["setor2"].id,
            "business_calendar_id": calendar_id,
            "meta_primeira_resposta_min": 45,
            "meta_resolucao_min": 360,
        },
    )
    assert r.status_code == 400
    assert "inativo" in r.json()["detail"].lower()
