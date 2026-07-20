"""Portal do cliente — auth, escopo e tickets (#263 / #300–#303)."""

from __future__ import annotations

from app.core.security import criar_access_token, hash_senha
from app.models.empresa import Empresa
from app.models.funcionario_rede import FuncionarioRede, FuncionarioRedeEmpresa
from app.models.ticket import Ticket, TicketMensagem


def _criar_funcionario(
    db_session,
    seed_base,
    *,
    tipo: str,
    email: str,
    senha: str = "portal123",
    empresa=None,
    empresas_extra=None,
    ativo: bool = True,
    rede=None,
):
    emp = empresa or seed_base["empresa"]
    rede_obj = rede or seed_base["rede"]
    f = FuncionarioRede(
        nome=f"Func {tipo}",
        email=email,
        tipo=tipo,
        escopo_empresas="all" if tipo == "socio" else "selected",
        ativo=ativo,
        rede_id=rede_obj.id,
        empresa_id=emp.id if tipo == "colaborador" else None,
        senha_hash=hash_senha(senha),
        must_change_password=False,
        token_version=0,
        notificar_email_portal=True,
    )
    db_session.add(f)
    db_session.flush()
    if tipo != "socio":
        ids = [emp.id]
        if empresas_extra:
            ids.extend(e.id for e in empresas_extra)
        for eid in dict.fromkeys(ids):
            db_session.add(FuncionarioRedeEmpresa(funcionario_id=f.id, empresa_id=eid))
            if tipo == "colaborador":
                f.empresa_id = eid
    db_session.commit()
    db_session.refresh(f)
    return f


def _portal_headers(funcionario: FuncionarioRede) -> dict[str, str]:
    tok = criar_access_token(
        {
            "sub": funcionario.email,
            "aud": "portal",
            "fid": funcionario.id,
            "tid": 1,
            "ver": int(funcionario.token_version or 0),
        }
    )
    return {"Authorization": f"Bearer {tok}", "X-Dx-Tenant-Id": "1"}


def test_portal_login_ok_e_inativo_403(client, db_session, seed_base):
    f = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="colab@example.com")
    r = client.post("/v1/portal/auth/login", json={"email": "colab@example.com", "senha": "portal123"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["must_change_password"] is False

    f.ativo = False
    db_session.commit()
    r2 = client.post("/v1/portal/auth/login", json={"email": "colab@example.com", "senha": "portal123"})
    assert r2.status_code == 401


def test_portal_token_nao_acessa_painel_interno(client, db_session, seed_base, auth_headers):
    f = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="colab2@example.com")
    headers = _portal_headers(f)
    r = client.get("/v1/atendentes/me", headers=headers)
    assert r.status_code == 401

    # Token interno também não passa no portal
    r2 = client.get("/v1/portal/me", headers=auth_headers["admin"])
    assert r2.status_code == 401


def test_portal_me_escopo_tres_perfis(client, db_session, seed_base):
    emp2 = Empresa(
        tenant_id=1,
        rede_id=seed_base["rede"].id,
        nome="Empresa 2",
        ativo=True,
    )
    db_session.add(emp2)
    db_session.commit()

    colab = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="c@example.com")
    super_v = _criar_funcionario(
        db_session,
        seed_base,
        tipo="supervisor",
        email="s@example.com",
        empresas_extra=[emp2],
    )
    socio = _criar_funcionario(db_session, seed_base, tipo="socio", email="so@example.com")

    me_c = client.get("/v1/portal/me", headers=_portal_headers(colab)).json()
    assert len(me_c["empresas"]) == 1
    assert me_c["empresas"][0]["id"] == seed_base["empresa"].id

    me_s = client.get("/v1/portal/me", headers=_portal_headers(super_v)).json()
    ids_s = {e["id"] for e in me_s["empresas"]}
    assert seed_base["empresa"].id in ids_s
    assert emp2.id in ids_s

    me_so = client.get("/v1/portal/me", headers=_portal_headers(socio)).json()
    ids_so = {e["id"] for e in me_so["empresas"]}
    assert seed_base["empresa"].id in ids_so
    assert emp2.id in ids_so


