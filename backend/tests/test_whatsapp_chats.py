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


def test_meus_e_visto_contam_nao_lidas(client, seed_base, auth_headers):
    """#951: nao_lidas_count sobe com inbound e zera após POST /visto."""
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "nl-1"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "nl-1"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="5511777666555", msg_id="nl-m1", text="oi"),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    assert client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"]).status_code == 200
    assert client.post(f"/v1/whatsapp/chats/{cid}/visto", headers=auth_headers["a1"]).status_code == 204

    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="5511777666555", msg_id="nl-m2", text="nova"),
        headers=h,
    )
    meus = client.get("/v1/whatsapp/chats/meus", headers=auth_headers["a1"]).json()
    row = next(c for c in meus if c["id"] == cid)
    assert row["nao_lidas_count"] >= 1
    assert "last_seen_at" in row

    assert client.post(f"/v1/whatsapp/chats/{cid}/visto", headers=auth_headers["a1"]).status_code == 204
    meus2 = client.get("/v1/whatsapp/chats/meus", headers=auth_headers["a1"]).json()
    row2 = next(c for c in meus2 if c["id"] == cid)
    assert row2["nao_lidas_count"] == 0


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


def test_colaborador_mesmo_setor_ve_chat_em_atendimento(client, seed_base, auth_headers, db_session):
    """#455 — colega do setor consulta chat activo; envio ao cliente continua bloqueado (#403)."""
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

    seed_base["a2"].setores.append(seed_base["setor1"])
    db_session.commit()

    ok = client.get(f"/v1/whatsapp/chats/{cid}", headers=auth_headers["a2"])
    assert ok.status_code == 200

    denied_cliente = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens",
        json={"texto": "Olá cliente"},
        headers=auth_headers["a2"],
    )
    assert denied_cliente.status_code == 403

    interno = client.post(
        f"/v1/whatsapp/chats/{cid}/comentarios-internos",
        json={"texto": "Nota interna de apoio"},
        headers=auth_headers["a2"],
    )
    assert interno.status_code == 201


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


def test_abrir_ticket_whatsapp_distribuicao_imediata(client, seed_base, auth_headers, db_session):
    """Ticket aberto a partir do chat WhatsApp entra na fila e respeita auto_imediato do setor."""
    from app.models import Ticket

    setor = seed_base["setor1"]
    setor.distribuicao_modo = "auto_imediato"
    db_session.commit()

    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "dist-wpp"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "dist-wpp"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="5511999445566", msg_id="dist-wpp-1"),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])

    r = client.post(
        f"/v1/whatsapp/chats/{cid}/abrir-ticket",
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": setor.id,
            "assunto": "Ticket WhatsApp auto",
            "descricao": "Deve atribuir automaticamente",
        },
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    ticket_ids = r.json()["ticket_ids"]
    assert ticket_ids
    ticket = db_session.query(Ticket).filter(Ticket.id == ticket_ids[-1]).first()
    assert ticket is not None
    assert ticket.atendente_id == seed_base["a1"].id


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


def test_encerrados_inclui_empresa_nome(client, seed_base, auth_headers, db_session):
    """#590 — listagem Atendimentos deve serializar empresa_nome do chat."""
    func = _criar_funcionario_colaborador(db_session, seed_base, email="hist-emp@test.local")
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511999445566", msg_id="hist-emp-1")
    client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-funcionario",
        json={"funcionario_rede_id": func["id"]},
        headers=auth_headers["a1"],
    )
    client.post(f"/v1/whatsapp/chats/{cid}/encerrar", headers=auth_headers["a1"])

    hist = client.get("/v1/whatsapp/chats/encerrados", headers=auth_headers["admin"]).json()
    item = next(x for x in hist["items"] if x["id"] == cid)
    assert item["empresa_id"] == seed_base["empresa"].id
    assert item["empresa_nome"]


