"""Grupos de permissão substituem o perfil fixo (#S202609-0024)."""


def test_atendente_nao_lista_grupos(client, auth_headers, seed_base):
    r = client.get("/v1/permissao-grupos", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_grupos_padrao_e_vinculo_por_perfil(client, auth_headers, seed_base):
    r = client.get("/v1/permissao-grupos", headers=auth_headers["admin"])
    assert r.status_code == 200
    slugs = {g["slug"] for g in r.json()}
    assert slugs >= {"administrador", "comercial", "atendente"}

    admin = client.get(f"/v1/atendentes/{seed_base['admin'].id}", headers=auth_headers["admin"])
    assert admin.status_code == 200
    corpo = admin.json()
    assert corpo["role"] == "admin"
    assert "Administrador" in corpo["grupo_nomes"]

    ops = client.get(f"/v1/atendentes/{seed_base['ops'].id}", headers=auth_headers["admin"])
    assert ops.status_code == 404


def test_grupo_customizado_deriva_perfil(client, auth_headers, seed_base):
    criado = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={"nome": "Vendas", "permissoes": ["comercial"]},
    )
    assert criado.status_code == 201
    grupo_id = criado.json()["id"]

    patch = client.patch(
        f"/v1/atendentes/{seed_base['a1'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [grupo_id]},
    )
    assert patch.status_code == 200
    assert patch.json()["role"] == "comercial"
    assert patch.json()["grupo_ids"] == [grupo_id]

    ainda = client.get("/v1/permissao-grupos", headers=auth_headers["a1"])
    assert ainda.status_code == 403


def test_uniao_fica_com_o_perfil_mais_amplo(client, auth_headers, seed_base):
    grupos = client.get("/v1/permissao-grupos", headers=auth_headers["admin"]).json()
    comercial = next(g["id"] for g in grupos if g["slug"] == "comercial")
    operacao = next(g["id"] for g in grupos if g["slug"] == "atendente")
    patch = client.patch(
        f"/v1/atendentes/{seed_base['a1'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [operacao, comercial]},
    )
    assert patch.status_code == 200
    assert patch.json()["role"] == "comercial"


def test_nao_remove_o_ultimo_administrador(client, auth_headers, seed_base):
    grupos = client.get("/v1/permissao-grupos", headers=auth_headers["admin"]).json()
    operacao = next(g["id"] for g in grupos if g["slug"] == "atendente")
    r = client.patch(
        f"/v1/atendentes/{seed_base['admin'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [operacao]},
    )
    assert r.status_code == 400
    segue = client.get(f"/v1/atendentes/{seed_base['admin'].id}", headers=auth_headers["admin"])
    assert segue.json()["role"] == "admin"


def test_grupo_padrao_nao_exclui_e_customizado_com_pessoa_tambem_nao(client, auth_headers, seed_base):
    grupos = client.get("/v1/permissao-grupos", headers=auth_headers["admin"]).json()
    padrao = next(g["id"] for g in grupos if g["slug"] == "administrador")
    assert client.delete(f"/v1/permissao-grupos/{padrao}", headers=auth_headers["admin"]).status_code == 400

    criado = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={"nome": "Plantão", "permissoes": ["operacional"]},
    )
    grupo_id = criado.json()["id"]
    client.patch(
        f"/v1/atendentes/{seed_base['a2'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [grupo_id]},
    )
    ocupado = client.delete(f"/v1/permissao-grupos/{grupo_id}", headers=auth_headers["admin"])
    assert ocupado.status_code == 400

    admin_id = next(g["id"] for g in grupos if g["slug"] == "administrador")
    comercial_id = next(g["id"] for g in grupos if g["slug"] == "comercial")
    # Devolve a2 a um grupo padrão e mantém outro administrador na instância.
    client.patch(
        f"/v1/atendentes/{seed_base['a2'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [comercial_id]},
    )
    assert client.delete(f"/v1/permissao-grupos/{grupo_id}", headers=auth_headers["admin"]).status_code == 204
    assert admin_id


def test_perfil_antigo_no_cadastro_vira_grupo_padrao(client, auth_headers, seed_base):
    r = client.post(
        "/v1/atendentes",
        headers=auth_headers["admin"],
        json={
            "email": "novo.comercial@example.com",
            "nome": "Novo Comercial",
            "senha": "senha123",
            "role": "comercial",
            "setor_ids": [seed_base["setor1"].id],
        },
    )
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["role"] == "comercial"
    assert corpo["grupo_nomes"] == ["Comercial"]


