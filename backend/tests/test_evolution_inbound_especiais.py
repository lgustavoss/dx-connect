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
    assert item["corpo"].startswith("[Contato] Maria Silva")
    assert "5511987654321" in item["corpo"]


def test_inbound_contacto_waid_item_tel():
    body = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "c2"},
            "message": {
                "contactMessage": {
                    "displayName": "Cristina Ciabotti",
                    "vcard": (
                        "BEGIN:VCARD\nVERSION:3.0\nFN:Cristina Ciabotti\n"
                        "item1.TEL;waid=5511987654321:+55 11 98765-4321\n"
                        "item1.X-ABLabel:Celular\nEND:VCARD"
                    ),
                }
            },
        },
    }
    item = _one(body)
    assert item["corpo"] == "[Contato] Cristina Ciabotti — 5511987654321"


def test_inbound_contactos_array():
    body = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "c3"},
            "message": {
                "contactsArrayMessage": {
                    "contacts": [
                        {
                            "displayName": "Ana",
                            "vcard": "BEGIN:VCARD\nFN:Ana\nTEL:+5511977776666\nEND:VCARD",
                        }
                    ]
                }
            },
        },
    }
    item = _one(body)
    assert "Ana" in item["corpo"]
    assert "5511977776666" in item["corpo"]


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


def test_inbound_documento_com_file_name():
    body = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "doc1"},
            "message": {
                "documentMessage": {
                    "fileName": "SPED_Fiscal_2026.txt",
                    "mimetype": "text/plain",
                    "caption": "Segue SPED",
                }
            },
        },
    }
    item = _one(body)
    assert item["tipo"] == "documento"
    assert item["file_name"] == "SPED_Fiscal_2026.txt"
    assert item["corpo"] == "Segue SPED"
    assert item["mimetype"] == "text/plain"


def test_inbound_documento_sanitiza_path_no_file_name():
    body = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "doc2"},
            "message": {
                "documentMessage": {
                    "fileName": "../../etc/passwd.pdf",
                    "mimetype": "application/pdf",
                }
            },
        },
    }
    item = _one(body)
    assert item["file_name"] == "passwd.pdf"


def test_inbound_resolve_lid_via_sender_pn():
    body = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "11122233344455@lid",
                "fromMe": False,
                "id": "lid1",
                "senderPn": "5511987654321@s.whatsapp.net",
            },
            "message": {"conversation": "oi"},
        },
    }
    item = _one(body)
    assert item["wa_id"] == "5511987654321"
    assert item["corpo"] == "oi"


def test_inbound_resolve_lid_via_remote_jid_alt():
    body = {
        "event": "messages.upsert",
        "data": {
            "messages": [
                {
                    "key": {
                        "remoteJid": "99988877766655@lid",
                        "remoteJidAlt": "5511888777666@s.whatsapp.net",
                        "fromMe": False,
                        "id": "lid2",
                    },
                    "message": {"conversation": "alt"},
                }
            ]
        },
    }
    item = _one(body)
    assert item["wa_id"] == "5511888777666"