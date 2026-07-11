"""Testes SSE do chat interno (IC-03)."""

from __future__ import annotations

from app.services import chat_interno as chat_svc
from app.services.realtime_emit import (
    emit_chat_interno_mensagem,
    ids_destinatarios_chat_interno_mensagem,
)


def test_ids_destinatarios_direta_exclui_remetente(db_session, seed_base):
    a1 = seed_base["a1"]
    admin = seed_base["admin"]
    conversa = chat_svc.obter_ou_criar_conversa_direta(db_session, 1, a1.id, admin.id)
    db_session.commit()

    ids = ids_destinatarios_chat_interno_mensagem(
        db_session,
        conversa,
        exclude_atendente_id=a1.id,
    )
    assert admin.id in ids
    assert a1.id not in ids
    assert seed_base["a2"].id not in ids


def test_ids_destinatarios_canal_setor_notifica_membros(db_session, seed_base):
    conversa = chat_svc.obter_ou_criar_canal_setor(db_session, 1, seed_base["setor1"].id)
    db_session.commit()

    ids = ids_destinatarios_chat_interno_mensagem(
        db_session,
        conversa,
        exclude_atendente_id=seed_base["a1"].id,
    )
    assert seed_base["admin"].id in ids
    assert seed_base["a2"].id not in ids
    assert seed_base["a1"].id not in ids


def test_emit_chat_interno_mensagem_direta(client, seed_base, db_session, monkeypatch):
    a1 = seed_base["a1"]
    admin = seed_base["admin"]
    conversa = chat_svc.obter_ou_criar_conversa_direta(db_session, 1, a1.id, admin.id)
    mensagem = chat_svc.enviar_mensagem(db_session, conversa, a1, "Olá admin")
    db_session.commit()

    eventos: list[tuple[str, dict]] = []
    contagem_calls: list[int] = []

    def fake_publish(atendente_ids, event_type, payload):
        for aid in atendente_ids:
            eventos.append((event_type, payload))
            assert aid == admin.id

    def fake_contagem_all(db):
        contagem_calls.append(1)

    monkeypatch.setattr("app.services.realtime_emit._publish_to_atendentes", fake_publish)
    monkeypatch.setattr(
        "app.services.realtime_emit._emit_notificacao_after_counter_change",
        fake_contagem_all,
    )

    emit_chat_interno_mensagem(db_session, conversa, mensagem, exclude_atendente_id=a1.id)

    assert len(eventos) == 1
    etype, payload = eventos[0]
    assert etype == "chat.interno.mensagem"
    assert payload["conversa_id"] == conversa.id
    assert payload["tipo"] == "direta"
    assert payload["remetente_id"] == a1.id
    assert "Olá admin" in payload["corpo_preview"]
    assert contagem_calls == [1]


def test_emit_chat_interno_canal_setor_notifica_todos_membros(client, seed_base, db_session, monkeypatch):
    conversa = chat_svc.obter_ou_criar_canal_setor(db_session, 1, seed_base["setor1"].id)
    mensagem = chat_svc.enviar_mensagem(db_session, conversa, seed_base["a1"], "Comunicado")
    db_session.commit()

    destinatarios: set[int] = set()

    def fake_publish(atendente_ids, event_type, payload):
        if event_type == "chat.interno.mensagem":
            destinatarios.update(atendente_ids)
            assert payload["tipo"] == "setor"
            assert payload["setor_id"] == seed_base["setor1"].id

    monkeypatch.setattr("app.services.realtime_emit._publish_to_atendentes", fake_publish)
    monkeypatch.setattr("app.services.realtime_emit._emit_notificacao_after_counter_change", lambda db: None)

    emit_chat_interno_mensagem(
        db_session,
        conversa,
        mensagem,
        exclude_atendente_id=seed_base["a1"].id,
    )

    assert seed_base["admin"].id in destinatarios
    assert seed_base["a1"].id not in destinatarios
    assert seed_base["a2"].id not in destinatarios


def test_emit_chat_interno_mensagem_atualizada(client, seed_base, db_session, monkeypatch):
    conversa = chat_svc.obter_ou_criar_conversa_direta(db_session, 1, seed_base["a1"].id, seed_base["admin"].id)
    mensagem = chat_svc.enviar_mensagem(db_session, conversa, seed_base["a1"], "Editar isto")
    db_session.commit()

    eventos: list[tuple[str, dict]] = []

    def fake_publish(atendente_ids, event_type, payload):
        for _aid in atendente_ids:
            eventos.append((event_type, payload))

    monkeypatch.setattr("app.services.realtime_emit._publish_to_atendentes", fake_publish)
    monkeypatch.setattr("app.services.realtime_emit._emit_notificacao_after_counter_change", lambda db: None)

    from app.services.realtime_emit import emit_chat_interno_mensagem_atualizada

    chat_svc.editar_mensagem(db_session, conversa, mensagem, seed_base["a1"], "Corrigido")
    db_session.commit()
    emit_chat_interno_mensagem_atualizada(db_session, conversa, mensagem, acao="editada")

    assert len(eventos) >= 1
    etype, payload = eventos[0]
    assert etype == "chat.interno.mensagem.atualizada"
    assert payload["conversa_id"] == conversa.id
    assert payload["mensagem_id"] == mensagem.id
    assert payload["acao"] == "editada"
