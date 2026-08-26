"""Perfil da conta ops (nome / e-mail) em Minha conta."""

from __future__ import annotations


def test_saas_me_atualizar_nome_e_email(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    h = auth_headers["ops"]

    nome = client.patch("/v1/saas/me", headers=h, json={"nome": "Ops Renomeado"})
    assert nome.status_code == 200, nome.text
    assert nome.json()["nome"] == "Ops Renomeado"
    assert nome.json()["access_token"] is None

    novo_email = "ops.renomeado@test.local"
    email = client.patch("/v1/saas/me", headers=h, json={"email": novo_email})
    assert email.status_code == 200, email.text
    assert email.json()["email"] == novo_email
    assert email.json()["access_token"]
    assert email.json()["refresh_token"]

    # Token antigo (sub = e-mail anterior) deixa de valer
    stale = client.get("/v1/saas/me/mcp-token", headers=h)
    assert stale.status_code == 401

    h_novo = {
        "Authorization": f"Bearer {email.json()['access_token']}",
        "X-Dx-Tenant-Id": "1",
    }
    ok = client.get("/v1/saas/me/mcp-token", headers=h_novo)
    assert ok.status_code == 200, ok.text

    me = client.get("/v1/atendentes/me", headers=h_novo)
    assert me.status_code == 200
    assert me.json()["email"] == novo_email
    assert me.json()["nome"] == "Ops Renomeado"


def test_saas_me_email_duplicado(client, seed_base, auth_headers, db_session, monkeypatch):
    from app.config import settings
    from app.core.security import hash_senha
    from app.models.atendente import Atendente

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    outro = Atendente(
        tenant_id=seed_base["tenant"].id,
        email="ops.outro@test.local",
        nome="Outro",
        senha_hash=hash_senha("ops123456"),
        role="saas_ops",
        ativo=True,
    )
    db_session.add(outro)
    db_session.commit()

    r = client.patch(
        "/v1/saas/me",
        headers=auth_headers["ops"],
        json={"email": "ops.outro@test.local"},
    )
    assert r.status_code == 400