def test_portal_tickets_criacao_listagem_e_cross_empresa(client, db_session, seed_base):
    emp2 = Empresa(tenant_id=1, rede_id=seed_base["rede"].id, nome="Outra Emp", ativo=True)
    db_session.add(emp2)
    db_session.commit()

    colab = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="tix@example.com")
    headers = _portal_headers(colab)

    r = client.post(
        "/v1/portal/tickets",
        headers=headers,
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "PDV offline no posto",
            "descricao": "Não inicia o sistema",
        },
    )
    assert r.status_code == 201, r.text
    ticket = r.json()
    assert ticket["protocolo"].startswith("#T")
    assert ticket["assunto"] == "PDV offline no posto"

    # aberto_por_id gravado no banco (não exposto no schema do portal)
    t_db = db_session.query(Ticket).filter(Ticket.id == ticket["id"]).first()
    assert t_db is not None
    assert t_db.aberto_por_id == colab.id

    lista = client.get("/v1/portal/tickets", headers=headers)
    assert lista.status_code == 200
    assert lista.json()["total"] == 1

    # Empresa fora do escopo → 404
    r404 = client.post(
        "/v1/portal/tickets",
        headers=headers,
        json={
            "empresa_id": emp2.id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Não deveria",
            "descricao": "x",
        },
    )
    assert r404.status_code == 404

    # Ticket de outra empresa não aparece / detalhe 404
    outro = _criar_funcionario(
        db_session, seed_base, tipo="colaborador", email="outro@example.com", empresa=emp2
    )
    r_outro = client.post(
        "/v1/portal/tickets",
        headers=_portal_headers(outro),
        json={
            "empresa_id": emp2.id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Ticket alheio",
            "descricao": "segredo",
        },
    )
    assert r_outro.status_code == 201
    tid_alheio = r_outro.json()["id"]
    assert client.get(f"/v1/portal/tickets/{tid_alheio}", headers=headers).status_code == 404


def test_portal_mensagens_publicas_omit_internas(client, db_session, seed_base, auth_headers):
    colab = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="msg@example.com")
    headers = _portal_headers(colab)
    created = client.post(
        "/v1/portal/tickets",
        headers=headers,
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Preciso de ajuda",
            "descricao": "Descrição inicial",
        },
    ).json()
    tid = created["id"]

    # Atendente assume e manda pública + interna
    client.patch(
        f"/v1/tickets/{tid}",
        headers=auth_headers["a1"],
        json={"atendente_id": seed_base["a1"].id},
    )
    client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["a1"],
        json={"corpo": "Estamos analisando", "tipo": "publico"},
    )
    client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["a1"],
        json={"corpo": "nota interna secreta", "tipo": "interno"},
    )

    msgs = client.get(f"/v1/portal/tickets/{tid}/mensagens", headers=headers)
    assert msgs.status_code == 200
    corpos = [m["corpo"] for m in msgs.json()]
    assert "Estamos analisando" in corpos
    assert "nota interna secreta" not in corpos
    assert all(m["tipo"] != "interno" for m in msgs.json())

    # Cliente responde
    r = client.post(
        f"/v1/portal/tickets/{tid}/mensagens",
        headers=headers,
        json={"corpo": "Obrigado, aguardo"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["autor_papel"] == "voce"

    m_db = (
        db_session.query(TicketMensagem)
        .filter(TicketMensagem.ticket_id == tid, TicketMensagem.tipo == "email_cliente")
        .first()
    )
    assert m_db is not None


def test_portal_anexo_upload_e_download(client, db_session, seed_base):
    colab = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="anx@example.com")
    headers = _portal_headers(colab)
    tid = client.post(
        "/v1/portal/tickets",
        headers=headers,
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Com anexo",
            "descricao": "veja o ficheiro",
        },
    ).json()["id"]

    up = client.post(
        f"/v1/portal/tickets/{tid}/anexos",
        headers=headers,
        files={"file": ("foto.txt", b"conteudo-teste", "text/plain")},
    )
    assert up.status_code == 201, up.text
    anexo_id = up.json()["id"]

    dl = client.get(f"/v1/portal/tickets/{tid}/anexos/{anexo_id}/download", headers=headers)
    assert dl.status_code == 200
    assert dl.content == b"conteudo-teste"


