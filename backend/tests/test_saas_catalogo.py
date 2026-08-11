"""Catálogo comercial de planos e módulos SaaS."""

from __future__ import annotations

from datetime import date


def _seed_catalogo(db_session):
    from app.models.saas_plano import SaasModulo, SaasPlano, SaasPlanoModulo

    mods = [
        SaasModulo(codigo="helpdesk", nome="Helpdesk / tickets", ativo=True),
        SaasModulo(codigo="boletos", nome="Boletos", ativo=True),
        SaasModulo(codigo="contratos", nome="Contratos", ativo=True),
    ]
    db_session.add_all(mods)
    db_session.flush()
    trial = SaasPlano(codigo="trial", nome="Trial", ativo=True, ordem=10)
    pro = SaasPlano(codigo="profissional", nome="Profissional", ativo=True, ordem=20)
    db_session.add_all([trial, pro])
    db_session.flush()
    db_session.add(SaasPlanoModulo(plano_id=trial.id, modulo_id=mods[0].id))
    db_session.add(SaasPlanoModulo(plano_id=pro.id, modulo_id=mods[0].id))
    db_session.add(SaasPlanoModulo(plano_id=pro.id, modulo_id=mods[1].id))
    db_session.commit()
    return {"helpdesk": mods[0], "boletos": mods[1], "contratos": mods[2], "trial": trial, "pro": pro}


def test_catalogo_403_atendente(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    assert client.get("/v1/saas/planos", headers=auth_headers["a1"]).status_code == 403
    assert client.get("/v1/saas/modulos", headers=auth_headers["a1"]).status_code == 403


def test_catalogo_404_desligado(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    assert client.get("/v1/saas/planos", headers=auth_headers["ops"]).status_code == 404


def test_planos_modulos_crud_e_licenca(client, auth_headers, db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_PROVISION_BASE_DOMAIN", "deskrudder.com.br")
    h = auth_headers["ops"]
    seed = _seed_catalogo(db_session)

    planos = client.get("/v1/saas/planos", headers=h)
    assert planos.status_code == 200, planos.text
    assert len(planos.json()) >= 2
    assert any(p["codigo"] == "trial" for p in planos.json())

    ativos = client.get("/v1/saas/planos?ativo=true", headers=h)
    assert ativos.status_code == 200
    assert all(p["ativo"] for p in ativos.json())

    modulos = client.get("/v1/saas/modulos", headers=h)
    assert modulos.status_code == 200
    assert len(modulos.json()) >= 3

    novo_mod = client.post(
        "/v1/saas/modulos",
        headers=h,
        json={"codigo": "nfe", "nome": "NFe", "descricao": "Notas fiscais"},
    )
    assert novo_mod.status_code == 201, novo_mod.text
    mid = novo_mod.json()["id"]

    novo_plano = client.post(
        "/v1/saas/planos",
        headers=h,
        json={
            "codigo": "custom",
            "nome": "Custom",
            "ordem": 50,
            "modulo_ids": [seed["helpdesk"].id, mid],
        },
    )
    assert novo_plano.status_code == 201, novo_plano.text
    pid = novo_plano.json()["id"]
    assert len(novo_plano.json()["modulos"]) == 2

    patch = client.patch(
        f"/v1/saas/planos/{pid}",
        headers=h,
        json={"nome": "Custom Plus", "modulo_ids": [seed["helpdesk"].id]},
    )
    assert patch.status_code == 200
    assert patch.json()["nome"] == "Custom Plus"
    assert len(patch.json()["modulos"]) == 1

    off = client.post(f"/v1/saas/planos/{pid}/desativar", headers=h)
    assert off.status_code == 200
    assert off.json()["ativo"] is False

    # Plano inactivo não pode ser atribuído a licença nova
    criar_fail = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Fail Co",
            "slug": "fail-co",
            "status": "trial",
            "data_inicio": str(date.today()),
            "plano_id": pid,
        },
    )
    assert criar_fail.status_code == 400

    on = client.post(f"/v1/saas/planos/{pid}/ativar", headers=h)
    assert on.status_code == 200

    criar = client.post(
        "/v1/saas/clientes",
        headers=h,
        json={
            "nome": "Plan Co",
            "slug": "plan-co",
            "status": "trial",
            "data_inicio": str(date.today()),
            "plano_id": pid,
        },
    )
    assert criar.status_code == 201, criar.text
    body = criar.json()
    assert body["plano_id"] == pid
    assert body["plano"] == "Custom Plus"
    assert any(m["codigo"] == "helpdesk" for m in body["plano_modulos"])

    # Desactivar plano já ligado — licença mantém; update com o mesmo plano_id ok
    client.post(f"/v1/saas/planos/{pid}/desativar", headers=h)
    keep = client.patch(
        f"/v1/saas/clientes/{body['id']}",
        headers=h,
        json={"plano_id": pid, "contato_nome": "Ops"},
    )
    assert keep.status_code == 200, keep.text
    assert keep.json()["plano_id"] == pid

    # Trocar para outro plano activo
    trocar = client.patch(
        f"/v1/saas/clientes/{body['id']}",
        headers=h,
        json={"plano_id": seed["trial"].id},
    )
    assert trocar.status_code == 200
    assert trocar.json()["plano_id"] == seed["trial"].id
    assert trocar.json()["plano"] == "Trial"

    desativar_mod = client.post(f"/v1/saas/modulos/{mid}/desativar", headers=h)
    assert desativar_mod.status_code == 200
    assert desativar_mod.json()["ativo"] is False
