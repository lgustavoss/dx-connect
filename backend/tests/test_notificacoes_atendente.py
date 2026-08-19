from __future__ import annotations

from app.models.atendente_notificacao import NotificacaoEmailOutbox


def _criar_ticket(client, seed_base, auth_headers, *, atendente_id=None):
    payload = {
        "empresa_id": seed_base["empresa"].id,
        "setor_id": seed_base["setor1"].id,
        "assunto": "Ticket notificação teste",
        "descricao": "Teste",
    }
    if atendente_id is not None:
        payload["atendente_id"] = atendente_id
    r = client.post("/v1/tickets", headers=auth_headers["admin"], json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_preferencias_padrao_e_atualizacao(client, seed_base, auth_headers):
    r = client.get("/v1/notificacoes/preferencias", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    assert body["email_habilitado"] is True
    assert body["email_ticket_atribuido"] is True
    assert body["email_nova_mensagem"] is True
    assert body["email_sla_em_risco"] is True
    assert body["email_sla_violado"] is True
    assert body["push_habilitado"] is False
    assert body["push_fila"] is True

    r2 = client.patch(
        "/v1/notificacoes/preferencias",
        headers=auth_headers["a1"],
        json={"email_nova_mensagem": False},
    )
    assert r2.status_code == 200
    assert r2.json()["email_nova_mensagem"] is False
    assert r2.json()["email_ticket_atribuido"] is True


def test_atribuicao_enfileira_email(client, seed_base, auth_headers, db_session):
    t = _criar_ticket(client, seed_base, auth_headers)
    r = client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"atendente_id": seed_base["a1"].id},
    )
    assert r.status_code == 200, r.text

    row = (
        db_session.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.ticket_id == t["id"],
            NotificacaoEmailOutbox.tipo == "ticket_atribuido",
        )
        .first()
    )
    assert row is not None
    assert row.atendente_id == seed_base["a1"].id
    assert row.status == "pendente"
    assert "Acesse:" in row.body
    assert f"/tickets/{t['id']}" not in row.body
    assert row.body.rstrip().endswith("/tickets")


def test_atribuicao_respeita_preferencias(client, seed_base, auth_headers, db_session):
    client.patch(
        "/v1/notificacoes/preferencias",
        headers=auth_headers["a1"],
        json={"email_habilitado": False},
    )
    t = _criar_ticket(client, seed_base, auth_headers)
    client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"atendente_id": seed_base["a1"].id},
    )
    row = db_session.query(NotificacaoEmailOutbox).filter(NotificacaoEmailOutbox.ticket_id == t["id"]).first()
    assert row is None


def test_nova_mensagem_enfileira_para_responsavel(client, seed_base, auth_headers, db_session):
    t = _criar_ticket(client, seed_base, auth_headers)
    client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"atendente_id": seed_base["a1"].id},
    )
    r = client.post(
        f"/v1/tickets/{t['id']}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": "Atualização da equipe", "tipo": "publico"},
    )
    assert r.status_code == 201, r.text

    row = (
        db_session.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.ticket_id == t["id"],
            NotificacaoEmailOutbox.tipo == "nova_mensagem",
        )
        .first()
    )
    assert row is not None
    assert row.atendente_id == seed_base["a1"].id


def test_process_pending_simula_envio_em_dev_sem_smtp(client, seed_base, auth_headers, db_session, monkeypatch):
    def fail_send(*args, **kwargs):
        raise ValueError("Envio de e-mail não configurado na plataforma.")

    monkeypatch.setattr("app.services.notificacao_atendente_email.enviar_mensagem_texto_sistema", fail_send)

    t = _criar_ticket(client, seed_base, auth_headers)
    client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"atendente_id": seed_base["a1"].id},
    )

    from app.services.notificacao_atendente_email import process_pending_notificacao_emails

    n = process_pending_notificacao_emails(db_session, limit=10)
    db_session.commit()
    assert n == 1
    row = db_session.query(NotificacaoEmailOutbox).filter(NotificacaoEmailOutbox.ticket_id == t["id"]).first()
    assert row is not None
    assert row.status == "enviada"


def test_mensagem_email_cliente_enfileira_notificacao(client, seed_base, auth_headers, db_session):
    from app.models.ticket import Ticket, TicketMensagem

    t = _criar_ticket(client, seed_base, auth_headers)
    client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"atendente_id": seed_base["a1"].id},
    )
    ticket = db_session.query(Ticket).filter(Ticket.id == t["id"]).first()
    msg = TicketMensagem(
        ticket_id=ticket.id,
        atendente_id=None,
        tipo="email_cliente",
        corpo="Resposta do cliente por e-mail",
        autor_externo="cliente@test.local",
    )
    db_session.add(msg)
    db_session.flush()

    from app.services.notificacao_atendente_email import notificar_nova_mensagem_ticket

    notificar_nova_mensagem_ticket(db_session, ticket=ticket, mensagem=msg, autor_atendente_id=None)
    db_session.commit()

    row = (
        db_session.query(NotificacaoEmailOutbox)
        .filter(
            NotificacaoEmailOutbox.ticket_id == t["id"],
            NotificacaoEmailOutbox.tipo == "nova_mensagem",
        )
        .first()
    )
    assert row is not None
    assert row.atendente_id == seed_base["a1"].id


def test_process_pending_envia_email(client, seed_base, auth_headers, db_session, monkeypatch):
    sent = []

    def fake_send(db, *, to_addr, subject, body, in_reply_to=None, references=None):
        sent.append({"to": to_addr, "subject": subject})
        return "<mid@test>"

    monkeypatch.setattr("app.services.notificacao_atendente_email.enviar_mensagem_texto_sistema", fake_send)

    t = _criar_ticket(client, seed_base, auth_headers)
    client.patch(
        f"/v1/tickets/{t['id']}",
        headers=auth_headers["admin"],
        json={"atendente_id": seed_base["a1"].id},
    )

    from app.services.notificacao_atendente_email import process_pending_notificacao_emails

    n = process_pending_notificacao_emails(db_session, limit=10)
    db_session.commit()
    assert n == 1
    assert len(sent) == 1
    assert seed_base["a1"].email in sent[0]["to"]
