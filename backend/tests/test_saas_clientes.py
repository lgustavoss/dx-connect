"""API e modelo do painel SaaS / licenças (#521–#522)."""

from __future__ import annotations

from datetime import date


def test_saas_desligado_404(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.get("/v1/saas/clientes", headers=auth_headers["admin"])
    assert r.status_code == 404


def test_saas_atendente_403(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.get("/v1/saas/clientes", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_saas_crud_admin(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    h = auth_headers["admin"]

    criar = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Duplex Soft",
            "slug": "duplex-soft",
            "status": "trial",
            "plano": "profissional",
            "data_inicio": str(date.today()),
            "data_renovacao": str(date.today()),
            "instancia_url": "duplexsoft.deskrudder.com.br",
            "notas": "Cliente piloto",
        },
    )
    assert criar.status_code == 201, criar.text
    body = criar.json()
    assert body["slug"] == "duplex-soft"
    assert body["status"] == "trial"
    assert body["instancia_url"].startswith("https://")
    cid = body["id"]

    lista = client.get("/v1/saas/clientes", headers=h)
    assert lista.status_code == 200
    assert lista.json()["total"] >= 1

    detalhe = client.get(f"/v1/saas/clientes/{cid}", headers=h)
    assert detalhe.status_code == 200
    assert detalhe.json()["nome"] == "Duplex Soft"

    patch = client.patch(
        f"/v1/saas/clientes/{cid}",
        headers=h,
        json={"status": "ativo", "plano": "enterprise"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "ativo"
    assert patch.json()["plano"] == "enterprise"

    susp = client.post(f"/v1/saas/clientes/{cid}/suspender", headers=h)
    assert susp.status_code == 200
    assert susp.json()["status"] == "suspenso"

    reat = client.post(f"/v1/saas/clientes/{cid}/reativar", headers=h)
    assert reat.status_code == 200
    assert reat.json()["status"] == "ativo"

    reg = client.post(
        f"/v1/saas/clientes/{cid}/registrar-instancia",
        headers=h,
        json={"instancia_url": "https://cliente01.deskrudder.com.br"},
    )
    assert reg.status_code == 200
    assert "cliente01.deskrudder.com.br" in reg.json()["instancia_url"]

    prov = client.post(f"/v1/saas/clientes/{cid}/solicitar-provisionamento", headers=h)
    assert prov.status_code == 200
    assert prov.json()["provisionamento_solicitado"] is True


def test_saas_slug_duplicado_409(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    h = auth_headers["admin"]
    payload = {
        "nome": "A",
        "slug": "mesmo-slug",
        "status": "ativo",
        "data_inicio": str(date.today()),
    }
    assert client.post("/v1/saas/clientes", headers=h, json=payload).status_code == 201
    r = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={**payload, "nome": "B"},
    )
    assert r.status_code == 409


def test_saas_slug_invalido_422(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.post(
        "/v1/saas/clientes",
        headers=auth_headers["admin"],
        json={
            "nome": "X",
            "slug": "Invalid_Slug!",
            "status": "trial",
            "data_inicio": str(date.today()),
        },
    )
    assert r.status_code == 422


def test_system_info_expõe_saas_flag(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.get("/v1/system/info", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert r.json()["saas_control_plane"] is True