def test_encerrados_filtra_por_empresa_id(client, seed_base, auth_headers, db_session):
    """#591 — filtro empresa_id isola chats de outras empresas."""
    from app.models.empresa import Empresa
    from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa
    from app.models.whatsapp_chat import WhatsappChat

    emp_a = seed_base["empresa"]
    emp_b = Empresa(tenant_id=1, rede_id=emp_a.rede_id, nome="Empresa Isolamento B", ativo=True)
    db_session.add(emp_b)
    db_session.flush()

    fa = FuncionarioRede(
        nome="Func A",
        email="func.a.iso@test.local",
        tipo="colaborador",
        escopo_empresas="selected",
        ativo=True,
        rede_id=emp_a.rede_id,
        empresa_id=emp_a.id,
    )
    fb = FuncionarioRede(
        nome="Func B",
        email="func.b.iso@test.local",
        tipo="colaborador",
        escopo_empresas="selected",
        ativo=True,
        rede_id=emp_a.rede_id,
        empresa_id=emp_b.id,
    )
    db_session.add_all([fa, fb])
    db_session.flush()
    db_session.add(FuncionarioRedeEmpresa(funcionario_id=fa.id, empresa_id=emp_a.id))
    db_session.add(FuncionarioRedeEmpresa(funcionario_id=fb.id, empresa_id=emp_b.id))
    db_session.commit()

    cid_a = _chat_ativo(client, seed_base, auth_headers, wa_id="5511999110001", msg_id="iso-a-1")
    client.post(
        f"/v1/whatsapp/chats/{cid_a}/vincular-funcionario",
        json={"funcionario_rede_id": fa.id, "empresa_id": emp_a.id},
        headers=auth_headers["a1"],
    )
    client.post(f"/v1/whatsapp/chats/{cid_a}/encerrar", headers=auth_headers["a1"])

    cid_b = _chat_ativo(client, seed_base, auth_headers, wa_id="5511999110002", msg_id="iso-b-1")
    client.post(
        f"/v1/whatsapp/chats/{cid_b}/vincular-funcionario",
        json={"funcionario_rede_id": fb.id, "empresa_id": emp_b.id},
        headers=auth_headers["a1"],
    )
    client.post(f"/v1/whatsapp/chats/{cid_b}/encerrar", headers=auth_headers["a1"])

    # Garante empresa_id no banco (fallback se vínculo legado)
    for cid, eid in ((cid_a, emp_a.id), (cid_b, emp_b.id)):
        chat = db_session.query(WhatsappChat).filter(WhatsappChat.id == cid).first()
        chat.empresa_id = eid
    db_session.commit()

    only_a = client.get(
        f"/v1/whatsapp/chats/encerrados?empresa_id={emp_a.id}&estado=todos",
        headers=auth_headers["admin"],
    ).json()
    ids_a = {x["id"] for x in only_a["items"]}
    assert cid_a in ids_a
    assert cid_b not in ids_a

    only_b = client.get(
        f"/v1/whatsapp/chats/encerrados?empresa_id={emp_b.id}&estado=todos",
        headers=auth_headers["admin"],
    ).json()
    ids_b = {x["id"] for x in only_b["items"]}
    assert cid_b in ids_b
    assert cid_a not in ids_b


def test_buscar_funcionarios_whatsapp(client, seed_base, auth_headers, db_session):
    func = _criar_funcionario_colaborador(db_session, seed_base, nome="Maria Silva", email="maria@test.local")
    r = client.get("/v1/whatsapp/chats/funcionarios?busca=Maria", headers=auth_headers["a1"])
    assert r.status_code == 200
    rows = r.json()
    ids = [x["id"] for x in rows]
    assert func["id"] in ids
    hit = next(x for x in rows if x["id"] == func["id"])
    assert hit["rede_nome"] == seed_base["rede"].nome
    assert any(e["id"] == seed_base["empresa"].id for e in hit["empresas"])


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

    from app.models.funcionario_rede import FuncionarioRede

    f = db_session.query(FuncionarioRede).filter(FuncionarioRede.id == body["funcionario_rede_id"]).first()
    assert f is not None
    assert f.telefone == "5511999112233"

    catalogo = client.get("/v1/whatsapp/chats/funcionarios/catalogo", headers=auth_headers["a1"])
    assert catalogo.status_code == 200
    assert any(re["id"] == seed_base["rede"].id for re in catalogo.json()["redes"])


