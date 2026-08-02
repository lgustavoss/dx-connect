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


def _webhook_revoke(wa_id: str, *, target_id: str, revoke_msg_id: str = "rev-1"):
    return {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": f"{wa_id}@s.whatsapp.net",
                "fromMe": False,
                "id": revoke_msg_id,
            },
            "message": {
                "protocolMessage": {
                    "type": "REVOKE",
                    "key": {
                        "remoteJid": f"{wa_id}@s.whatsapp.net",
                        "fromMe": False,
                        "id": target_id,
                    },
                }
            },
        },
    }


def _webhook_edit(wa_id: str, *, target_id: str, texto: str, edit_msg_id: str = "edit-1"):
    return {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": f"{wa_id}@s.whatsapp.net",
                "fromMe": False,
                "id": target_id,
            },
            "message": {
                "editedMessage": {
                    "key": {
                        "remoteJid": f"{wa_id}@s.whatsapp.net",
                        "fromMe": False,
                        "id": target_id,
                    },
                    "message": {"conversation": texto},
                }
            },
        },
    }


def _chat_em_atendimento(client, auth_headers, wa_id="5511999000801", msg_id="edit-base-1"):
    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "edit-630",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
            "auto_msg_assumido_ativa": False,
            "auto_msg_espera_ativa": False,
        },
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "edit-630"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id=wa_id, msg_id=msg_id),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    return cid, h


def test_editar_mensagem_via_api(client, seed_base, auth_headers, monkeypatch):
    n = {"i": 0}
    updated: list[dict] = []

    def fake_send(*_a, **_k):
        n["i"] += 1
        return True, None, f"wa-out-edit-{n['i']}"

    def fake_update(*_a, **kwargs):
        updated.append(kwargs)
        return True, None

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_text", fake_send)
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_update_message",
        fake_update,
    )

    cid, _h = _chat_em_atendimento(client, auth_headers)
    r_msg = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens",
        json={"texto": "Texto original"},
        headers=auth_headers["a1"],
    )
    assert r_msg.status_code == 201
    mid = r_msg.json()["id"]
    assert r_msg.json().get("pode_editar") is True

    ok = client.patch(
        f"/v1/whatsapp/chats/{cid}/mensagens/{mid}",
        json={"texto": "Texto corrigido"},
        headers=auth_headers["a1"],
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["editada"] is True
    assert "Texto corrigido" in body["corpo"]
    assert updated and "Texto corrigido" in (updated[-1].get("text") or "")


def test_apagar_mensagem_via_api(client, seed_base, auth_headers, monkeypatch):
    n = {"i": 0}
    deleted: list[dict] = []

    def fake_send(*_a, **_k):
        n["i"] += 1
        return True, None, f"wa-out-del-{n['i']}"

    def fake_delete(*_a, **kwargs):
        deleted.append(kwargs)
        return True, None

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_text", fake_send)
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_delete_message_for_everyone",
        fake_delete,
    )

    cid, _h = _chat_em_atendimento(
        client, auth_headers, wa_id="5511999000802", msg_id="del-base-2"
    )
    r_msg = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens",
        json={"texto": "Vai sumir"},
        headers=auth_headers["a1"],
    )
    assert r_msg.status_code == 201
    mid = r_msg.json()["id"]
    assert r_msg.json().get("pode_apagar_para_todos") is True

    ok = client.delete(
        f"/v1/whatsapp/chats/{cid}/mensagens/{mid}",
        headers=auth_headers["a1"],
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["apagada"] is True
    assert body["corpo"] == "Mensagem apagada"
    assert body["pode_editar"] is False
    assert deleted


def test_webhook_revoke_marca_apagada(client, seed_base, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-rev"),
    )
    cid, h = _chat_em_atendimento(
        client, auth_headers, wa_id="5511999000803", msg_id="rev-in-3"
    )
    msgs = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()
    inbound = next(m for m in msgs if m["direcao"] == "inbound")
    target = inbound["wa_message_id"]

    r = client.post(
        "/v1/webhooks/evolution",
        json=_webhook_revoke("5511999000803", target_id=target),
        headers=h,
    )
    assert r.status_code == 200
    assert r.json().get("revokes", 0) >= 1

    msgs2 = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()
    alvo = next(m for m in msgs2 if m["id"] == inbound["id"])
    assert alvo["apagada"] is True
    assert alvo["corpo"] == "Mensagem apagada"


def test_webhook_edit_atualiza_corpo(client, seed_base, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-edw"),
    )
    cid, h = _chat_em_atendimento(
        client, auth_headers, wa_id="5511999000804", msg_id="edit-in-4"
    )
    msgs = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()
    inbound = next(m for m in msgs if m["direcao"] == "inbound")
    target = inbound["wa_message_id"]

    r = client.post(
        "/v1/webhooks/evolution",
        json=_webhook_edit("5511999000804", target_id=target, texto="Texto editado pelo cliente"),
        headers=h,
    )
    assert r.status_code == 200
    assert r.json().get("edits", 0) >= 1

    msgs2 = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()
    alvo = next(m for m in msgs2 if m["id"] == inbound["id"])
    assert alvo["editada"] is True
    assert alvo["corpo"] == "Texto editado pelo cliente"


def test_editar_exige_responsavel(client, seed_base, auth_headers, monkeypatch):
    n = {"i": 0}

    def fake_send(*_a, **_k):
        n["i"] += 1
        return True, None, f"wa-out-deny-{n['i']}"

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_text", fake_send)
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_update_message",
        lambda *_a, **_k: (True, None),
    )
    cid, _h = _chat_em_atendimento(
        client, auth_headers, wa_id="5511999000805", msg_id="deny-5"
    )
    r_msg = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens",
        json={"texto": "Só o responsável"},
        headers=auth_headers["a1"],
    )
    mid = r_msg.json()["id"]
    denied = client.patch(
        f"/v1/whatsapp/chats/{cid}/mensagens/{mid}",
        json={"texto": "Hack"},
        headers=auth_headers["a2"],
    )
    assert denied.status_code == 403
