from __future__ import annotations


def _create_ticket(
    client,
    headers: dict[str, str],
    *,
    setor_id: int,
    assunto: str = "Teste",
    descricao: str = "Desc",
    empresa_id: int | None = None,
    rede_id: int | None = None,
    parent_ticket_id: int | None = None,
    prioridade: str | None = None,
):
    body: dict = {"setor_id": setor_id, "assunto": assunto, "descricao": descricao}
    if empresa_id is not None:
        body["empresa_id"] = empresa_id
    if rede_id is not None:
        body["rede_id"] = rede_id
    if parent_ticket_id is not None:
        body["parent_ticket_id"] = parent_ticket_id
    if prioridade is not None:
        body["prioridade"] = prioridade
    return client.post("/v1/tickets", headers=headers, json=body)


def test_criar_ticket_coordenacao_rede(client, seed_base, auth_headers):
    r = _create_ticket(
        client,
        auth_headers["admin"],
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
        assunto="Rollout v2",
        descricao="Atualização em toda a rede",
        prioridade="alta",
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["empresa_id"] is None
    assert body["rede_id"] == seed_base["rede"].id
    assert body["coordenacao_rede"] is True
    assert body["rede_nome"] == seed_base["rede"].nome
    assert body["prioridade"] == "alta"
    assert len(body["children"]) == 1
    filho = client.get(f"/v1/tickets/{body['children'][0]['id']}", headers=auth_headers["admin"])
    assert filho.status_code == 200, filho.text
    assert filho.json()["empresa_id"] == seed_base["empresa"].id
    assert filho.json()["parent_ticket_id"] == body["id"]
    assert filho.json()["assunto"] == "Rollout v2"
    assert filho.json()["descricao"] == "Atualização em toda a rede"
    assert filho.json()["prioridade"] == "alta"
    assert filho.json()["setor_id"] == seed_base["setor1"].id
    hist = client.get(f"/v1/tickets/{body['id']}/historico", headers=auth_headers["admin"])
    assert hist.status_code == 200
    assert any(h["campo"] == "filhos_em_massa" and h["valor_novo"] == "1" for h in hist.json())


def test_rejeita_create_sem_empresa_sem_rede(client, seed_base, auth_headers):
    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={"setor_id": seed_base["setor1"].id, "assunto": "X", "descricao": "Y"},
    )
    assert r.status_code == 422


def test_rejeita_create_empresa_e_rede(client, seed_base, auth_headers):
    r = _create_ticket(
        client,
        auth_headers["admin"],
        empresa_id=seed_base["empresa"].id,
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
    )
    assert r.status_code == 422


def test_coordenacao_abre_filho_por_empresa_ativa(client, seed_base, auth_headers, db_session):
    from app.models import Empresa

    e2 = Empresa(tenant_id=1, rede_id=seed_base["rede"].id, nome="Filial 2", ativo=True)
    inativa = Empresa(tenant_id=1, rede_id=seed_base["rede"].id, nome="Filial inativa", ativo=False)
    db_session.add_all([e2, inativa])
    db_session.commit()

    pai = _create_ticket(
        client,
        auth_headers["admin"],
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
        assunto="Coordenação rollout",
        descricao="Atualização em toda a rede",
    )
    assert pai.status_code == 201, pai.text
    body = pai.json()
    assert len(body["children"]) == 2

    empresas_filhas = set()
    for c in body["children"]:
        det = client.get(f"/v1/tickets/{c['id']}", headers=auth_headers["admin"])
        assert det.status_code == 200
        empresas_filhas.add(det.json()["empresa_id"])
    assert empresas_filhas == {seed_base["empresa"].id, e2.id}

    op = client.get(f"/v1/tickets/{body['id']}/filhos-em-massa/opcoes", headers=auth_headers["admin"])
    assert op.status_code == 200, op.text
    ativas = [e for e in op.json()["empresas"] if e["id"] != inativa.id]
    assert all(e["ja_tem_filho"] for e in ativas)
    assert inativa.id not in {e["id"] for e in op.json()["empresas"]}


