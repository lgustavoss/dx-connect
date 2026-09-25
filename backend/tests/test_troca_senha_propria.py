"""Troca da própria senha: sessão atual segue válida (#884)."""


def test_troca_senha_propria_mantem_a_sessao(client, auth_headers):
    headers = auth_headers["a1"]
    troca = client.post(
        "/v1/atendentes/me/trocar-senha",
        headers=headers,
        json={"senha_atual": "at123", "senha_nova": "novaSenha1"},
    )
    assert troca.status_code == 200, troca.text
    assert troca.json()["must_change_password"] is False
    assert troca.json()["email"] == "atendente1@test.local"

    me = client.get("/v1/atendentes/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["nome"] == "Atendente 1"

    antigo = client.post(
        "/v1/auth/login",
        json={"email": "atendente1@test.local", "senha": "at123"},
    )
    assert antigo.status_code == 401

    novo = client.post(
        "/v1/auth/login",
        json={"email": "atendente1@test.local", "senha": "novaSenha1"},
    )
    assert novo.status_code == 200, novo.text
    assert novo.json()["must_change_password"] is False


def test_troca_senha_rejeita_atual_errada_e_repetida(client, auth_headers):
    headers = auth_headers["admin"]
    errada = client.post(
        "/v1/atendentes/me/trocar-senha",
        headers=headers,
        json={"senha_atual": "nao-e-a-senha", "senha_nova": "outraSenha1"},
    )
    assert errada.status_code == 400
    assert "incorreta" in errada.json()["detail"].lower()

    igual = client.post(
        "/v1/atendentes/me/trocar-senha",
        headers=headers,
        json={"senha_atual": "admin123", "senha_nova": "admin123"},
    )
    assert igual.status_code == 400
    assert "diferente" in igual.json()["detail"].lower()

    curta = client.post(
        "/v1/atendentes/me/trocar-senha",
        headers=headers,
        json={"senha_atual": "admin123", "senha_nova": "curta"},
    )
    assert curta.status_code == 422