def test_portal_notificacao_email_mensagem_publica(client, db_session, seed_base, auth_headers, monkeypatch):
    from app.services.portal_notificacoes import clear_debounce_for_tests

    clear_debounce_for_tests()
    enviados: list[dict] = []

    def fake_send(db, *, to_addr, subject, body, **kwargs):
        enviados.append({"to": to_addr, "subject": subject, "body": body})
        return "msg-id-fake"

    monkeypatch.setattr(
        "app.services.portal_notificacoes.enviar_mensagem_texto_sistema",
        fake_send,
    )

    colab = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="mail@example.com")
    headers = _portal_headers(colab)
    tid = client.post(
        "/v1/portal/tickets",
        headers=headers,
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Notificar",
            "descricao": "x",
        },
    ).json()["id"]

    client.patch(
        f"/v1/tickets/{tid}",
        headers=auth_headers["a1"],
        json={"atendente_id": seed_base["a1"].id},
    )
    client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["a1"],
        json={"corpo": "Resposta da equipe", "tipo": "publico"},
    )
    assert any("Resposta da equipe" in e["body"] for e in enviados)
    assert any(e["to"] == "mail@example.com" for e in enviados)

    # Interna não notifica
    n_antes = len(enviados)
    client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["a1"],
        json={"corpo": "só interno", "tipo": "interno"},
    )
    assert len(enviados) == n_antes


