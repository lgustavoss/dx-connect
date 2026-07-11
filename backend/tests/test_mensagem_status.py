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
    assert ack_evolution_para_status(1) == STATUS_ENVIADA
    assert ack_evolution_para_status(2) == STATUS_ENTREGUE
    assert ack_evolution_para_status(3) == STATUS_LIDA
    assert ack_evolution_para_status(4) == STATUS_LIDA
    assert ack_evolution_para_status("READ") == STATUS_LIDA
    assert ack_evolution_para_status("DELIVERY_ACK") == STATUS_ENTREGUE


def test_status_deve_atualizar_somente_para_frente():
    assert status_deve_atualizar(STATUS_ENVIADA, STATUS_ENTREGUE)
    assert not status_deve_atualizar(STATUS_LIDA, STATUS_ENTREGUE)
    assert status_deve_atualizar(None, STATUS_ENVIADA)


def test_status_inicial_outbound_whatsapp():
    assert status_inicial_outbound_whatsapp(wa_message_id="abc") == STATUS_ENVIADA
    assert status_inicial_outbound_whatsapp(wa_message_id=None) == "pendente"


def test_iter_message_status_updates():
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
    assert rows[0]["status_entrega"] == STATUS_LIDA
