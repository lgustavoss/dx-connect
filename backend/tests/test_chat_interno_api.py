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


def test_fluxo_conversa_direta_e_inbox(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["admin"].id)
    assert conv["tipo"] == "direta"
    assert conv["titulo"] == "Admin"

    _enviar_mensagem(client, auth_headers["a1"], conv["id"], "Dúvida rápida")

    r = client.get("/v1/chat-interno/conversas", headers=auth_headers["a1"])
    assert r.status_code == 200
    inbox = r.json()
    assert len(inbox) == 1
    assert inbox[0]["ultima_mensagem_corpo"] == "Dúvida rápida"
    assert inbox[0]["nao_lidas_count"] == 0

    r_admin = client.get("/v1/chat-interno/conversas", headers=auth_headers["admin"])
    assert r_admin.status_code == 200
    inbox_admin = r_admin.json()
    assert len(inbox_admin) == 1
    assert inbox_admin[0]["nao_lidas_count"] == 1
    assert inbox_admin[0]["titulo"] == "Atendente 1"


def test_fluxo_canal_setor(client, seed_base, auth_headers):
    setor1 = seed_base["setor1"].id
    r = client.get(f"/v1/chat-interno/setores/{setor1}/canal", headers=auth_headers["a1"])
    assert r.status_code == 200
    canal = r.json()
    assert canal["tipo"] == "setor"
    assert canal["setor_id"] == setor1

    r_pub = client.post(
        f"/v1/chat-interno/setores/{setor1}/canal/mensagens",
        json={"corpo": "Comunicado do setor"},
        headers=auth_headers["a1"],
    )
    assert r_pub.status_code == 201

    r_msgs = client.get(
        f"/v1/chat-interno/conversas/{canal['id']}/mensagens",
        headers=auth_headers["a1"],
    )
    assert r_msgs.status_code == 200
    body = r_msgs.json()
    assert body["total"] == 1
    assert body["items"][0]["corpo"] == "Comunicado do setor"


def test_403_canal_fora_do_setor(client, seed_base, auth_headers):
    setor2 = seed_base["setor2"].id
    r = client.get(f"/v1/chat-interno/setores/{setor2}/canal", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_403_mensagens_conversa_alheia(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["a2"].id)
    r = client.get(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens",
        headers=auth_headers["admin"],
    )
    assert r.status_code == 403


def test_inbox_nao_lista_conversa_alheia(client, seed_base, auth_headers):
    _criar_direta(client, auth_headers["a1"], seed_base["admin"].id)
    r = client.get("/v1/chat-interno/conversas", headers=auth_headers["a2"])
    assert r.status_code == 200
    ids_diretas = [c["id"] for c in r.json() if c["tipo"] == "direta"]
    assert ids_diretas == []


def test_corpo_vazio_rejeitado(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["admin"].id)
    r = client.post(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens",
        json={"corpo": ""},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 422


def test_post_visto_zera_nao_lidas(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["admin"].id)
    _enviar_mensagem(client, auth_headers["a1"], conv["id"], "Ping")

    r_before = client.get("/v1/chat-interno/conversas", headers=auth_headers["admin"])
    assert r_before.json()[0]["nao_lidas_count"] == 1

    r_visto = client.post(
        f"/v1/chat-interno/conversas/{conv['id']}/visto",
        headers=auth_headers["admin"],
    )
    assert r_visto.status_code == 204

    r_after = client.get("/v1/chat-interno/conversas", headers=auth_headers["admin"])
    assert r_after.json()[0]["nao_lidas_count"] == 0


def test_admin_publica_no_canal_sem_vinculo(client, seed_base, auth_headers):
    setor1 = seed_base["setor1"].id
    r = client.post(
        f"/v1/chat-interno/setores/{setor1}/canal/mensagens",
        json={"corpo": "Aviso geral"},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 201