def test_admin_define_senha_portal_no_funcionario(client, db_session, seed_base, auth_headers):
    # Cria sem senha via API admin
    r = client.post(
        "/v1/funcionarios-rede",
        headers=auth_headers["admin"],
        json={
            "nome": "Sem senha",
            "email": "novoportal@example.com",
            "tipo": "colaborador",
            "escopo_empresas": "selected",
            "empresa_ids": [seed_base["empresa"].id],
            "rede_id": seed_base["rede"].id,
            "ativo": True,
        },
    )
    assert r.status_code == 201, r.text
    fid = r.json()["id"]
    assert r.json()["portal_habilitado"] is False

    r2 = client.patch(
        f"/v1/funcionarios-rede/{fid}",
        headers=auth_headers["admin"],
        json={"senha_portal": "senhaforte1", "must_change_password": True},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["portal_habilitado"] is True
    assert r2.json()["must_change_password"] is True

    login = client.post(
        "/v1/portal/auth/login",
        json={"email": "novoportal@example.com", "senha": "senhaforte1"},
    )
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True


def test_criar_socio_sem_empresa_ids_normaliza_escopo_all(client, db_session, seed_base, auth_headers):
    from app.models.funcionario_rede import FuncionarioRede
    from app.services.funcionario_escopo import empresa_ids_vinculados, escopo_efetivo

    r = client.post(
        "/v1/funcionarios-rede",
        headers=auth_headers["admin"],
        json={
            "nome": "Sócio Rede",
            "email": "socio.rede@example.com",
            "tipo": "socio",
            "rede_id": seed_base["rede"].id,
            "ativo": True,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["escopo_empresas"] == "all"
    assert body["tipo"] == "socio"
    f = db_session.query(FuncionarioRede).filter(FuncionarioRede.id == body["id"]).first()
    assert f is not None
    assert escopo_efetivo(f) == "all"
    assert seed_base["empresa"].id in empresa_ids_vinculados(db_session, f)


def test_criar_funcionario_com_senha_portal_no_create(client, seed_base, auth_headers):
    r = client.post(
        "/v1/funcionarios-rede",
        headers=auth_headers["admin"],
        json={
            "nome": "Com portal",
            "email": "portal.create@example.com",
            "tipo": "colaborador",
            "escopo_empresas": "selected",
            "empresa_ids": [seed_base["empresa"].id],
            "rede_id": seed_base["rede"].id,
            "ativo": True,
            "senha_portal": "senhaforte1",
            "must_change_password": True,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["portal_habilitado"] is True

    login = client.post(
        "/v1/portal/auth/login",
        json={"email": "portal.create@example.com", "senha": "senhaforte1"},
    )
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True


def _ticket_portal(client, funcionario, seed_base, *, assunto: str):
    return client.post(
        "/v1/portal/tickets",
        headers=_portal_headers(funcionario),
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": assunto,
            "descricao": "teste rbac",
        },
    )


def test_portal_rbac_tickets_por_papel(client, db_session, seed_base, auth_headers):
    emp2 = Empresa(
        tenant_id=1,
        rede_id=seed_base["rede"].id,
        nome="Empresa RBAC 2",
        ativo=True,
    )
    db_session.add(emp2)
    db_session.commit()

    colab1 = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="rbac.c1@example.com")
    colab2 = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="rbac.c2@example.com")
    supervisor = _criar_funcionario(
        db_session,
        seed_base,
        tipo="supervisor",
        email="rbac.sup@example.com",
        empresas_extra=[emp2],
    )
    socio = _criar_funcionario(db_session, seed_base, tipo="socio", email="rbac.so@example.com")

    t1 = _ticket_portal(client, colab1, seed_base, assunto="Ticket colab 1").json()
    t2 = _ticket_portal(client, colab2, seed_base, assunto="Ticket colab 2").json()
    assert t1["id"] != t2["id"]

    ids_c1 = {x["id"] for x in client.get("/v1/portal/tickets", headers=_portal_headers(colab1)).json()["items"]}
    assert ids_c1 == {t1["id"]}
    assert client.get(f"/v1/portal/tickets/{t2['id']}", headers=_portal_headers(colab1)).status_code == 404

    ids_c2 = {x["id"] for x in client.get("/v1/portal/tickets", headers=_portal_headers(colab2)).json()["items"]}
    assert ids_c2 == {t2["id"]}

    ids_sup = {x["id"] for x in client.get("/v1/portal/tickets", headers=_portal_headers(supervisor)).json()["items"]}
    assert {t1["id"], t2["id"]} <= ids_sup

    ids_so = {x["id"] for x in client.get("/v1/portal/tickets", headers=_portal_headers(socio)).json()["items"]}
    assert {t1["id"], t2["id"]} <= ids_so

    interno = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Aberto pela equipe",
            "descricao": "interno",
            "prioridade": "normal",
        },
    )
    assert interno.status_code == 201, interno.text
    tid_interno = interno.json()["id"]
    assert tid_interno not in ids_c1
    assert client.get(f"/v1/portal/tickets/{tid_interno}", headers=_portal_headers(colab1)).status_code == 404
    assert client.get(f"/v1/portal/tickets/{tid_interno}", headers=_portal_headers(supervisor)).status_code == 200
    assert client.get(f"/v1/portal/tickets/{tid_interno}", headers=_portal_headers(socio)).status_code == 200

    colab_emp2 = _criar_funcionario(
        db_session,
        seed_base,
        tipo="colaborador",
        email="rbac.emp2@example.com",
        empresa=emp2,
    )
    t_emp2 = client.post(
        "/v1/portal/tickets",
        headers=_portal_headers(colab_emp2),
        json={
            "empresa_id": emp2.id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Só emp2",
            "descricao": "x",
        },
    )
    assert t_emp2.status_code == 201
    tid_emp2 = t_emp2.json()["id"]
    assert tid_emp2 not in ids_c1
    assert client.get(f"/v1/portal/tickets/{tid_emp2}", headers=_portal_headers(supervisor)).status_code == 200


def _webhook_whatsapp(wa_id: str, msg_id: str, text: str = "Olá"):
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


def _chat_wpp_vinculado(client, seed_base, auth_headers, funcionario_id: int, *, wa_id: str, msg_id: str, secret: str):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": secret},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": secret}
    client.post("/v1/webhooks/evolution", json=_webhook_whatsapp(wa_id, msg_id), headers=h)
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    client.post(
        f"/v1/whatsapp/chats/{cid}/vincular-funcionario",
        json={"funcionario_rede_id": funcionario_id},
        headers=auth_headers["a1"],
    )
    return cid