def test_grupo_granular_separa_ver_criar_e_editar(client, auth_headers, seed_base, db_session):
    """Gerente cadastra; suporte só vê redes e edita empresas, sem criar."""
    gerente = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={
            "nome": "Gerente do Suporte",
            "permissoes": [
                "operacional",
                "redes.ver",
                "redes.criar",
                "redes.editar",
                "empresas.ver",
                "empresas.criar",
                "empresas.editar",
                "chat.encerrar_sem_demanda",
            ],
        },
    )
    assert gerente.status_code == 201, gerente.text
    suporte = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={
            "nome": "Suporte",
            "permissoes": ["operacional", "redes.ver", "empresas.ver", "empresas.editar"],
        },
    )
    assert suporte.status_code == 201, suporte.text
    client.patch(
        f"/v1/atendentes/{seed_base['a1'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [suporte.json()["id"]]},
    )
    h = auth_headers["a1"]
    assert client.get("/v1/redes", headers=h).status_code == 200
    negado = client.post("/v1/redes", headers=h, json={"nome": "Rede bloqueada"})
    assert negado.status_code == 403
    editada = client.patch(
        f"/v1/empresas/{seed_base['empresa'].id}",
        headers=h,
        json={"nome": "Empresa editada pelo suporte"},
    )
    assert editada.status_code == 200, editada.text
    criada = client.post(
        "/v1/empresas",
        headers=h,
        json={"nome": "Nova bloqueada", "rede_id": seed_base["rede"].id},
    )
    assert criada.status_code == 403

    from app.models.whatsapp_chat import WhatsappChat

    chat = WhatsappChat(
        protocolo="WPP-PERM-1",
        wa_id="5511988887777",
        cliente_nome="Cliente",
        estado="em_atendimento",
        atendente_id=seed_base["a1"].id,
    )
    db_session.add(chat)
    db_session.commit()
    encerrar = client.post(f"/v1/whatsapp/chats/{chat.id}/encerrar", headers=h)
    assert encerrar.status_code == 403


def test_permissoes_modulares_nao_promovem_o_perfil(client, auth_headers, seed_base):
    """Ver setor e ver CRM não viram administrador nem comercial."""
    setor = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={"nome": "Cadastro de setores", "permissoes": ["setores.ver"]},
    )
    assert setor.status_code == 201, setor.text
    crm = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={"nome": "Consulta CRM", "permissoes": ["crm.ver"]},
    )
    assert crm.status_code == 201, crm.text

    pessoa_setor = client.patch(
        f"/v1/atendentes/{seed_base['a1'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [setor.json()["id"]]},
    )
    assert pessoa_setor.status_code == 200, pessoa_setor.text
    assert pessoa_setor.json()["role"] == "atendente"
    h = auth_headers["a1"]
    assert client.get("/v1/setores", headers=h).status_code == 200
    assert client.post("/v1/setores", headers=h, json={"nome": "Bloqueado", "slug": "bloqueado"}).status_code == 403
    assert client.get("/v1/crm/leads", headers=h).status_code == 403

    pessoa_crm = client.patch(
        f"/v1/atendentes/{seed_base['a1'].id}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [crm.json()["id"]]},
    )
    assert pessoa_crm.json()["role"] == "atendente"
    assert client.get("/v1/crm/leads", headers=h).status_code == 200
    assert client.post("/v1/crm/leads", headers=h, json={"nome": "Lead bloqueado"}).status_code == 403


def test_editar_sem_visualizar_grava_o_ver(client, auth_headers, seed_base):
    """Não dá para editar empresa sem ver a lista."""
    r = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={"nome": "Edita empresa", "permissoes": ["empresas.editar", "tickets.reabrir"]},
    )
    assert r.status_code == 201, r.text
    assert set(r.json()["permissoes"]) == {
        "empresas.editar",
        "empresas.ver",
        "tickets.reabrir",
        "tickets.ver",
    }


def test_membros_do_grupo_inclui_e_remove(client, auth_headers, seed_base):
    grupos = client.get("/v1/permissao-grupos", headers=auth_headers["admin"]).json()
    comercial = next(g for g in grupos if g["slug"] == "comercial")
    pessoa = seed_base["a1"].id
    entrou = client.post(
        f"/v1/permissao-grupos/{comercial['id']}/membros",
        headers=auth_headers["admin"],
        json={"atendente_id": pessoa},
    )
    assert entrou.status_code == 201, entrou.text
    membros = client.get(f"/v1/permissao-grupos/{comercial['id']}/membros", headers=auth_headers["admin"])
    assert membros.status_code == 200
    assert pessoa in {item["id"] for item in membros.json()}
    saiu = client.delete(
        f"/v1/permissao-grupos/{comercial['id']}/membros/{pessoa}",
        headers=auth_headers["admin"],
    )
    assert saiu.status_code == 204
    depois = client.get(f"/v1/permissao-grupos/{comercial['id']}/membros", headers=auth_headers["admin"]).json()
    assert pessoa not in {item["id"] for item in depois}


def test_nao_remove_pessoa_do_ultimo_grupo(client, auth_headers, seed_base):
    grupos = client.get("/v1/permissao-grupos", headers=auth_headers["admin"]).json()
    operacao = next(g for g in grupos if g["slug"] == "atendente")
    pessoa = seed_base["a2"].id
    client.patch(
        f"/v1/atendentes/{pessoa}",
        headers=auth_headers["admin"],
        json={"grupo_ids": [operacao["id"]]},
    )
    r = client.delete(
        f"/v1/permissao-grupos/{operacao['id']}/membros/{pessoa}",
        headers=auth_headers["admin"],
    )
    assert r.status_code == 400


def test_permissao_invalida(client, auth_headers, seed_base):
    r = client.post(
        "/v1/permissao-grupos",
        headers=auth_headers["admin"],
        json={"nome": "Estranho", "permissoes": ["ponto.aprovar"]},
    )
    assert r.status_code == 400
