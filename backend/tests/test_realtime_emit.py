"""Testes emissão SSE — tickets e chats (#265)."""

from __future__ import annotations

from app.services.realtime_emit import (
    emit_chat_mensagem,
    ids_atendentes_acesso_chat,
    ids_atendentes_chat_fila,
    ids_atendentes_ticket_fila,
    ids_atendentes_ticket_mensagem,
)


def test_ids_atendentes_chat_fila_setor(client, seed_base, db_session):
    from app.models.whatsapp_chat import WhatsappChat

    chat = WhatsappChat(
        protocolo="WCH-TEST-1",
        wa_id="5511999990001",
        cliente_nome="Cliente",
        estado="aguardando_atendente",
        setor_id=seed_base["setor1"].id,
    )
    db_session.add(chat)
    db_session.commit()

    ids = ids_atendentes_chat_fila(db_session, chat)
    assert seed_base["a1"].id in ids
    assert seed_base["a2"].id not in ids
    assert seed_base["admin"].id in ids


def test_ids_atendentes_ticket_fila(client, seed_base, db_session):
    from app.models.ticket import Ticket
    from app.models.status_ticket import StatusTicket

    st = db_session.query(StatusTicket).first()
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-0001",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="Teste fila",
        descricao="x",
        atendente_id=None,
    )
    db_session.add(ticket)
    db_session.commit()

    ids = ids_atendentes_ticket_fila(db_session, ticket)
    assert seed_base["a1"].id in ids
    assert seed_base["a2"].id not in ids


def test_emit_chat_mensagem_rbac(client, seed_base, db_session, monkeypatch):
    from app.models.whatsapp_chat import WhatsappChat

    chat = WhatsappChat(
        protocolo="WCH-TEST-2",
        wa_id="5511999990002",
        cliente_nome="Cliente",
        estado="em_atendimento",
        setor_id=seed_base["setor1"].id,
        atendente_id=seed_base["a1"].id,
    )
    db_session.add(chat)
    db_session.commit()

    publicados: list[int] = []

    def fake_publish(atendente_ids, event_type, payload):
        if event_type == "chat.mensagem":
            publicados.extend(atendente_ids)
            assert payload["chat_id"] == chat.id

    monkeypatch.setattr("app.services.realtime_emit._publish_to_atendentes", fake_publish)

    emit_chat_mensagem(
        db_session,
        chat,
        {"id": 1, "chat_id": chat.id, "corpo": "oi"},
    )
    assert seed_base["a1"].id in publicados
    assert seed_base["admin"].id in publicados
    assert seed_base["a2"].id not in publicados

def test_ids_atendentes_acesso_chat_em_atendimento(client, seed_base, db_session):
    from app.models.whatsapp_chat import WhatsappChat

    chat = WhatsappChat(
        protocolo="WCH-TEST-3",
        wa_id="5511999990003",
        cliente_nome="Cliente",
        estado="em_atendimento",
        setor_id=seed_base["setor2"].id,
        atendente_id=seed_base["a2"].id,
    )
    db_session.add(chat)
    db_session.commit()

    ids = ids_atendentes_acesso_chat(db_session, chat)
    assert seed_base["a2"].id in ids
    assert seed_base["admin"].id in ids
    assert seed_base["a1"].id not in ids


def test_ids_atendentes_ticket_mensagem_por_setor(client, seed_base, db_session):
    from app.models.ticket import Ticket
    from app.models.status_ticket import StatusTicket

    st = db_session.query(StatusTicket).first()
    ticket = Ticket(
        tenant_id=1,
        protocolo="#T202606-0002",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=st.id,
        assunto="Msg",
        descricao="x",
        atendente_id=seed_base["a1"].id,
    )
    db_session.add(ticket)
    db_session.commit()

    ids = ids_atendentes_ticket_mensagem(db_session, ticket)
    assert seed_base["a1"].id in ids
    assert seed_base["admin"].id in ids
    assert seed_base["a2"].id not in ids


def test_emit_crm_lembrete_so_para_o_autor(monkeypatch):
    from app.services.realtime_emit import emit_crm_lembrete

    eventos: list[tuple[list[int], str, dict]] = []

    def fake_publish(atendente_ids, event_type, payload):
        eventos.append((list(atendente_ids), event_type, payload))

    monkeypatch.setattr("app.services.realtime_emit._publish_to_atendentes", fake_publish)
    emit_crm_lembrete(
        {
            "autor_id": 7,
            "atividade_id": 3,
            "negociacao_id": 9,
            "texto": "Reunião",
            "lead_nome": "Posto Alpha",
            "lembrete_em": "2026-09-28T15:00:00+00:00",
        }
    )
    assert len(eventos) == 1
    ids, tipo, payload = eventos[0]
    assert ids == [7]
    assert tipo == "crm.lembrete"
    assert payload["negociacao_id"] == 9
    assert payload["lead_nome"] == "Posto Alpha"
