from __future__ import annotations


def _create_ticket(client, headers: dict[str, str], empresa_id: int, setor_id: int, assunto: str = "Teste", descricao: str = "Desc"):
    r = client.post(
        "/v1/tickets",
        headers=headers,
        json={"empresa_id": empresa_id, "setor_id": setor_id, "assunto": assunto, "descricao": descricao},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_atendente_nao_acessa_ticket_fora_do_setor(client, seed_base, auth_headers):
    # Ticket no setor 2 criado por admin
    t = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor2"].id, assunto="S2")

    # Atendente 1 (setor 1) não pode visualizar ticket do setor 2
    r = client.get(f"/v1/tickets/{t['id']}", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_atendente_nao_define_outro_responsavel(client, seed_base, auth_headers):
    t = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id, assunto="S1")

    # Atendente 1 tenta definir atendente 2 como responsável
    r = client.patch(f"/v1/tickets/{t['id']}", headers=auth_headers["a1"], json={"atendente_id": seed_base["a2"].id})
    assert r.status_code == 403


def test_admin_pode_atribuir_admin_sem_vinculo_setor(client, seed_base, auth_headers, db_session):
    # Cria outro admin (sem setor)
    from app.core.security import hash_senha
    from app.models import Atendente

    admin2 = Atendente(
        email="admin2@test.local",
        nome="Admin 2",
        senha_hash=hash_senha("admin123"),
        role="admin",
        ativo=True,
        must_change_password=False,
    )
    db_session.add(admin2)
    db_session.commit()
    db_session.refresh(admin2)

    t = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id, assunto="S1")
    r = client.patch(f"/v1/tickets/{t['id']}", headers=auth_headers["admin"], json={"atendente_id": admin2.id})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["atendente_id"] == admin2.id


def test_mudar_setor_mantem_admin_responsavel(client, seed_base, auth_headers):
    t = _create_ticket(client, auth_headers["admin"], seed_base["empresa"].id, seed_base["setor1"].id, assunto="S1")

    # Admin vira responsável
    r1 = client.patch(f"/v1/tickets/{t['id']}", headers=auth_headers["admin"], json={"atendente_id": seed_base["admin"].id})
    assert r1.status_code == 200, r1.text
    assert r1.json()["atendente_id"] == seed_base["admin"].id

    # Mudança de setor sem informar atendente_id deve manter admin responsável
    r2 = client.patch(f"/v1/tickets/{t['id']}", headers=auth_headers["admin"], json={"setor_id": seed_base["setor2"].id})
    assert r2.status_code == 200, r2.text
    assert r2.json()["setor_id"] == seed_base["setor2"].id
    assert r2.json()["atendente_id"] == seed_base["admin"].id


def test_listar_atendentes_por_setor_inclui_admins(client, seed_base, auth_headers, db_session):
    from app.core.security import hash_senha
    from app.models import Atendente

    # Outro admin para garantir que vem no endpoint
    admin2 = Atendente(
        email="admin3@test.local",
        nome="Admin 3",
        senha_hash=hash_senha("admin123"),
        role="admin",
        ativo=True,
        must_change_password=False,
    )
    db_session.add(admin2)
    db_session.commit()
    db_session.refresh(admin2)

    r = client.get(f"/v1/atendentes/por-setor/{seed_base['setor1'].id}", headers=auth_headers["a1"])
    assert r.status_code == 200, r.text
    ids = {a["id"] for a in r.json()}
    assert seed_base["a1"].id in ids  # vinculado ao setor
    assert seed_base["admin"].id in ids  # admin sempre deve aparecer
    assert admin2.id in ids  # admin adicional também