def test_cadastrar_funcionario_no_chat_sem_email(client, seed_base, auth_headers):
    """#444 — cadastro pelo WhatsApp sem e-mail vincula o contacto."""
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511999112244", msg_id="func-sem-email")
    r = client.post(
        f"/v1/whatsapp/chats/{cid}/cadastrar-funcionario",
        json={
            "nome": "Contacto Só WhatsApp",
            "rede_id": seed_base["rede"].id,
            "tipo": "colaborador",
            "escopo_empresas": "selected",
            "empresa_ids": [seed_base["empresa"].id],
        },
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["funcionario_nome"] == "Contacto Só WhatsApp"
    assert body["funcionario_email"] is None
    assert body["funcionario_rede_id"] is not None
    assert body["empresa_id"] == seed_base["empresa"].id


def test_cadastrar_funcionario_em_chat_encerrado(client, seed_base, auth_headers, db_session):
    """#534 — identificar contato no Histórico (chat já encerrado) e gravar telefone."""
    wa_id = "5511999112255"
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id=wa_id, msg_id="func-cad-enc")
    enc = client.post(f"/v1/whatsapp/chats/{cid}/encerrar", headers=auth_headers["a1"])
    assert enc.status_code == 200
    assert enc.json()["estado"] in ("encerrado", "aguardando_avaliacao")

    r = client.post(
        f"/v1/whatsapp/chats/{cid}/cadastrar-funcionario",
        json={
            "nome": "Cliente Pós Encerrar",
            "rede_id": seed_base["rede"].id,
            "tipo": "colaborador",
            "escopo_empresas": "selected",
            "empresa_ids": [seed_base["empresa"].id],
        },
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["funcionario_rede_id"] is not None
    assert body["funcionario_nome"] == "Cliente Pós Encerrar"

    from app.models.funcionario_rede import FuncionarioRede

    f = db_session.query(FuncionarioRede).filter(FuncionarioRede.id == body["funcionario_rede_id"]).first()
    assert f is not None
    assert f.telefone == wa_id


def test_vincular_funcionario_em_chat_encerrado_preenche_telefone(
    client, seed_base, auth_headers, db_session
):
    """#534 — vincular existente em chat encerrado preenche telefone se vazio."""
    wa_id = "5511999112266"
    func = _criar_funcionario_colaborador(db_session, seed_base, email="vinc-enc@test.local")
    from app.models.funcionario_rede import FuncionarioRede

    f0 = db_session.query(FuncionarioRede).filter(FuncionarioRede.id == func["id"]).first()
    assert f0 is not None
    assert not (f0.telefone or "").strip()

    cid = _chat_ativo(client, seed_base, auth_headers, wa_id=wa_id, msg_id="func-vinc-enc")
    assert client.post(f"/v1/whatsapp/chats/{cid}/encerrar", headers=auth_headers["a1"]).status_code == 200

    r = client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-funcionario",
        json={"funcionario_rede_id": func["id"]},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    assert r.json()["funcionario_rede_id"] == func["id"]

    db_session.refresh(f0)
    assert f0.telefone == wa_id


def test_admin_nao_envia_ao_cliente_usa_comentario_interno(client, seed_base, auth_headers, monkeypatch):
    """#403 — admin acompanha chat alheio; mensagem ao cliente bloqueada; comentário interno permitido."""
    sent = {"n": 0, "seq": 0}

    def fake_send(*_a, **_k):
        sent["n"] += 1
        sent["seq"] += 1
        return True, None, f"wa-out-{sent['seq']}"

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_text", fake_send)

    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "adm-int",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
        },
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "adm-int"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="5511999001122", msg_id="adm-int-1"),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    enviados_antes = sent["n"]

    denied = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens",
        json={"texto": "Olá cliente"},
        headers=auth_headers["admin"],
    )
    assert denied.status_code == 403
    assert sent["n"] == enviados_antes

    ok = client.post(
        f"/v1/whatsapp/chats/{cid}/comentarios-internos",
        json={"texto": "Orientação interna para o operador"},
        headers=auth_headers["admin"],
    )
    assert ok.status_code == 201
    body = ok.json()
    assert body["evento_sistema"] == "comentario_interno"
    assert body["wa_message_id"] is None
    assert "Orientação interna" in body["corpo"]

    allowed = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens",
        json={"texto": "Resposta oficial"},
        headers=auth_headers["a1"],
    )
    assert allowed.status_code == 201
    assert sent["n"] == enviados_antes + 1


