"""Cadastro da equipa saas_ops no painel (#883)."""

from __future__ import annotations

from app.core.security import criar_access_token, hash_senha
from app.models.atendente import Atendente


def _headers_ops(email: str) -> dict[str, str]:
    tok = criar_access_token({"sub": email, "tid": 1})
    return {"Authorization": f"Bearer {tok}", "X-Dx-Tenant-Id": "1"}


def test_saas_usuarios_404_sem_control_plane(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", False)
    r = client.get("/v1/saas/usuarios", headers=auth_headers["ops"])
    assert r.status_code == 404


def test_saas_usuarios_admin_helpdesk_403(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    assert client.get("/v1/saas/usuarios", headers=auth_headers["admin"]).status_code == 403


def test_saas_usuarios_criar_login_e_token_cursor(client, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    monkeypatch.setattr(settings, "SAAS_INSTANCE_SLUG", "local")
    criado = client.post(
        "/v1/saas/usuarios",
        headers=auth_headers["ops"],
        json={"nome": "Dev Cursor", "email": "dev.cursor@test.local"},
    )
    assert criado.status_code == 201, criado.text
    body = criado.json()
    senha = body["senha_temporaria"]
    assert len(senha) >= 8
    assert body["must_change_password"] is True
    assert body["mcp_token_configurado"] is False
    assert "mcp_token_hash" not in body

    login = client.post("/v1/auth/login", json={"email": body["email"], "senha": senha})
    assert login.status_code == 200, login.text
    assert login.json()["must_change_password"] is True

    h_dev = _headers_ops(body["email"])
    troca = client.post(
        "/v1/atendentes/me/trocar-senha",
        headers=h_dev,
        json={"senha_atual": senha, "senha_nova": "novaSenhaSegura1"},
    )
    assert troca.status_code == 200, troca.text
    token = client.post("/v1/saas/me/mcp-token", headers=h_dev)
    assert token.status_code == 200, token.text
    listed = client.get("/v1/saas/solicitacoes", headers={"Authorization": f"Bearer {token.json()['token']}"})
    assert listed.status_code == 200, listed.text

    lista = client.get("/v1/saas/usuarios", headers=auth_headers["ops"])
    assert lista.status_code == 200
    row = next(i for i in lista.json()["items"] if i["email"] == body["email"])
    assert row["mcp_token_configurado"] is True


def test_saas_usuarios_nao_desactiva_ultimo_nem_a_si(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    ops_id = seed_base["ops"].id
    self_off = client.patch(
        f"/v1/saas/usuarios/{ops_id}",
        headers=auth_headers["ops"],
        json={"ativo": False},
    )
    assert self_off.status_code == 400

    outro = client.post(
        "/v1/saas/usuarios",
        headers=auth_headers["ops"],
        json={"nome": "Ops Extra", "email": "ops.extra@test.local"},
    ).json()
    extra_off = client.patch(
        f"/v1/saas/usuarios/{outro['id']}",
        headers=auth_headers["ops"],
        json={"ativo": False},
    )
    assert extra_off.status_code == 200
    ultimo = client.patch(
        f"/v1/saas/usuarios/{ops_id}",
        headers=auth_headers["ops"],
        json={"ativo": False},
    )
    assert ultimo.status_code == 400


def test_saas_usuarios_helpdesk_nao_ve_ops(client, seed_base, auth_headers, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    lista = client.get("/v1/atendentes", headers=auth_headers["admin"])
    assert lista.status_code == 200
    emails = {i["email"] for i in lista.json()["items"]}
    assert seed_base["ops"].email not in emails
    assert client.get(f"/v1/atendentes/{seed_base['ops'].id}", headers=auth_headers["admin"]).status_code == 404


def test_saas_usuarios_email_duplicado_e_reset_senha(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "SAAS_CONTROL_PLANE", True)
    dup = client.post(
        "/v1/saas/usuarios",
        headers=auth_headers["ops"],
        json={"nome": "Cópia", "email": seed_base["ops"].email},
    )
    assert dup.status_code == 400

    extra = Atendente(
        tenant_id=seed_base["tenant"].id,
        email="ops.reset@test.local",
        nome="Reset Me",
        senha_hash=hash_senha("antiga123"),
        role="saas_ops",
        ativo=True,
        must_change_password=False,
    )
    db_session.add(extra)
    db_session.commit()
    db_session.refresh(extra)

    reset = client.post(f"/v1/saas/usuarios/{extra.id}/senha-temporaria", headers=auth_headers["ops"])
    assert reset.status_code == 200, reset.text
    senha = reset.json()["senha_temporaria"]
    login_old = client.post("/v1/auth/login", json={"email": extra.email, "senha": "antiga123"})
    assert login_old.status_code == 401
    login_new = client.post("/v1/auth/login", json={"email": extra.email, "senha": senha})
    assert login_new.status_code == 200
    assert login_new.json()["must_change_password"] is True
