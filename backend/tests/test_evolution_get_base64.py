from __future__ import annotations

import json

from app.services import evolution_api


def test_payloads_get_base64_inclui_envelope_e_key_minima():
    envelope = {
        "key": {
            "remoteJid": "5511999999999@s.whatsapp.net",
            "fromMe": False,
            "id": "MSG-IMG-1",
        },
        "message": {"imageMessage": {"mimetype": "image/jpeg"}},
    }
    payloads = evolution_api._payloads_get_base64_from_envelope(envelope)
    assert payloads[0] is envelope
    assert {"key": {"id": "MSG-IMG-1"}} in payloads
    assert any(p.get("key", {}).get("remoteJid") for p in payloads)


def test_get_base64_tenta_fallback_quando_envelope_completo_falha(monkeypatch):
    envelope = {
        "key": {"id": "MID-2", "remoteJid": "5511888777666@s.whatsapp.net", "fromMe": False},
        "message": {"audioMessage": {"mimetype": "audio/ogg"}},
    }
    calls: list[dict] = []

    def fake_request(method, url, *, headers, body=None, timeout=20):
        calls.append(body or {})
        key = (body or {}).get("message", {}).get("key", {})
        if key == {"id": "MID-2"}:
            return 200, {"base64": "ZGF0YQ=="}, None
        return 400, None, '{"message":["Message not found"]}'

    monkeypatch.setattr(evolution_api, "_request_json_with_retry", fake_request)
    monkeypatch.setattr(evolution_api.time, "sleep", lambda _s: None)

    ok, b64, err = evolution_api.evolution_get_base64_from_media_message(
        "http://evo.test",
        "inst",
        "key",
        envelope,
    )
    assert ok is True
    assert b64 == "ZGF0YQ=="
    assert err is None
    assert len(calls) >= 2
    assert json.dumps({"message": {"key": {"id": "MID-2"}}, "convertToMp4": False}, sort_keys=True) in {
        json.dumps(c, sort_keys=True) for c in calls
    }
