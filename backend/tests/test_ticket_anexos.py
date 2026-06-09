from __future__ import annotations


def _create_ticket(client, headers: dict[str, str], empresa_id: int, setor_id: int):
    r = client.post(
        "/v1/tickets",
        headers=headers,
        json={"empresa_id": empresa_id, "setor_id": setor_id, "assunto": "Teste", "descricao": "Desc"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_upload_list_download_anexo_ticket(client, seed_base, auth_headers):
    t = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id)

    up = client.post(
        f"/v1/tickets/{t['id']}/anexos",
        headers=auth_headers["admin"],
        files={"file": ("teste.txt", b"ola", "text/plain")},
    )
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["anexo"]["ticket_id"] == t["id"]
    assert body["anexo"]["nome_original"] == "teste.txt"
    assert body["download_url"].endswith("/download")

    lst = client.get(f"/v1/tickets/{t['id']}/anexos", headers=auth_headers["admin"])
    assert lst.status_code == 200, lst.text
    items = lst.json()
    assert len(items) == 1
    assert items[0]["nome_original"] == "teste.txt"

    dl = client.get(body["download_url"], headers=auth_headers["admin"])
    assert dl.status_code == 200
    assert dl.content == b"ola"


def test_anexo_respeita_rbac_ticket(client, seed_base, auth_headers):
    # Ticket em setor2 (admin cria); a1 não pode ver.
    t = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor2"].id)
    up = client.post(
        f"/v1/tickets/{t['id']}/anexos",
        headers=auth_headers["admin"],
        files={"file": ("teste.txt", b"ola", "text/plain")},
    )
    assert up.status_code == 201, up.text
    url = up.json()["download_url"]

    r1 = client.get(f"/v1/tickets/{t['id']}/anexos", headers=auth_headers["a1"])
    assert r1.status_code == 403
    r2 = client.get(url, headers=auth_headers["a1"])
    assert r2.status_code == 403


def test_nao_permite_upload_em_ticket_fechado(client, seed_base, auth_headers, db_session):
    from app.models import StatusTicket
    from app.models.ticket_classificacao import TicketMotivo, TicketNatureza

    # Cria status Fechado.
    fechado = StatusTicket(nome="Fechado", slug="fechado", ordem=99, ativo=True)
    db_session.add(fechado)
    n = TicketNatureza(nome="Dúvida", slug="duvida", ordem=20, ativo=True)
    db_session.add(n)
    db_session.flush()
    m = TicketMotivo(natureza_id=n.id, nome="Operacional", slug="operacional", ordem=10, ativo=True)
    db_session.add(m)
    db_session.commit()
    db_session.refresh(fechado)

    t = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id)
    r = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"status_id": fechado.id, "motivo_id": m.id},
    )
    assert r.status_code == 200, r.text

    up = client.post(
        f"/v1/tickets/{t['id']}/anexos",
        headers=auth_headers["admin"],
        files={"file": ("teste.txt", b"ola", "text/plain")},
    )
    assert up.status_code == 400