def test_webhook_inbound_midia_grava_ficheiro(client, seed_base, auth_headers, monkeypatch, tmp_path):
    """Mídia inbound: obtém base64 da Evolution e persiste em disco (#431)."""
    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "midia-in",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
        },
        headers=auth_headers["admin"],
    )
    monkeypatch.setattr("app.config.settings.WHATSAPP_MEDIA_DIR", str(tmp_path))

    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    def fake_get_base64(_base, _inst, _key, envelope, *, convert_to_mp4=False, timeout=90):
        assert envelope.get("key", {}).get("id") == "img-in-1"
        return True, png_b64, None

    monkeypatch.setattr(
        "app.api.whatsapp_webhook.evolution_api.evolution_get_base64_from_media_message",
        fake_get_base64,
    )

    h = {"X-Dx-Webhook-Secret": "midia-in"}
    body = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511666555444@s.whatsapp.net",
                "fromMe": False,
                "id": "img-in-1",
            },
            "message": {
                "imageMessage": {
                    "mimetype": "image/jpeg",
                    "caption": "Foto teste",
                }
            },
        },
    }
    r = client.post("/v1/webhooks/evolution", json=body, headers=h)
    assert r.status_code == 200
    assert r.json().get("processados") == 1

    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    rows = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()
    last = rows[-1]
    assert last["tipo_midia"] == "imagem"
    assert last["midia_disponivel"] is True
    assert last["corpo"] == "Foto teste"

    r_mid = client.get(
        f"/v1/whatsapp/chats/{cid}/mensagens/{last['id']}/midia",
        headers=auth_headers["a1"],
    )
    assert r_mid.status_code == 200
    assert r_mid.headers.get("content-type", "").startswith("image/")


def test_enviar_audio_usa_sendWhatsAppAudio(client, seed_base, auth_headers, monkeypatch):
    """#441 — áudio outbound via sendWhatsAppAudio com encoding, não sendMedia."""
    calls: list[str] = []

    def fake_audio(*_a, **_k):
        calls.append("audio")
        return True, None, "wa-audio-1"

    def fake_media(*_a, **_k):
        calls.append("media")
        return True, None, "wa-media-1"

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_whatsapp_audio", fake_audio)
    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_media", fake_media)

    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "aud-out",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
        },
        headers=auth_headers["admin"],
    )
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511999445566", msg_id="aud-out-1")

    webm_bytes = b"\x1a\x45\xdf\xa3" + b"\x00" * 64
    r = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens/midia",
        data={"mediatipo": "audio", "caption": ""},
        files={"file": ("gravacao.webm", webm_bytes, "audio/webm")},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 201
    body = r.json()
    assert body["tipo_midia"] == "audio"
    assert body["wa_message_id"] == "wa-audio-1"
    assert calls == ["audio"]


def test_enviar_audio_falha_sem_wa_message_id(client, seed_base, auth_headers, monkeypatch):
    """#441 — não persiste áudio se Evolution não devolver wa_message_id."""
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_whatsapp_audio",
        lambda *_a, **_k: (True, None, None),
    )
    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "aud-fail",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
        },
        headers=auth_headers["admin"],
    )
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511999556677", msg_id="aud-fail-1")
    webm_bytes = b"\x1a\x45\xdf\xa3" + b"\x00" * 64
    r = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens/midia",
        data={"mediatipo": "audio", "caption": ""},
        files={"file": ("gravacao.webm", webm_bytes, "audio/webm")},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 502
    rows = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()
    assert all(m.get("tipo_midia") != "audio" or m.get("direcao") != "outbound" for m in rows)


def test_enviar_figurinha_usa_sendSticker(client, seed_base, auth_headers, monkeypatch):
    calls: list[str] = []

    def fake_sticker(*_a, **_k):
        calls.append("sticker")
        return True, None, "wa-sticker-1"

    def fake_media(*_a, **_k):
        calls.append("media")
        return True, None, "wa-media-1"

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_sticker", fake_sticker)
    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_media", fake_media)

    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "stk-out",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
        },
        headers=auth_headers["admin"],
    )
    cid = _chat_ativo(client, seed_base, auth_headers, wa_id="5511999667788", msg_id="stk-out-1")

    webp_bytes = b"RIFF" + b"\x00" * 64
    r = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens/midia",
        data={"mediatipo": "figurinha", "caption": ""},
        files={"file": ("fig.webp", webp_bytes, "image/webp")},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 201
    body = r.json()
    assert body["tipo_midia"] == "figurinha"
    assert body["wa_message_id"] == "wa-sticker-1"
    assert calls == ["sticker"]


def _evolution_settings(client, auth_headers, secret="outb"):
    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": secret,
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
        },
        headers=auth_headers["admin"],
    )