def test_portal_chats_rbac_e_mensagens(client, db_session, seed_base, auth_headers):
    colab1 = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="wpp.c1@example.com")
    colab2 = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="wpp.c2@example.com")
    supervisor = _criar_funcionario(db_session, seed_base, tipo="supervisor", email="wpp.sup@example.com")
    socio = _criar_funcionario(db_session, seed_base, tipo="socio", email="wpp.so@example.com")

    cid1 = _chat_wpp_vinculado(
        client, seed_base, auth_headers, colab1.id, wa_id="5511888000001", msg_id="pw-1", secret="portal-wpp-1"
    )
    cid2 = _chat_wpp_vinculado(
        client, seed_base, auth_headers, colab2.id, wa_id="5511888000002", msg_id="pw-2", secret="portal-wpp-2"
    )

    ids_c1 = {x["id"] for x in client.get("/v1/portal/chats", headers=_portal_headers(colab1)).json()["items"]}
    assert ids_c1 == {cid1}
    assert client.get(f"/v1/portal/chats/{cid2}", headers=_portal_headers(colab1)).status_code == 404

    ids_sup = {x["id"] for x in client.get("/v1/portal/chats", headers=_portal_headers(supervisor)).json()["items"]}
    assert {cid1, cid2} <= ids_sup

    ids_so = {x["id"] for x in client.get("/v1/portal/chats", headers=_portal_headers(socio)).json()["items"]}
    assert {cid1, cid2} <= ids_so

    client.post(
        f"/v1/whatsapp/chats/{cid1}/comentarios-internos",
        headers=auth_headers["a1"],
        json={"texto": "nota secreta"},
    )

    msgs = client.get(f"/v1/portal/chats/{cid1}/mensagens", headers=_portal_headers(colab1)).json()
    corpos = [m["corpo"] for m in msgs]
    assert any("Olá" in c for c in corpos)
    assert not any("nota secreta" in c for c in corpos)
    assert not any("INTERNO" in c for c in corpos)

    det = client.get(f"/v1/portal/chats/{cid1}", headers=_portal_headers(colab1)).json()
    assert det["protocolo"].startswith("#")
    assert det["empresa_id"] == seed_base["empresa"].id


def test_portal_equipe_403_nao_socio(client, db_session, seed_base):
    colab = _criar_funcionario(db_session, seed_base, tipo="colaborador", email="eq.c@example.com")
    supervisor = _criar_funcionario(db_session, seed_base, tipo="supervisor", email="eq.s@example.com")
    for headers in (_portal_headers(colab), _portal_headers(supervisor)):
        assert client.get("/v1/portal/equipe/funcionarios", headers=headers).status_code == 403
        assert client.get("/v1/portal/equipe/empresas", headers=headers).status_code == 403
        assert (
            client.post(
                "/v1/portal/equipe/funcionarios",
                headers=headers,
                json={
                    "nome": "Novo",
                    "email": "novo@example.com",
                    "tipo": "colaborador",
                    "empresa_id": seed_base["empresa"].id,
                    "ativo": True,
                },
            ).status_code
            == 403
        )


