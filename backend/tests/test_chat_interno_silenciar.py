"""Chat interno — silenciar grupo (notificações sonoras)."""


def _criar_grupo(client, headers, titulo: str, atendente_ids: list[int]) -> dict:
    r = client.post(
        "/v1/chat-interno/conversas/grupo",
        json={"titulo": titulo, "atendente_ids": atendente_ids},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_silenciar_e_dessilenciar_grupo(client, seed_base, auth_headers):
    grupo = _criar_grupo(client, auth_headers["a1"], "Plantão", [seed_base["admin"].id])
    assert grupo["silenciado"] is False

    r_mute = client.patch(
        f"/v1/chat-interno/conversas/{grupo['id']}/silenciar",
        json={"silenciado": True},
        headers=auth_headers["a1"],
    )
    assert r_mute.status_code == 200, r_mute.text
    assert r_mute.json()["silenciado"] is True

    r_get = client.get(f"/v1/chat-interno/conversas/{grupo['id']}", headers=auth_headers["a1"])
    assert r_get.status_code == 200
    assert r_get.json()["silenciado"] is True

    r_inbox = client.get("/v1/chat-interno/conversas", headers=auth_headers["a1"])
    assert r_inbox.status_code == 200
    item = next(c for c in r_inbox.json() if c["id"] == grupo["id"])
    assert item["silenciado"] is True

    # Preferência é por participante: outro membro não fica silenciado
    r_other = client.get(f"/v1/chat-interno/conversas/{grupo['id']}", headers=auth_headers["admin"])
    assert r_other.status_code == 200
    assert r_other.json()["silenciado"] is False

    r_unmute = client.patch(
        f"/v1/chat-interno/conversas/{grupo['id']}/silenciar",
        json={"silenciado": False},
        headers=auth_headers["a1"],
    )
    assert r_unmute.status_code == 200
    assert r_unmute.json()["silenciado"] is False


def test_silenciar_grupo_exige_participante(client, seed_base, auth_headers):
    grupo = _criar_grupo(client, auth_headers["a1"], "Privado", [seed_base["admin"].id])
    r = client.patch(
        f"/v1/chat-interno/conversas/{grupo['id']}/silenciar",
        json={"silenciado": True},
        headers=auth_headers["a2"],
    )
    assert r.status_code == 403