def test_listar_contatos_whatsapp(client, seed_base, auth_headers, db_session):
    func = _criar_funcionario_colaborador(db_session, seed_base, nome="Ana Contato", email="ana.contato@test.local")
    from app.models.funcionario_rede import FuncionarioRede

    f = db_session.query(FuncionarioRede).filter(FuncionarioRede.id == func["id"]).first()
    f.telefone = "5511988776655"
    db_session.commit()

    r = client.get("/v1/whatsapp/chats/contatos?busca=Ana", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    ids = [x["id"] for x in body["items"]]
    assert func["id"] in ids
    row = next(x for x in body["items"] if x["id"] == func["id"])
    assert row["telefone"] == "5511988776655"
    assert any(e["id"] == seed_base["empresa"].id for e in row["empresas"])


def test_iniciar_chat_outbound_por_telefone(client, seed_base, auth_headers, monkeypatch):
    sent = {"n": 0}

    def fake_send(*_a, **_k):
        sent["n"] += 1
        return True, None, "wa-out-1"

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_text", fake_send)
    _evolution_settings(client, auth_headers, "iniciar-1")

    r = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"telefone": "11988776655", "mensagem_inicial": "Olá, retorno da demanda"},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["estado"] == "em_atendimento"
    assert body["atendente_id"] == seed_base["a1"].id
    assert body["wa_id"] == "5511988776655"
    assert sent["n"] == 1

    meus = client.get("/v1/whatsapp/chats/meus", headers=auth_headers["a1"]).json()
    assert any(c["id"] == body["id"] for c in meus)


def test_iniciar_chat_reusa_aberto_mesmo_responsavel(client, seed_base, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out"),
    )
    _evolution_settings(client, auth_headers, "iniciar-2")

    r1 = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"telefone": "5511999000011"},
        headers=auth_headers["a1"],
    )
    assert r1.status_code == 200
    cid = r1.json()["id"]

    r2 = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"telefone": "5511999000011"},
        headers=auth_headers["a1"],
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == cid


def test_iniciar_chat_409_outro_responsavel(client, seed_base, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out"),
    )
    _evolution_settings(client, auth_headers, "iniciar-3")

    r1 = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"telefone": "5511999000022"},
        headers=auth_headers["a1"],
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"telefone": "5511999000022"},
        headers=auth_headers["a2"],
    )
    assert r2.status_code == 409


def test_inbound_apos_outbound_nao_abre_fila_com_variante_wa_id(
    client, seed_base, auth_headers, monkeypatch
):
    """
    Atendente inicia com número digitado; cliente responde com variante (sem nono dígito).
    Não deve criar chat novo em aguardando_atendente (alerta de fila).
    """
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-var"),
    )
    _evolution_settings(client, auth_headers, "iniciar-var")

    r = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"telefone": "11988770011", "mensagem_inicial": "Olá"},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    chat = r.json()
    assert chat["estado"] == "em_atendimento"
    assert chat["wa_id"] == "5511988770011"
    cid = chat["id"]

    h = {"X-Dx-Webhook-Secret": "iniciar-var"}
    # Evolution / WhatsApp pode devolver sem o nono dígito
    wr = client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="551188770011", msg_id="reply-var-1", text="Oi, recebi"),
        headers=h,
    )
    assert wr.status_code == 200
    assert wr.json().get("processados", 0) >= 1

    fila = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()
    assert not any(c["wa_id"] in ("5511988770011", "551188770011") for c in fila), fila

    detalhe = client.get(f"/v1/whatsapp/chats/{cid}", headers=auth_headers["a1"])
    assert detalhe.status_code == 200
    assert detalhe.json()["estado"] == "em_atendimento"

    msgs = client.get(f"/v1/whatsapp/chats/{cid}/mensagens", headers=auth_headers["a1"]).json()
    corpos = [m["corpo"] for m in (msgs if isinstance(msgs, list) else msgs.get("items", []))]
    assert any("Oi, recebi" in (c or "") for c in corpos), msgs


def test_inbound_apos_outbound_resolve_lid_com_sender_pn(
    client, seed_base, auth_headers, monkeypatch
):
    """Resposta com remoteJid @lid + senderPn deve reutilizar o chat outbound."""
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-lid"),
    )
    _evolution_settings(client, auth_headers, "iniciar-lid")

    r = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"telefone": "5511999000044", "mensagem_inicial": "Retorno"},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    cid = r.json()["id"]

    body = {
        "event": "messages.upsert",
        "data": {
            "messages": [
                {
                    "key": {
                        "remoteJid": "98765432109876@lid",
                        "fromMe": False,
                        "id": "reply-lid-1",
                        "senderPn": "5511999000044@s.whatsapp.net",
                    },
                    "message": {"conversation": "Resposta via LID"},
                }
            ]
        },
    }
    wr = client.post(
        "/v1/webhooks/evolution",
        json=body,
        headers={"X-Dx-Webhook-Secret": "iniciar-lid"},
    )
    assert wr.status_code == 200
    assert wr.json().get("processados", 0) >= 1

    fila = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()
    assert not any(c["id"] == cid or c.get("wa_id") == "5511999000044" for c in fila), fila
    assert not any(c.get("wa_id") == "98765432109876" for c in fila), fila

    detalhe = client.get(f"/v1/whatsapp/chats/{cid}", headers=auth_headers["a1"])
    assert detalhe.json()["estado"] == "em_atendimento"


