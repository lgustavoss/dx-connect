from __future__ import annotations

import json

from app.services.email_outbox_policy import MAX_EMAIL_SEND_ATTEMPTS, retry_delay_seconds


def test_max_attempts():
    assert MAX_EMAIL_SEND_ATTEMPTS == 5


def test_retry_delay_backoff():
    assert retry_delay_seconds(1) == 60
    assert retry_delay_seconds(2) == 120
    assert retry_delay_seconds(3) == 240
    assert retry_delay_seconds(10) == 900


def test_health_liveness(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert "capabilities" in body
    assert "integrations" in body
    assert "web_push" in body["integrations"]
    assert "environment" in body


def test_health_ready_ok(client, db_session):
    r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body.get("checks", {}).get("database", {}).get("status") == "ok"
    assert body.get("status") in ("ok", "degraded")


def test_health_ready_db_failure(client, monkeypatch):
    def fail_db(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr("app.services.health_checks.check_database", lambda db: {"status": "error", "detail": "db down"})

    r = client.get("/health/ready")
    assert r.status_code == 503
    body = r.json()
    assert body.get("status") == "unavailable"


def test_structured_log(caplog):
    import logging

    from app.core.structured_log import log_event

    log = logging.getLogger("test.structured")
    with caplog.at_level(logging.INFO):
        log_event(log, "test_event", foo=1, bar="x")
    assert caplog.records
    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "test_event"
    assert payload["foo"] == 1


def test_http_retry_delay():
    from app.services.email_outbox_policy import http_retry_delay_seconds

    assert http_retry_delay_seconds(1) == 2.0
    assert http_retry_delay_seconds(2) == 4.0
    assert http_retry_delay_seconds(10) == 30.0


def test_evolution_send_text_retenta_falha_transiente(monkeypatch):
    from app.services import evolution_api

    calls = {"n": 0}

    def fake_request(method, url, *, headers, body=None, timeout=20):
        calls["n"] += 1
        if calls["n"] < 3:
            return 503, None, "unavailable"
        return 201, {"key": {"id": "wa-msg-1"}}, None

    monkeypatch.setattr(evolution_api, "_request_json", fake_request)
    monkeypatch.setattr(evolution_api.settings, "EVOLUTION_HTTP_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(evolution_api.time, "sleep", lambda s: None)

    ok, err, mid = evolution_api.evolution_send_text(
        "http://evo.local",
        "inst",
        "key",
        "5511999999999",
        "oi",
    )
    assert ok is True
    assert err is None
    assert mid == "wa-msg-1"
    assert calls["n"] == 3


def test_ticket_mensagem_email_retry_ate_falha_permanente(client, seed_base, auth_headers, monkeypatch, db_session):
    from app.models.ticket import TicketMensagem
    from app.services.ticket_mensagem_email_outbox import EMAIL_STATUS_FALHA, process_pending_ticket_mensagem_emails
    from app.services.system_email_config import TransactionalEmailConfig
    from tests.test_ticket_reply_email import _headers, _minimal_rfc822

    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "e165")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    mid_in = "<inbound-retry@dx.test>"
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
    for mod in ("app.services.ticket_client_email", "app.services.system_email_config"):
        monkeypatch.setattr(f"{mod}.get_singleton_email_settings", lambda db: object())
        monkeypatch.setattr(f"{mod}.transactional_config_from_row", lambda row: _cfg)

    def fail_send(*a, **k):
        raise ValueError("Resend indisponível")

    monkeypatch.setattr("app.services.ticket_client_email.enviar_mensagem_texto_sistema", fail_send)
    monkeypatch.setattr("app.config.settings.TICKET_MENSAGEM_EMAIL_GRACE_SECONDS", 0)
    monkeypatch.setattr("app.services.ticket_mensagem_email_outbox.retry_delay_seconds", lambda n: 0)

    r1 = client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["admin"],
        json={
            "corpo": "Tentativa de envio.",
            "tipo": "publico",
            "notificar_cliente_por_email": True,
        },
    )
    assert r1.status_code == 201
    msg_id = r1.json()["id"]

    for _ in range(5):
        process_pending_ticket_mensagem_emails(db_session, limit=10)
        db_session.commit()

    msg = db_session.query(TicketMensagem).filter(TicketMensagem.id == msg_id).first()
    assert msg is not None
    assert msg.email_status == EMAIL_STATUS_FALHA
    assert msg.email_send_attempts == 5
    assert msg.email_last_error
