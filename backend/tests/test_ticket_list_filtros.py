from __future__ import annotations


def _create_ticket(client, headers: dict[str, str], empresa_id: int, setor_id: int, assunto: str):
    r = client.post(
        "/v1/tickets",
        headers=headers,
        json={"empresa_id": empresa_id, "setor_id": setor_id, "assunto": assunto, "descricao": "Teste"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_listar_filtro_com_responsavel(client, seed_base, auth_headers):
    empresa_id = seed_base["empresa"].id
    setor_id = seed_base["setor1"].id

    na_fila = _create_ticket(client, auth_headers["admin"], empresa_id, setor_id, "Na fila")
    com_resp = _create_ticket(client, auth_headers["admin"], empresa_id, setor_id, "Com responsável")
    r_patch = client.patch(
        f"/v1/tickets/{com_resp['id']}",
        headers=auth_headers["admin"],
        json={"atendente_id": seed_base["a1"].id},
    )
    assert r_patch.status_code == 200, r_patch.text

    r_fila = client.get(
        "/v1/tickets",
        params={"situacao": "abertos", "sem_responsavel": True},
        headers=auth_headers["admin"],
    )
    assert r_fila.status_code == 200
    ids_fila = {t["id"] for t in r_fila.json()["items"]}
    assert na_fila["id"] in ids_fila
    assert com_resp["id"] not in ids_fila

    r_atend = client.get(
        "/v1/tickets",
        params={"situacao": "abertos", "com_responsavel": True},
        headers=auth_headers["admin"],
    )
    assert r_atend.status_code == 200
    ids_atend = {t["id"] for t in r_atend.json()["items"]}
    assert com_resp["id"] in ids_atend
    assert na_fila["id"] not in ids_atend