def test_coordenacao_rede_sem_empresas_nao_cria_filhos(client, seed_base, auth_headers, db_session):
    from app.models import Rede

    vazia = Rede(tenant_id=1, nome="Rede sem lojas", ativo=True)
    db_session.add(vazia)
    db_session.commit()

    pai = _create_ticket(
        client,
        auth_headers["admin"],
        rede_id=vazia.id,
        setor_id=seed_base["setor1"].id,
        assunto="Coordenação vazia",
    )
    assert pai.status_code == 201, pai.text
    assert pai.json()["children"] == []
    assert pai.json()["coordenacao_rede"] is True


def test_coordenacao_respeita_teto_e_resto_vai_para_massa(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    from app.models import Empresa
    from app.services import ticket_filhos_massa as svc

    monkeypatch.setattr(svc, "MAX_FILHOS_MASSA", 2)
    extras = [
        Empresa(tenant_id=1, rede_id=seed_base["rede"].id, nome="Filial B", ativo=True),
        Empresa(tenant_id=1, rede_id=seed_base["rede"].id, nome="Filial C", ativo=True),
    ]
    db_session.add_all(extras)
    db_session.commit()

    pai = _create_ticket(
        client,
        auth_headers["admin"],
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
        assunto="Coordenação teto",
    )
    assert pai.status_code == 201, pai.text
    body = pai.json()
    parent_id = body["id"]
    assert len(body["children"]) == 2

    op = client.get(f"/v1/tickets/{parent_id}/filhos-em-massa/opcoes", headers=auth_headers["admin"])
    assert op.status_code == 200, op.text
    pendentes = [e["id"] for e in op.json()["empresas"] if not e["ja_tem_filho"]]
    assert len(pendentes) == 1

    criar = client.post(
        f"/v1/tickets/{parent_id}/filhos-em-massa",
        headers=auth_headers["admin"],
        json={"empresa_ids": pendentes},
    )
    assert criar.status_code == 201, criar.text
    assert criar.json()["total"] == 1
    det = client.get(f"/v1/tickets/{parent_id}", headers=auth_headers["admin"])
    assert len(det.json()["children"]) == 3


def test_empresa_nova_ainda_pode_receber_filho_em_massa(client, seed_base, auth_headers, db_session):
    from app.models import Empresa

    pai = _create_ticket(
        client,
        auth_headers["admin"],
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
        assunto="Coordenação rollout",
    )
    assert pai.status_code == 201, pai.text
    parent_id = pai.json()["id"]
    assert len(pai.json()["children"]) == 1

    e2 = Empresa(tenant_id=1, rede_id=seed_base["rede"].id, nome="Filial 2", ativo=True)
    db_session.add(e2)
    db_session.commit()

    criar = client.post(
        f"/v1/tickets/{parent_id}/filhos-em-massa",
        headers=auth_headers["admin"],
        json={"empresa_ids": [e2.id]},
    )
    assert criar.status_code == 201, criar.text
    assert criar.json()["total"] == 1

    det = client.get(f"/v1/tickets/{parent_id}", headers=auth_headers["admin"])
    assert len(det.json()["children"]) == 2


def test_filho_exige_empresa(client, seed_base, auth_headers):
    pai = _create_ticket(
        client,
        auth_headers["admin"],
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
        assunto="Pai coordenação",
    )
    assert pai.status_code == 201
    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "rede_id": seed_base["rede"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Filho inválido",
            "descricao": "x",
            "parent_ticket_id": pai.json()["id"],
        },
    )
    assert r.status_code == 422


def test_pai_coordenacao_bloqueia_fechamento_com_filho_aberto(client, seed_base, auth_headers, db_session):
    from app.models import StatusTicket

    fechado = StatusTicket(nome="Fechado", slug="fechado", ordem=99, ativo=True)
    db_session.add(fechado)
    db_session.commit()
    db_session.refresh(fechado)

    pai = _create_ticket(
        client,
        auth_headers["admin"],
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
        assunto="Coordenação",
    )
    assert pai.status_code == 201
    parent_id = pai.json()["id"]
    assert len(pai.json()["children"]) == 1

    r = client.patch(
        f"/v1/tickets/{parent_id}",
        headers=auth_headers["admin"],
        json={"status_id": fechado.id},
    )
    assert r.status_code == 400
    assert "filho" in r.json()["detail"].lower()
