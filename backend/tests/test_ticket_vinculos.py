"""Vínculos entre tickets duplicado / relacionado (#115)."""

from __future__ import annotations


def _ensure_status_fechado(db_session):
    from sqlalchemy import func

    from app.models import StatusTicket

    st = db_session.query(StatusTicket).filter(func.lower(StatusTicket.slug) == "fechado").first()
    if st:
        st.ativo = True
        db_session.commit()
        return st
    st = StatusTicket(nome="Fechado", slug="fechado", ordem=99, ativo=True)
    db_session.add(st)
    db_session.commit()
    db_session.refresh(st)
    return st


def _create_ticket(client, auth_headers, seed_base, assunto: str = "Ticket base"):
    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": assunto,
            "descricao": "Teste",
        },
    )
    assert r.status_code == 201
    return r.json()


def test_criar_vinculo_duplicado_e_relacionado(client, seed_base, auth_headers, db_session):
    _ensure_status_fechado(db_session)
    a = _create_ticket(client, auth_headers, seed_base, "Original")
    b = _create_ticket(client, auth_headers, seed_base, "Cópia")
    c = _create_ticket(client, auth_headers, seed_base, "Outro")

    r1 = client.post(
        f"/v1/tickets/{b['id']}/vinculos",
        headers=auth_headers["admin"],
        json={"related_ticket_id": a["id"], "tipo": "duplicado_de"},
    )
    assert r1.status_code == 201, r1.text
    j1 = r1.json()
    assert j1["tipo"] == "duplicado_de"
    assert j1["rotulo"] == "Duplicado de"
    assert j1["outro_ticket"]["id"] == a["id"]
    assert j1["duplicado_fechado"] is True

    g_b_fechado = client.get(f"/v1/tickets/{b['id']}", headers=auth_headers["admin"])
    assert g_b_fechado.json()["fechado_em"] is not None

    msgs_b = client.get(f"/v1/tickets/{b['id']}/mensagens", headers=auth_headers["admin"])
    assert msgs_b.status_code == 200
    publicas = [m for m in msgs_b.json() if m["tipo"] == "publico"]
    assert any("duplicado de" in m["corpo"].lower() for m in publicas)

    r2 = client.post(
        f"/v1/tickets/{b['id']}/vinculos",
        headers=auth_headers["admin"],
        json={"related_ticket_id": c["id"], "tipo": "relacionado_a"},
    )
    assert r2.status_code == 201, r2.text

    g_b = client.get(f"/v1/tickets/{b['id']}", headers=auth_headers["admin"])
    assert g_b.status_code == 200
    assert len(g_b.json()["vinculos"]) == 2

    g_a = client.get(f"/v1/tickets/{a['id']}", headers=auth_headers["admin"])
    assert g_a.status_code == 200
    vinculos_a = g_a.json()["vinculos"]
    assert len(vinculos_a) == 1
    assert vinculos_a[0]["rotulo"] == "É duplicado deste"
    assert vinculos_a[0]["outro_ticket"]["id"] == b["id"]


def test_nao_vincula_a_si(client, seed_base, auth_headers):
    t = _create_ticket(client, auth_headers, seed_base)
    r = client.post(
        f"/v1/tickets/{t['id']}/vinculos",
        headers=auth_headers["admin"],
        json={"related_ticket_id": t["id"], "tipo": "relacionado_a"},
    )
    assert r.status_code == 400


def test_vinculo_duplicado_rejeitado(client, seed_base, auth_headers, db_session):
    _ensure_status_fechado(db_session)
    a = _create_ticket(client, auth_headers, seed_base, "A")
    b = _create_ticket(client, auth_headers, seed_base, "B")
    payload = {"related_ticket_id": a["id"], "tipo": "duplicado_de"}
    assert client.post(f"/v1/tickets/{b['id']}/vinculos", headers=auth_headers["admin"], json=payload).status_code == 201
    r2 = client.post(f"/v1/tickets/{b['id']}/vinculos", headers=auth_headers["admin"], json=payload)
    assert r2.status_code == 400


