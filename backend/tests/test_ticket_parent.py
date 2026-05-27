from __future__ import annotations


def _create_ticket(
    client,
    headers: dict[str, str],
    empresa_id: int,
    setor_id: int,
    *,
    assunto: str = "Teste",
    descricao: str = "Desc",
    parent_ticket_id: int | None = None,
):
    body: dict = {"empresa_id": empresa_id, "setor_id": setor_id, "assunto": assunto, "descricao": descricao}
    if parent_ticket_id is not None:
        body["parent_ticket_id"] = parent_ticket_id
    r = client.post("/v1/tickets", headers=headers, json=body)
    return r


def test_criar_com_pai_mesma_rede(client, seed_base, auth_headers):
    p = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id, assunto="Pai")
    assert p.status_code == 201, p.text
    pai = p.json()
    c = _create_ticket(
        client,
        auth_headers["admin"],
        seed_base["empresa"].id,
        seed_base["setor1"].id,
        assunto="Filho",
        parent_ticket_id=pai["id"],
    )
    assert c.status_code == 201, c.text
    filho = c.json()
    assert filho["parent_ticket_id"] == pai["id"]
    assert filho["parent"] is not None
    assert filho["parent"]["id"] == pai["id"]
    assert len(filho["children"]) == 0

    g = client.get(f"/v1/tickets/{pai['id']}", headers=auth_headers["admin"])
    assert g.status_code == 200, g.text
    corpo = g.json()
    assert len(corpo["children"]) == 1
    assert corpo["children"][0]["id"] == filho["id"]


def test_nao_fecha_pai_com_filho_aberto(client, seed_base, auth_headers, db_session):
    from app.models import StatusTicket

    fechado = StatusTicket(nome="Fechado", slug="fechado", ordem=99, ativo=True)
    db_session.add(fechado)
    db_session.commit()
    db_session.refresh(fechado)

    p = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id, assunto="Pai")
    assert p.status_code == 201
    pai = p.json()
    c = _create_ticket(
        client,
        auth_headers["admin"],
        seed_base["empresa"].id,
        seed_base["setor1"].id,
        assunto="Filho",
        parent_ticket_id=pai["id"],
    )
    assert c.status_code == 201

    r = client.patch(f"/v1/tickets/{pai['id']}", headers=auth_headers["admin"], json={"status_id": fechado.id})
    assert r.status_code == 400, r.text
    assert "filho" in r.json()["detail"].lower()


def test_rejeita_ciclo(client, seed_base, auth_headers):
    a = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id, assunto="A")
    assert a.status_code == 201
    b = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id, assunto="B")
    assert b.status_code == 201
    id_a = a.json()["id"]
    id_b = b.json()["id"]

    r1 = client.patch(f"/v1/tickets/{id_b}", headers=auth_headers["admin"], json={"parent_ticket_id": id_a})
    assert r1.status_code == 200, r1.text

    r2 = client.patch(f"/v1/tickets/{id_a}", headers=auth_headers["admin"], json={"parent_ticket_id": id_b})
    assert r2.status_code == 400, r2.text


def test_rejeita_pai_outra_rede(client, seed_base, auth_headers, db_session):
    from app.models import Empresa, Rede

    tid = seed_base["tenant"].id
    r2 = Rede(tenant_id=tid, nome="Outra rede", ativo=True)
    db_session.add(r2)
    db_session.flush()
    e2 = Empresa(tenant_id=tid, rede_id=r2.id, nome="Empresa outra rede", ativo=True)
    db_session.add(e2)
    db_session.commit()
    db_session.refresh(e2)

    p = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id)
    assert p.status_code == 201
    pid = p.json()["id"]

    c = _create_ticket(
        client,
        auth_headers["admin"],
        e2.id,
        seed_base["setor1"].id,
        parent_ticket_id=pid,
    )
    assert c.status_code == 400, c.text


def test_desvincular_pai(client, seed_base, auth_headers):
    p = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id)
    assert p.status_code == 201
    pid = p.json()["id"]
    c = _create_ticket(
        client,
        auth_headers["admin"],
        seed_base["empresa"].id,
        seed_base["setor1"].id,
        parent_ticket_id=pid,
    )
    assert c.status_code == 201
    cid = c.json()["id"]

    r = client.patch(f"/v1/tickets/{cid}", headers=auth_headers["admin"], json={"parent_ticket_id": None})
    assert r.status_code == 200, r.text
    assert r.json()["parent_ticket_id"] is None
    assert r.json()["parent"] is None
