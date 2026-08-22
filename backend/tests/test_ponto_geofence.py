"""Testes de geofence e política de geo (#844)."""

import pytest


def _criar_local(client, headers, *, lat=-23.55052, lon=-46.633308, raio=500):
    return client.post(
        "/v1/ponto/locais",
        headers=headers,
        json={
            "nome": "Matriz",
            "latitude": lat,
            "longitude": lon,
            "raio_metros": raio,
        },
    )


def _set_politica(client, headers, politica: str):
    return client.patch(
        "/v1/ponto/settings",
        headers=headers,
        json={"politica_geolocalizacao": politica},
    )


def test_ponto_geofence_obrigatoria_dentro(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    assert _criar_local(client, admin).status_code == 201
    assert _set_politica(client, admin, "obrigatoria").status_code == 200

    r = client.post(
        "/v1/ponto/bater",
        headers=user,
        json={
            "tipo": "entrada",
            "latitude": -23.55052,
            "longitude": -46.633308,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["fora_area"] is False


def test_ponto_geofence_obrigatoria_sem_geo(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    assert _criar_local(client, admin).status_code == 201
    assert _set_politica(client, admin, "obrigatoria").status_code == 200

    r = client.post("/v1/ponto/bater", headers=user, json={"tipo": "entrada"})
    assert r.status_code == 400
    assert "obrigat" in r.json()["detail"].lower()


def test_ponto_geofence_obrigatoria_fora(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    assert _criar_local(client, admin, lat=-23.55, lon=-46.63, raio=100).status_code == 201
    assert _set_politica(client, admin, "obrigatoria").status_code == 200

    r = client.post(
        "/v1/ponto/bater",
        headers=user,
        json={"tipo": "entrada", "latitude": -23.60, "longitude": -46.70},
    )
    assert r.status_code == 400
    assert "fora" in r.json()["detail"].lower()


def test_ponto_geofence_recomendada_fora_regista(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    assert _criar_local(client, admin, lat=-23.55, lon=-46.63, raio=100).status_code == 201
    assert _set_politica(client, admin, "recomendada").status_code == 200

    r = client.post(
        "/v1/ponto/bater",
        headers=user,
        json={"tipo": "entrada", "latitude": -23.60, "longitude": -46.70},
    )
    assert r.status_code == 200, r.text
    assert r.json()["fora_area"] is True


def test_ponto_locais_crud(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    r = _criar_local(client, admin)
    assert r.status_code == 201
    local_id = r.json()["id"]
    lst = client.get("/v1/ponto/locais", headers=admin)
    assert lst.status_code == 200
    assert any(x["id"] == local_id for x in lst.json())
    r_up = client.patch(
        f"/v1/ponto/locais/{local_id}",
        headers=admin,
        json={"nome": "Matriz atualizada", "ativo": False},
    )
    assert r_up.status_code == 200, r_up.text
    assert r_up.json()["nome"] == "Matriz atualizada"
    assert r_up.json()["ativo"] is False
    assert client.delete(f"/v1/ponto/locais/{local_id}", headers=admin).status_code == 204


def test_ponto_me_settings(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    _set_politica(client, admin, "recomendada")
    r = client.get("/v1/ponto/me/settings", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    assert body["politica_geolocalizacao"] == "recomendada"
    assert body["tem_locais_ativos"] is False


def test_ponto_export_pdf_xlsx(client, seed_base, auth_headers, monkeypatch):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    client.post("/v1/ponto/bater", headers=user, json={"tipo": "entrada"})
    client.post("/v1/ponto/bater", headers=user, json={"tipo": "saida"})

    monkeypatch.setattr("app.services.ponto_relatorio.html_para_pdf", lambda _html: b"%PDF-fake")

    r_pdf = client.get("/v1/ponto/batidas/export.pdf", headers=admin)
    assert r_pdf.status_code == 200
    assert r_pdf.headers["content-type"].startswith("application/pdf")

    r_xlsx = client.get("/v1/ponto/batidas/export.xlsx", headers=admin)
    assert r_xlsx.status_code == 200
    assert "spreadsheetml" in r_xlsx.headers["content-type"]
