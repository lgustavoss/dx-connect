"""Dia convocado — trabalho fora da grade (#985)."""

from datetime import date, datetime, timedelta, timezone

from app.services.escala import PONTO_TZ


def _folga_total(client, headers, atendente_id: int):
    return client.patch(
        f"/v1/atendentes/{atendente_id}",
        headers=headers,
        json={"modo_jornada": "nenhum", "usa_escala": False},
    )


def test_convocado_folga_gera_falta_e_esperado(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    assert _folga_total(client, admin, a1.id).status_code == 200
    amanha = date.today() + timedelta(days=1)
    r = client.post(
        "/v1/ponto/convocados/conceder",
        headers=admin,
        json={
            "atendente_id": a1.id,
            "data_ref": amanha.isoformat(),
            "inicio": "09:00",
            "fim": "13:00",
            "motivo": "Inventário no posto",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "ativa"
    assert body["inicio"] == "09:00"
    cal = client.get(
        f"/v1/ponto/me/calendario?ano={amanha.year}&mes={amanha.month}",
        headers=user,
    )
    assert cal.status_code == 200
    dia = next(d for d in cal.json()["dias"] if d["data"] == amanha.isoformat())
    assert dia["esperado"] is True
    assert dia["dia_convocado"] is True
    assert dia["status"] == "falta"
    assert dia["segundos_esperados"] == 4 * 3600


def test_convocado_atraso_usa_janela_propria(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    assert _folga_total(client, admin, a1.id).status_code == 200
    alvo = date.today() + timedelta(days=2)
    assert (
        client.post(
            "/v1/ponto/convocados/conceder",
            headers=admin,
            json={
                "atendente_id": a1.id,
                "data_ref": alvo.isoformat(),
                "inicio": "08:00",
                "fim": "12:00",
                "motivo": "Plantão",
                "tolerancia_minutos": 0,
            },
        ).status_code
        == 201
    )
    entrada = datetime(alvo.year, alvo.month, alvo.day, 8, 30, tzinfo=PONTO_TZ)
    bat = client.post(
        "/v1/ponto/batidas",
        headers=admin,
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": entrada.astimezone(timezone.utc).isoformat(),
            "motivo": "teste convocado atraso",
        },
    )
    assert bat.status_code == 201, bat.text
    cal = client.get(
        f"/v1/ponto/me/calendario?ano={alvo.year}&mes={alvo.month}",
        headers=user,
    )
    dia = next(d for d in cal.json()["dias"] if d["data"] == alvo.isoformat())
    assert dia["atrasado"] is True


def test_convocado_cancelar_futuro(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1 = seed_base["a1"]
    assert _folga_total(client, admin, a1.id).status_code == 200
    futuro = date.today() + timedelta(days=5)
    criado = client.post(
        "/v1/ponto/convocados/conceder",
        headers=admin,
        json={
            "atendente_id": a1.id,
            "data_ref": futuro.isoformat(),
            "inicio": "10:00",
            "fim": "14:00",
            "motivo": "Evento",
        },
    )
    assert criado.status_code == 201
    cid = criado.json()["id"]
    cancel = client.delete(f"/v1/ponto/convocados/{cid}", headers=admin)
    assert cancel.status_code == 200
    assert cancel.json()["estado"] == "cancelada"
    lista = client.get("/v1/ponto/convocados?estado=ativa", headers=admin)
    assert all(x["id"] != cid for x in lista.json())


def test_convocado_cancelar_reverte_calendario(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    assert _folga_total(client, admin, a1.id).status_code == 200
    futuro = date.today() + timedelta(days=4)
    criado = client.post(
        "/v1/ponto/convocados/conceder",
        headers=admin,
        json={
            "atendente_id": a1.id,
            "data_ref": futuro.isoformat(),
            "inicio": "09:00",
            "fim": "13:00",
            "motivo": "Inventário",
        },
    )
    assert criado.status_code == 201
    cid = criado.json()["id"]
    cal1 = client.get(
        f"/v1/ponto/me/calendario?ano={futuro.year}&mes={futuro.month}",
        headers=user,
    )
    dia1 = next(d for d in cal1.json()["dias"] if d["data"] == futuro.isoformat())
    assert dia1["esperado"] is True
    assert client.delete(f"/v1/ponto/convocados/{cid}", headers=admin).status_code == 200
    cal2 = client.get(
        f"/v1/ponto/me/calendario?ano={futuro.year}&mes={futuro.month}",
        headers=user,
    )
    dia2 = next(d for d in cal2.json()["dias"] if d["data"] == futuro.isoformat())
    assert dia2["esperado"] is False
    assert dia2["dia_convocado"] is False
    assert dia2["status"] in ("folga", "livre")


def test_convocado_conflita_com_ausencia(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1 = seed_base["a1"]
    dia = date.today() + timedelta(days=3)
    assert (
        client.post(
            "/v1/ponto/ausencias/conceder",
            headers=admin,
            json={
                "atendente_id": a1.id,
                "tipo": "folga_programada",
                "desde": dia.isoformat(),
                "ate": dia.isoformat(),
                "motivo": "Folga",
            },
        ).status_code
        == 201
    )
    r = client.post(
        "/v1/ponto/convocados/conceder",
        headers=admin,
        json={
            "atendente_id": a1.id,
            "data_ref": dia.isoformat(),
            "inicio": "08:00",
            "fim": "12:00",
            "motivo": "Conflito",
        },
    )
    assert r.status_code == 400
