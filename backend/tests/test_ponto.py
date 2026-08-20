"""Controle de ponto (#761+)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.models.atendente import Atendente
from app.services.escala import eh_dia_de_trabalho, em_periodo_trabalho


def test_ponto_bater_entrada_saida(client, seed_base, auth_headers):
    r = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tipo"] == "entrada"
    assert body["atendente_id"] == seed_base["a1"].id

    me = client.get("/v1/ponto/me", headers=auth_headers["a1"])
    assert me.status_code == 200
    assert me.json()["em_jornada"] is True
    assert me.json()["entrada_aberta_em"]

    r2 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    assert r2.status_code == 400

    r3 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})
    assert r3.status_code == 200
    assert r3.json()["tipo"] == "saida"

    me2 = client.get("/v1/ponto/me", headers=auth_headers["a1"])
    assert me2.json()["em_jornada"] is False

    r4 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})
    assert r4.status_code == 400


def test_ponto_historico_proprio_e_totais(client, seed_base, auth_headers):
    r1 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    assert r1.status_code == 200, r1.text
    r2 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})
    assert r2.status_code == 200, r2.text

    r = client.get("/v1/ponto/me/batidas", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    # total = nº de intervalos (entrada+saída = 1 intervalo fechado)
    assert body["total"] >= 1
    assert len(body["intervalos"]) >= 1
    assert body["total_segundos_fechados"] >= 0
    assert body["intervalos"][0]["aberto"] is False


def test_ponto_admin_lista_e_403(client, seed_base, auth_headers):
    client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})

    r_403 = client.get("/v1/ponto/batidas", headers=auth_headers["a1"])
    assert r_403.status_code == 403

    r = client.get(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        params={"atendente_id": seed_base["a1"].id},
    )
    assert r.status_code == 200
    assert r.json()["total"] >= 2
    assert r.json()["items"][0]["atendente_nome"]


def test_ponto_comercial_bate(client, seed_base, auth_headers):
    r = client.post("/v1/ponto/bater", headers=auth_headers["comercial"], json={"tipo": "entrada"})
    assert r.status_code == 200
    r2 = client.post("/v1/ponto/bater", headers=auth_headers["comercial"], json={"tipo": "saida"})
    assert r2.status_code == 200


def test_ponto_saas_ops_403(client, seed_base, auth_headers):
    r = client.get("/v1/ponto/me", headers=auth_headers["ops"])
    assert r.status_code == 403


def test_escala_12x36_ciclo(db_session, seed_base):
    a1: Atendente = seed_base["a1"]
    a1.usa_escala = True
    a1.escala_horas_trabalho = 12
    a1.escala_horas_folga = 36
    a1.escala_inicio_em = date(2026, 1, 1)
    db_session.add(a1)
    db_session.commit()

    tz = ZoneInfo("America/Sao_Paulo")
    assert em_periodo_trabalho(a1, datetime(2026, 1, 1, 6, 0, tzinfo=tz)) is True
    assert em_periodo_trabalho(a1, datetime(2026, 1, 1, 18, 0, tzinfo=tz)) is False
    assert em_periodo_trabalho(a1, datetime(2026, 1, 2, 12, 0, tzinfo=tz)) is False
    assert em_periodo_trabalho(a1, datetime(2026, 1, 3, 0, 0, tzinfo=tz)) is True

    assert eh_dia_de_trabalho(a1, date(2026, 1, 1)) is True
    assert eh_dia_de_trabalho(a1, date(2026, 1, 2)) is False
    assert eh_dia_de_trabalho(a1, date(2026, 1, 3)) is True


def test_atendente_escala_patch(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    r = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={
            "usa_escala": True,
            "escala_horas_trabalho": 12,
            "escala_horas_folga": 36,
            "escala_inicio_em": "2026-08-01",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["usa_escala"] is True
    assert body["escala_horas_trabalho"] == 12
    assert body["escala_horas_folga"] == 36
    assert body["escala_inicio_em"] == "2026-08-01"

    r_bad = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={
            "usa_escala": True,
            "escala_horas_trabalho": 12,
            "escala_horas_folga": None,
            "escala_inicio_em": None,
        },
    )
    assert r_bad.status_code == 400

    cal = client.get(
        "/v1/ponto/me/calendario",
        headers=auth_headers["a1"],
        params={"ano": 2026, "mes": 8},
    )
    assert cal.status_code == 200
    assert cal.json()["usa_escala"] is True
    assert cal.json()["escala_rotulo"] == "12×36"
    assert len(cal.json()["dias"]) >= 28


def test_ponto_hoje_admin(client, seed_base, auth_headers):
    # Sem escala ainda pode listar (visão inclui quem tem usa_escala ou todos — ver serviço)
    r = client.get("/v1/ponto/hoje", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert "itens" in r.json()
    r403 = client.get("/v1/ponto/hoje", headers=auth_headers["a1"])
    assert r403.status_code == 403


def test_ponto_pausas_excluem_do_total(client, seed_base, auth_headers):
    h = auth_headers["a1"]
    assert client.post("/v1/ponto/bater", headers=h, json={"tipo": "entrada"}).status_code == 200
    assert client.post("/v1/ponto/bater", headers=h, json={"tipo": "pausa_inicio"}).status_code == 200
    me = client.get("/v1/ponto/me", headers=h).json()
    assert me["em_jornada"] is True
    assert me["em_pausa"] is True
    assert client.post("/v1/ponto/bater", headers=h, json={"tipo": "saida"}).status_code == 400
    assert client.post("/v1/ponto/bater", headers=h, json={"tipo": "pausa_fim"}).status_code == 200
    assert client.post("/v1/ponto/bater", headers=h, json={"tipo": "saida"}).status_code == 200

    hist = client.get("/v1/ponto/me/batidas", headers=h).json()
    assert hist["total"] >= 1
    it = hist["intervalos"][0]
    assert it["aberto"] is False
    assert "segundos_pausa" in it
    assert hist["total_segundos_pausa"] >= 0


def test_ponto_ajuste_admin_e_403(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    r403 = client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["a1"],
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": "2026-08-20T12:00:00+00:00",
            "motivo": "esquecimento",
        },
    )
    assert r403.status_code == 403

    r = client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": "2026-08-20T12:00:00+00:00",
            "motivo": "esquecimento de batida",
        },
    )
    assert r.status_code == 201, r.text
    bid = r.json()["id"]

    r2 = client.patch(
        f"/v1/ponto/batidas/{bid}",
        headers=auth_headers["admin"],
        json={"registrado_em": "2026-08-20T12:05:00+00:00", "motivo": "hora errada"},
    )
    assert r2.status_code == 200

    r3 = client.post(
        f"/v1/ponto/batidas/{bid}/anular",
        headers=auth_headers["admin"],
        json={"motivo": "batida duplicada"},
    )
    assert r3.status_code == 200
    assert r3.json()["anulada"] is True


def test_ponto_export_csv(client, seed_base, auth_headers):
    client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})
    r = client.get("/v1/ponto/batidas/export.csv", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    text = r.content.decode("utf-8-sig")
    assert "atendente" in text
    assert "trabalhado_min" in text
    r403 = client.get("/v1/ponto/batidas/export.csv", headers=auth_headers["a1"])
    assert r403.status_code == 403
