from __future__ import annotations

import json
from datetime import datetime, timezone

from app.models.status_ticket import StatusTicket
from app.models.webhook_outbox import WebhookOutbox
from app.services.ticket_closed_webhook import (
    EVENT_TICKET_CLOSED,
    STATUS_ENVIADA,
    enfileirar_webhook_ticket_fechado,
    process_pending_webhooks,
)


def _status_fechado(db_session):
    st = db_session.query(StatusTicket).filter(StatusTicket.slug == "fechado").first()
    if st:
        return st
    st = StatusTicket(nome="Fechado", slug="fechado", ordem=99, ativo=True)
    db_session.add(st)
    db_session.commit()
    return st


def test_enfileira_webhook_ao_fechar(seed_base, db_session, monkeypatch):
    from app.models.ticket import Ticket
    from app.services.protocolo_mensal import gerar_protocolo_ticket

    monkeypatch.setattr("app.config.settings.TICKET_CLOSED_WEBHOOK_URL", "https://hooks.example.com/ticket-closed")
    monkeypatch.setattr("app.config.settings.TICKET_CLOSED_WEBHOOK_SECRET", "segredo-teste")

    st = _status_fechado(db_session)
    ticket = Ticket(
        tenant_id=seed_base["tenant"].id,
        protocolo=gerar_protocolo_ticket(db_session),
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="Webhook close test",
        descricao="Corpo",
        fechado_em=datetime.now(timezone.utc),
    )
    db_session.add(ticket)
    db_session.commit()

    enfileirar_webhook_ticket_fechado(db_session, ticket.id)
    db_session.commit()

    row = (
        db_session.query(WebhookOutbox)
        .filter(
            WebhookOutbox.event_type == EVENT_TICKET_CLOSED,
            WebhookOutbox.dedup_key == f"{EVENT_TICKET_CLOSED}:{ticket.id}",
        )
        .first()
    )
    assert row is not None
    payload = json.loads(row.payload_json)
    assert payload["ticket_id"] == ticket.id
    assert payload["event"] == EVENT_TICKET_CLOSED


def test_process_pending_webhook_envia_com_assinatura(db_session, monkeypatch):
    monkeypatch.setattr("app.config.settings.TICKET_CLOSED_WEBHOOK_SECRET", "segredo-teste")
    sent = []

    def fake_post(*, url, body, event_type, secret):
        sent.append({"url": url, "body": body, "event_type": event_type, "secret": secret})
        return 200, None

    monkeypatch.setattr("app.services.ticket_closed_webhook._post_webhook", fake_post)

    now = datetime.now(timezone.utc)
    db_session.add(
        WebhookOutbox(
            event_type=EVENT_TICKET_CLOSED,
            dedup_key=f"{EVENT_TICKET_CLOSED}:99",
            target_url="https://hooks.example.com/x",
            payload_json=json.dumps({"event": EVENT_TICKET_CLOSED, "ticket_id": 99}),
            status="pendente",
            scheduled_at=now,
        )
    )
    db_session.commit()

    n = process_pending_webhooks(db_session, limit=5)
    db_session.commit()
    assert n == 1
    assert len(sent) == 1
    assert sent[0]["secret"] == "segredo-teste"
    row = db_session.query(WebhookOutbox).filter(WebhookOutbox.dedup_key.like(f"{EVENT_TICKET_CLOSED}:99%")).first()
    assert row is not None
    assert row.status == STATUS_ENVIADA


def test_enfileirar_ignora_sem_url(db_session, monkeypatch):
    from app.models.ticket import Ticket
    from app.services.protocolo_mensal import gerar_protocolo_ticket

    monkeypatch.setattr("app.config.settings.TICKET_CLOSED_WEBHOOK_URL", None)
    st = _status_fechado(db_session)
    ticket = Ticket(
        tenant_id=1,
        protocolo=gerar_protocolo_ticket(db_session),
        empresa_id=None,
        setor_id=1,
        status_id=st.id,
        assunto="Sem webhook",
        descricao="x",
        fechado_em=datetime.now(timezone.utc),
    )
    db_session.add(ticket)
    db_session.commit()
    enfileirar_webhook_ticket_fechado(db_session, ticket.id)
    db_session.commit()
    assert db_session.query(WebhookOutbox).count() == 0
