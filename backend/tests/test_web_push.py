from __future__ import annotations

from datetime import datetime, timezone

from app.models.web_push import PushOutbox, PushSubscription
from app.services.notificacao_atendente_email import obter_ou_criar_preferencias
from app.services.web_push_outbox import STATUS_PENDENTE, enfileirar_para_atendentes, process_pending_web_push


def test_vapid_desligado_sem_chaves(client, auth_headers):
    r = client.get("/v1/web-push/vapid", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    assert body["configurado"] is False
    assert body["public_key"] is None


def test_vapid_exige_jwt(client):
    r = client.get("/v1/web-push/vapid")
    assert r.status_code in (401, 403)


def test_registrar_listar_apagar_subscription(client, seed_base, auth_headers, db_session, monkeypatch):
    monkeypatch.setattr("app.config.settings.WEB_PUSH_VAPID_PUBLIC_KEY", "BNpublic")
    monkeypatch.setattr("app.config.settings.WEB_PUSH_VAPID_PRIVATE_KEY", "priv")

    r = client.get("/v1/web-push/vapid", headers=auth_headers["a1"])
    assert r.status_code == 200
    assert r.json()["configurado"] is True
    assert r.json()["public_key"] == "BNpublic"

    payload = {
        "endpoint": "https://push.example.com/a1",
        "p256dh": "p256dh-key-value",
        "auth": "auth-key-value",
        "user_agent": "TestAgent",
    }
    r = client.post("/v1/web-push/subscriptions", headers=auth_headers["a1"], json=payload)
    assert r.status_code == 201, r.text
    sub_id = r.json()["id"]

    r = client.get("/v1/web-push/subscriptions", headers=auth_headers["a1"])
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["endpoint"] == payload["endpoint"]

    r = client.get("/v1/web-push/subscriptions", headers=auth_headers["a2"])
    assert r.status_code == 200
    assert r.json() == []

    r = client.delete(f"/v1/web-push/subscriptions/{sub_id}", headers=auth_headers["a2"])
    assert r.status_code == 403

    r = client.delete(f"/v1/web-push/subscriptions/{sub_id}", headers=auth_headers["a1"])
    assert r.status_code == 204
    assert db_session.query(PushSubscription).count() == 0


def test_registra_subscription_formato_unifiedpush(client, auth_headers, monkeypatch):
    """APK Android (#737): endpoint Web Push + chaves base64url, sem Firebase."""
    monkeypatch.setattr("app.config.settings.WEB_PUSH_VAPID_PUBLIC_KEY", "BNpublic")
    monkeypatch.setattr("app.config.settings.WEB_PUSH_VAPID_PRIVATE_KEY", "priv")
    payload = {
        "endpoint": "https://fcm.googleapis.com/wp/eid-abc",
        "p256dh": "BNabcdefghijklmnopqrstuvwxyz0123456789-_xx",
        "auth": "dGVzdGF1dGg",
        "user_agent": "DeskRudder-Android-UnifiedPush",
    }
    r = client.post("/v1/web-push/subscriptions", headers=auth_headers["a1"], json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["endpoint"] == payload["endpoint"]
    r = client.post("/v1/web-push/subscriptions", headers=auth_headers["a1"], json=payload)
    assert r.status_code == 201
    assert r.json()["id"] == body["id"]


def test_nao_registra_endpoint_de_outro_utilizador(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    db_session.add(
        PushSubscription(
            atendente_id=a1.id,
            endpoint="https://push.example.com/owned-by-a1",
            p256dh="p256dh-key-value",
            auth="auth-key-value",
        )
    )
    db_session.commit()
    r = client.post(
        "/v1/web-push/subscriptions",
        headers=auth_headers["a2"],
        json={
            "endpoint": "https://push.example.com/owned-by-a1",
            "p256dh": "p256dh-key-value",
            "auth": "auth-key-value",
        },
    )
    assert r.status_code == 403
    assert db_session.query(PushSubscription).count() == 1


def test_nao_apaga_subscription_alheia_por_endpoint(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    db_session.add(
        PushSubscription(
            atendente_id=a1.id,
            endpoint="https://push.example.com/a1-only",
            p256dh="p256dh-key-value",
            auth="auth-key-value",
        )
    )
    db_session.commit()
    r = client.delete(
        "/v1/web-push/subscriptions",
        headers=auth_headers["a2"],
        params={"endpoint": "https://push.example.com/a1-only"},
    )
    assert r.status_code == 204
    assert db_session.query(PushSubscription).count() == 1


def test_enfileira_so_com_pref_e_subscription(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.web_push_outbox.vapid_configurado", lambda: True)
    a1 = seed_base["a1"]
    prefs = obter_ou_criar_preferencias(db_session, a1.id)
    prefs.push_habilitado = True
    prefs.push_fila = True
    db_session.add(
        PushSubscription(
            atendente_id=a1.id,
            endpoint="https://push.example.com/fila",
            p256dh="p256dh-key-value",
            auth="auth-key-value",
        )
    )
    db_session.commit()

    enfileirar_para_atendentes(
        atendente_ids={a1.id, seed_base["a2"].id},
        event_type="chat.fila",
        entity_id=99,
        titulo="Cliente na fila WhatsApp",
        url_path="/chat/espera",
        corpo="João",
    )
    rows = db_session.query(PushOutbox).all()
    assert len(rows) == 1
    assert rows[0].atendente_id == a1.id
    assert rows[0].status == STATUS_PENDENTE


def test_nao_enfileira_fila_quando_mute(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.web_push_outbox.vapid_configurado", lambda: True)
    a1 = seed_base["a1"]
    prefs = obter_ou_criar_preferencias(db_session, a1.id)
    prefs.push_habilitado = True
    prefs.push_fila = False
    db_session.add(
        PushSubscription(
            atendente_id=a1.id,
            endpoint="https://push.example.com/mute",
            p256dh="p256dh-key-value",
            auth="auth-key-value",
        )
    )
    db_session.commit()
    enfileirar_para_atendentes(
        atendente_ids={a1.id},
        event_type="chat.fila",
        entity_id=7,
        titulo="Cliente na fila WhatsApp",
        url_path="/chat/espera",
    )
    assert db_session.query(PushOutbox).count() == 0


def test_worker_envia_e_respeita_410(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.config.settings.WEB_PUSH_VAPID_PUBLIC_KEY", "pub")
    monkeypatch.setattr("app.config.settings.WEB_PUSH_VAPID_PRIVATE_KEY", "priv")
    monkeypatch.setattr("app.services.web_push_outbox.vapid_configurado", lambda: True)
    a1 = seed_base["a1"]
    prefs = obter_ou_criar_preferencias(db_session, a1.id)
    prefs.push_habilitado = True
    sub = PushSubscription(
        atendente_id=a1.id,
        endpoint="https://push.example.com/gone",
        p256dh="p256dh-key-value",
        auth="auth-key-value",
    )
    db_session.add(sub)
    db_session.commit()
    db_session.add(
        PushOutbox(
            atendente_id=a1.id,
            event_type="ticket.fila",
            dedup_key="ticket.fila:1:x",
            payload_json='{"tipo":"ticket.fila","id":1,"titulo":"Fila","url_path":"/tickets"}',
            status=STATUS_PENDENTE,
            scheduled_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    def fake_enviar(sub_row, payload):
        return 410, "Gone"

    monkeypatch.setattr("app.services.web_push_outbox._enviar_uma", fake_enviar)
    process_pending_web_push(db_session, limit=10)
    db_session.commit()
    assert db_session.query(PushSubscription).count() == 0


def test_fila_remind_enfileira_com_chat_aguardando(seed_base, db_session, monkeypatch):
    from app.models.whatsapp_chat import WhatsappChat
    from app.services.web_push_outbox import EVENTO_FILA_REMIND, process_fila_web_push_reminders

    monkeypatch.setattr("app.services.web_push_outbox.vapid_configurado", lambda: True)
    monkeypatch.setattr("app.config.settings.WEB_PUSH_FILA_REMIND_MINUTES", 2)
    a1 = seed_base["a1"]
    prefs = obter_ou_criar_preferencias(db_session, a1.id)
    prefs.push_habilitado = True
    prefs.push_fila = True
    db_session.add(
        PushSubscription(
            atendente_id=a1.id,
            endpoint="https://push.example.com/remind",
            p256dh="p256dh-key-value",
            auth="auth-key-value",
        )
    )
    db_session.add(
        WhatsappChat(
            protocolo="WCH-REMIND-1",
            wa_id="5511999990099",
            cliente_nome="Cliente Reminder",
            estado="aguardando_atendente",
            setor_id=seed_base["setor1"].id,
        )
    )
    db_session.commit()

    n = process_fila_web_push_reminders()
    assert n >= 1
    db_session.expire_all()
    rows = (
        db_session.query(PushOutbox)
        .filter(PushOutbox.event_type == EVENTO_FILA_REMIND, PushOutbox.atendente_id == a1.id)
        .all()
    )
    assert len(rows) == 1
    assert "aguardando" in (rows[0].payload_json or "")

    # Dedup na mesma janela
    assert process_fila_web_push_reminders() == 0
    assert (
        db_session.query(PushOutbox)
        .filter(PushOutbox.event_type == EVENTO_FILA_REMIND, PushOutbox.atendente_id == a1.id)
        .count()
        == 1
    )


def test_fila_remind_respeita_mute_e_fila_vazia(seed_base, db_session, monkeypatch):
    from app.models.whatsapp_chat import WhatsappChat
    from app.services.web_push_outbox import EVENTO_FILA_REMIND, process_fila_web_push_reminders

    monkeypatch.setattr("app.services.web_push_outbox.vapid_configurado", lambda: True)
    monkeypatch.setattr("app.config.settings.WEB_PUSH_FILA_REMIND_MINUTES", 2)
    a1 = seed_base["a1"]
    prefs = obter_ou_criar_preferencias(db_session, a1.id)
    prefs.push_habilitado = True
    prefs.push_fila = False
    db_session.add(
        PushSubscription(
            atendente_id=a1.id,
            endpoint="https://push.example.com/remind-mute",
            p256dh="p256dh-key-value",
            auth="auth-key-value",
        )
    )
    db_session.add(
        WhatsappChat(
            protocolo="WCH-REMIND-MUTE",
            wa_id="5511999990088",
            cliente_nome="Mute",
            estado="aguardando_atendente",
            setor_id=seed_base["setor1"].id,
        )
    )
    db_session.commit()
    assert process_fila_web_push_reminders() == 0
    assert db_session.query(PushOutbox).filter(PushOutbox.event_type == EVENTO_FILA_REMIND).count() == 0

    prefs.push_fila = True
    db_session.commit()
    # Sem chats aguardando após limpar estado
    chat = db_session.query(WhatsappChat).filter(WhatsappChat.protocolo == "WCH-REMIND-MUTE").one()
    chat.estado = "em_atendimento"
    db_session.commit()
    assert process_fila_web_push_reminders() == 0
