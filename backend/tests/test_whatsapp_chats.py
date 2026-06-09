from __future__ import annotations


def _webhook_body(wa_id: str = "5511999999999", msg_id: str = "mid1", text: str = "Olá"):
    return {
        "event": "messages.upsert",
        "data": {
            "messages": [
                {
                    "key": {
                        "remoteJid": f"{wa_id}@s.whatsapp.net",
                        "fromMe": False,
                        "id": msg_id,
                    },
                    "message": {"conversation": text},
                }
            ]
        },
    }


def test_webhook_requer_segredo_quando_configurado(client, seed_base, auth_headers):
    r = client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "segredo-wpp"},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 200
    body = _webhook_body()
    r401 = client.post("/v1/webhooks/evolution", json=body)
    assert r401.status_code == 401
    r200 = client.post("/v1/webhooks/evolution", json=body, headers={"X-Dx-Webhook-Secret": "segredo-wpp"})
    assert r200.status_code == 200
    data = r200.json()
    assert data.get("ok") is True
    assert data.get("processados", 0) >= 1


def test_webhook_idempotente_por_wa_message_id(client, seed_base, auth_headers):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "x"},
        headers=auth_headers["admin"],
    )
    body = _webhook_body(msg_id="dup-1", text="A")
    h = {"X-Dx-Webhook-Secret": "x"}
    assert client.post("/v1/webhooks/evolution", json=body, headers=h).status_code == 200
    assert client.post("/v1/webhooks/evolution", json=body, headers=h).status_code == 200


def test_fila_e_assumir(client, seed_base, auth_headers):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "y"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "y"}
    client.post("/v1/webhooks/evolution", json=_webhook_body(wa_id="5511888777666", msg_id="m1"), headers=h)
    r_fila = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"])
    assert r_fila.status_code == 200
    chats = r_fila.json()
    assert len(chats) == 1
    cid = chats[0]["id"]
    r_ass = client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    assert r_ass.status_code == 200
    assert r_ass.json()["estado"] == "em_atendimento"
    assert client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json() == []


def test_listar_encerrados_filtra_e_respeita_rbac(client, seed_base, auth_headers):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "rbac-1"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "rbac-1"}

    client.post("/v1/webhooks/evolution", json=_webhook_body(wa_id="5511999111122", msg_id="chat-a-1"), headers=h)
    r_fila = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["admin"])
    assert r_fila.status_code == 200
    chat_a_id = r_fila.json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{chat_a_id}/assumir", headers=auth_headers["a1"])
    client.post(f"/v1/whatsapp/chats/{chat_a_id}/encerrar", headers=auth_headers["a1"])

    client.post("/v1/webhooks/evolution", json=_webhook_body(wa_id="5511999222233", msg_id="chat-b-1"), headers=h)
    r_fila = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["admin"])
    assert r_fila.status_code == 200
    chat_b_id = next(c["id"] for c in r_fila.json() if c["id"] != chat_a_id)
    client.post(f"/v1/whatsapp/chats/{chat_b_id}/assumir", headers=auth_headers["a2"])
    client.post(f"/v1/whatsapp/chats/{chat_b_id}/encerrar", headers=auth_headers["a2"])

    admin_history = client.get("/v1/whatsapp/chats/encerrados", headers=auth_headers["admin"]).json()
    assert admin_history["total"] >= 2
    assert any(item["id"] == chat_a_id for item in admin_history["items"])
    assert any(item["id"] == chat_b_id for item in admin_history["items"])

    a1_history = client.get("/v1/whatsapp/chats/encerrados", headers=auth_headers["a1"]).json()
    assert all(item["atendente_id"] == seed_base["a1"].id for item in a1_history["items"])
    assert any(item["id"] == chat_a_id for item in a1_history["items"])
    assert not any(item["id"] == chat_b_id for item in a1_history["items"])

    admin_filter = client.get(f"/v1/whatsapp/chats/encerrados?busca=5511999222233", headers=auth_headers["admin"]).json()
    assert len(admin_filter["items"]) == 1
    assert admin_filter["items"][0]["id"] == chat_b_id

    denied = client.get(f"/v1/whatsapp/chats/{chat_b_id}", headers=auth_headers["a1"])
    assert denied.status_code == 403


def test_nao_acessa_chat_em_atendimento_de_outro_atendente_mesmo_setor(client, seed_base, auth_headers):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "rbac-2"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "rbac-2"}

    client.post("/v1/webhooks/evolution", json=_webhook_body(wa_id="5511999333344", msg_id="chat-c-1"), headers=h)
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]

    client.post(
        f"/v1/whatsapp/chats/{cid}/transferir",
        json={"setor_id": seed_base["setor1"].id, "atendente_id": None},
        headers=auth_headers["a1"],
    )

    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])

    denied = client.get(f"/v1/whatsapp/chats/{cid}", headers=auth_headers["a2"])
    assert denied.status_code == 403


def test_webhook_guarda_citacao_em_mensagem(client, seed_base, auth_headers):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "cit"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "cit"}
    body = {
        "event": "messages.upsert",
        "data": {
            "messages": [
                {
                    "key": {
                        "remoteJid": "5511333444555@s.whatsapp.net",
                        "fromMe": False,
                        "id": "reply-msg-1",
                    },
                    "message": {
                        "extendedTextMessage": {
                            "text": "Resposta citando",
                            "contextInfo": {
                                "stanzaId": "orig-msg-1",
                                "quotedMessage": {"conversation": "Texto original"},
                            },
                        }
                    },
                }
            ]
        },
    }
    r = client.post("/v1/webhooks/evolution", json=body, headers=h)
    assert r.status_code == 200
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    r_msgs = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"])
    assert r_msgs.status_code == 200
    rows = r_msgs.json()
    assert len(rows) >= 1
    last = rows[-1]
    assert last.get("quoted_wa_message_id") == "orig-msg-1"
    assert "original" in (last.get("quoted_corpo_preview") or "").lower()


def test_abrir_ticket_vincula(client, seed_base, auth_headers):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "z"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "z"}
    client.post("/v1/webhooks/evolution", json=_webhook_body(wa_id="5511999111122", msg_id="t1"), headers=h)
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    empresa_id = seed_base["empresa"].id
    setor_id = seed_base["setor1"].id
    r = client.post(
        f"/v1/whatsapp/chats/{cid}/abrir-ticket",
        json={"empresa_id": empresa_id, "setor_id": setor_id, "assunto": "Via WhatsApp", "descricao": "Detalhe"},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    assert r.json()["ticket_ids"]
