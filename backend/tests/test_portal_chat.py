"""Testes — chat ao vivo do portal /kb (#468)."""

from __future__ import annotations

VISITOR_HEADER = "X-Portal-Visitor-Token"


def _habilitar_chat(client, auth_headers, setor_id: int):
    return client.put(
        "/v1/kb/portal-settings",
        json={
            "chat_habilitado": True,
            "chat_setor_id": setor_id,
            "chat_texto_boas_vindas": "Olá! Em que posso ajudar?",
        },
        headers=auth_headers["admin"],
    )


def test_protocolo_portal(client, seed_base, db_session):
    from app.services.protocolo_mensal import gerar_protocolo_chat

    p1 = gerar_protocolo_chat(db_session)
    p2 = gerar_protocolo_chat(db_session)
    db_session.commit()
    assert p1.startswith("#C")
    assert p1 != p2


def test_sessao_publica_fila_assumir_mensagens(client, seed_base, auth_headers):
    assert _habilitar_chat(client, auth_headers, seed_base["setor1"].id).status_code == 200

    r_sess = client.post(
        "/v1/kb/public/chat/session",
        json={"visitante_nome": "Maria Portal", "visitante_email": "maria@exemplo.com"},
    )
    assert r_sess.status_code == 200, r_sess.text
    body = r_sess.json()
    token = body["visitor_token"]
    assert body["chat"]["estado"] == "aguardando_atendente"
    assert body["chat"]["protocolo"].startswith("#C")
    assert len(body["mensagens"]) >= 1

    r_fila = client.get("/v1/portal-chats/fila", headers=auth_headers["a1"])
    assert r_fila.status_code == 200
    fila = r_fila.json()
    assert len(fila) == 1
    chat_id = fila[0]["id"]

    r_ass = client.post(f"/v1/portal-chats/{chat_id}/assumir", headers=auth_headers["a1"])
    assert r_ass.status_code == 200
    assert r_ass.json()["estado"] == "em_atendimento"

    r_msg = client.post(
        f"/v1/portal-chats/{chat_id}/mensagens",
        json={"corpo": "Olá Maria, sou o atendente."},
        headers=auth_headers["a1"],
    )
    assert r_msg.status_code == 200

    r_visit = client.post(
        "/v1/kb/public/chat/mensagens",
        json={"corpo": "Preciso de ajuda com login."},
        headers={VISITOR_HEADER: token},
    )
    assert r_visit.status_code == 200

    r_poll = client.get("/v1/kb/public/chat/mensagens", headers={VISITOR_HEADER: token})
    assert r_poll.status_code == 200
    msgs = r_poll.json()
    assert any(m["corpo"] == "Olá Maria, sou o atendente." for m in msgs)
    assert any(m["corpo"] == "Preciso de ajuda com login." for m in msgs)

    r_enc = client.post(f"/v1/portal-chats/{chat_id}/encerrar", headers=auth_headers["a1"])
    assert r_enc.status_code == 200
    assert r_enc.json()["estado"] == "encerrado"

    r_off = client.post(
        "/v1/kb/public/chat/mensagens",
        json={"corpo": "Ainda estou aqui"},
        headers={VISITOR_HEADER: token},
    )
    assert r_off.status_code == 400


def test_portal_chat_rbac_fila(client, seed_base, auth_headers):
    assert _habilitar_chat(client, auth_headers, seed_base["setor1"].id).status_code == 200
    r_sess = client.post(
        "/v1/kb/public/chat/session",
        json={"visitante_nome": "João"},
    )
    token = r_sess.json()["visitor_token"]

    r_fila_a2 = client.get("/v1/portal-chats/fila", headers=auth_headers["a2"])
    assert r_fila_a2.status_code == 200
    assert r_fila_a2.json() == []

    chat_id = client.get("/v1/portal-chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    r_forbidden = client.post(f"/v1/portal-chats/{chat_id}/assumir", headers=auth_headers["a2"])
    assert r_forbidden.status_code == 403

    client.post(f"/v1/portal-chats/{chat_id}/assumir", headers=auth_headers["a1"])
    client.post(
        "/v1/kb/public/chat/mensagens",
        json={"corpo": "Mensagem do visitante"},
        headers={VISITOR_HEADER: token},
    )

    r_resumo = client.get("/v1/notificacoes/resumo", headers=auth_headers["a1"])
    assert r_resumo.status_code == 200
    assert r_resumo.json()["portal_fila_count"] == 0
    assert r_resumo.json()["portal_respostas_count"] >= 0


def test_chat_desabilitado(client, seed_base, auth_headers):
    r = client.post(
        "/v1/kb/public/chat/session",
        json={"visitante_nome": "Visitante"},
    )
    assert r.status_code == 403


def _seed_natureza_motivo(db_session):
    from app.models.ticket_classificacao import TicketMotivo, TicketNatureza

    nat = TicketNatureza(nome="Dúvida Portal", slug="duvida-portal-test", ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    mot = TicketMotivo(natureza_id=nat.id, nome="Login Portal", slug="login-portal-test", ordem=1, ativo=True)
    db_session.add(mot)
    db_session.commit()
    return nat, mot


def _portal_chat_em_atendimento(client, auth_headers, seed_base):
    assert _habilitar_chat(client, auth_headers, seed_base["setor1"].id).status_code == 200
    r_sess = client.post("/v1/kb/public/chat/session", json={"visitante_nome": "Ana Portal"})
    chat_id = r_sess.json()["chat"]["id"]
    client.post(f"/v1/portal-chats/{chat_id}/assumir", headers=auth_headers["a1"])
    return chat_id


def test_portal_demanda_e_transferencia(client, seed_base, auth_headers, db_session):
    nat, mot = _seed_natureza_motivo(db_session)
    chat_id = _portal_chat_em_atendimento(client, auth_headers, seed_base)

    r_dem = client.post(
        f"/v1/portal-chats/{chat_id}/demandas",
        json={"natureza_id": nat.id, "motivo_id": mot.id, "descricao_curta": "Problema de acesso"},
        headers=auth_headers["a1"],
    )
    assert r_dem.status_code == 201, r_dem.text
    assert r_dem.json()["desfecho"] == "resolvido_sessao"

    msgs = client.get(f"/v1/portal-chats/{chat_id}/mensagens", headers=auth_headers["a1"]).json()
    assert any(m.get("evento_sistema") == "demanda_registrada" for m in msgs)

    r_tr = client.post(
        f"/v1/portal-chats/{chat_id}/transferir",
        json={"setor_id": seed_base["setor2"].id},
        headers=auth_headers["a1"],
    )
    assert r_tr.status_code == 200, r_tr.text
    body = r_tr.json()
    assert body["estado"] == "aguardando_atendente"
    assert body["setor_id"] == seed_base["setor2"].id

    msgs2 = client.get(f"/v1/portal-chats/{chat_id}/mensagens", headers=auth_headers["admin"]).json()
    assert any(m.get("evento_sistema") == "transferencia" for m in msgs2)
