from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.models.atendente_notificacao import AtendenteNotificacaoPreferencias
from app.models.dispositivo import Dispositivo, FcmOutbox
from app.models.whatsapp_chat import WhatsappChat
from app.services.fcm_outbox import (
    STATUS_ENVIADA,
    STATUS_PENDENTE,
    enfileirar_para_atendentes,
    process_fila_fcm_reminders,
    process_pending_fcm,
)


def _dispositivo(db, atendente_id: int, token: str) -> Dispositivo:
    row = Dispositivo(atendente_id=atendente_id, token=token, plataforma="android")
    db.add(row)
    db.commit()
    return row


def _prefs(db, atendente_id: int, *, push_habilitado: bool = True, push_fila: bool = True):
    row = AtendenteNotificacaoPreferencias(
        atendente_id=atendente_id,
        push_habilitado=push_habilitado,
        push_fila=push_fila,
    )
    db.add(row)
    db.commit()
    return row


def _outbox(db, atendente_id: int, *, event_type="ticket.fila", dedup="fcm:ticket.fila:1:x"):
    row = FcmOutbox(
        atendente_id=atendente_id,
        event_type=event_type,
        dedup_key=dedup,
        payload_json='{"tipo":"ticket.fila","id":1,"titulo":"Fila","url_path":"/tickets","ticket_id":1,"deep_link":"/ticket/1"}',
        status=STATUS_PENDENTE,
        scheduled_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    return row


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


def test_registro_de_dispositivo_liga_push(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    assert (
        db_session.query(AtendenteNotificacaoPreferencias)
        .filter(AtendenteNotificacaoPreferencias.atendente_id == a1.id)
        .first()
        is None
    )
    r = client.post(
        "/v1/dispositivos",
        headers=auth_headers["a1"],
        json={"token": "fcm-token-optin-aaaaaaaaaaaa", "plataforma": "android"},
    )
    assert r.status_code == 201, r.text
    prefs = (
        db_session.query(AtendenteNotificacaoPreferencias)
        .filter(AtendenteNotificacaoPreferencias.atendente_id == a1.id)
        .first()
    )
    assert prefs is not None and prefs.push_habilitado is True


def test_token_de_outro_usuario_passa_para_quem_logou(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-owned-by-a1-xxxxxx")
    r = client.post(
        "/v1/dispositivos",
        headers=auth_headers["a2"],
        json={"token": "fcm-token-owned-by-a1-xxxxxx", "plataforma": "android"},
    )
    assert r.status_code == 201, r.text
    db_session.expire_all()
    rows = db_session.query(Dispositivo).all()
    assert len(rows) == 1
    assert rows[0].atendente_id == seed_base["a2"].id


def test_nao_apaga_dispositivo_alheio(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    disp = _dispositivo(db_session, a1.id, "fcm-token-a1-only-yyyyyyyy")
    r = client.delete(f"/v1/dispositivos/{disp.id}", headers=auth_headers["a2"])
    assert r.status_code == 403
    assert db_session.query(Dispositivo).count() == 1


def test_nao_enfileira_sem_fcm_configurado(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: False)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-sem-config-aaaaaaaa")
    _prefs(db_session, a1.id)
    enfileirar_para_atendentes(
        atendente_ids={a1.id},
        event_type="chat.fila",
        entity_id=99,
        titulo="Cliente na fila WhatsApp",
        url_path="/chat/espera",
        chat_id=99,
    )
    assert db_session.query(FcmOutbox).count() == 0


def test_enfileira_fcm_para_atendente_com_prefs(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-fila-zzzzzzzzzzzz")
    _prefs(db_session, a1.id)

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


def test_nao_enfileira_com_push_desligado(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-push-off-aaaaaaaa")
    _prefs(db_session, a1.id, push_habilitado=False)
    enfileirar_para_atendentes(
        atendente_ids={a1.id},
        event_type="chat.fila",
        entity_id=99,
        titulo="Cliente na fila WhatsApp",
        url_path="/chat/espera",
        chat_id=99,
    )
    assert db_session.query(FcmOutbox).count() == 0


def test_push_fila_desligado_ainda_recebe_mensagem(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-fila-off-bbbbbbbb")
    _prefs(db_session, a1.id, push_fila=False)
    enfileirar_para_atendentes(
        atendente_ids={a1.id},
        event_type="chat.fila",
        entity_id=99,
        titulo="Cliente na fila WhatsApp",
        url_path="/chat/espera",
        chat_id=99,
    )
    assert db_session.query(FcmOutbox).count() == 0
    enfileirar_para_atendentes(
        atendente_ids={a1.id},
        event_type="chat.mensagem",
        entity_id=7,
        titulo="Nova mensagem",
        url_path="/conversa/7",
        chat_id=7,
    )
    assert db_session.query(FcmOutbox).count() == 1


def test_emit_chat_fila_enfileira_fcm(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-emit-fila-aaaaaa")
    _prefs(db_session, a1.id)
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


def test_nao_enfileira_fcm_portal(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-portal-cccccccccc")
    _prefs(db_session, a1.id)
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


def test_lembrete_de_fila_enfileira_e_deduplica(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-remind-dddddddd")
    _prefs(db_session, a1.id)
    chat = WhatsappChat(
        protocolo="WCH-FCM-REMIND",
        wa_id="5511999990022",
        cliente_nome="Cliente Remind",
        estado="aguardando_atendente",
        setor_id=seed_base["setor1"].id,
    )
    db_session.add(chat)
    db_session.commit()

    assert process_fila_fcm_reminders() == 1
    assert process_fila_fcm_reminders() == 0
    db_session.expire_all()
    rows = db_session.query(FcmOutbox).filter(FcmOutbox.atendente_id == a1.id).all()
    assert len(rows) == 1
    payload = json.loads(rows[0].payload_json)
    assert rows[0].event_type == "chat.fila.remind"
    assert payload["deep_link"] == "/chat"


def test_worker_fcm_envia_e_marca_enviada(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-ok-eeeeeeeeee")
    row = _outbox(db_session, a1.id)
    monkeypatch.setattr("app.services.fcm_outbox.enviar_para_token", lambda token, payload: (200, None))

    assert process_pending_fcm(db_session, limit=10) == 1
    db_session.expire_all()
    assert db_session.get(FcmOutbox, row.id).status == STATUS_ENVIADA
    assert db_session.get(FcmOutbox, row.id).sent_at is not None


def test_worker_fcm_respeita_410(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-gone-bbbbbbbbbb")
    row = _outbox(db_session, a1.id)
    monkeypatch.setattr("app.services.fcm_outbox.enviar_para_token", lambda token, payload: (410, "Gone"))

    process_pending_fcm(db_session, limit=10)
    db_session.expire_all()
    assert db_session.query(Dispositivo).count() == 0
    assert db_session.get(FcmOutbox, row.id).status == STATUS_ENVIADA


def test_worker_fcm_400_token_invalido_remove_dispositivo(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-invalid-ffffffff")
    row = _outbox(db_session, a1.id)
    monkeypatch.setattr(
        "app.services.fcm_outbox.enviar_para_token",
        lambda token, payload: (400, "INVALID_ARGUMENT: registration token is not valid"),
    )
    process_pending_fcm(db_session, limit=10)
    db_session.expire_all()
    assert db_session.query(Dispositivo).count() == 0
    assert db_session.get(FcmOutbox, row.id).status == STATUS_ENVIADA


def test_worker_fcm_403_sender_mismatch_remove_dispositivo(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-mismatch-gggggggg")
    row = _outbox(db_session, a1.id)
    monkeypatch.setattr(
        "app.services.fcm_outbox.enviar_para_token",
        lambda token, payload: (403, "SenderIdMismatch"),
    )
    process_pending_fcm(db_session, limit=10)
    db_session.expire_all()
    assert db_session.query(Dispositivo).count() == 0
    assert db_session.get(FcmOutbox, row.id).status == STATUS_ENVIADA


def test_worker_fcm_erro_transitorio_agenda_retry(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-retry-hhhhhhhh")
    row = _outbox(db_session, a1.id)
    monkeypatch.setattr("app.services.fcm_outbox.enviar_para_token", lambda token, payload: (503, "UNAVAILABLE"))

    assert process_pending_fcm(db_session, limit=10) == 0
    db_session.expire_all()
    atual = db_session.get(FcmOutbox, row.id)
    assert atual.status == STATUS_PENDENTE
    assert atual.tentativas == 1
    agendado = atual.scheduled_at
    if agendado.tzinfo is None:
        agendado = agendado.replace(tzinfo=timezone.utc)
    assert agendado > datetime.now(timezone.utc) + timedelta(seconds=1)
    assert db_session.query(Dispositivo).count() == 1


def test_worker_fcm_sem_dispositivo_marca_enviada(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    row = _outbox(db_session, a1.id)
    process_pending_fcm(db_session, limit=10)
    db_session.expire_all()
    atual = db_session.get(FcmOutbox, row.id)
    assert atual.status == STATUS_ENVIADA
    assert atual.last_error == "sem dispositivo"


def test_worker_fcm_nao_envia_sem_configuracao(seed_base, db_session, monkeypatch):
    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: False)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-off-iiiiiiii")
    row = _outbox(db_session, a1.id)
    assert process_pending_fcm(db_session, limit=10) == 0
    db_session.expire_all()
    atual = db_session.get(FcmOutbox, row.id)
    assert atual.status == STATUS_PENDENTE
    assert atual.tentativas == 0


def test_worker_fcm_falha_permanente_apos_max_tentativas(seed_base, db_session, monkeypatch):
    from app.services.email_outbox_policy import MAX_EMAIL_SEND_ATTEMPTS

    monkeypatch.setattr("app.services.fcm_outbox.fcm_configurado", lambda: True)
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-fail-jjjjjjjj")
    row = _outbox(db_session, a1.id)
    row.tentativas = MAX_EMAIL_SEND_ATTEMPTS - 1
    db_session.commit()
    monkeypatch.setattr("app.services.fcm_outbox.enviar_para_token", lambda token, payload: (503, "UNAVAILABLE"))

    assert process_pending_fcm(db_session, limit=10) == 0
    db_session.expire_all()
    atual = db_session.get(FcmOutbox, row.id)
    assert atual.status == "falha"
    assert atual.tentativas == MAX_EMAIL_SEND_ATTEMPTS


def test_excluir_atendente_remove_dispositivo_e_outbox(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    _dispositivo(db_session, a1.id, "fcm-token-del-zzzzzzzzzz")
    _outbox(db_session, a1.id, event_type="chat.mensagem", dedup="fcm:chat.mensagem:9:del")

    r = client.delete(f"/v1/atendentes/{a1.id}", headers=auth_headers["admin"])
    assert r.status_code == 204, r.text
    db_session.expire_all()
    assert db_session.query(Dispositivo).count() == 0
    assert db_session.query(FcmOutbox).count() == 0
