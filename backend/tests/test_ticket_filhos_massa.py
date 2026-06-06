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
    return client.post("/v1/tickets", headers=headers, json=body)


def _add_empresas_rede(db_session, rede_id: int, nomes: list[str]):
    from app.models import Empresa

    rows = [Empresa(tenant_id=1, rede_id=rede_id, nome=n, ativo=True) for n in nomes]
    db_session.add_all(rows)
    db_session.commit()
    return rows


def test_opcoes_e_criacao_filhos_em_massa(client, seed_base, auth_headers, db_session):
    extras = _add_empresas_rede(db_session, seed_base["rede"].id, ["Loja B", "Loja C"])

    pai = _create_ticket(
        client,
        auth_headers["admin"],
        seed_base["empresa"].id,
        seed_base["setor1"].id,
        assunto="Atualização de sistema",
        descricao="Deploy v2 em toda a rede",
    )
    assert pai.status_code == 201, pai.text
    parent_id = pai.json()["id"]

    op = client.get(f"/v1/tickets/{parent_id}/filhos-em-massa/opcoes", headers=auth_headers["admin"])
    assert op.status_code == 200, op.text
    body = op.json()
    assert body["rede_id"] == seed_base["rede"].id
    assert body["assunto_padrao"] == "Atualização de sistema"
    assert len(body["empresas"]) == 3
    assert all(not e["ja_tem_filho"] for e in body["empresas"])

    ids = [e["id"] for e in body["empresas"]]
    criar = client.post(
        f"/v1/tickets/{parent_id}/filhos-em-massa",
        headers=auth_headers["admin"],
        json={"empresa_ids": ids},
    )
    assert criar.status_code == 201, criar.text
    res = criar.json()
    assert res["total"] == 3
    assert len(res["criados"]) == 3
    assert {c["empresa_id"] for c in res["criados"]} == set(ids)

    det = client.get(f"/v1/tickets/{parent_id}", headers=auth_headers["admin"])
    assert det.status_code == 200
    assert len(det.json()["children"]) == 3

    hist = client.get(f"/v1/tickets/{parent_id}/historico", headers=auth_headers["admin"])
    assert hist.status_code == 200
    assert any(h["campo"] == "filhos_em_massa" and h["valor_novo"] == "3" for h in hist.json())

    op2 = client.get(f"/v1/tickets/{parent_id}/filhos-em-massa/opcoes", headers=auth_headers["admin"])
    assert op2.status_code == 200
    assert all(e["ja_tem_filho"] for e in op2.json()["empresas"])

    dup = client.post(
        f"/v1/tickets/{parent_id}/filhos-em-massa",
        headers=auth_headers["admin"],
        json={"empresa_ids": [extras[0].id]},
    )
    assert dup.status_code == 400
    assert "Já existe ticket filho" in dup.json()["detail"]


def test_filhos_em_massa_assunto_customizado(client, seed_base, auth_headers):
    pai = _create_ticket(
        client,
        auth_headers["admin"],
        seed_base["empresa"].id,
        seed_base["setor1"].id,
        assunto="Pai",
    )
    assert pai.status_code == 201
    parent_id = pai.json()["id"]

    criar = client.post(
        f"/v1/tickets/{parent_id}/filhos-em-massa",
        headers=auth_headers["admin"],
        json={
            "empresa_ids": [seed_base["empresa"].id],
            "assunto": "Filho custom",
            "descricao": "Instruções específicas",
        },
    )
    assert criar.status_code == 201, criar.text
    filho_id = criar.json()["criados"][0]["id"]
    filho = client.get(f"/v1/tickets/{filho_id}", headers=auth_headers["admin"])
    assert filho.status_code == 200
    assert filho.json()["assunto"] == "Filho custom"
    assert filho.json()["descricao"] == "Instruções específicas"


def test_filhos_em_massa_rbac_setor(client, seed_base, auth_headers, db_session):
    _add_empresas_rede(db_session, seed_base["rede"].id, ["Outra loja"])
    pai = _create_ticket(
        client,
        auth_headers["admin"],
        seed_base["empresa"].id,
        seed_base["setor2"].id,
        assunto="Pai financeiro",
    )
    assert pai.status_code == 201
    parent_id = pai.json()["id"]

    op = client.get(f"/v1/tickets/{parent_id}/filhos-em-massa/opcoes", headers=auth_headers["a1"])
    assert op.status_code == 403

    ids = [e["id"] for e in client.get(
        f"/v1/tickets/{parent_id}/filhos-em-massa/opcoes",
        headers=auth_headers["admin"],
    ).json()["empresas"]]

    criar = client.post(
        f"/v1/tickets/{parent_id}/filhos-em-massa",
        headers=auth_headers["a1"],
        json={"empresa_ids": ids[:1]},
    )
    assert criar.status_code == 403
