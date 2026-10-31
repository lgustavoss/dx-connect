from __future__ import annotations

import json
from datetime import datetime, timezone

from app.models.dispositivo import Dispositivo, FcmOutbox
from app.models.whatsapp_chat import WhatsappChat
from app.services.fcm_outbox import STATUS_PENDENTE, enfileirar_para_atendentes, process_pending_fcm


def test_dispositivos_exige_jwt(client):
    r = client.get("/v1/dispositivos")
    assert r.status_code in (401, 403)


def test_registrar_listar_apagar_dispositivo(client, seed_base, auth_headers, db_session):
    payload = {"token": "fcm-token-a1-abcdefghijklmnopqrstuvwxyz", "plataforma": "android"}
    r = client.post("/v1/dispositivos", headers=auth_headers["a1"], json=payload)
    assert r.status_code == 201, r.text
    disp_id = r.json()["id"]
    assert r.json()["token"] == payload["token"]

    r = client.post("/v1/dispositivos", headers=auth_headers["a1"], json=payload)
    assert r.status_code == 201
    assert r.json()["id"] == disp_id

    r = client.get("/v1/dispositivos", headers=auth_headers["a1"])
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get("/v1/dispositivos", headers=auth_headers["a2"])
    assert r.status_code == 200
    assert r.json() == []

    r = client.delete(f"/v1/dispositivos/{disp_id}", headers=auth_headers["a2"])
    assert r.status_code == 403
    assert db_session.query(Dispositivo).count() == 1

    r = client.delete(f"/v1/dispositivos/{disp_id}", headers=auth_headers["a1"])
    assert r.status_code == 204
    assert db_session.query(Dispositivo).count() == 0


def test_nao_registra_token_de_outro_usuario(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    db_session.add(
        Dispositivo(
            atendente_id=a1.id,
            token="fcm-token-owned-by-a1-xxxxxx",
            plataforma="android",
        )
    )
    db_session.commit()
    r = client.post(
        "/v1/dispositivos",
        headers=auth_headers["a2"],
        json={"token": "fcm-token-owned-by-a1-xxxxxx", "plataforma": "android"},
    )
    assert r.status_code == 403
    assert db_session.query(Dispositivo).count() == 1


def test_nao_apaga_dispositivo_alheio_por_token(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    db_session.add(
        Dispositivo(
            atendente_id=a1.id,
            token="fcm-token-a1-only-yyyyyyyy",
            plataforma="android",
        )
    )
    db_session.commit()
    r = client.delete(
        "/v1/dispositivos",
        headers=auth_headers["a2"],
        params={"token": "fcm-token-a1-only-yyyyyyyy"},
    )
    assert r.status_code == 204
    assert db_session.query(Dispositivo).count() == 1


def test_enfileira_fcm_sem_vapid(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.web_push_outbox.vapid_configurado", lambda: False)
    a1 = seed_base["a1"]
    db_session.add(
        Dispositivo(
            atendente_id=a1.id,
            token="fcm-token-fila-zzzzzzzzzzzz",
            plataforma="android",
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
        chat_id=99,
    )
    rows = db_session.query(FcmOutbox).all()
    assert len(rows) == 1
    assert rows[0].atendente_id == a1.id
    assert rows[0].status == STATUS_PENDENTE
    payload = json.loads(rows[0].payload_json)
    assert payload["chat_id"] == 99
    assert payload["deep_link"] == "/conversa/99"


def test_emit_chat_fila_enfileira_fcm(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.web_push_outbox.vapid_configurado", lambda: False)
    a1 = seed_base["a1"]
    db_session.add(
        Dispositivo(
            atendente_id=a1.id,
            token="fcm-token-emit-fila-aaaaaa",
            plataforma="android",
        )
    )
    chat = WhatsappChat(
        protocolo="WCH-FCM-1",
        wa_id="5511999990011",
        cliente_nome="Cliente FCM",
        estado="aguardando_atendente",
        setor_id=seed_base["setor1"].id,
    )
    db_session.add(chat)
    db_session.commit()

    from app.services.realtime_emit import emit_chat_fila

    emit_chat_fila(db_session, chat)
    db_session.expire_all()
    rows = db_session.query(FcmOutbox).filter(FcmOutbox.atendente_id == a1.id).all()
    assert len(rows) == 1
    payload = json.loads(rows[0].payload_json)
    assert payload["tipo"] == "chat.fila"
    assert payload["chat_id"] == chat.id
    assert payload["deep_link"] == f"/conversa/{chat.id}"


def test_nao_enfileira_fcm_portal(seed_base, db_session):
    a1 = seed_base["a1"]
    db_session.add(
        Dispositivo(
            atendente_id=a1.id,
            token="fcm-token-portal-cccccccccc",
            plataforma="android",
        )
    )
    db_session.commit()
    enfileirar_para_atendentes(
        atendente_ids={a1.id},
        event_type="portal.chat.fila",
        entity_id=12,
        titulo="Cliente na fila do portal",
        url_path="/chat/espera",
        corpo="Novo atendimento no portal",
        chat_id=12,
    )
    assert db_session.query(FcmOutbox).count() == 0


def test_worker_fcm_envia_e_respeita_410(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    disp = Dispositivo(
        atendente_id=a1.id,
        token="fcm-token-gone-bbbbbbbbbb",
        plataforma="android",
    )
    db_session.add(disp)
    db_session.commit()
    db_session.add(
        FcmOutbox(
            atendente_id=a1.id,
            event_type="ticket.fila",
            dedup_key="fcm:ticket.fila:1:x",
            payload_json='{"tipo":"ticket.fila","id":1,"titulo":"Fila","url_path":"/tickets","ticket_id":1,"deep_link":"/ticket/1"}',
            status=STATUS_PENDENTE,
            scheduled_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    monkeypatch.setattr("app.services.fcm_outbox.enviar_para_token", lambda token, payload: (410, "Gone"))
    process_pending_fcm(db_session, limit=10)
    db_session.commit()
    assert db_session.query(Dispositivo).count() == 0
