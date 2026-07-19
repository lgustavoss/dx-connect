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
