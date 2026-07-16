"""Testes SSE — infraestrutura tempo real (#264)."""

from __future__ import annotations

import asyncio
import json

from app.core.security import criar_access_token
from app.services.realtime_hub import RealtimeHub, channel_atendente, format_sse


async def _short_stream(channel, *, initial_payload=None, disconnect_check=None, **_kwargs):
    """Generator finito para TestClient (evita conexão longa em testes)."""
    if initial_payload is not None:
        yield format_sse(initial_payload)


def test_events_stream_401_sem_token(client):
    r = client.get("/v1/events/stream")
    assert r.status_code == 401


def test_events_stream_conectado_com_bearer(client, seed_base, auth_headers, monkeypatch):
    monkeypatch.setattr("app.api.events.stream_channel_events", _short_stream)
    r = client.get("/v1/events/stream", headers=auth_headers["a1"])
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "connected" in r.text
    payload = json.loads(r.text.split("data: ", 1)[1].strip())
    assert payload["type"] == "connected"
    assert payload["payload"]["atendente_id"] == seed_base["a1"].id
    assert payload["payload"]["canal"] == channel_atendente(seed_base["a1"].id)


def test_events_stream_conectado_com_query_token(client, seed_base, monkeypatch):
    monkeypatch.setattr("app.api.events.stream_channel_events", _short_stream)
    token = criar_access_token({"sub": seed_base["a1"].email, "tid": 1})
    r = client.get(
        f"/v1/events/stream?token={token}",
        headers={"X-Dx-Tenant-Id": "1"},
    )
    assert r.status_code == 200
    assert "connected" in r.text


def test_hub_publish_subscribe():
    async def _run() -> None:
        hub = RealtimeHub()
        channel = channel_atendente(99)
        queue = await hub.subscribe(channel)
        await hub.publish(channel, "ticket.mensagem", {"ticket_id": 1})
        envelope = await asyncio.wait_for(queue.get(), timeout=1)
        assert envelope["type"] == "ticket.mensagem"
        assert envelope["payload"]["ticket_id"] == 1
        await hub.unsubscribe(channel, queue)

    asyncio.run(_run())


def test_format_sse():
    line = format_sse({"type": "ping", "payload": {}})
    assert line.startswith("event: message\n")
    assert "data: " in line
    assert line.endswith("\n\n")
