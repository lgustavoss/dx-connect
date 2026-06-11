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


def test_webhook_boas_vindas_usa_nome_empresa_exibicao(client, seed_base, auth_headers, monkeypatch):
    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "emp-wpp",
            "nome_empresa_exibicao": "DX Connect",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
        },
        headers=auth_headers["admin"],
    )

    sent: list[str] = []

    def fake_send(_base, _inst, _key, number_digits, text, **_kw):
        sent.append(text)
        return True, None, "out-welcome-1"

    monkeypatch.setattr("app.api.whatsapp_webhook.evolution_api.evolution_send_text", fake_send)

    h = {"X-Dx-Webhook-Secret": "emp-wpp"}
    body = {
        "event": "messages.upsert",
        "data": {
            "messages": [
                {
                    "key": {
                        "remoteJid": "5511777888999@s.whatsapp.net",
                        "fromMe": False,
                        "id": "welcome-emp-1",
                    },
                    "message": {"conversation": "Oi"},
                }
            ]
        },
    }
    r = client.post("/v1/webhooks/evolution", json=body, headers=h)
    assert r.status_code == 200
    assert sent, "deveria enviar boas-vindas"
    assert "DX Connect" in sent[0]
    assert "nossa empresa" not in sent[0]


def test_webhook_guarda_citacao_formato_evolution(client, seed_base, auth_headers):
    """Evolution prepareMessage coloca contextInfo no envelope, não dentro de extendedTextMessage."""
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "cit-ev"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "cit-ev"}
    body = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511444555666@s.whatsapp.net",
                "fromMe": False,
                "id": "reply-msg-ev-1",
            },
            "message": {"conversation": "Resposta citando (Evolution)"},
            "contextInfo": {
                "stanzaId": "orig-msg-ev-1",
                "quotedMessage": {"conversation": "Texto original Evolution"},
            },
        },
    }
    r = client.post("/v1/webhooks/evolution", json=body, headers=h)
    assert r.status_code == 200
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    rows = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()
    last = rows[-1]
    assert last.get("quoted_wa_message_id") == "orig-msg-ev-1"
    assert "evolution" in (last.get("quoted_corpo_preview") or "").lower()


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


def test_vincular_ticket_existente(client, seed_base, auth_headers):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "vinc"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "vinc"}
    client.post("/v1/webhooks/evolution", json=_webhook_body(wa_id="5511999778899", msg_id="vinc-1"), headers=h)
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])

    ticket = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Ticket para vincular",
            "descricao": "Teste",
        },
    )
    assert ticket.status_code == 201
    tid = ticket.json()["id"]

    r = client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-ticket",
        json={"ticket_id": tid},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    assert tid in r.json()["ticket_ids"]

    por_ticket = client.get(f"/v1/whatsapp/chats/por-ticket/{tid}", headers=auth_headers["admin"]).json()
    assert any(c["id"] == cid for c in por_ticket)


def test_transferir_registra_mensagem_interna(client, seed_base, auth_headers):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "tr-int"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "tr-int"}
    client.post("/v1/webhooks/evolution", json=_webhook_body(wa_id="5511999445566", msg_id="tr-1"), headers=h)
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])

    r = client.post(
        f"/v1/whatsapp/chats/{cid}/transferir",
        json={"setor_id": seed_base["setor2"].id, "atendente_id": None},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["estado"] == "aguardando_atendente"
    assert body["setor_id"] == seed_base["setor2"].id

    msgs = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["admin"]).json()
    transfer_msgs = [m for m in msgs if m.get("evento_sistema") == "transferencia"]
    assert len(transfer_msgs) == 1
    assert "Financeiro" in transfer_msgs[0]["corpo"]


def _criar_funcionario_colaborador(db_session, seed_base, *, nome="João Cliente", email="joao.cliente@test.local"):
    from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa

    emp = seed_base["empresa"]
    f = FuncionarioRede(
        nome=nome,
        email=email,
        tipo="colaborador",
        escopo_empresas="selected",
        ativo=True,
        rede_id=emp.rede_id,
        empresa_id=emp.id,
    )
    db_session.add(f)
    db_session.flush()
    db_session.add(FuncionarioRedeEmpresa(funcionario_id=f.id, empresa_id=emp.id))
    db_session.commit()
    db_session.refresh(f)
    return {"id": f.id, "nome": f.nome, "email": f.email}


def _chat_ativo(client, seed_base, auth_headers, wa_id="5511999334455", msg_id="func-1"):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "func-vinc"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "func-vinc"}
    client.post("/v1/webhooks/evolution", json=_webhook_body(wa_id=wa_id, msg_id=msg_id), headers=h)
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    return cid


def test_vincular_funcionario_no_chat(client, seed_base, auth_headers, db_session):
    func = _criar_funcionario_colaborador(db_session, seed_base)
    cid = _chat_ativo(client, seed_base, auth_headers)

    r = client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-funcionario",
        json={"funcionario_rede_id": func["id"]},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["funcionario_rede_id"] == func["id"]
    assert body["funcionario_nome"] == func["nome"]
    assert body["empresa_id"] == seed_base["empresa"].id
    assert body["empresa_nome"]

    get_r = client.get(f"/v1/whatsapp/chats/{cid}", headers=auth_headers["a1"])
    assert get_r.status_code == 200
    assert get_r.json()["funcionario_rede_id"] == func["id"]


def test_buscar_funcionarios_whatsapp(client, seed_base, auth_headers, db_session):
    func = _criar_funcionario_colaborador(db_session, seed_base, nome="Maria Silva", email="maria@test.local")
    r = client.get("/v1/whatsapp/chats/funcionarios?busca=Maria", headers=auth_headers["a1"])
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert func["id"] in ids


def test_desvincular_funcionario_no_chat(client, seed_base, auth_headers, db_session):
    func = _criar_funcionario_colaborador(db_session, seed_base, email="desv@test.local")
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511999223344", msg_id="func-desv")
    client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-funcionario",
        json={"funcionario_rede_id": func["id"]},
        headers=auth_headers["a1"],
    )
    r = client.post(f"/v1/whatsapp/chats/{cid}/desvincular-funcionario", headers=auth_headers["a1"])
    assert r.status_code == 200
    assert r.json()["funcionario_rede_id"] is None
    assert r.json()["empresa_id"] is None


def test_cadastrar_funcionario_no_chat(client, seed_base, auth_headers, db_session):
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511999112233", msg_id="func-cad")
    r = client.post(
        f"/v1/whatsapp/chats/{cid}/cadastrar-funcionario",
        json={
            "nome": "Cliente Novo",
            "email": "cliente.novo@test.local",
            "rede_id": seed_base["rede"].id,
            "tipo": "colaborador",
            "escopo_empresas": "selected",
            "empresa_ids": [seed_base["empresa"].id],
        },
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["funcionario_nome"] == "Cliente Novo"
    assert body["funcionario_email"] == "cliente.novo@test.local"
    assert body["empresa_id"] == seed_base["empresa"].id

    catalogo = client.get("/v1/whatsapp/chats/funcionarios/catalogo", headers=auth_headers["a1"])
    assert catalogo.status_code == 200
    assert any(re["id"] == seed_base["rede"].id for re in catalogo.json()["redes"])

