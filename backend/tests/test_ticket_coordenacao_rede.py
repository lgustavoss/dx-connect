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
):
    body: dict = {"setor_id": setor_id, "assunto": assunto, "descricao": descricao}
    if empresa_id is not None:
        body["empresa_id"] = empresa_id
    if rede_id is not None:
        body["rede_id"] = rede_id
    if parent_ticket_id is not None:
        body["parent_ticket_id"] = parent_ticket_id
    return client.post("/v1/tickets", headers=headers, json=body)


def test_criar_ticket_coordenacao_rede(client, seed_base, auth_headers):
    r = _create_ticket(
        client,
        auth_headers["admin"],
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
        assunto="Rollout v2",
        descricao="Atualização em toda a rede",
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["empresa_id"] is None
    assert body["rede_id"] == seed_base["rede"].id
    assert body["coordenacao_rede"] is True
    assert body["rede_nome"] == seed_base["rede"].nome


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


def test_filhos_em_massa_com_pai_coordenacao(client, seed_base, auth_headers, db_session):
    from app.models import Empresa

    e2 = Empresa(tenant_id=1, rede_id=seed_base["rede"].id, nome="Filial 2", ativo=True)
    db_session.add(e2)
    db_session.commit()

    pai = _create_ticket(
        client,
        auth_headers["admin"],
        rede_id=seed_base["rede"].id,
        setor_id=seed_base["setor1"].id,
        assunto="Coordenação rollout",
    )
    assert pai.status_code == 201, pai.text
    parent_id = pai.json()["id"]

    op = client.get(f"/v1/tickets/{parent_id}/filhos-em-massa/opcoes", headers=auth_headers["admin"])
    assert op.status_code == 200, op.text
    ids = [e["id"] for e in op.json()["empresas"] if not e["ja_tem_filho"]]

    criar = client.post(
        f"/v1/tickets/{parent_id}/filhos-em-massa",
        headers=auth_headers["admin"],
        json={"empresa_ids": ids},
    )
    assert criar.status_code == 201, criar.text
    assert criar.json()["total"] == 2

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

    client.post(
        f"/v1/tickets/{parent_id}/filhos-em-massa",
        headers=auth_headers["admin"],
        json={"empresa_ids": [seed_base["empresa"].id]},
    )

    r = client.patch(
        f"/v1/tickets/{parent_id}",
        headers=auth_headers["admin"],
        json={"status_id": fechado.id},
    )
    assert r.status_code == 400
    assert "filho" in r.json()["detail"].lower()
