from __future__ import annotations

from app.services.evolution_inbound import quoted_reply_from_envelope


def test_quoted_reply_envelope_evolution():
    envelope = {
        "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "r1"},
        "message": {"conversation": "Resposta"},
        "contextInfo": {
            "stanzaId": "orig-1",
            "quotedMessage": {"conversation": "Original"},
        },
    }
    wid, prev = quoted_reply_from_envelope(envelope, envelope["message"])
    assert wid == "orig-1"
    assert prev == "Original"


def test_quoted_reply_envelope_baileys_aninhado():
    inner = {
        "extendedTextMessage": {
            "text": "Resposta",
            "contextInfo": {
                "stanzaId": "orig-2",
                "quotedMessage": {"conversation": "Legado"},
            },
        }
    }
    envelope = {"message": inner}
    wid, prev = quoted_reply_from_envelope(envelope, inner)
    assert wid == "orig-2"
    assert prev == "Legado"
