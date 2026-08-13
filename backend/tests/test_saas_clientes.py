"""API e modelo do painel SaaS / licenças (#521–#522)."""

from __future__ import annotations

from datetime import date


def test_saas_desligado_404(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.get("/v1/saas/clientes", headers=auth_headers["ops"])
    assert r.status_code == 404


def test_saas_atendente_403(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.get("/v1/saas/clientes", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_saas_admin_tenant_403(client, auth_headers, monkeypatch):
    """Admin do painel de atendimento não acede às APIs SaaS (só saas_ops)."""
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    r = client.get("/v1/saas/clientes", headers=auth_headers["admin"])
    assert r.status_code == 403


def test_saas_crud_admin(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]

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
            "contato_nome": "Luis Duplex",
            "contato_email": "luis@duplex.example",
            "notas": "Cliente piloto",
        },
    )
    assert criar.status_code == 201, criar.text
    body = criar.json()
    assert body["slug"] == "duplex-soft"
    assert body["status"] == "trial"
    assert body["instancia_url"] == "https://duplex-soft.deskrudder.com.br/"
    assert body["contato_nome"] == "Luis Duplex"
    assert body["contato_email"] == "luis@duplex.example"
    cid = body["id"]

    lista = client.get("/v1/saas/clientes", headers=h)
    assert lista.status_code == 200
    assert lista.json()["total"] >= 1

    busca_email = client.get("/v1/saas/clientes?busca=luis@duplex", headers=h)
    assert busca_email.status_code == 200
    assert any(i["id"] == cid for i in busca_email.json()["items"])

    detalhe = client.get(f"/v1/saas/clientes/{cid}", headers=h)
    assert detalhe.status_code == 200
    assert detalhe.json()["nome"] == "Duplex Soft"

    patch = client.patch(
        f"/v1/saas/clientes/{cid}",
        headers=h,
        json={"status": "ativo", "plano": "enterprise", "contato_email": "ops@duplex.example"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "ativo"
    assert patch.json()["plano"] == "enterprise"
    assert patch.json()["contato_email"] == "ops@duplex.example"
    assert patch.json()["instancia_url"] == "https://duplex-soft.deskrudder.com.br/"

    email_invalido = client.patch(
        f"/v1/saas/clientes/{cid}",
        headers=h,
        json={"contato_email": "nao-e-email"},
    )
    assert email_invalido.status_code == 422

    susp = client.post(f"/v1/saas/clientes/{cid}/suspender", headers=h)
    assert susp.status_code == 200
    assert susp.json()["status"] == "suspenso"

    reat = client.post(f"/v1/saas/clientes/{cid}/reativar", headers=h)
    assert reat.status_code == 200
    assert reat.json()["status"] == "ativo"

    # Body livre é ignorado: URL vem sempre do slug + domínio base.
    reg = client.post(
        f"/v1/saas/clientes/{cid}/registrar-instancia",
        headers=h,
        json={"instancia_url": "https://cliente01.deskrudder.com.br"},
    )
    assert reg.status_code == 200
    assert reg.json()["instancia_url"] == "https://duplex-soft.deskrudder.com.br/"

    prov = client.post(f"/v1/saas/clientes/{cid}/solicitar-provisionamento", headers=h)
    assert prov.status_code == 200
    assert prov.json()["provisionamento_solicitado"] is True


def test_saas_resumo_ops(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_RENEWAL_ALERT_DAYS_BEFORE", 14)
    h = auth_headers["ops"]

    client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Resumo Co",
            "slug": "resumo-co",
            "status": "ativo",
            "data_inicio": str(date.today()),
            "data_renovacao": str(date.today()),
        },
    )
    r = client.get("/v1/saas/resumo", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["clientes_total"] >= 1
    assert "por_status" in body
    assert body["janela_renovacao_dias"] == 14
    assert "vencendo_em_breve" in body
    assert "leads_novos" in body
    assert body.get("base_dominio_provisionamento")


def test_saas_resumo_desligado_404(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.get("/v1/saas/resumo", headers=auth_headers["ops"])
    assert r.status_code == 404


def test_saas_slug_duplicado_409(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    h = auth_headers["ops"]
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
        headers=auth_headers["ops"],
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
    r = client.get("/v1/system/info", headers=auth_headers["ops"])
    assert r.status_code == 200
    assert r.json()["saas_control_plane"] is True
