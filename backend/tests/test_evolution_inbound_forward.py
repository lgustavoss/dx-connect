from __future__ import annotations

from app.services.evolution_inbound import (
    forward_info_from_envelope,
    quoted_reply_from_envelope,
)


def test_forward_envelope_evolution():
    envelope = {
        "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "f1"},
        "message": {"conversation": "Olá"},
        "contextInfo": {
            "isForwarded": True,
            "forwardingScore": 3,
        },
    }
    fwd, score = forward_info_from_envelope(envelope, envelope["message"])
    assert fwd is True
    assert score == 3


def test_forward_baileys_aninhado():
    inner = {
        "extendedTextMessage": {
            "text": "Encaminhada",
            "contextInfo": {
                "isForwarded": True,
                "forwardingScore": 127,
            },
        }
    }
    envelope = {"message": inner}
    fwd, score = forward_info_from_envelope(envelope, inner)
    assert fwd is True
    assert score == 127


def test_forward_score_sem_flag_ainda_marca():
    envelope = {
        "message": {"conversation": "x"},
        "contextInfo": {"forwardingScore": 2},
    }
    fwd, score = forward_info_from_envelope(envelope, envelope["message"])
    assert fwd is True
    assert score == 2


def test_forward_ausente():
    envelope = {
        "message": {"conversation": "normal"},
    }
    fwd, score = forward_info_from_envelope(envelope, envelope["message"])
    assert fwd is False
    assert score is None


def test_forward_e_citacao_juntos():
    envelope = {
        "message": {"conversation": "Resposta"},
        "contextInfo": {
            "stanzaId": "orig-9",
            "quotedMessage": {"conversation": "Original"},
            "isForwarded": True,
            "forwardingScore": 1,
        },
    }
    wid, prev = quoted_reply_from_envelope(envelope, envelope["message"])
    fwd, score = forward_info_from_envelope(envelope, envelope["message"])
    assert wid == "orig-9"
    assert prev == "Original"
    assert fwd is True
    assert score == 1
