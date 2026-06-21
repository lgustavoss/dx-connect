"""Testes do relatório de tickets (D-08 / export CSV)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import Ticket


def _criar_ticket(db_session, seed_base):
    t = Ticket(
        tenant_id=1,
        protocolo=f"R{datetime.now().timestamp()}",
        empresa_id=seed_base["empresa"].id,
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
        status_id=seed_base["status"].id,
        assunto="Relatório teste",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(t)
    db_session.commit()
    return t


def test_relatorio_tickets_admin_json(client, seed_base, auth_headers, db_session):
    _criar_ticket(db_session, seed_base)
    r = client.get("/v1/relatorios/tickets", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert len(body["itens"]) >= 1
    assert body["itens"][0]["protocolo"]


def test_relatorio_tickets_atendente_403(client, seed_base, auth_headers, db_session):
    _criar_ticket(db_session, seed_base)
    r = client.get("/v1/relatorios/tickets", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_relatorio_tickets_export_csv(client, seed_base, auth_headers, db_session):
    _criar_ticket(db_session, seed_base)
    r = client.get(
        "/v1/relatorios/tickets",
        headers=auth_headers["admin"],
        params={"format": "csv"},
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    text = r.text
    assert text.startswith("\ufeff")
    assert "protocolo" in text
    assert "Relatório teste" in text
