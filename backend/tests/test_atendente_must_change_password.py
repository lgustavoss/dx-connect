"""Exigir troca de senha no próximo login (#atendentes)."""

from __future__ import annotations


def test_criar_atendente_exige_troca_senha_por_padrao(client, seed_base, auth_headers):
    setor_id = seed_base["setor1"].id
    r = client.post(
        "/v1/atendentes",
        headers=auth_headers["admin"],
        json={
            "email": "novo.temp@example.com",
            "nome": "Novo Temp",
            "senha": "SenhaTemp1!",
            "role": "atendente",
            "setor_ids": [setor_id],
            "ativo": True,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["must_change_password"] is True


def test_admin_pode_ligar_e_desligar_must_change_sem_trocar_senha(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    r = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={"must_change_password": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["must_change_password"] is True

    r2 = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={"must_change_password": False},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["must_change_password"] is False


def test_definir_senha_nova_liga_must_change_por_padrao(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={"must_change_password": False},
    )
    r = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={"senha": "OutraSenha1!"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["must_change_password"] is True
