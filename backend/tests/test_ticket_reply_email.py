"""Resposta da equipa por e-mail + índice Message-ID (#165)."""

from __future__ import annotations

import pytest

from app.models.ticket_email_message_id import TicketEmailMessageId
from app.services.system_email_config import TransactionalEmailConfig
from app.services.ticket_client_email import extrair_email_de_from_address
from app.services.ticket_email_index import registar_message_id_para_ticket
from app.services.ticket_mensagem_email_outbox import process_pending_ticket_mensagem_emails


def _headers(secret: str) -> dict[str, str]:
    return {"X-Dx-Email-Webhook-Secret": secret}


def _minimal_rfc822(message_id: str = "<unique-test-msg@dx.local>") -> str:
    return (
        f"From: Cliente Teste <cliente@example.com>\r\n"
        f"To: suporte@dxconnect.local\r\n"
        f"Subject: Problema no sistema\r\n"
        f"Message-ID: {message_id}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"Corpo do pedido de suporte.\r\n"
    )


def _create_ticket_via_api(client, auth_headers, seed_base):
    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Só API",
            "descricao": "Sem e-mail",
        },
    )
    assert r.status_code == 201
    return r.json()


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Foo Bar <cliente@example.com>", "cliente@example.com"),
        ("cliente@example.com", "cliente@example.com"),
        ("Nome", None),
        ("", None),
    ],
)
def test_extrair_email_de_from_address(raw, expected):
    assert extrair_email_de_from_address(raw) == expected


def test_notificar_email_interno_rejeitado(client, seed_base, auth_headers):
    t = _create_ticket_via_api(client, auth_headers, seed_base)
    r = client.post(
        f"/v1/tickets/{t['id']}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": "x", "tipo": "interno", "notificar_cliente_por_email": True},
    )
    assert r.status_code == 400


def test_notificar_email_sem_historico_inbound(client, seed_base, auth_headers):
    t = _create_ticket_via_api(client, auth_headers, seed_base)
    r = client.post(
        f"/v1/tickets/{t['id']}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": "Resposta", "tipo": "publico", "notificar_cliente_por_email": True},
    )
    assert r.status_code == 400
    assert "webhook" in r.json()["detail"].lower() or "histórico" in r.json()["detail"].lower()


def test_notificar_email_webhook_grava_outbound_mid(client, seed_base, auth_headers, monkeypatch, db_session):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "e165")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    mid_in = "<inbound-team-reply@dx.test>"
    r0 = client.post(
        "/v1/webhooks/email-inbound",
        headers=_headers("e165"),
        json={"rfc822": _minimal_rfc822(mid_in)},
    )
    assert r0.status_code == 200
    tid = r0.json()["ticket_id"]

    _cfg = TransactionalEmailConfig(
        api_key="re_test",
        from_email="noreply@test.local",
        from_name="Suporte",
    )
    monkeypatch.setattr(
        "app.services.ticket_client_email.get_singleton_email_settings",
        lambda db: object(),
    )
    monkeypatch.setattr(
        "app.services.ticket_client_email.transactional_config_from_row",
        lambda row: _cfg,
    )
    monkeypatch.setattr(
        "app.services.ticket_client_email.enviar_mensagem_texto_sistema",
        lambda *a, **k: "outbound-team@dx.test",
    )

    r1 = client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["admin"],
        json={
            "corpo": "Segue análise da equipa.",
            "tipo": "publico",
            "notificar_cliente_por_email": True,
        },
    )
    assert r1.status_code == 201, r1.text
    j = r1.json()
    assert j["status"] == "pendente_envio"
    assert j["cliente_notificado_por_email"] is False
    assert j["scheduled_at"] is not None

    n = process_pending_ticket_mensagem_emails(db_session, limit=10)
    assert n == 1
    db_session.commit()

    rows = (
        db_session.query(TicketEmailMessageId)
        .filter(TicketEmailMessageId.ticket_id == tid, TicketEmailMessageId.source == "outbound")
        .all()
    )
    assert len(rows) >= 1
    assert any(r.message_id_normalized == "outbound-team@dx.test" for r in rows)


def test_registar_message_id_idempotente(db_session, seed_base):
    from app.models.ticket import Ticket
    from app.models.status_ticket import StatusTicket
    from app.services.protocolo_mensal import gerar_protocolo_ticket

    st = db_session.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).first()
    t = Ticket(
        tenant_id=seed_base["tenant"].id,
        protocolo=gerar_protocolo_ticket(db_session),
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="t",
        descricao="d",
    )
    db_session.add(t)
    db_session.flush()
    ok1 = registar_message_id_para_ticket(db_session, ticket_id=t.id, message_id="<dup@x>", source="outbound")
    db_session.flush()
    ok2 = registar_message_id_para_ticket(db_session, ticket_id=t.id, message_id="<dup@x>", source="outbound")
    assert ok1 is True
    assert ok2 is False
    db_session.commit()


def test_cliente_responde_a_mid_outbound_equipa_fica_no_mesmo_ticket(
    client, seed_base, auth_headers, monkeypatch, db_session
):
    from tests.test_email_inbound_webhook import _rfc822_reply

    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "thr165")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    root = "<thread-outbound-root@dx.test>"
    r0 = client.post(
        "/v1/webhooks/email-inbound",
        headers=_headers("thr165"),
        json={"rfc822": _minimal_rfc822(root)},
    )
    assert r0.status_code == 200
    tid = r0.json()["ticket_id"]

    out_mid = "reply-from-staff-mid@dx.test"
    _cfg = TransactionalEmailConfig(
        api_key="re_test",
        from_email="noreply@test.local",
        from_name="Suporte",
    )
    monkeypatch.setattr(
        "app.services.ticket_client_email.get_singleton_email_settings",
        lambda db: object(),
    )
    monkeypatch.setattr(
        "app.services.ticket_client_email.transactional_config_from_row",
        lambda row: _cfg,
    )
    monkeypatch.setattr(
        "app.services.ticket_client_email.enviar_mensagem_texto_sistema",
        lambda *a, **k: out_mid,
    )

    r_team = client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": "Resposta da equipa.", "tipo": "publico", "notificar_cliente_por_email": True},
    )
    assert r_team.status_code == 201, r_team.text
    process_pending_ticket_mensagem_emails(db_session, limit=10)
    db_session.commit()

    db_session.expire_all()
    follow = _rfc822_reply(message_id="<client-followup@dx.test>", in_reply_to=f"<{out_mid}>")
    r2 = client.post(
        "/v1/webhooks/email-inbound",
        headers=_headers("thr165"),
        json={"rfc822": follow},
    )
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["threaded"] is True
    assert j2["ticket_id"] == tid