def test_portal_equipe_socio_crud_e_restricoes(client, db_session, seed_base):
    emp2 = Empresa(
        tenant_id=1,
        rede_id=seed_base["rede"].id,
        nome="Empresa Equipe 2",
        ativo=True,
    )
    db_session.add(emp2)
    db_session.commit()

    socio = _criar_funcionario(db_session, seed_base, tipo="socio", email="eq.so@example.com")
    outro_socio = _criar_funcionario(db_session, seed_base, tipo="socio", email="eq.so2@example.com")
    headers = _portal_headers(socio)

    lista = client.get("/v1/portal/equipe/funcionarios", headers=headers)
    assert lista.status_code == 200, lista.text
    emails = {x["email"] for x in lista.json()["items"]}
    assert "eq.so@example.com" in emails
    assert "eq.so2@example.com" in emails

    empresas = client.get("/v1/portal/equipe/empresas", headers=headers)
    assert empresas.status_code == 200
    ids_emp = {e["id"] for e in empresas.json()}
    assert seed_base["empresa"].id in ids_emp
    assert emp2.id in ids_emp

    r_socio = client.post(
        "/v1/portal/equipe/funcionarios",
        headers=headers,
        json={
            "nome": "Não pode",
            "email": "nao.socio@example.com",
            "tipo": "socio",
            "ativo": True,
        },
    )
    assert r_socio.status_code == 422

    r_colab = client.post(
        "/v1/portal/equipe/funcionarios",
        headers=headers,
        json={
            "nome": "Colab Portal",
            "email": "colab.portal@example.com",
            "tipo": "colaborador",
            "empresa_id": seed_base["empresa"].id,
            "senha_portal": "senhaforte1",
            "must_change_password": True,
            "ativo": True,
        },
    )
    assert r_colab.status_code == 201, r_colab.text
    fid = r_colab.json()["id"]
    assert r_colab.json()["portal_habilitado"] is True
    assert r_colab.json()["tipo"] == "colaborador"

    login = client.post(
        "/v1/portal/auth/login",
        json={"email": "colab.portal@example.com", "senha": "senhaforte1"},
    )
    assert login.status_code == 200

    r_sup = client.patch(
        f"/v1/portal/equipe/funcionarios/{fid}",
        headers=headers,
        json={
            "tipo": "supervisor",
            "empresa_ids": [seed_base["empresa"].id, emp2.id],
            "nome": "Super Portal",
        },
    )
    assert r_sup.status_code == 200, r_sup.text
    assert r_sup.json()["tipo"] == "supervisor"
    assert set(r_sup.json()["empresa_ids"]) == {seed_base["empresa"].id, emp2.id}

    r_outro = client.patch(
        f"/v1/portal/equipe/funcionarios/{outro_socio.id}",
        headers=headers,
        json={"nome": "Tentativa inválida", "ativo": False},
    )
    assert r_outro.status_code == 400, r_outro.text

    r_outro_ok = client.patch(
        f"/v1/portal/equipe/funcionarios/{outro_socio.id}",
        headers=headers,
        json={"ativo": False, "notificar_email_portal": False},
    )
    assert r_outro_ok.status_code == 200, r_outro_ok.text
    assert r_outro_ok.json()["ativo"] is False
    assert r_outro_ok.json()["notificar_email_portal"] is False


def test_portal_public_branding_compartilha_settings(client, auth_headers):
    client.put(
        "/v1/kb/portal-settings",
        headers=auth_headers["admin"],
        json={
            "portal_titulo": "Suporte ACME",
            "cor_header": "#112233",
            "cor_primaria": "#AABBCC",
            "cor_texto_header": "#FFFFFF",
            "cor_texto_corpo": "#222222",
            "cor_fundo": "#EEEEEE",
            "cor_link": "#0055AA",
            "texto_boas_vindas": "Bem-vindo ao suporte ACME.",
        },
    )
    kb = client.get("/v1/kb/public/branding")
    portal = client.get("/v1/portal/public/branding")
    assert kb.status_code == 200, kb.text
    assert portal.status_code == 200, portal.text
    kb_body = kb.json()
    portal_body = portal.json()
    assert kb_body["cor_primaria"] == "#AABBCC"
    assert portal_body["cor_primaria"] == "#AABBCC"
    assert kb_body["portal_titulo"] == "Suporte ACME"
    assert portal_body["portal_titulo"] == "Portal do cliente"
    assert portal_body["texto_boas_vindas"] == "Bem-vindo ao suporte ACME."


def test_portal_public_branding_fallback_sem_settings(client):
    r = client.get("/v1/portal/public/branding")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["portal_titulo"] == "Portal do cliente"
    assert body["cor_primaria"] == "#0D9488"
    assert body["logo_url"] is None
