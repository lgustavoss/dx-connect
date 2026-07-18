from app.services.evolution_inbound import iter_message_status_updates
from app.services.mensagem_status import (
    STATUS_ENTREGUE,
    STATUS_ENVIADA,
    STATUS_LIDA,
    ack_evolution_para_status,
    status_deve_atualizar,
    status_inicial_outbound_whatsapp,
)


def test_ack_evolution_para_status():
    # Baileys WAMessageStatus: 1 PENDING, 2 SERVER_ACK, 3 DELIVERY_ACK, 4 READ
    assert ack_evolution_para_status(1) == STATUS_ENVIADA
    assert ack_evolution_para_status(2) == STATUS_ENVIADA
    assert ack_evolution_para_status(3) == STATUS_ENTREGUE
    assert ack_evolution_para_status(4) == STATUS_LIDA
    assert ack_evolution_para_status(5) == STATUS_LIDA
    assert ack_evolution_para_status("READ") == STATUS_LIDA
    assert ack_evolution_para_status("DELIVERY_ACK") == STATUS_ENTREGUE
    assert ack_evolution_para_status("SERVER_ACK") == STATUS_ENVIADA


def test_status_deve_atualizar_somente_para_frente():
    assert status_deve_atualizar(STATUS_ENVIADA, STATUS_ENTREGUE)
    assert not status_deve_atualizar(STATUS_LIDA, STATUS_ENTREGUE)
    assert status_deve_atualizar(None, STATUS_ENVIADA)


def test_status_inicial_outbound_whatsapp():
    assert status_inicial_outbound_whatsapp(wa_message_id="abc") == STATUS_ENVIADA
    assert status_inicial_outbound_whatsapp(wa_message_id=None) == "pendente"


def test_iter_message_status_updates_nested():
    body = {
        "event": "messages.update",
        "data": {
            "key": {"id": "MSG123", "fromMe": True},
            "update": {"status": 3},
        },
    }
    rows = list(iter_message_status_updates(body))
    assert len(rows) == 1
    assert rows[0]["wa_message_id"] == "MSG123"
    assert rows[0]["status_entrega"] == STATUS_ENTREGUE


def test_iter_message_status_updates_evolution_flat():
    """Payload real Evolution MESSAGES_UPDATE (keyId + status string)."""
    body = {
        "event": "messages.update",
        "data": {
            "keyId": "3EB0C7B4E7A2B8E6D4F1",
            "remoteJid": "5511999999999@s.whatsapp.net",
            "fromMe": True,
            "status": "DELIVERY_ACK",
        },
    }
    rows = list(iter_message_status_updates(body))
    assert len(rows) == 1
    assert rows[0]["wa_message_id"] == "3EB0C7B4E7A2B8E6D4F1"
    assert rows[0]["status_entrega"] == STATUS_ENTREGUE


def test_iter_message_status_updates_evolution_flat_read():
    body = {
        "event": "MESSAGES_UPDATE",
        "data": {
            "keyId": "ABC123",
            "fromMe": True,
            "status": "READ",
        },
    }
    rows = list(iter_message_status_updates(body))
    assert len(rows) == 1
    assert rows[0]["status_entrega"] == STATUS_LIDA


def test_iter_message_status_updates_lista_flat():
    body = {
        "event": "messages.update",
        "data": [
            {"keyId": "A1", "fromMe": True, "status": "SERVER_ACK"},
            {"keyId": "A2", "fromMe": True, "status": "DELIVERY_ACK"},
            {"keyId": "B1", "fromMe": False, "status": "READ"},
        ],
    }
    rows = list(iter_message_status_updates(body))
    assert [(r["wa_message_id"], r["status_entrega"]) for r in rows] == [
        ("A1", STATUS_ENVIADA),
        ("A2", STATUS_ENTREGUE),
    ]
