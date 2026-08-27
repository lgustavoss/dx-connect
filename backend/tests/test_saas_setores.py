"""Setores (cargos) da equipe SaaS + vínculo N:N com usuários ops."""

from __future__ import annotations

from app.core.security import criar_access_token


def _headers_ops(email: str) -> dict[str, str]:
    tok = criar_access_token({"sub": email, "tid": 1})
    return {"Authorization": f"Bearer {tok}", "X-Dx-Tenant-Id": "1"}


def test_saas_setores_crud_e_vinculo_multiplo(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)

    assert client.get("/v1/saas/setores", headers=auth_headers["admin"]).status_code == 403

    a = client.post("/v1/saas/setores", headers=auth_headers["ops"], json={"nome": "  Admin  "})
    assert a.status_code == 201, a.text
    assert a.json()["nome"] == "Admin"

    d = client.post("/v1/saas/setores", headers=auth_headers["ops"], json={"nome": "Desenvolvimento"})
    assert d.status_code == 201, d.text
    c = client.post("/v1/saas/setores", headers=auth_headers["ops"], json={"nome": "Comercial"})
    assert c.status_code == 201, c.text

    dup = client.post("/v1/saas/setores", headers=auth_headers["ops"], json={"nome": "admin"})
    assert dup.status_code == 400

    lista = client.get("/v1/saas/setores", headers=auth_headers["ops"])
    assert lista.status_code == 200
    nomes = [x["nome"] for x in lista.json()]
    assert nomes == sorted(nomes)
    assert "Admin" in nomes

    criado = client.post(
        "/v1/saas/usuarios",
        headers=auth_headers["ops"],
        json={
            "nome": "Luis Multi",
            "email": "luis.multi@test.local",
            "setor_ids": [a.json()["id"], d.json()["id"]],
        },
    )
    assert criado.status_code == 201, criado.text
    body = criado.json()
    assert sorted(body["setor_ids"]) == sorted([a.json()["id"], d.json()["id"]])
    assert {s["nome"] for s in body["setores"]} == {"Admin", "Desenvolvimento"}

    patch = client.patch(
        f"/v1/saas/usuarios/{body['id']}",
        headers=auth_headers["ops"],
        json={"setor_ids": [c.json()["id"], a.json()["id"]]},
    )
    assert patch.status_code == 200, patch.text
    assert {s["nome"] for s in patch.json()["setores"]} == {"Admin", "Comercial"}

    login = client.post(
        "/v1/auth/login",
        json={"email": body["email"], "senha": body["senha_temporaria"]},
    )
    assert login.status_code == 200
    me = client.get("/v1/atendentes/me", headers=_headers_ops(body["email"]))
    assert me.status_code == 200, me.text
    assert set(me.json()["saas_setor_nomes"]) == {"Admin", "Comercial"}


def test_saas_setores_inativo_nao_vincula(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    s = client.post("/v1/saas/setores", headers=auth_headers["ops"], json={"nome": "Temporário"}).json()
    off = client.patch(
        f"/v1/saas/setores/{s['id']}",
        headers=auth_headers["ops"],
        json={"ativo": False},
    )
    assert off.status_code == 200
    assert off.json()["ativo"] is False

    bad = client.post(
        "/v1/saas/usuarios",
        headers=auth_headers["ops"],
        json={"nome": "X", "email": "x.setores@test.local", "setor_ids": [s["id"]]},
    )
    assert bad.status_code == 400
