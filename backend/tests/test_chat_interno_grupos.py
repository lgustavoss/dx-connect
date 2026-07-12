"""Chat interno — grupos personalizados (IC-10)."""


def _criar_grupo(client, headers, titulo: str, atendente_ids: list[int]) -> dict:
    r = client.post(
        "/v1/chat-interno/conversas/grupo",
        json={"titulo": titulo, "atendente_ids": atendente_ids},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_criar_grupo_e_inbox(client, seed_base, auth_headers):
    admin_id = seed_base["admin"].id
    a2_id = seed_base["a2"].id
    grupo = _criar_grupo(client, auth_headers["a1"], "Equipe Plantão", [admin_id, a2_id])
    assert grupo["tipo"] == "grupo"
    assert grupo["titulo"] == "Equipe Plantão"
    assert grupo["sou_admin_grupo"] is True
    assert len(grupo["participantes"]) == 3

    r_admin = client.get("/v1/chat-interno/conversas", headers=auth_headers["admin"])
    assert any(c["id"] == grupo["id"] and c["tipo"] == "grupo" for c in r_admin.json())

    r_out = client.get(f"/v1/chat-interno/conversas/{grupo['id']}", headers=auth_headers["admin"])
    assert r_out.status_code == 200


def test_403_fora_do_grupo(client, seed_base, auth_headers):
    grupo = _criar_grupo(client, auth_headers["a1"], "Privado", [seed_base["admin"].id])
    r = client.get(f"/v1/chat-interno/conversas/{grupo['id']}/mensagens", headers=auth_headers["a2"])
    assert r.status_code == 403


def test_admin_adiciona_e_remove_membro(client, seed_base, auth_headers):
    grupo = _criar_grupo(client, auth_headers["a1"], "Ops", [seed_base["admin"].id])
    a2_id = seed_base["a2"].id

    r_add = client.patch(
        f"/v1/chat-interno/conversas/{grupo['id']}/participantes",
        json={"adicionar": [a2_id]},
        headers=auth_headers["a1"],
    )
    assert r_add.status_code == 200
    ids = {p["atendente_id"] for p in r_add.json()["participantes"]}
    assert a2_id in ids

    r_rm = client.patch(
        f"/v1/chat-interno/conversas/{grupo['id']}/participantes",
        json={"remover": [a2_id]},
        headers=auth_headers["a1"],
    )
    assert r_rm.status_code == 200
    ids2 = {p["atendente_id"] for p in r_rm.json()["participantes"]}
    assert a2_id not in ids2

    r_a2 = client.get(f"/v1/chat-interno/conversas/{grupo['id']}", headers=auth_headers["a2"])
    assert r_a2.status_code == 403


def test_membro_nao_gerencia_participantes(client, seed_base, auth_headers):
    grupo = _criar_grupo(client, auth_headers["a1"], "Time", [seed_base["admin"].id])
    r = client.patch(
        f"/v1/chat-interno/conversas/{grupo['id']}/participantes",
        json={"adicionar": [seed_base["a2"].id]},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 403


def test_promover_admin(client, seed_base, auth_headers):
    admin_id = seed_base["admin"].id
    grupo = _criar_grupo(client, auth_headers["a1"], "Liderança", [admin_id])
    r = client.patch(
        f"/v1/chat-interno/conversas/{grupo['id']}/participantes",
        json={"promover_admin": [admin_id]},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    admin_row = next(p for p in r.json()["participantes"] if p["atendente_id"] == admin_id)
    assert admin_row["papel"] == "admin"

    r2 = client.patch(
        f"/v1/chat-interno/conversas/{grupo['id']}/participantes",
        json={"adicionar": [seed_base["a2"].id]},
        headers=auth_headers["admin"],
    )
    assert r2.status_code == 200
