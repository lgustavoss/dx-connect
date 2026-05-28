"""
Teste de integração com tempo real (#140): janela de graça, edição e reagendamento.

Requer grace curto via monkeypatch (8s). Demora ~20–25s no total.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from app.models.ticket import TicketMensagem
from app.services.ticket_mensagem_email_outbox import (
    EMAIL_STATUS_ENVIADA,
    EMAIL_STATUS_PENDENTE,
    _as_utc,
    process_pending_ticket_mensagem_emails,
)
from app.services.system_email_config import TransactionalEmailConfig


def _rfc822(mid: str = "<grace-timing@dx.local>") -> str:
    return (
        f"From: Cliente <cliente@example.com>\r\n"
        f"To: suporte@dxconnect.local\r\n"
        f"Subject: Grace timing\r\n"
        f"Message-ID: {mid}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"Corpo.\r\n"
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
    monkeypatch.setattr(
        "app.services.ticket_client_email.enviar_mensagem_texto_sistema",
        lambda *a, **k: "outbound-grace-timing@dx.test",
    )


def test_janela_edicao_reinicia_contagem_e_envia_depois(client, seed_base, auth_headers, monkeypatch, db_session):
    """
    1) Agenda envio em +8s
    2) Após 3s ainda pendente (dá tempo de editar)
    3) Editar reinicia scheduled_at (~+8s a partir da edição)
    4) Só envia após o novo scheduled_at
    """
    grace = 8
    monkeypatch.setattr("app.config.settings.TICKET_MENSAGEM_EMAIL_GRACE_SECONDS", grace)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "gracet")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)
    _mock_resend(monkeypatch)

    r0 = client.post(
        "/v1/webhooks/email-inbound",
        headers={"X-Dx-Email-Webhook-Secret": "gracet"},
        json={"rfc822": _rfc822()},
    )
    assert r0.status_code == 200
    tid = r0.json()["ticket_id"]

    t0 = time.perf_counter()
    r1 = client.post(
        f"/v1/tickets/{tid}/mensagens",
        headers=auth_headers["admin"],
        json={
            "corpo": "Versão 1 — texto errado",
            "tipo": "publico",
            "notificar_cliente_por_email": True,
        },
    )
    assert r1.status_code == 201, r1.text
    mid = r1.json()["id"]
    sched1 = _as_utc(datetime.fromisoformat(r1.json()["scheduled_at"].replace("Z", "+00:00")))
    assert r1.json()["status"] == EMAIL_STATUS_PENDENTE

    time.sleep(3)
    process_pending_ticket_mensagem_emails(db_session, limit=10)
    db_session.commit()
    m = db_session.query(TicketMensagem).filter(TicketMensagem.id == mid).first()
    assert m is not None
    assert m.email_status == EMAIL_STATUS_PENDENTE, "Aos 3s ainda deve dar tempo de editar (não enviou)"

    r_edit = client.post(
        f"/v1/tickets/{tid}/mensagens/{mid}/start-edit",
        headers=auth_headers["admin"],
    )
    assert r_edit.status_code == 200
    token = r_edit.json()["edit_lock_token"]
    t_antes_patch = time.perf_counter()
    r_patch = client.patch(
        f"/v1/tickets/{tid}/mensagens/{mid}",
        headers=auth_headers["admin"],
        json={"corpo": "Versão 2 — texto corrigido", "edit_lock_token": token},
    )
    assert r_patch.status_code == 200
    db_session.expire_all()
    m = db_session.query(TicketMensagem).filter(TicketMensagem.id == mid).first()
    assert m is not None and m.scheduled_at is not None
    sched2 = _as_utc(m.scheduled_at)
    assert sched2 and sched1 and sched2 > sched1, "Edição deve reagendar para depois do horário original"
    seg_ate_envio = (sched2 - datetime.now(timezone.utc)).total_seconds()
    assert seg_ate_envio >= grace - 2, "Novo envio ~grace segundos após salvar edição"

    # Antes do novo prazo: ainda pendente
    wait_until = seg_ate_envio - 1.5
    if wait_until > 0:
        time.sleep(wait_until)
    process_pending_ticket_mensagem_emails(db_session, limit=10)
    db_session.commit()
    db_session.refresh(m)
    assert m.email_status == EMAIL_STATUS_PENDENTE, "Ainda não deve enviar antes do scheduled_at reagendado"

    # Após o prazo reagendado: envia
    restante = (sched2 - datetime.now(timezone.utc)).total_seconds() + 0.5
    if restante > 0:
        time.sleep(restante)
    n = process_pending_ticket_mensagem_emails(db_session, limit=10)
    db_session.commit()
    db_session.refresh(m)
    assert n >= 1
    assert m.email_status == EMAIL_STATUS_ENVIADA
    assert m.corpo == "Versão 2 — texto corrigido"
    assert m.sent_at is not None

    elapsed = time.perf_counter() - t0
    elapsed_edit = time.perf_counter() - t_antes_patch
    print(
        f"\n[grace-timing] total={elapsed:.1f}s | "
        f"editou aos ~{t_antes_patch - t0:.1f}s | "
        f"enviou após reagendamento (grace={grace}s)\n"
    )
    assert elapsed >= grace + 3, "Tempo total cobre grace inicial + reagendamento após edição"
