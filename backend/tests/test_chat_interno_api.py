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


def test_status_leitura_mensagem_direta(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["admin"].id)
    _enviar_mensagem(client, auth_headers["a1"], conv["id"], "Olá admin")

    r_antes = client.get(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens",
        headers=auth_headers["a1"],
    )
    assert r_antes.status_code == 200
    assert r_antes.json()["items"][0]["status_entrega"] == "enviada"

    client.post(
        f"/v1/chat-interno/conversas/{conv['id']}/visto",
        headers=auth_headers["admin"],
    )

    r_depois = client.get(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens",
        headers=auth_headers["a1"],
    )
    assert r_depois.json()["items"][0]["status_entrega"] == "lida"


def test_admin_publica_no_canal_sem_vinculo(client, seed_base, auth_headers):
    setor1 = seed_base["setor1"].id
    r = client.post(
        f"/v1/chat-interno/setores/{setor1}/canal/mensagens",
        json={"corpo": "Aviso geral"},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 201


def test_responder_mensagem_interna(client, seed_base, auth_headers):
    """#539 — reply_to_message_id + preview na leitura."""
    conv = _criar_direta(client, auth_headers["a1"], seed_base["a2"].id)
    original = _enviar_mensagem(client, auth_headers["a1"], conv["id"], "Mensagem original")
    r = client.post(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens",
        json={"corpo": "Resposta citada", "reply_to_message_id": original["id"]},
        headers=auth_headers["a2"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reply_to_message_id"] == original["id"]
    assert body["reply_preview"] == "Mensagem original"
    assert body["reply_autor_nome"]

    r404 = client.post(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens",
        json={"corpo": "x", "reply_to_message_id": 999999},
        headers=auth_headers["a1"],
    )
    assert r404.status_code == 400


def test_criar_setor_cria_canal_interno(client, seed_base, auth_headers, db_session):
    """#916 — criar setor activo cria conversa tipo setor."""
    from app.models.chat_interno import ConversaInterna, TIPO_CONVERSA_SETOR

    r = client.post(
        "/v1/setores",
        json={"nome": "Financeiro IC", "slug": "financeiro-ic", "ativo": True},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 201, r.text
    setor_id = r.json()["id"]

    canal = (
        db_session.query(ConversaInterna)
        .filter(
            ConversaInterna.tipo == TIPO_CONVERSA_SETOR,
            ConversaInterna.setor_id == setor_id,
        )
        .one()
    )
    assert canal.titulo == "Financeiro IC"


def test_activar_setor_cria_canal_interno(client, seed_base, auth_headers, db_session):
    """#916 — activar setor inactivo garante o canal."""
    from app.models.chat_interno import ConversaInterna, TIPO_CONVERSA_SETOR

    r = client.post(
        "/v1/setores",
        json={"nome": "Inactivo IC", "slug": "inactivo-ic", "ativo": False},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 201, r.text
    setor_id = r.json()["id"]
    assert (
        db_session.query(ConversaInterna)
        .filter(ConversaInterna.setor_id == setor_id, ConversaInterna.tipo == TIPO_CONVERSA_SETOR)
        .count()
        == 0
    )

    r_act = client.patch(
        f"/v1/setores/{setor_id}",
        json={"ativo": True},
        headers=auth_headers["admin"],
    )
    assert r_act.status_code == 200, r_act.text
    assert (
        db_session.query(ConversaInterna)
        .filter(ConversaInterna.setor_id == setor_id, ConversaInterna.tipo == TIPO_CONVERSA_SETOR)
        .count()
        == 1
    )


def test_inbox_lista_canal_setor_vazio(client, seed_base, auth_headers):
    """#916 — canal de setor sem mensagens aparece em Interno → Setores."""
    setor1 = seed_base["setor1"].id
    r_canal = client.get(f"/v1/chat-interno/setores/{setor1}/canal", headers=auth_headers["a1"])
    assert r_canal.status_code == 200
    canal_id = r_canal.json()["id"]

    r = client.get("/v1/chat-interno/conversas", headers=auth_headers["a1"])
    assert r.status_code == 200
    setores = [c for c in r.json() if c["tipo"] == "setor"]
    assert any(c["id"] == canal_id for c in setores)
    assert any(c["id"] == canal_id and c.get("ultima_mensagem_corpo") is None for c in setores)


def test_inbox_setor_respeita_vinculo_e_admin_ve_todos(client, seed_base, auth_headers):
    """#916 — membro vê o seu; outro setor 403; admin vê todos os canais."""
    setor1 = seed_base["setor1"].id
    setor2 = seed_base["setor2"].id
    c1 = client.get(f"/v1/chat-interno/setores/{setor1}/canal", headers=auth_headers["a1"]).json()
    c2 = client.get(f"/v1/chat-interno/setores/{setor2}/canal", headers=auth_headers["a2"]).json()

    inbox_a1 = client.get("/v1/chat-interno/conversas", headers=auth_headers["a1"]).json()
    ids_a1 = {c["id"] for c in inbox_a1 if c["tipo"] == "setor"}
    assert c1["id"] in ids_a1
    assert c2["id"] not in ids_a1

    assert (
        client.get(f"/v1/chat-interno/setores/{setor2}/canal", headers=auth_headers["a1"]).status_code
        == 403
    )

    inbox_admin = client.get("/v1/chat-interno/conversas", headers=auth_headers["admin"]).json()
    ids_admin = {c["id"] for c in inbox_admin if c["tipo"] == "setor"}
    assert c1["id"] in ids_admin
    assert c2["id"] in ids_admin


def test_vincular_setor_mostra_canal_na_inbox(client, seed_base, auth_headers, db_session):
    """#916 — novo vínculo setor_ids passa a listar o canal sem passo manual."""
    from app.models.chat_interno import ConversaInterna, TIPO_CONVERSA_SETOR

    r_setor = client.post(
        "/v1/setores",
        json={"nome": "Novo Setor IC", "slug": "novo-setor-ic", "ativo": True},
        headers=auth_headers["admin"],
    )
    assert r_setor.status_code == 201, r_setor.text
    setor_id = r_setor.json()["id"]
    canal = (
        db_session.query(ConversaInterna)
        .filter(ConversaInterna.setor_id == setor_id, ConversaInterna.tipo == TIPO_CONVERSA_SETOR)
        .one()
    )

    a1_id = seed_base["a1"].id
    r_patch = client.patch(
        f"/v1/atendentes/{a1_id}",
        json={"setor_ids": [seed_base["setor1"].id, setor_id]},
        headers=auth_headers["admin"],
    )
    assert r_patch.status_code == 200, r_patch.text

    inbox = client.get("/v1/chat-interno/conversas", headers=auth_headers["a1"]).json()
    assert any(c["id"] == canal.id for c in inbox if c["tipo"] == "setor")

    r_un = client.patch(
        f"/v1/atendentes/{a1_id}",
        json={"setor_ids": [seed_base["setor1"].id]},
        headers=auth_headers["admin"],
    )
    assert r_un.status_code == 200, r_un.text
    inbox2 = client.get("/v1/chat-interno/conversas", headers=auth_headers["a1"]).json()
    assert not any(c["id"] == canal.id for c in inbox2 if c["tipo"] == "setor")
