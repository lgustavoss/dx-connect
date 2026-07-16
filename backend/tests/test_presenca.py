"""Presença online de atendentes (#546+)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.presenca import PRESENCA_TTL_SEC, tocar_presenca


def test_presenca_online_403_atendente(client, seed_base, auth_headers):
    r = client.get("/v1/presenca/online", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_presenca_online_admin_lista_vazia(client, seed_base, auth_headers):
    r = client.get("/v1/presenca/online", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert r.json() == {"itens": []}


def test_presenca_online_admin_ve_atendente_com_heartbeat(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    tocar_presenca(db_session, a1.id)
    db_session.commit()

    r = client.get("/v1/presenca/online", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    ids = {item["atendente_id"] for item in body["itens"]}
    assert a1.id in ids
    item = next(i for i in body["itens"] if i["atendente_id"] == a1.id)
    assert item["nome"] == a1.nome
    assert item["email"] == a1.email
    assert item["online_desde"]
    assert isinstance(item["setores"], list)


def test_presenca_ignora_heartbeat_expirado(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    antigo = datetime.now(timezone.utc) - timedelta(seconds=PRESENCA_TTL_SEC + 30)
    a1.presenca_online_desde = antigo
    a1.presenca_heartbeat_em = antigo
    db_session.add(a1)
    db_session.commit()

    r = client.get("/v1/presenca/online", headers=auth_headers["admin"])
    assert r.status_code == 200
    ids = {item["atendente_id"] for item in r.json()["itens"]}
    assert a1.id not in ids


def test_presenca_ignora_inativo(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    a1.ativo = False
    tocar_presenca(db_session, a1.id)
    db_session.add(a1)
    db_session.commit()

    try:
        r = client.get("/v1/presenca/online", headers=auth_headers["admin"])
        assert r.status_code == 200
        ids = {item["atendente_id"] for item in r.json()["itens"]}
        assert a1.id not in ids
    finally:
        a1.ativo = True
        a1.presenca_online_desde = None
        a1.presenca_heartbeat_em = None
        db_session.add(a1)
        db_session.commit()


def test_forcar_saida_invalida_token_e_remove_presenca(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    tocar_presenca(db_session, a1.id)
    db_session.commit()

    r_ok = client.get("/v1/atendentes/me", headers=auth_headers["a1"])
    assert r_ok.status_code == 200

    r = client.post(
        f"/v1/presenca/online/{a1.id}/forcar-saida",
        headers=auth_headers["admin"],
    )
    assert r.status_code == 204

    r_me = client.get("/v1/atendentes/me", headers=auth_headers["a1"])
    assert r_me.status_code == 401

    r_lista = client.get("/v1/presenca/online", headers=auth_headers["admin"])
    assert r_lista.status_code == 200
    ids = {item["atendente_id"] for item in r_lista.json()["itens"]}
    assert a1.id not in ids


def test_forcar_saida_403_atendente(client, seed_base, auth_headers):
    r = client.post(
        f"/v1/presenca/online/{seed_base['a1'].id}/forcar-saida",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 403


def test_forcar_saida_404(client, seed_base, auth_headers):
    r = client.post("/v1/presenca/online/999999/forcar-saida", headers=auth_headers["admin"])
    assert r.status_code == 404
