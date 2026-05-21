"""Webhook de ingestão de e-mail → ticket (idempotência + threading #164)."""

from datetime import datetime, timezone

from app.services.email_inbound_parse import ParsedInboundEmail, thread_lookup_message_ids
from app.services.system_email_config import TransactionalEmailConfig


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


def _rfc822_reply(*, message_id: str, in_reply_to: str | None, references: str | None = None) -> str:
    irt = f"In-Reply-To: {in_reply_to}\r\n" if in_reply_to else ""
    refs = f"References: {references}\r\n" if references else ""
    return (
        f"From: Cliente Teste <cliente@example.com>\r\n"
        f"To: suporte@dxconnect.local\r\n"
        f"Subject: Re: Problema\r\n"
        f"Message-ID: {message_id}\r\n"
        f"{irt}{refs}"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"Corpo da resposta.\r\n"
    )


def test_thread_lookup_message_ids_ordem():
    p = ParsedInboundEmail(
        message_id="novo@x",
        in_reply_to="pai@x",
        references="<avo@x> <pai@x>",
        from_display="a",
        from_email="a@b",
        subject="s",
        body_text="b",
    )
    ids = thread_lookup_message_ids(p)
    assert ids[0] == "pai@x"
    assert "pai@x" in ids and "avo@x" in ids
    assert ids.index("pai@x") < ids.index("avo@x")


def test_webhook_sem_secret_retorna_503(client):
    r = client.post("/v1/webhooks/email-inbound", headers=_headers("qualquer"), json={"rfc822": _minimal_rfc822()})
    assert r.status_code == 503


def test_webhook_secret_errado_retorna_401(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "segredo-correto")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", 1)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", 1)
    r = client.post("/v1/webhooks/email-inbound", headers=_headers("errado"), json={"rfc822": _minimal_rfc822()})
    assert r.status_code == 401


def test_webhook_json_cria_ticket_e_idempotente(client, seed_base, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "segredo-teste")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    mid = "<idempotency-1@dx.test>"
    body = {"rfc822": _minimal_rfc822(mid)}
    r1 = client.post("/v1/webhooks/email-inbound", headers=_headers("segredo-teste"), json=body)
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["duplicate"] is False
    assert j1.get("threaded") is False
    assert j1["ticket_id"] >= 1
    assert j1["protocolo"]

    r2 = client.post("/v1/webhooks/email-inbound", headers=_headers("segredo-teste"), json=body)
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["duplicate"] is True
    assert j2.get("threaded") is False
    assert j2["ticket_id"] == j1["ticket_id"]
    assert j2["protocolo"] == j1["protocolo"]


