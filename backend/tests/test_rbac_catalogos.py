from __future__ import annotations


def _post_ticket(client, headers: dict[str, str], empresa_id: int, setor_id: int):
    r = client.post(
        "/v1/tickets",
        headers=headers,
        json={"empresa_id": empresa_id, "setor_id": setor_id, "assunto": "T", "descricao": "D"},
    )
    assert r.status_code == 201, r.text


def test_atendente_lista_somente_setores_vinculados(client, seed_base, auth_headers):
    r_admin = client.get("/v1/setores", headers=auth_headers["admin"])
    assert r_admin.status_code == 200
    assert r_admin.json()["total"] == 2

    r_a1 = client.get("/v1/setores", headers=auth_headers["a1"])
    assert r_a1.status_code == 200
    assert r_a1.json()["total"] == 1
    assert r_a1.json()["items"][0]["id"] == seed_base["setor1"].id


def test_atendente_lista_empresas_somente_redes_com_ticket_no_escopo(client, seed_base, auth_headers, db_session):
    from app.models import Empresa

    # Sem tickets: nenhuma rede entra no filtro do atendente
    r0 = client.get("/v1/empresas", headers=auth_headers["a1"])
    assert r0.status_code == 200
    assert r0.json()["total"] == 0

    _post_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id)

    r1 = client.get("/v1/empresas", headers=auth_headers["a1"])
    assert r1.status_code == 200
    assert r1.json()["total"] == 1

    # Outra empresa na mesma rede: aparece para quem já enxerga a rede via tickets no setor
    e2 = Empresa(rede_id=seed_base["rede"].id, nome="Empresa 2", ativo=True)
    db_session.add(e2)
    db_session.commit()

    r2 = client.get("/v1/empresas", headers=auth_headers["a1"])
    assert r2.status_code == 200
    assert r2.json()["total"] == 2

    # Atendente do setor 2 não vê empresas só expostas por ticket no setor 1
    r_a2 = client.get("/v1/empresas", headers=auth_headers["a2"])
    assert r_a2.status_code == 200
    assert r_a2.json()["total"] == 0


def test_atendente_lista_empresas_apos_ticket_no_seu_setor(client, seed_base, auth_headers, db_session):
    from app.models import Empresa

    _post_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor2"].id)

    r_a2 = client.get("/v1/empresas", headers=auth_headers["a2"])
    assert r_a2.status_code == 200
    assert r_a2.json()["total"] == 1

    db_session.add(Empresa(rede_id=seed_base["rede"].id, nome="Empresa S2", ativo=True))
    db_session.commit()

    r2 = client.get("/v1/empresas", headers=auth_headers["a2"])
    assert r2.status_code == 200
    assert r2.json()["total"] == 2
