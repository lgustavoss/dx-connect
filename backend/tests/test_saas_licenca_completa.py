"""Controle de licenças: snapshot, timeline, plano no lead, preço/limites."""

from __future__ import annotations

from datetime import date


def _seed_plano_com_modulos(db_session, *, preco=199.9, max_postos=10, max_usuarios=5):
    from app.models.saas_plano import SaasModulo, SaasPlano, SaasPlanoModulo

    m1 = SaasModulo(codigo="helpdesk", nome="Helpdesk", ativo=True)
    m2 = SaasModulo(codigo="whatsapp", nome="WhatsApp", ativo=True)
    db_session.add_all([m1, m2])
    db_session.flush()
    plano = SaasPlano(
        codigo="pro-lic",
        nome="Pro Licença",
        ativo=True,
        ordem=20,
        preco_mensal=preco,
        max_postos=max_postos,
        max_usuarios=max_usuarios,
    )
    db_session.add(plano)
    db_session.flush()
    db_session.add(SaasPlanoModulo(plano_id=plano.id, modulo_id=m1.id))
    db_session.add(SaasPlanoModulo(plano_id=plano.id, modulo_id=m2.id))
    db_session.commit()
    return plano


def test_plano_preco_limites_e_snapshot(client, auth_headers, db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]
    plano = _seed_plano_com_modulos(db_session)

    planos = client.get("/v1/saas/planos", headers=h)
    assert planos.status_code == 200
    found = next(p for p in planos.json() if p["id"] == plano.id)
    assert float(found["preco_mensal"]) == 199.9
    assert found["max_postos"] == 10
    assert found["max_usuarios"] == 5

    r = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Lic Snapshot",
            "slug": "lic-snap",
            "status": "ativo",
            "data_inicio": str(date.today()),
            "plano_id": plano.id,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert sorted(body.get("modulos_snapshot") or []) == ["helpdesk", "whatsapp"]
    assert body["max_postos"] == 10
    assert body["max_usuarios"] == 5
    assert body["plano"] == "Pro Licença"

    tid = body["id"]
    tl = client.get(f"/v1/saas/clientes/{tid}/timeline", headers=h)
    assert tl.status_code == 200, tl.text
    assert isinstance(tl.json(), list)
    assert any(ev["action"] == "create" for ev in tl.json())

    resumo = client.get("/v1/saas/resumo", headers=h)
    assert resumo.status_code == 200
    assert "instancias" in resumo.json()


def test_converter_lead_com_plano_id(client, auth_headers, db_session, monkeypatch):
    from app.config import settings
    from app.models.lead_comercial import LeadComercial

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]
    plano = _seed_plano_com_modulos(db_session, preco=49, max_postos=3, max_usuarios=2)

    lead = LeadComercial(
        nome="Lead Plano",
        email="lead-plano@test.local",
        mensagem="Quero trial",
        status="novo",
    )
    db_session.add(lead)
    db_session.commit()

    conv = client.post(
        f"/v1/saas/leads/{lead.id}/converter",
        headers=h,
        json={"enfileirar_provisionamento": False, "plano_id": plano.id, "slug": "lead-plano-lic"},
    )
    assert conv.status_code == 201, conv.text
    body = conv.json()
    assert body["plano_id"] == plano.id
    assert sorted(body.get("modulos_snapshot") or []) == ["helpdesk", "whatsapp"]
    assert body["max_postos"] == 3