def test_webhook_form_sendgrid_like(client, seed_base, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "s2")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    r = client.post(
        "/v1/webhooks/email-inbound",
        headers=_headers("s2"),
        data={
            "from": "Form User <form@example.com>",
            "subject": "Assunto form",
            "text": "Texto do corpo",
            "headers": "Message-ID: <form-msg-99@example.com>\n",
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert j["duplicate"] is False
    assert j.get("threaded") is False


def test_webhook_sem_message_id_retorna_400(client, seed_base, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "s3")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    bad = (
        "From: a@b.com\r\n"
        "To: x@y.com\r\n"
        "Subject: Sem mid\r\n"
        "Content-Type: text/plain\r\n"
        "\r\n"
        "oi\r\n"
    )
    r = client.post("/v1/webhooks/email-inbound", headers=_headers("s3"), json={"rfc822": bad})
    assert r.status_code == 400


def test_webhook_resposta_in_reply_to_mesmo_ticket(client, seed_base, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "thr1")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    root = "<thread-root-aa@dx.test>"
    r1 = client.post("/v1/webhooks/email-inbound", headers=_headers("thr1"), json={"rfc822": _minimal_rfc822(root)})
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["threaded"] is False

    reply = _rfc822_reply(message_id="<thread-reply-aa@dx.test>", in_reply_to=root)
    r2 = client.post("/v1/webhooks/email-inbound", headers=_headers("thr1"), json={"rfc822": reply})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["duplicate"] is False
    assert j2["threaded"] is True
    assert j2["ticket_id"] == j1["ticket_id"]
    assert j2["protocolo"] == j1["protocolo"]

    r3 = client.post("/v1/webhooks/email-inbound", headers=_headers("thr1"), json={"rfc822": reply})
    assert r3.status_code == 200
    j3 = r3.json()
    assert j3["duplicate"] is True


def test_webhook_sem_match_cria_segundo_ticket(client, seed_base, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "thr2")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    a = "<novo-ticket-a@dx.test>"
    b = "<novo-ticket-b@dx.test>"
    ja = client.post("/v1/webhooks/email-inbound", headers=_headers("thr2"), json={"rfc822": _minimal_rfc822(a)}).json()
    jb = client.post("/v1/webhooks/email-inbound", headers=_headers("thr2"), json={"rfc822": _minimal_rfc822(b)}).json()
    assert ja["ticket_id"] != jb["ticket_id"]
    assert jb["threaded"] is False


def test_webhook_resposta_ticket_fechado_cria_triagem_e_auto_resposta(client, seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "closed1")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    _cfg = TransactionalEmailConfig(
        api_key="re_test",
        from_email="noreply@test.local",
        from_name="Suporte",
    )

    monkeypatch.setattr(
        "app.services.ticket_from_inbound_email.get_singleton_email_settings",
        lambda db: object(),
    )
    monkeypatch.setattr(
        "app.services.ticket_from_inbound_email.transactional_config_from_row",
        lambda row: _cfg,
    )
    monkeypatch.setattr(
        "app.services.ticket_from_inbound_email.enviar_mensagem_texto_sistema",
        lambda *a, **k: "auto-reply-mid@dx.test",
    )

    root = "<thread-closed-root@dx.test>"
    r1 = client.post("/v1/webhooks/email-inbound", headers=_headers("closed1"), json={"rfc822": _minimal_rfc822(root)})
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["after_close_new_ticket"] is False

    from app.models.ticket import Ticket

    t = db_session.get(Ticket, j1["ticket_id"])
    assert t is not None
    t.fechado_em = datetime.now(timezone.utc)
    db_session.commit()

    reply = _rfc822_reply(message_id="<thread-closed-reply@dx.test>", in_reply_to=root)
    r2 = client.post("/v1/webhooks/email-inbound", headers=_headers("closed1"), json={"rfc822": reply})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["duplicate"] is False
    assert j2["threaded"] is False
    assert j2["after_close_new_ticket"] is True
    assert j2["auto_reply_sent"] is True
    assert j2["ticket_id"] != j1["ticket_id"]
    assert j2["protocolo"] != j1["protocolo"]

    t_new = db_session.get(Ticket, j2["ticket_id"])
    assert t_new is not None
    assert "[Triagem]" in (t_new.assunto or "")
    assert j1["protocolo"] in (t_new.assunto or "")

    from app.models.ticket_email_message_id import TicketEmailMessageId

    out_rows = (
        db_session.query(TicketEmailMessageId)
        .filter(
            TicketEmailMessageId.ticket_id == j2["ticket_id"],
            TicketEmailMessageId.source == "outbound",
        )
        .all()
    )
    assert len(out_rows) == 1
    assert out_rows[0].message_id_normalized == "auto-reply-mid@dx.test"


def test_webhook_resposta_ticket_fechado_sem_resend_nao_envia_auto_reply(client, seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "closed2")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    root = "<thread-closed-nosmtp@dx.test>"
    r1 = client.post("/v1/webhooks/email-inbound", headers=_headers("closed2"), json={"rfc822": _minimal_rfc822(root)})
    j1 = r1.json()

    from app.models.ticket import Ticket

    t = db_session.get(Ticket, j1["ticket_id"])
    t.fechado_em = datetime.now(timezone.utc)
    db_session.commit()

    reply = _rfc822_reply(message_id="<thread-closed-reply2@dx.test>", in_reply_to=root)
    r2 = client.post("/v1/webhooks/email-inbound", headers=_headers("closed2"), json={"rfc822": reply})
    j2 = r2.json()
    assert j2["after_close_new_ticket"] is True
    assert j2["auto_reply_sent"] is False