def test_iniciar_chat_funcionario_sem_telefone_exige_numero(client, seed_base, auth_headers, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out"),
    )
    _evolution_settings(client, auth_headers, "iniciar-4")
    func = _criar_funcionario_colaborador(db_session, seed_base, nome="Sem Fone", email="semfone@test.local")

    denied = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"funcionario_id": func["id"]},
        headers=auth_headers["a1"],
    )
    assert denied.status_code == 400

    ok = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"funcionario_id": func["id"], "telefone": "5511999000033"},
        headers=auth_headers["a1"],
    )
    assert ok.status_code == 200
    assert ok.json()["funcionario_rede_id"] == func["id"]

    from app.models.funcionario_rede import FuncionarioRede

    f = db_session.query(FuncionarioRede).filter(FuncionarioRede.id == func["id"]).first()
    db_session.refresh(f)
    assert f.telefone == "5511999000033"


def _criar_funcionario_multi_empresa(db_session, seed_base, *, email="multi.emp@test.local"):
    from app.models.empresa import Empresa
    from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa

    emp = seed_base["empresa"]
    e2 = Empresa(tenant_id=1, rede_id=emp.rede_id, nome="Empresa Filial B", ativo=True)
    db_session.add(e2)
    db_session.flush()
    f = FuncionarioRede(
        nome="Multi Empresa",
        email=email,
        tipo="colaborador",
        escopo_empresas="selected",
        ativo=True,
        rede_id=emp.rede_id,
        empresa_id=emp.id,
        telefone="5511999000099",
    )
    db_session.add(f)
    db_session.flush()
    db_session.add(FuncionarioRedeEmpresa(funcionario_id=f.id, empresa_id=emp.id))
    db_session.add(FuncionarioRedeEmpresa(funcionario_id=f.id, empresa_id=e2.id))
    db_session.commit()
    db_session.refresh(f)
    db_session.refresh(e2)
    return {"id": f.id, "empresa_a": emp.id, "empresa_b": e2.id, "telefone": f.telefone}


def test_iniciar_chat_1_empresa_auto(client, seed_base, auth_headers, db_session, monkeypatch):
    """#592 — funcionário com 1 empresa: inicia sem empresa_id no body."""
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out"),
    )
    _evolution_settings(client, auth_headers, "iniciar-1emp")
    func = _criar_funcionario_colaborador(db_session, seed_base, email="um.emp@test.local")
    from app.models.funcionario_rede import FuncionarioRede

    f = db_session.query(FuncionarioRede).filter(FuncionarioRede.id == func["id"]).first()
    f.telefone = "5511999000044"
    db_session.commit()

    r = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"funcionario_id": func["id"]},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["empresa_id"] == seed_base["empresa"].id
    assert body["empresa_nome"]


def test_iniciar_chat_multi_empresa_permite_sem_empresa_id(client, seed_base, auth_headers, db_session, monkeypatch):
    """#592 — >1 empresas: pode iniciar sem empresa_id e definir depois; inválida → 400."""
    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out"),
    )
    _evolution_settings(client, auth_headers, "iniciar-multi")
    multi = _criar_funcionario_multi_empresa(db_session, seed_base)

    sem = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"funcionario_id": multi["id"]},
        headers=auth_headers["a1"],
    )
    assert sem.status_code == 200
    body = sem.json()
    assert body["empresa_id"] is None
    assert body["funcionario_rede_id"] == multi["id"]
    assert len(body.get("empresas_opcoes") or []) >= 2

    invalid = client.post(
        "/v1/whatsapp/chats/iniciar",
        json={"funcionario_id": multi["id"], "telefone": "5511999000077", "empresa_id": 999999},
        headers=auth_headers["a1"],
    )
    assert invalid.status_code == 400

    ok = client.post(
        f"/v1/whatsapp/chats/{body['id']}/empresa-contexto",
        json={"empresa_id": multi["empresa_b"]},
        headers=auth_headers["a1"],
    )
    assert ok.status_code == 200
    assert ok.json()["empresa_id"] == multi["empresa_b"]

    # Pode alterar enquanto não encerrado
    trocou = client.post(
        f"/v1/whatsapp/chats/{body['id']}/empresa-contexto",
        json={"empresa_id": multi["empresa_a"]},
        headers=auth_headers["a1"],
    )
    assert trocou.status_code == 200
    assert trocou.json()["empresa_id"] == multi["empresa_a"]