def test_remover_vinculo(client, seed_base, auth_headers):
    a = _create_ticket(client, auth_headers, seed_base, "Manter")
    b = _create_ticket(client, auth_headers, seed_base, "Remover")
    r = client.post(
        f"/v1/tickets/{b['id']}/vinculos",
        headers=auth_headers["admin"],
        json={"related_ticket_id": a["id"], "tipo": "relacionado_a"},
    )
    vid = r.json()["id"]
    d = client.delete(f"/v1/tickets/{b['id']}/vinculos/{vid}", headers=auth_headers["admin"])
    assert d.status_code == 204
    g = client.get(f"/v1/tickets/{b['id']}", headers=auth_headers["admin"])
    assert g.json()["vinculos"] == []


def test_atendente_sem_acesso_ao_outro_ticket(client, seed_base, auth_headers):
    a = _create_ticket(client, auth_headers, seed_base, "Setor1")
    b = _create_ticket(client, auth_headers, seed_base, "Setor1 B")
    # atendente1 só vê setor1 - ok for both same setor
    r_ok = client.post(
        f"/v1/tickets/{b['id']}/vinculos",
        headers=auth_headers["a1"],
        json={"related_ticket_id": a["id"], "tipo": "relacionado_a"},
    )
    assert r_ok.status_code == 201

    # ticket em setor2 invisível para a1
    t2 = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor2"].id,
            "assunto": "Financeiro",
            "descricao": "x",
        },
    ).json()
    r_denied = client.post(
        f"/v1/tickets/{a['id']}/vinculos",
        headers=auth_headers["a1"],
        json={"related_ticket_id": t2["id"], "tipo": "relacionado_a"},
    )
    assert r_denied.status_code == 403


def test_duplicado_sem_fechar_mantem_ticket_aberto(client, seed_base, auth_headers):
    a = _create_ticket(client, auth_headers, seed_base, "Original")
    b = _create_ticket(client, auth_headers, seed_base, "Cópia aberta")

    r = client.post(
        f"/v1/tickets/{b['id']}/vinculos",
        headers=auth_headers["admin"],
        json={
            "related_ticket_id": a["id"],
            "tipo": "duplicado_de",
            "fechar_como_duplicado": False,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["duplicado_fechado"] is False

    g_b = client.get(f"/v1/tickets/{b['id']}", headers=auth_headers["admin"])
    assert g_b.json()["fechado_em"] is None


def test_duplicado_rejeita_empresa_diferente(client, seed_base, auth_headers, db_session):
    from app.models import Empresa

    _ensure_status_fechado(db_session)
    outra = Empresa(tenant_id=seed_base["tenant"].id, rede_id=seed_base["rede"].id, nome="Empresa B", ativo=True)
    db_session.add(outra)
    db_session.commit()
    db_session.refresh(outra)

    original = _create_ticket(client, auth_headers, seed_base, "Original")
    outro = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": outra.id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Outra empresa",
            "descricao": "Teste",
        },
    )
    assert outro.status_code == 201

    r = client.post(
        f"/v1/tickets/{outro.json()['id']}/vinculos",
        headers=auth_headers["admin"],
        json={
            "related_ticket_id": original["id"],
            "tipo": "duplicado_de",
            "fechar_como_duplicado": False,
        },
    )
    assert r.status_code == 400
    assert "mesma empresa" in r.json()["detail"].lower()


def test_duplicado_rejeita_rede_diferente(client, seed_base, auth_headers, db_session):
    from app.models import Empresa, Rede

    _ensure_status_fechado(db_session)
    rede2 = Rede(tenant_id=seed_base["tenant"].id, nome="Rede B", ativo=True)
    db_session.add(rede2)
    db_session.flush()
    emp2 = Empresa(tenant_id=seed_base["tenant"].id, rede_id=rede2.id, nome="Empresa rede B", ativo=True)
    db_session.add(emp2)
    db_session.commit()
    db_session.refresh(emp2)

    original = _create_ticket(client, auth_headers, seed_base, "Original rede A")
    outro = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": emp2.id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Outra rede",
            "descricao": "Teste",
        },
    )
    assert outro.status_code == 201

    r = client.post(
        f"/v1/tickets/{outro.json()['id']}/vinculos",
        headers=auth_headers["admin"],
        json={
            "related_ticket_id": original["id"],
            "tipo": "duplicado_de",
            "fechar_como_duplicado": False,
        },
    )
    assert r.status_code == 400
    assert "mesma rede" in r.json()["detail"].lower() or "mesma empresa" in r.json()["detail"].lower()
