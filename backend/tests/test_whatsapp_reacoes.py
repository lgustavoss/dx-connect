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


def _webhook_reaction(
    wa_id: str,
    *,
    target_id: str,
    emoji: str,
    from_me: bool = False,
    reaction_msg_id: str = "react-1",
):
    return {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": f"{wa_id}@s.whatsapp.net",
                "fromMe": from_me,
                "id": reaction_msg_id,
            },
            "message": {
                "reactionMessage": {
                    "key": {
                        "remoteJid": f"{wa_id}@s.whatsapp.net",
                        "fromMe": True,
                        "id": target_id,
                    },
                    "text": emoji,
                }
            },
        },
    }


def _chat_em_atendimento(client, auth_headers, wa_id="5511999000701", msg_id="reac-base-1"):
    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "reac-630",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
            "auto_msg_assumido_ativa": False,
            "auto_msg_espera_ativa": False,
        },
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "reac-630"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id=wa_id, msg_id=msg_id),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    return cid, h


def test_webhook_reacao_cliente_aparece_na_mensagem(client, seed_base, auth_headers, monkeypatch):
    n = {"i": 0}

    def fake_send(*_a, **_k):
        n["i"] += 1
        return True, None, f"wa-out-{n['i']}"

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_text", fake_send)
    cid, h = _chat_em_atendimento(client, auth_headers)
    # Mensagem outbound do atendente
    r_msg = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens",
        json={"texto": "Olá!"},
        headers=auth_headers["a1"],
    )
    assert r_msg.status_code == 201
    target = r_msg.json()["wa_message_id"]
    assert target

    r = client.post(
        "/v1/webhooks/evolution",
        json=_webhook_reaction("5511999000701", target_id=target, emoji="👍"),
        headers=h,
    )
    assert r.status_code == 200
    assert r.json().get("reacoes", 0) >= 1

    msgs = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()
    alvo = next(m for m in msgs if m["wa_message_id"] == target)
    assert any(r["emoji"] == "👍" and r.get("tem_cliente") for r in alvo.get("reacoes") or [])


def test_atendente_reage_via_api(client, seed_base, auth_headers, monkeypatch):
    sent: list[dict] = []
    n = {"i": 0}

    def fake_send(*_a, **_k):
        n["i"] += 1
        return True, None, f"wa-out-reac-{n['i']}"

    def fake_reaction(*_a, **kwargs):
        sent.append(kwargs)
        return True, None

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_text", fake_send)
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_reaction",
        fake_reaction,
    )

    cid, _h = _chat_em_atendimento(client, auth_headers, wa_id="5511999000702", msg_id="reac-in-2")
    inbound_id = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()[0]["id"]

    ok = client.put(
        f"/v1/whatsapp/chats/{cid}/mensagens/{inbound_id}/reacoes",
        json={"emoji": "❤️"},
        headers=auth_headers["a1"],
    )
    assert ok.status_code == 200
    body = ok.json()
    assert any(r["emoji"] == "❤️" and r["reagiu_eu"] for r in body.get("reacoes") or [])
    assert sent and sent[-1].get("reaction") == "❤️"

    # Toggle remove
    rem = client.put(
        f"/v1/whatsapp/chats/{cid}/mensagens/{inbound_id}/reacoes",
        json={"emoji": "❤️"},
        headers=auth_headers["a1"],
    )
    assert rem.status_code == 200
    assert not any(r["emoji"] == "❤️" for r in rem.json().get("reacoes") or [])
    assert sent[-1].get("reaction") == ""


def test_reacao_exige_responsavel(client, seed_base, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_reaction",
        lambda *_a, **_k: (True, None),
    )
    cid, _h = _chat_em_atendimento(client, auth_headers, wa_id="5511999000703", msg_id="reac-in-3")
    mid = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()[0]["id"]
    denied = client.put(
        f"/v1/whatsapp/chats/{cid}/mensagens/{mid}/reacoes",
        json={"emoji": "👍"},
        headers=auth_headers["a2"],
    )
    assert denied.status_code == 403
