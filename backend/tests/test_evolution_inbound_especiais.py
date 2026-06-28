from __future__ import annotations

from app.services.evolution_inbound import iter_inbound_whatsapp_messages


def _one(body: dict) -> dict:
    return next(iter_inbound_whatsapp_messages(body))


def test_inbound_contacto():
    body = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "c1"},
            "message": {
                "contactMessage": {
                    "displayName": "Maria Silva",
                    "vcard": "BEGIN:VCARD\nVERSION:3.0\nFN:Maria Silva\nTEL;type=CELL:+5511987654321\nEND:VCARD",
                }
            },
        },
    }
    item = _one(body)
    assert item["tipo"] == "texto"
    assert "Maria Silva" in item["corpo"]
    assert "5511987654321" in item["corpo"]


def test_inbound_localizacao():
    body = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511888777666@s.whatsapp.net", "fromMe": False, "id": "loc1"},
            "message": {
                "locationMessage": {
                    "name": "Escritório",
                    "degreesLatitude": -23.5505,
                    "degreesLongitude": -46.6333,
                }
            },
        },
    }
    item = _one(body)
    assert item["tipo"] == "texto"
    assert "[Localização]" in item["corpo"]
    assert "maps.google.com" in item["corpo"]
