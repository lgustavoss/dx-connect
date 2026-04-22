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
