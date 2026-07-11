"""Paginação de mensagens do chat interno (IC-08)."""


def _criar_direta(client, headers, atendente_id: int) -> dict:
    r = client.post(
        "/v1/chat-interno/conversas/direta",
        json={"atendente_id": atendente_id},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _enviar_mensagem(client, headers, conversa_id: int, corpo: str) -> dict:
    r = client.post(
        f"/v1/chat-interno/conversas/{conversa_id}/mensagens",
        json={"corpo": corpo},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_mensagens_pagina_recentes_e_cursor(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["admin"].id)
    for i in range(55):
        _enviar_mensagem(client, auth_headers["a1"], conv["id"], f"Msg {i + 1}")

    r = client.get(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 55
    assert body["tem_mais_antigas"] is True
    assert len(body["items"]) == 50
    assert body["items"][0]["corpo"] == "Msg 6"
    assert body["items"][-1]["corpo"] == "Msg 55"

    primeiro_id = body["items"][0]["id"]
    r2 = client.get(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens",
        params={"antes_de_id": primeiro_id},
        headers=auth_headers["a1"],
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["tem_mais_antigas"] is False
    assert len(body2["items"]) == 5
    assert body2["items"][0]["corpo"] == "Msg 1"
    assert body2["items"][-1]["corpo"] == "Msg 5"


def test_mensagens_poucas_sem_mais_antigas(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["admin"].id)
    _enviar_mensagem(client, auth_headers["a1"], conv["id"], "Única")

    r = client.get(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["tem_mais_antigas"] is False
    assert body["items"][0]["corpo"] == "Única"
