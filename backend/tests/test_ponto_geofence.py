"""Testes de geofence e política de geo (#844 / #984)."""


def _criar_local(client, headers, atendente_id: int, *, lat=-23.55052, lon=-46.633308, raio=500):
    return client.post(
        "/v1/ponto/locais",
        headers=headers,
        json={
            "atendente_id": atendente_id,
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


def _set_empresa_pin(client, headers, *, lat=-23.55052, lon=-46.633308, raio=200):
    return client.put(
        "/v1/settings/empresa-sistema",
        headers=headers,
        json={
            "nome": "Empresa Teste",
            "latitude": lat,
            "longitude": lon,
            "ponto_raio_metros": raio,
        },
    )


def test_ponto_geofence_obrigatoria_dentro(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1_id = seed_base["a1"].id
    assert _criar_local(client, admin, a1_id).status_code == 201
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
    assert _criar_local(client, admin, seed_base["a1"].id).status_code == 201
    assert _set_politica(client, admin, "obrigatoria").status_code == 200

    r = client.post("/v1/ponto/bater", headers=user, json={"tipo": "entrada"})
    assert r.status_code == 400
    assert "obrigat" in r.json()["detail"].lower()


def test_ponto_geofence_obrigatoria_fora(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    assert _criar_local(client, admin, seed_base["a1"].id, lat=-23.55, lon=-46.63, raio=100).status_code == 201
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
    assert _criar_local(client, admin, seed_base["a1"].id, lat=-23.55, lon=-46.63, raio=100).status_code == 201
    assert _set_politica(client, admin, "recomendada").status_code == 200

    r = client.post(
        "/v1/ponto/bater",
        headers=user,
        json={"tipo": "entrada", "latitude": -23.60, "longitude": -46.70},
    )
    assert r.status_code == 200, r.text
    assert r.json()["fora_area"] is True


def test_ponto_geofence_local_desativado_nao_conta(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1_id = seed_base["a1"].id
    r = _criar_local(client, admin, a1_id, lat=-23.55, lon=-46.63, raio=100)
    assert r.status_code == 201
    local_id = r.json()["id"]
    assert client.patch(
        f"/v1/ponto/locais/{local_id}",
        headers=admin,
        json={"ativo": False},
    ).status_code == 200
    assert _set_politica(client, admin, "obrigatoria").status_code == 200
    # Sem locais ativos: política obrigatória não bloqueia (igual a sem locais).
    r_bat = client.post(
        "/v1/ponto/bater",
        headers=user,
        json={"tipo": "entrada", "latitude": -23.55, "longitude": -46.63},
    )
    assert r_bat.status_code == 200, r_bat.text


def test_ponto_geofence_empresa_pin(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    assert _set_empresa_pin(client, admin, lat=-23.55, lon=-46.63, raio=150).status_code == 200
    assert _set_politica(client, admin, "obrigatoria").status_code == 200
    # usar_local_empresa default true
    r = client.post(
        "/v1/ponto/bater",
        headers=user,
        json={"tipo": "entrada", "latitude": -23.5501, "longitude": -46.6301},
    )
    assert r.status_code == 200, r.text
    assert r.json()["fora_area"] is False


def test_ponto_geofence_orfao_nao_conta(client, seed_base, auth_headers, db_session):
    """Locais sem atendente_id (legado) não entram no geofence."""
    from app.models.ponto_settings import PontoLocal

    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    row = PontoLocal(
        tenant_id=seed_base["a1"].tenant_id,
        atendente_id=None,
        nome="Legado",
        latitude=-23.55,
        longitude=-46.63,
        raio_metros=500,
        ativo=True,
    )
    db_session.add(row)
    db_session.commit()
    assert _set_politica(client, admin, "obrigatoria").status_code == 200
    r = client.post(
        "/v1/ponto/bater",
        headers=user,
        json={"tipo": "entrada", "latitude": -23.55, "longitude": -46.63},
    )
    # Sem locais do atendente: não bloqueia por geofence.
    assert r.status_code == 200, r.text


def test_ponto_locais_crud(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1_id = seed_base["a1"].id
    r = _criar_local(client, admin, a1_id)
    assert r.status_code == 201
    local_id = r.json()["id"]
    assert r.json()["atendente_id"] == a1_id
    lst = client.get(f"/v1/ponto/locais?atendente_id={a1_id}", headers=admin)
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

    assert _criar_local(client, admin, seed_base["a1"].id).status_code == 201
    r2 = client.get("/v1/ponto/me/settings", headers=auth_headers["a1"])
    assert r2.status_code == 200
    assert r2.json()["tem_locais_ativos"] is True


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