def test_assumir_multi_empresa_sem_bloquear(client, seed_base, auth_headers, db_session):
    """#592 — assumir multi-empresa sem empresa_id é permitido; contexto fica para depois."""
    multi = _criar_funcionario_multi_empresa(db_session, seed_base, email="assumir.multi@test.local")
    from app.models.whatsapp_chat import WhatsappChat

    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "assumir-multi"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "assumir-multi"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="5511999000088", msg_id="assumir-multi-1"),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    chat = db_session.query(WhatsappChat).filter(WhatsappChat.id == cid).first()
    chat.funcionario_rede_id = multi["id"]
    chat.empresa_id = None
    db_session.commit()

    ok = client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    assert ok.status_code == 200
    assert ok.json()["empresa_id"] is None
    assert ok.json()["estado"] == "em_atendimento"

    ctx = client.post(
        f"/v1/whatsapp/chats/{cid}/empresa-contexto",
        json={"empresa_id": multi["empresa_a"]},
        headers=auth_headers["a1"],
    )
    assert ctx.status_code == 200
    assert ctx.json()["empresa_id"] == multi["empresa_a"]


def _webhook_body_multi(wa_id: str, messages: list[tuple[str, str]]):
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
                for msg_id, text in messages
            ]
        },
    }


def test_webhook_duas_mensagens_mesmo_payload_um_chat(client, seed_base, auth_headers, db_session):
    """#608 — duas mensagens inbound no mesmo payload → um chat, duas mensagens."""
    from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem

    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "dup-payload", "auto_msg_espera_ativa": False, "auto_msg_fora_horario_ativa": False},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "dup-payload"}
    wa_id = "5511999000608"
    body = _webhook_body_multi(
        wa_id,
        [("608-a", "Bom dia"), ("608-b", "Td bem?")],
    )
    r = client.post("/v1/webhooks/evolution", json=body, headers=h)
    assert r.status_code == 200
    assert r.json().get("processados") == 2

    abertos = (
        db_session.query(WhatsappChat)
        .filter(
            WhatsappChat.wa_id == wa_id,
            WhatsappChat.estado.in_(("aguardando_atendente", "em_atendimento")),
        )
        .all()
    )
    assert len(abertos) == 1
    msgs = (
        db_session.query(WhatsappMensagem)
        .filter(
            WhatsappMensagem.chat_id == abertos[0].id,
            WhatsappMensagem.direcao == "inbound",
        )
        .all()
    )
    assert len(msgs) == 2
    assert {m.corpo for m in msgs} == {"Bom dia", "Td bem?"}


def test_webhook_mensagens_paralelas_mesmo_wa_id_um_chat(client, seed_base, auth_headers, db_session):
    """#608 — webhooks paralelos do mesmo wa_id → um único chat aberto."""
    import threading

    from app.models.whatsapp_chat import WhatsappChat

    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "dup-race", "auto_msg_espera_ativa": False, "auto_msg_fora_horario_ativa": False},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "dup-race"}
    wa_id = "5511999000609"
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def post(msg_id: str, text: str) -> None:
        try:
            barrier.wait(timeout=5)
            r = client.post(
                "/v1/webhooks/evolution",
                json=_webhook_body(wa_id=wa_id, msg_id=msg_id, text=text),
                headers=h,
            )
            assert r.status_code == 200
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=post, args=("608-r1", "Olá"))
    t2 = threading.Thread(target=post, args=("608-r2", "Tudo bem?"))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)
    assert not errors, errors

    abertos = (
        db_session.query(WhatsappChat)
        .filter(
            WhatsappChat.wa_id == wa_id,
            WhatsappChat.estado.in_(("aguardando_atendente", "em_atendimento")),
        )
        .all()
    )
    assert len(abertos) == 1


