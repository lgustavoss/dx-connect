"""Fila de e-mail em mensagens públicas (#140)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.ticket import TicketMensagem
from app.services.system_email_config import TransactionalEmailConfig
from app.services.ticket_mensagem_email_outbox import (
    EMAIL_STATUS_CANCELADA,
    EMAIL_STATUS_EM_EDICAO,
    EMAIL_STATUS_ENVIADA,
    EMAIL_STATUS_PENDENTE,
    _dt_for_db,
    agendar_envio_email,
    cancelar_envio,
    iniciar_edicao,
    liberar_locks_expirados,
    process_pending_ticket_mensagem_emails,
    salvar_edicao,
    validar_lock,
)


def _mock_resend(monkeypatch):
    _cfg = TransactionalEmailConfig(
        api_key="re_test",
        from_email="noreply@test.local",
        from_name="Suporte",
    )
    for mod in ("app.services.ticket_client_email", "app.services.system_email_config"):
        monkeypatch.setattr(f"{mod}.get_singleton_email_settings", lambda db: object())
        monkeypatch.setattr(f"{mod}.transactional_config_from_row", lambda row: _cfg)


def _minimal_rfc822(message_id: str = "<outbox-test@dx.local>") -> str:
    return (
        f"From: Cliente <cliente@example.com>\r\n"
        f"To: suporte@dxconnect.local\r\n"
        f"Subject: Teste outbox\r\n"
        f"Message-ID: {message_id}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"Corpo.\r\n"
    )


def test_criar_mensagem_agenda_sem_enviar_imediato(client, seed_base, auth_headers, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "ob140a")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)
    _mock_resend(monkeypatch)
    r0 = client.post(
        "/v1/webhooks/email-inbound",
        headers={"X-Dx-Email-Webhook-Secret": "ob140a"},
        json={"rfc822": _minimal_rfc822("<ob140a@dx.local>")},
    )
    tid = r0.json()["ticket_id"]

    r1 = client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": "Quase pronto", "tipo": "publico", "notificar_cliente_por_email": True},
    )
    assert r1.status_code == 201
    j = r1.json()
    assert j["status"] == EMAIL_STATUS_PENDENTE
    assert j["scheduled_at"]
    assert j["cliente_notificado_por_email"] is False


def test_editar_cancelar_e_reagendar(client, seed_base, auth_headers, monkeypatch):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "ob140b")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)
    _mock_resend(monkeypatch)
    r0 = client.post(
        "/v1/webhooks/email-inbound",
        headers={"X-Dx-Email-Webhook-Secret": "ob140b"},
        json={"rfc822": _minimal_rfc822("<ob140b@dx.local>")},
    )
    tid = r0.json()["ticket_id"]
    r1 = client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": "Texto errado", "tipo": "publico", "notificar_cliente_por_email": True},
    )
    mid = r1.json()["id"]

    r_edit = client.post(
        f"/v1/tickets/{tid}/mensagens/{mid}/start-edit",
        headers=auth_headers["admin"],
    )
    assert r_edit.status_code == 200
    token = r_edit.json()["edit_lock_token"]
    assert r_edit.json()["mensagem"]["status"] == EMAIL_STATUS_EM_EDICAO

    r_patch = client.patch(
        f"/v1/tickets/{tid}/mensagens/{mid}",
        headers=auth_headers["admin"],
        json={"corpo": "Texto corrigido", "edit_lock_token": token},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["status"] == EMAIL_STATUS_PENDENTE
    assert r_patch.json()["corpo"] == "Texto corrigido"

    r_cancel = client.post(
        f"/v1/tickets/{tid}/mensagens/{mid}/cancel",
        headers=auth_headers["admin"],
    )
    assert r_cancel.status_code == 200
    assert r_cancel.json()["status"] == EMAIL_STATUS_CANCELADA


def test_lock_expirado_libera_para_pendente(client, seed_base, auth_headers, monkeypatch, db_session):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "ob140c")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)
    _mock_resend(monkeypatch)
    r0 = client.post(
        "/v1/webhooks/email-inbound",
        headers={"X-Dx-Email-Webhook-Secret": "ob140c"},
        json={"rfc822": _minimal_rfc822("<ob140c@dx.local>")},
    )
    tid = r0.json()["ticket_id"]
    r1 = client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": "x", "tipo": "publico", "notificar_cliente_por_email": True},
    )
    mid = r1.json()["id"]
    r_edit = client.post(
        f"/v1/tickets/{tid}/mensagens/{mid}/start-edit",
        headers=auth_headers["admin"],
    )
    token = r_edit.json()["edit_lock_token"]
    m = db_session.query(TicketMensagem).filter(TicketMensagem.id == mid).first()
    assert m is not None
    m.edit_lock_expires_at = _dt_for_db() - timedelta(seconds=1)
    db_session.commit()
    liberar_locks_expirados(db_session)
    db_session.commit()
    db_session.refresh(m)
    assert m.email_status == EMAIL_STATUS_PENDENTE
    with pytest.raises(ValueError):
        validar_lock(m, token)


def test_unit_salvar_edicao_reinicia_janela(monkeypatch, db_session):
    monkeypatch.setattr("app.config.settings.TICKET_MENSAGEM_EMAIL_GRACE_SECONDS", 90)
    from app.models.email_settings import EmailSettings

    row = EmailSettings(ticket_mensagem_email_grace_seconds=90)
    db_session.add(row)
    db_session.flush()
    m = TicketMensagem(ticket_id=1, atendente_id=1, tipo="publico", corpo="a")
    agendar_envio_email(m, db_session)
    t0 = m.scheduled_at
    token = iniciar_edicao(m)
    validar_lock(m, token)
    salvar_edicao(m, db_session, corpo="b")
    assert m.corpo == "b"
    assert m.scheduled_at > t0


def test_cancelar_envio(db_session):
    m = TicketMensagem(ticket_id=1, atendente_id=1, tipo="publico", corpo="x")
    agendar_envio_email(m, db_session)
    cancelar_envio(m)
    assert m.email_status == EMAIL_STATUS_CANCELADA


def test_process_pending_com_scheduled_at_timezone_aware(
    client, seed_base, auth_headers, monkeypatch, db_session
):
    """Postgres devolve TIMESTAMPTZ como datetime aware; comparação naive não pode falhar."""
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "ob140tz")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)
    monkeypatch.setattr("app.config.settings.TICKET_MENSAGEM_EMAIL_GRACE_SECONDS", 0)
    _mock_resend(monkeypatch)
    monkeypatch.setattr(
        "app.services.ticket_client_email.enviar_mensagem_texto_sistema",
        lambda *a, **k: "outbound-tz-aware@dx.test",
    )

    r0 = client.post(
        "/v1/webhooks/email-inbound",
        headers={"X-Dx-Email-Webhook-Secret": "ob140tz"},
        json={"rfc822": _minimal_rfc822("<ob140tz@dx.local>")},
    )
    tid = r0.json()["ticket_id"]

    r1 = client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["admin"],
        json={"corpo": "Resposta", "tipo": "publico", "notificar_cliente_por_email": True},
    )
    mid = r1.json()["id"]
    m = db_session.query(TicketMensagem).filter(TicketMensagem.id == mid).first()
    assert m is not None
    # Simula TIMESTAMPTZ do Postgres (aware) na instância que o worker vai ler.
    m.scheduled_at = datetime.now(timezone.utc) - timedelta(seconds=30)

    n = process_pending_ticket_mensagem_emails(db_session, limit=10)
    assert n == 1
    db_session.commit()
    db_session.refresh(m)
    assert m.email_status == EMAIL_STATUS_ENVIADA
