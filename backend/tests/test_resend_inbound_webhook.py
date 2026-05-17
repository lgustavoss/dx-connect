"""Webhook Resend email.received → ticket."""

import json

from app.services.email_inbound_parse import normalize_message_id


def _resend_event(email_id: str = "evt-email-uuid") -> bytes:
    return json.dumps(
        {
            "type": "email.received",
            "created_at": "2026-05-16T20:00:00Z",
            "data": {
                "email_id": email_id,
                "from": "cliente@teste.com",
                "to": ["suporte.t1@inbound.dx.test"],
                "subject": "Teste Resend inbound",
                "message_id": "<resend-inbound-test@dx.local>",
            },
        }
    ).encode("utf-8")


def test_resend_webhook_ignora_outros_eventos(client):
    body = json.dumps({"type": "email.sent", "data": {}}).encode("utf-8")
    r = client.post(
        "/v1/webhooks/resend-inbound",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200
    assert r.json().get("ignored") is True


def test_resend_webhook_cria_ticket(client, seed_base, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)
    monkeypatch.setattr("app.config.settings.RESEND_API_KEY", "re_test")
    monkeypatch.setattr("app.config.settings.RESEND_WEBHOOK_SECRET", "")

    received = {
        "id": "evt-email-uuid",
        "from": "cliente@teste.com",
        "to": ["suporte.t1@inbound.dx.test"],
        "subject": "Teste Resend inbound",
        "message_id": "<resend-inbound-test@dx.local>",
        "text": "Corpo do pedido via Resend.",
        "headers": {},
    }

    def fake_fetch(email_id: str, *, api_key: str | None = None):
        assert email_id == "evt-email-uuid"
        return received

    monkeypatch.setattr("app.api.resend_inbound_webhook.fetch_received_email_with_retry", fake_fetch)

    r = client.post(
        "/v1/webhooks/resend-inbound",
        content=_resend_event(),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["duplicate"] is False
    assert j["ticket_id"] > 0
    assert normalize_message_id("<resend-inbound-test@dx.local>")


def test_resend_webhook_fallback_quando_get_falha(client, seed_base, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)
    monkeypatch.setattr("app.config.settings.RESEND_API_KEY", "re_test")
    monkeypatch.setattr("app.config.settings.RESEND_WEBHOOK_SECRET", "")

    def fail_fetch(email_id: str, *, api_key: str | None = None, attempts: int = 4):
        raise ValueError("Resend receiving falhou (HTTP 400): test")

    monkeypatch.setattr("app.api.resend_inbound_webhook.fetch_received_email_with_retry", fail_fetch)

    r = client.post(
        "/v1/webhooks/resend-inbound",
        content=_resend_event(),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ticket_id"] > 0
