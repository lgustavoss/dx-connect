"""Classificação (natureza/motivo) e prioridade de tickets (#107, #108)."""

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


def _seed_classificacao(db_session):
    from app.models.ticket_classificacao import TicketMotivo, TicketNatureza

    n_erro = TicketNatureza(nome="Erro", slug="erro", ordem=10, ativo=True)
    n_duv = TicketNatureza(nome="Dúvida", slug="duvida", ordem=20, ativo=True)
    db_session.add_all([n_erro, n_duv])
    db_session.flush()
    m_falha = TicketMotivo(
        natureza_id=n_erro.id, nome="Falha no PDV", slug="falha-pdv", ordem=10, ativo=True
    )
    m_outros = TicketMotivo(natureza_id=n_erro.id, nome="Outros", slug="outros", ordem=99, ativo=True)
    m_op = TicketMotivo(
        natureza_id=n_duv.id, nome="Operacional", slug="operacional", ordem=10, ativo=True
    )
    db_session.add_all([m_falha, m_outros, m_op])
    db_session.commit()
    return {
        "erro": n_erro,
        "duvida": n_duv,
        "falha_pdv": m_falha,
        "outros": m_outros,
        "operacional": m_op,
    }


def _create_ticket(client, auth_headers, seed_base, **extra):
    payload = {
        "empresa_id": seed_base["empresa"].id,
        "setor_id": seed_base["setor1"].id,
        "assunto": extra.pop("assunto", "Ticket teste"),
        "descricao": "Teste",
        **extra,
    }
    r = client.post("/v1/tickets", headers=auth_headers["admin"], json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_criar_ticket_com_prioridade(client, seed_base, auth_headers):
    t = _create_ticket(client, auth_headers, seed_base, prioridade="alta")
    assert t["prioridade"] == "alta"


def test_criar_ticket_prioridade_padrao_normal(client, seed_base, auth_headers):
    t = _create_ticket(client, auth_headers, seed_base)
    assert t["prioridade"] == "normal"


def test_fechar_exige_motivo(client, seed_base, auth_headers, db_session):
    cat = _seed_classificacao(db_session)
    fechado = _ensure_status_fechado(db_session)
    t = _create_ticket(client, auth_headers, seed_base)

    r = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"status_id": fechado.id},
    )
    assert r.status_code == 400
    assert "motivo" in r.json()["detail"].lower()

    r2 = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"status_id": fechado.id, "motivo_id": cat["falha_pdv"].id},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["fechado_em"] is not None
    assert body["motivo_id"] == cat["falha_pdv"].id
    assert body["motivo_nome"] == "Falha no PDV"
    assert body["natureza_nome"] == "Erro"


def test_motivo_outros_exige_texto(client, seed_base, auth_headers, db_session):
    cat = _seed_classificacao(db_session)
    fechado = _ensure_status_fechado(db_session)
    t = _create_ticket(client, auth_headers, seed_base)

    r = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"status_id": fechado.id, "motivo_id": cat["outros"].id},
    )
    assert r.status_code == 400

    r2 = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={
            "status_id": fechado.id,
            "motivo_id": cat["outros"].id,
            "motivo_outro_texto": "Problema específico no caixa 3",
        },
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["motivo_outro_texto"] == "Problema específico no caixa 3"


def test_classificacao_opcional_enquanto_aberto(client, seed_base, auth_headers, db_session):
    cat = _seed_classificacao(db_session)
    t = _create_ticket(client, auth_headers, seed_base)

    r = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"motivo_id": cat["operacional"].id},
    )
    assert r.status_code == 200, r.text
    assert r.json()["motivo_nome"] == "Operacional"
    assert r.json()["natureza_nome"] == "Dúvida"


def test_admin_altera_classificacao_ticket_fechado(client, seed_base, auth_headers, db_session):
    cat = _seed_classificacao(db_session)
    fechado = _ensure_status_fechado(db_session)
    t = _create_ticket(client, auth_headers, seed_base)

    client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"status_id": fechado.id, "motivo_id": cat["falha_pdv"].id},
    )

    r = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"motivo_id": cat["operacional"].id},
    )
    assert r.status_code == 200, r.text
    assert r.json()["motivo_id"] == cat["operacional"].id


def test_atendente_nao_altera_ticket_fechado(client, seed_base, auth_headers, db_session):
    cat = _seed_classificacao(db_session)
    fechado = _ensure_status_fechado(db_session)
    t = _create_ticket(client, auth_headers, seed_base)

    client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"status_id": fechado.id, "motivo_id": cat["falha_pdv"].id},
    )

    r = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["a1"],
        json={"prioridade": "urgente"},
    )
    assert r.status_code == 403


def test_crud_catalogos_admin(client, seed_base, auth_headers, db_session):
    _seed_classificacao(db_session)

    r_list = client.get("/v1/ticket-naturezas", headers=auth_headers["admin"])
    assert r_list.status_code == 200
    assert r_list.json()["total"] >= 2

    r_n = client.post(
        "/v1/ticket-naturezas",
        headers=auth_headers["admin"],
        json={"nome": "Reclamação", "slug": "reclamacao", "ordem": 40, "ativo": True},
    )
    assert r_n.status_code == 201
    nid = r_n.json()["id"]

    r_m = client.post(
        "/v1/ticket-motivos",
        headers=auth_headers["admin"],
        json={
            "natureza_id": nid,
            "nome": "Atendimento",
            "slug": "atendimento",
            "ordem": 1,
            "ativo": True,
        },
    )
    assert r_m.status_code == 201

    r_forbidden = client.post(
        "/v1/ticket-naturezas",
        headers=auth_headers["a1"],
        json={"nome": "X", "slug": "x", "ordem": 1},
    )
    assert r_forbidden.status_code == 403