def test_assumir_define_setor_unico_e_prefixo_mensagem(client, seed_base, auth_headers, monkeypatch):
    """#628 — 1 setor auto ao assumir; prefixo «[ Setor - Nome ]:» + texto na linha de baixo."""
    sent: list[str] = []

    def fake_send(*_a, **kwargs):
        text = kwargs.get("text")
        if text is None and len(_a) > 4:
            text = _a[4]
        sent.append(text or "")
        return True, None, f"wa-pfx-{len(sent)}"

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_text", fake_send)

    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "pfx-628",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
        },
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "pfx-628"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="5511999000628", msg_id="pfx-628-1"),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    r_ass = client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    assert r_ass.status_code == 200
    assert r_ass.json()["setor_id"] == seed_base["setor1"].id

    r_msg = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens",
        json={"texto": "Olá, em que posso ajudar?"},
        headers=auth_headers["a1"],
    )
    assert r_msg.status_code == 201
    corpo = r_msg.json()["corpo"]
    assert corpo.startswith("[ Suporte - Atendente 1 ]:\n")
    assert "Olá, em que posso ajudar?" in corpo
    assert sent and sent[-1].startswith("[ Suporte - Atendente 1 ]:\n")


def test_assumir_multi_setor_exige_setor_id(client, seed_base, auth_headers, db_session):
    """#628 — atendente com vários setores precisa informar setor_id ao assumir."""
    a1 = seed_base["a1"]
    a1.setores.append(seed_base["setor2"])
    db_session.commit()

    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "multi-628"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "multi-628"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="5511999000629", msg_id="multi-628-1"),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]

    sem = client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    assert sem.status_code == 400
    assert "setor" in (sem.json().get("detail") or "").lower()

    ok = client.post(
        f"/v1/whatsapp/chats/{cid}/assumir",
        params={"setor_id": seed_base["setor2"].id},
        headers=auth_headers["a1"],
    )
    assert ok.status_code == 200
    assert ok.json()["setor_id"] == seed_base["setor2"].id


def test_prefixo_apos_transferencia_usa_novo_setor(client, seed_base, auth_headers, monkeypatch):
    """#628 — após transferir, novas mensagens usam o setor novo do chat."""
    sent: list[str] = []

    def fake_send(*_a, **kwargs):
        text = kwargs.get("text")
        if text is None and len(_a) > 4:
            text = _a[4]
        sent.append(text or "")
        return True, None, f"wa-tr-{len(sent)}"

    monkeypatch.setattr("app.api.whatsapp_chats.evolution_api.evolution_send_text", fake_send)

    client.patch(
        "/v1/settings/whatsapp",
        json={
            "webhook_secret": "tr-pfx",
            "evolution_base_url": "http://evolution.test",
            "evolution_instance_name": "inst",
            "evolution_api_key": "key-test",
        },
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "tr-pfx"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="5511999000630", msg_id="tr-pfx-1"),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    tr = client.post(
        f"/v1/whatsapp/chats/{cid}/transferir",
        json={"setor_id": seed_base["setor2"].id, "atendente_id": None},
        headers=auth_headers["a1"],
    )
    assert tr.status_code == 200
    assert tr.json()["setor_id"] == seed_base["setor2"].id
    ass2 = client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a2"])
    assert ass2.status_code == 200
    r_msg = client.post(
        f"/v1/whatsapp/chats/{cid}/mensagens",
        json={"texto": "Sou do Financeiro"},
        headers=auth_headers["a2"],
    )
    assert r_msg.status_code == 201
    assert r_msg.json()["corpo"].startswith("[ Financeiro - Atendente 2 ]:\n")


def test_chat_read_inclui_foto_perfil_campos(client, seed_base, auth_headers, db_session):
    """#630 lote 1 — schema expõe foto_perfil_url / foto_perfil_atualizada_em."""
    from datetime import datetime, timezone

    from app.models import WhatsappChat

    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "foto-630"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "foto-630"}
    client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id="5511999000631", msg_id="foto-630-1"),
        headers=h,
    )
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    chat = db_session.query(WhatsappChat).filter(WhatsappChat.id == cid).first()
    assert chat is not None
    chat.foto_perfil_url = "https://example.test/foto.jpg"
    chat.foto_perfil_atualizada_em = datetime.now(timezone.utc)
    db_session.commit()

    r = client.get(f"/v1/whatsapp/chats/{cid}", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    assert body["foto_perfil_url"] == "https://example.test/foto.jpg"
    assert body.get("foto_perfil_atualizada_em")
